"""Parse an ADS query string back into an IntentSpec.

This is the inverse of the assembler: given a raw ADS query (e.g., from the LLM),
it extracts structured fields into an IntentSpec so that merge can happen at the
intent level rather than the string level.

The parser handles:
- author:"X" → authors
- abs:"X" → free_text_terms
- title:"X" → title_terms
- pubdate:[Y TO Z] → year_from, year_to
- bibstem:"X" → bibstems (validated against known bibstems)
- object:X → objects
- (inst:"X" OR aff:"X") / aff:"X" / inst:"X" → affiliations
- doctype:X → doctype (validated)
- property:X → property (validated)
- database:X / collection:X → collection (validated)
- bibgroup:X → bibgroup (validated)
- esources:X → esources (validated)
- data:X → data (validated)
- has:X → has_fields (validated)
- NOT abs:"X" → negated_terms
- NOT property:X → negated_properties
- NOT doctype:X → negated_doctypes
- grant:X → grant_terms
- ack:"X" → ack_terms
- citation_count:[N TO *] → citation_count_min/max
- read_count:[N TO *] → read_count_min
- full:"X" → full_text_terms
- =field:"value" → exact_match_fields
- citations(...), references(...), etc. → operator
- Anything else → passthrough_clauses
"""

import logging
import re

from .field_constraints import FIELD_ENUMS
from .intent_spec import OPERATORS, IntentSpec

logger = logging.getLogger(__name__)

# Bibstem synonyms (loaded lazily)
_KNOWN_BIBSTEMS: set[str] | None = None


def _get_known_bibstems() -> set[str]:
    """Lazily load known bibstem abbreviations."""
    global _KNOWN_BIBSTEMS
    if _KNOWN_BIBSTEMS is not None:
        return _KNOWN_BIBSTEMS
    try:
        import json
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[6]
            / "data"
            / "model"
            / "bibstem_synonyms.json"
        )
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            _KNOWN_BIBSTEMS = set()
            for entry in data.get("journals", []):
                bibstem = entry.get("bibstem", "")
                if bibstem:
                    _KNOWN_BIBSTEMS.add(bibstem)
        else:
            _KNOWN_BIBSTEMS = set()
    except Exception:
        _KNOWN_BIBSTEMS = set()
    return _KNOWN_BIBSTEMS


def _validate_enum(field: str, value: str) -> str | None:
    """Return canonical value if valid for field, else None."""
    valid = FIELD_ENUMS.get(field)
    if valid is None:
        return value  # No constraints
    for v in valid:
        if v.lower() == value.lower():
            return v
    return None


def _extract_quoted_value(query: str, pos: int) -> tuple[str, int]:
    """Extract a quoted value starting at pos (which should be a '"').

    Returns (value, end_pos) where end_pos is after the closing quote.
    """
    if pos >= len(query) or query[pos] != '"':
        return "", pos
    end = query.find('"', pos + 1)
    if end == -1:
        return query[pos + 1 :], len(query)
    return query[pos + 1 : end], end + 1


def _extract_paren_value(query: str, pos: int) -> tuple[str, int]:
    """Extract a parenthesized value starting at pos (which should be '(').

    Returns (inner_content, end_pos) where end_pos is after the closing paren.
    """
    if pos >= len(query) or query[pos] != "(":
        return "", pos
    depth = 1
    i = pos + 1
    while i < len(query) and depth > 0:
        if query[i] == "(":
            depth += 1
        elif query[i] == ")":
            depth -= 1
        i += 1
    return query[pos + 1 : i - 1], i


def _parse_or_list(inner: str) -> list[str]:
    """Parse 'val1 OR val2 OR val3' into a list of values."""
    parts = re.split(r"\s+OR\s+", inner, flags=re.IGNORECASE)
    return [p.strip().strip('"') for p in parts if p.strip()]


def _parse_field_value(query: str, pos: int) -> tuple[str | list[str], int]:
    """Parse the value after a field: prefix.

    Returns (value_or_list, end_pos).
    Value can be a string or list of strings (for OR lists).
    """
    if pos >= len(query):
        return "", pos

    ch = query[pos]

    if ch == '"':
        val, end = _extract_quoted_value(query, pos)
        return val, end

    if ch == "(":
        inner, end = _extract_paren_value(query, pos)
        # Check if it's an OR list
        if re.search(r"\s+OR\s+", inner, re.IGNORECASE):
            return _parse_or_list(inner), end
        # Single value in parens
        return inner.strip().strip('"'), end

    if ch == "[":
        # Range value like [2020 TO 2023]
        bracket_end = query.find("]", pos)
        if bracket_end == -1:
            return query[pos:], len(query)
        return query[pos : bracket_end + 1], bracket_end + 1

    # Bare value (until whitespace)
    match = re.match(r"[^\s)]+", query[pos:])
    if match:
        return match.group(0), pos + match.end()
    return "", pos


def _parse_range(range_str: str) -> tuple[str | None, str | None]:
    """Parse [X TO Y] range string into (from, to) values."""
    m = re.match(r"\[\s*(\S+)\s+TO\s+(\S+)\s*\]", range_str, re.IGNORECASE)
    if not m:
        return None, None
    lo = m.group(1) if m.group(1) != "*" else None
    hi = m.group(2) if m.group(2) != "*" else None
    return lo, hi


def _try_parse_year(val: str) -> int | None:
    """Try to extract a year from a value like '2020', '2020-01'."""
    m = re.match(r"(\d{4})", val)
    return int(m.group(1)) if m else None


def _is_now_range(range_str: str) -> bool:
    """Check if a range uses NOW- syntax."""
    return "NOW" in range_str.upper()


def parse_query_to_intent(query: str) -> IntentSpec:
    """Parse an ADS query string into a structured IntentSpec.

    This extracts field:value pairs from the query and maps them to
    IntentSpec fields. Unrecognized patterns are preserved as
    passthrough_clauses.

    Args:
        query: ADS query string (e.g., from LLM output)

    Returns:
        IntentSpec with extracted fields
    """
    if not query or not query.strip():
        return IntentSpec()

    intent = IntentSpec(raw_user_text=query)

    # Normalize whitespace
    q = query.strip()

    # Step 1: Extract top-level operator wrapping, if any
    # e.g., citations(abs:"dark matter" pubdate:[2020 TO 2023])
    op_match = re.match(
        r"^(citations|references|trending|useful|similar|reviews)\((.+)\)\s*$",
        q,
        re.IGNORECASE | re.DOTALL,
    )
    if op_match:
        op_name = op_match.group(1).lower()
        if op_name in OPERATORS:
            intent.operator = op_name
            q = op_match.group(2).strip()

    # Step 2: Extract (inst:"X" OR aff:"X") patterns before general parsing
    # These contain parens that would confuse the field parser
    inst_aff_pattern = re.compile(
        r'\(\s*inst:"([^"]+)"\s+OR\s+aff:"[^"]+"\s*\)', re.IGNORECASE
    )
    for m in inst_aff_pattern.finditer(q):
        intent.affiliations.append(m.group(1))
    q = inst_aff_pattern.sub(" ", q)

    # Step 3: Extract NOT clauses
    # NOT abs:"X", NOT property:X, NOT doctype:X
    # Also handle ADS "-" prefix syntax: -author:"X", -property:X, -aff:"X"
    not_pattern = re.compile(
        r"(?:\bNOT\s+|-)(abs|title|property|doctype|bibstem|author|aff|inst):", re.IGNORECASE
    )
    not_positions = [(m.start(), m.end(), m.group(1).lower()) for m in not_pattern.finditer(q)]
    # Process in reverse to preserve positions
    for start, field_end, field_name in reversed(not_positions):
        val, val_end = _parse_field_value(q, field_end)

        if field_name in ("abs", "title"):
            if isinstance(val, str):
                intent.negated_terms.append(val)
            elif isinstance(val, list):
                intent.negated_terms.extend(val)
        elif field_name == "property":
            if isinstance(val, str):
                canonical = _validate_enum("property", val)
                if canonical:
                    intent.negated_properties.add(canonical)
            elif isinstance(val, list):
                for v in val:
                    canonical = _validate_enum("property", v)
                    if canonical:
                        intent.negated_properties.add(canonical)
        elif field_name == "doctype":
            if isinstance(val, str):
                canonical = _validate_enum("doctype", val)
                if canonical:
                    intent.negated_doctypes.add(canonical)
            elif isinstance(val, list):
                for v in val:
                    canonical = _validate_enum("doctype", v)
                    if canonical:
                        intent.negated_doctypes.add(canonical)
        elif field_name == "author":
            # No dedicated negated_authors field; emit as passthrough with NOT syntax
            if isinstance(val, str):
                intent.passthrough_clauses.append(f'NOT author:"{val}"')
            elif isinstance(val, list):
                for v in val:
                    intent.passthrough_clauses.append(f'NOT author:"{v}"')
        else:
            # bibstem, aff, inst — no dedicated negated field; normalize to NOT syntax
            if isinstance(val, str):
                val_str = f'"{val}"' if '"' not in val else f'"{val}"'
                intent.passthrough_clauses.append(f"NOT {field_name}:{val_str}")
            elif isinstance(val, list):
                for v in val:
                    intent.passthrough_clauses.append(f'NOT {field_name}:"{v}"')

        q = q[:start] + " " + q[val_end:]

    # Step 4: Extract =field:"value" exact match patterns
    exact_match_pattern = re.compile(r'=(\w+):"([^"]+)"')
    for m in exact_match_pattern.finditer(q):
        intent.exact_match_fields[m.group(1)] = m.group(2)
    q = exact_match_pattern.sub(" ", q)

    # Step 5: Parse remaining field:value pairs
    # Build a regex that matches any field: prefix
    field_names = (
        "author", "abs", "title", "pubdate", "year", "bibstem", "object",
        "aff", "inst", "affil", "doctype", "property", "database",
        "collection", "bibgroup", "esources", "data", "has", "grant",
        "ack", "caption", "full", "body", "keyword", "orcid", "doi",
        "identifier", "arxiv_class", "arxiv", "bibcode", "citation_count",
        "read_count", "uat", "planetary_feature", "mention_count",
        "credit_count", "page_count", "author_count", "entdate",
    )
    field_pattern = re.compile(
        r"\b(" + "|".join(field_names) + r"):\s*", re.IGNORECASE
    )

    # Collect all field:value extractions
    remaining_parts = []
    last_end = 0

    for m in field_pattern.finditer(q):
        # Save text before this field
        before = q[last_end : m.start()].strip()
        if before:
            remaining_parts.append(before)

        field_name = m.group(1).lower()
        val, val_end = _parse_field_value(q, m.end())
        last_end = val_end

        _add_field_to_intent(intent, field_name, val)

    # Save any text after the last field
    after = q[last_end:].strip()
    if after:
        remaining_parts.append(after)

    # Step 6: Handle remaining text as passthrough
    for part in remaining_parts:
        part = part.strip()
        if not part:
            continue
        # Skip bare Boolean operators
        if part.upper() in ("AND", "OR", "NOT"):
            continue
        # If it looks like an unrecognized field or complex expression, passthrough
        if part and not re.match(r"^(AND|OR|NOT)$", part, re.IGNORECASE):
            intent.passthrough_clauses.append(part)

    return intent


def _parse_count_range(intent: IntentSpec, field_name: str, lo: str | None, hi: str | None) -> None:
    """Parse a count range [lo TO hi] into the appropriate IntentSpec min/max fields."""
    _COUNT_FIELD_MAP = {
        "citation_count": ("citation_count_min", "citation_count_max"),
        "read_count": ("read_count_min", None),
        "mention_count": ("mention_count_min", "mention_count_max"),
        "credit_count": ("credit_count_min", "credit_count_max"),
        "author_count": ("author_count_min", "author_count_max"),
        "page_count": ("page_count_min", "page_count_max"),
    }
    mapping = _COUNT_FIELD_MAP.get(field_name)
    if not mapping:
        return
    min_attr, max_attr = mapping
    if lo and min_attr:
        try:
            setattr(intent, min_attr, int(lo))
        except ValueError:
            pass
    if hi and max_attr:
        try:
            setattr(intent, max_attr, int(hi))
        except ValueError:
            pass


def _add_field_to_intent(intent: IntentSpec, field_name: str, val: str | list[str]) -> None:
    """Add a parsed field:value to the appropriate IntentSpec field."""

    def _as_list(v: str | list[str]) -> list[str]:
        return v if isinstance(v, list) else [v]

    def _as_str(v: str | list[str]) -> str:
        return v if isinstance(v, str) else " ".join(v)

    if field_name == "author":
        for v in _as_list(val):
            # Strip leading ^ for first author but preserve it
            intent.authors.append(v)

    elif field_name == "abs":
        vals = _as_list(val)
        # If the parse returned a list from an OR pattern, these should be OR'd
        if isinstance(val, list) and len(val) > 1:
            intent.or_terms.extend(vals)
        else:
            for v in vals:
                # Handle abs:(word1 AND word2) that was parsed as a single string
                if " AND " in v:
                    words = re.split(r"\s+AND\s+", v, flags=re.IGNORECASE)
                    phrase = " ".join(w.strip().strip('"') for w in words)
                    intent.free_text_terms.append(phrase)
                else:
                    intent.free_text_terms.append(v)

    elif field_name == "title":
        for v in _as_list(val):
            intent.title_terms.append(v)

    elif field_name in ("pubdate", "year"):
        val_str = _as_str(val)
        if val_str.startswith("["):
            if _is_now_range(val_str):
                # Preserve NOW- ranges as passthrough
                intent.passthrough_clauses.append(f"{field_name}:{val_str}")
            else:
                lo, hi = _parse_range(val_str)
                if lo:
                    y = _try_parse_year(lo)
                    if y:
                        intent.year_from = y
                if hi:
                    y = _try_parse_year(hi)
                    if y:
                        intent.year_to = y
        else:
            # Check for dash-separated range like "2014-2023"
            dash_match = re.match(r'^(\d{4})-(\d{4})$', val_str)
            if dash_match:
                y_from = _try_parse_year(dash_match.group(1))
                y_to = _try_parse_year(dash_match.group(2))
                if y_from:
                    intent.year_from = y_from
                if y_to:
                    intent.year_to = y_to
            else:
                y = _try_parse_year(val_str)
                if y:
                    intent.year_from = y
                    intent.year_to = y

    elif field_name == "entdate":
        val_str = _as_str(val)
        if val_str.startswith("["):
            intent.entdate_range = val_str
        else:
            intent.passthrough_clauses.append(f"entdate:{val_str}")

    elif field_name == "bibstem":
        for v in _as_list(val):
            intent.bibstems.append(v)

    elif field_name == "object":
        for v in _as_list(val):
            intent.objects.append(v)

    elif field_name == "planetary_feature":
        for v in _as_list(val):
            intent.planetary_features.append(v)

    elif field_name in ("aff", "inst", "affil"):
        for v in _as_list(val):
            if v not in intent.affiliations:
                intent.affiliations.append(v)

    elif field_name == "doctype":
        for v in _as_list(val):
            canonical = _validate_enum("doctype", v)
            if canonical:
                intent.doctype.add(canonical)

    elif field_name == "property":
        for v in _as_list(val):
            canonical = _validate_enum("property", v)
            if canonical:
                intent.property.add(canonical)

    elif field_name in ("database", "collection"):
        for v in _as_list(val):
            canonical = _validate_enum("database", v)
            if canonical:
                intent.collection.add(canonical)

    elif field_name == "bibgroup":
        for v in _as_list(val):
            canonical = _validate_enum("bibgroup", v)
            if canonical:
                intent.bibgroup.add(canonical)

    elif field_name == "esources":
        for v in _as_list(val):
            canonical = _validate_enum("esources", v)
            if canonical:
                intent.esources.add(canonical)

    elif field_name == "data":
        for v in _as_list(val):
            canonical = _validate_enum("data", v)
            if canonical:
                intent.data.add(canonical)

    elif field_name == "has":
        for v in _as_list(val):
            canonical = _validate_enum("has", v)
            if canonical:
                intent.has_fields.add(canonical)

    elif field_name == "grant":
        for v in _as_list(val):
            intent.grant_terms.append(v)

    elif field_name == "ack":
        for v in _as_list(val):
            intent.ack_terms.append(v)

    elif field_name in ("full", "body"):
        for v in _as_list(val):
            intent.full_text_terms.append(v)

    elif field_name == "keyword":
        for v in _as_list(val):
            intent.keyword_terms.append(v)

    elif field_name == "orcid":
        for v in _as_list(val):
            intent.orcid_ids.append(v)

    elif field_name == "identifier":
        for v in _as_list(val):
            intent.identifiers.append(v)

    elif field_name == "doi":
        for v in _as_list(val):
            intent.identifiers.append(f"doi:{v}")

    elif field_name == "arxiv":
        val_str = _as_str(val)
        intent.identifiers.append(f"arxiv:{val_str}")

    elif field_name == "arxiv_class":
        for v in _as_list(val):
            intent.arxiv_classes.append(v)

    elif field_name == "bibcode":
        for v in _as_list(val):
            intent.identifiers.append(f"bibcode:{v}")

    elif field_name in ("citation_count", "read_count", "mention_count",
                         "credit_count", "page_count", "author_count"):
        val_str = _as_str(val)
        if val_str.startswith("["):
            lo, hi = _parse_range(val_str)
            _parse_count_range(intent, field_name, lo, hi)
        else:
            intent.passthrough_clauses.append(f"{field_name}:{val_str}")

    else:
        # Unknown or complex field — passthrough
        val_str = _as_str(val)
        intent.passthrough_clauses.append(f"{field_name}:{val_str}")
