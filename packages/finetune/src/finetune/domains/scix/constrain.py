"""Post-processing filter for model-generated ADS queries.

Cleans up model output by removing invalid field combinations and
enforcing field enumeration constraints. Logs warnings for removed fields.
"""

import logging
import re

from finetune.domains.scix.field_constraints import FIELD_ENUMS
from finetune.domains.scix.validate import VALID_FIELD_PREFIXES

logger = logging.getLogger(__name__)

# Operator names that may be malformed
OPERATORS = {"citations", "references", "trending", "useful", "similar", "reviews", "topn"}


def _fix_malformed_operators(query: str) -> str:
    """Fix malformed operator syntax like 'citationsauthor:' -> 'citations(author:...')'.

    Model sometimes concatenates operator name directly with field name instead of
    using parentheses. This reconstructs the correct syntax.

    Handles patterns like:
    - citationsauthor:"query" -> citations(author:"query")
    - trendingabs:exoplanet -> trending(abs:exoplanet)
    - usefulabs:"cosmology" -> useful(abs:"cosmology")
    """
    for op in OPERATORS:
        # Pattern: operator followed directly by field name + colon
        # Match: citations + author: -> citations(author:
        pattern = rf"\b{op}((?:author|abs|title|pubdate|bibstem|object|keyword|doctype|property|database|bibgroup|aff|full|identifier):)"

        def replace_op(match: re.Match) -> str:
            field_part = match.group(1)
            logger.warning(f"Fixed malformed operator: {op}{field_part} -> {op}({field_part}")
            return f"{op}({field_part}"

        query = re.sub(pattern, replace_op, query, flags=re.IGNORECASE)

    # Balance parentheses if the fix introduced unbalanced ones
    while query.count("(") > query.count(")"):
        # Add closing paren to last unclosed operator
        # Find the position of the last ( without a matching )
        last_unclosed = -1
        paren_count = 0
        for i, c in enumerate(query):
            if c == "(":
                paren_count += 1
                last_unclosed = i
            elif c == ")":
                paren_count -= 1

        if last_unclosed >= 0:
            # Insert ) at the end, before any trailing operators or whitespace
            query = query + ")"
        else:
            break

    return query


def _fix_first_author_caret(query: str) -> str:
    """Fix misplaced first-author caret.

    Common LLM errors:
    - ^author:"Last" -> author:"^Last"
    - author:^"Last" -> author:"^Last"
    """
    # ^author:"Last" -> author:"^Last"
    query = re.sub(
        r'\^author:\s*"([^"]+)"',
        r'author:"^\1"',
        query,
    )
    # author:^"Last" -> author:"^Last"
    query = re.sub(
        r'author:\s*\^"([^"]+)"',
        r'author:"^\1"',
        query,
    )
    return query


def _fix_backwards_year_range(query: str) -> str:
    """Fix backwards pubdate ranges: pubdate:[2025 TO 2020] -> pubdate:[2020 TO 2025]."""

    def swap_range(match: re.Match) -> str:
        start, end = match.group(1), match.group(2)
        try:
            s, e = int(start), int(end)
            if s > e:
                logger.warning(
                    f"Fixed backwards year range: [{start} TO {end}] -> [{end} TO {start}]"
                )
                return f"pubdate:[{end} TO {start}]"
        except ValueError:
            pass
        return match.group(0)

    return re.sub(
        r"pubdate:\[(\d{4})\s+TO\s+(\d{4})\]", swap_range, query, flags=re.IGNORECASE
    )


def _fix_unquoted_operator_values(query: str) -> str:
    """Quote unquoted multi-word values inside operators.

    citations(abs:dark matter) -> citations(abs:"dark matter")
    trending(abs:exoplanet atmospheres) -> trending(abs:"exoplanet atmospheres")
    """

    def quote_value(match: re.Match) -> str:
        field = match.group(1)
        value = match.group(2).strip()
        # Only quote if multi-word (single word is OK unquoted for some fields)
        if " " in value:
            logger.warning(f"Quoted unquoted value in operator: {field}{value}")
            return f'{field}"{value}")'
        return match.group(0)

    # Match field:unquoted_value) where value has spaces
    # This targets values inside operators (before closing paren)
    return re.sub(
        r"((?:abs|title|full|keyword|author|object):)([^\")(\n][^)\n]*?)\)",
        quote_value,
        query,
    )


# Common misspellings -> correct values
_ENUM_CORRECTIONS: dict[str, dict[str, str]] = {
    "doctype": {
        "preprint": "eprint",
        "journal": "article",
        "paper": "article",
        "research": "article",
        "publication": "article",
        "peer-reviewed": "article",
        "conference": "inproceedings",
        "thesis": "phdthesis",
        "review": "article",
    },
    "property": {
        "peer-reviewed": "refereed",
        "peer_reviewed": "refereed",
        "peerreviewed": "refereed",
        "reviewed": "refereed",
        "open_access": "openaccess",
        "open-access": "openaccess",
        "oa": "openaccess",
    },
    "database": {
        "astrophysics": "astronomy",
        "astro": "astronomy",
        "earth_science": "earthscience",
        "earth-science": "earthscience",
        "planetary": "earthscience",
    },
}


def _fix_common_enum_misspellings(query: str) -> str:
    """Replace common misspelled enum values with correct ones."""
    for field_name, corrections in _ENUM_CORRECTIONS.items():
        for wrong, right in corrections.items():
            # Match field:wrong (unquoted)
            pattern = rf"\b{field_name}:{re.escape(wrong)}\b"
            replacement = f"{field_name}:{right}"
            new_query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
            if new_query != query:
                logger.warning(
                    f"Fixed enum value: {field_name}:{wrong} -> {field_name}:{right}"
                )
                query = new_query
            # Match field:"wrong" (quoted)
            pattern_q = rf'{field_name}:"{re.escape(wrong)}"'
            replacement_q = f"{field_name}:{right}"
            new_query = re.sub(pattern_q, replacement_q, query, flags=re.IGNORECASE)
            if new_query != query:
                logger.warning(
                    f'Fixed enum value: {field_name}:"{wrong}" -> {field_name}:{right}'
                )
                query = new_query
    return query


# --- Data-driven misplaced field value redirect ---
# Build reverse index: value.lower() → (field_name, original_value)
# Priority order: first match wins (doctype > property > database > ...)
# "collection" omitted since it's an alias for "database" with identical values
_FIELD_PRIORITY = ["doctype", "property", "database", "bibgroup", "esources", "data", "has"]

_ENUM_REVERSE_INDEX: dict[str, tuple[str, str]] = {}
for _field in _FIELD_PRIORITY:
    if _field in FIELD_ENUMS:
        for _val in FIELD_ENUMS[_field]:
            _key = _val.lower()
            if _key not in _ENUM_REVERSE_INDEX:  # First field wins (priority)
                _ENUM_REVERSE_INDEX[_key] = (_field, _val)

# Common English words that are valid enum values BUT also legitimate abs:/title:
# search terms. These MUST NOT be redirected.
_COMMON_WORDS: frozenset[str] = frozenset({
    # Doctypes that are common English words / legitimate abstract topics
    "abstract", "article", "book", "catalog", "circular", "editorial",
    "talk", "software", "proceedings", "proposal", "obituary", "misc",
    # Properties that are common words
    "data", "presentation",
    # Collections — all are common topic words
    "astronomy", "physics", "general", "earthscience",
    # Telescope/mission names — valid abs: terms (abs:"Chandra" ≠ bibgroup:Chandra)
    "hst", "jwst", "chandra", "xmm", "galex", "tess", "k2",
    "spitzer", "kepler", "copernicus", "swift", "herschel",
    "iso", "gemini", "keck", "magellan", "subaru", "alma",
    "soho", "stereo", "rosat", "fuse", "iue", "euve",
    # Data/archive names that appear in abstracts
    "mast", "simbad", "vizier", "ned", "irsa", "esa", "eso",
    "heasarc", "pds", "cxo",
    # Institutional/program names
    "leiden", "seti", "cfa",
}) | frozenset(
    # All has: values safelisted — has:X means "paper has field X populated",
    # semantically different from searching for "X" in abstract text
    v.lower() for v in FIELD_ENUMS.get("has", ())
)

# User-friendly synonyms: natural terms that aren't exact enum values
# but unambiguously map to a specific field:value
_USER_SYNONYMS: dict[str, tuple[str, str]] = {
    "preprint": ("doctype", "eprint"),
    "preprints": ("doctype", "eprint"),
    "peer-reviewed": ("property", "refereed"),
    "peer reviewed": ("property", "refereed"),
    "open access": ("property", "openaccess"),
    "open-access": ("property", "openaccess"),
    "non-refereed": ("property", "nonarticle"),
}


def _fix_misplaced_field_values(query: str) -> str:
    """Redirect abs:/title: values that belong in enum-constrained fields.

    Uses a reverse index built from FIELD_ENUMS to automatically detect
    when an enum value is misplaced in abs: or title:. A common-words
    safelist prevents redirecting legitimate abstract search terms.

    Handles both positive and negated forms:
    - abs:"eprint" -> doctype:eprint
    - NOT abs:"preprint" -> NOT doctype:eprint
    - -abs:"nonarticle" -> -property:nonarticle
    """
    for field in ("abs", "title"):
        # Match quoted: abs:"value" or NOT abs:"value" or -abs:"value"
        for match in re.finditer(
            rf'((?:NOT\s+|-)?){field}:\s*"([^"]+)"', query, re.IGNORECASE
        ):
            prefix = match.group(1)  # "NOT " or "-" or ""
            value = match.group(2)
            value_lower = value.lower()

            # Check user synonyms first (preprint, peer-reviewed, etc.)
            if value_lower in _USER_SYNONYMS:
                target_field, target_val = _USER_SYNONYMS[value_lower]
                replacement = f"{prefix}{target_field}:{target_val}"
                query = query[:match.start()] + replacement + query[match.end():]
                logger.warning(f"Redirected: {match.group(0)} -> {replacement}")
                return _fix_misplaced_field_values(query)  # Re-scan

            # Check reverse index (exact enum values)
            if value_lower in _ENUM_REVERSE_INDEX and value_lower not in _COMMON_WORDS:
                target_field, target_val = _ENUM_REVERSE_INDEX[value_lower]
                replacement = f"{prefix}{target_field}:{target_val}"
                query = query[:match.start()] + replacement + query[match.end():]
                logger.warning(f"Redirected: {match.group(0)} -> {replacement}")
                return _fix_misplaced_field_values(query)  # Re-scan

        # Match unquoted: abs:value (single word only)
        for match in re.finditer(
            rf'((?:NOT\s+|-)?){field}:([^\s"()\[\]]+)', query, re.IGNORECASE
        ):
            prefix = match.group(1)
            value = match.group(2)
            value_lower = value.lower()

            if value_lower in _USER_SYNONYMS:
                target_field, target_val = _USER_SYNONYMS[value_lower]
                replacement = f"{prefix}{target_field}:{target_val}"
                query = query[:match.start()] + replacement + query[match.end():]
                logger.warning(f"Redirected: {match.group(0)} -> {replacement}")
                return _fix_misplaced_field_values(query)

            if value_lower in _ENUM_REVERSE_INDEX and value_lower not in _COMMON_WORDS:
                target_field, target_val = _ENUM_REVERSE_INDEX[value_lower]
                replacement = f"{prefix}{target_field}:{target_val}"
                query = query[:match.start()] + replacement + query[match.end():]
                logger.warning(f"Redirected: {match.group(0)} -> {replacement}")
                return _fix_misplaced_field_values(query)

    return query


def _fix_spaced_out_ranges(query: str) -> str:
    """Fix spaced-out characters in bracket ranges.

    LLM tokenization artifact where characters are output separated by spaces:
    [1 0 0 T O *] → [100 TO *]
    [2 0 2 0 T O 2 0 2 5] → [2020 TO 2025]
    """

    def fix_bracket(match: re.Match) -> str:
        inner = match.group(1)
        tokens = inner.split()

        # Only fix if most tokens are single characters (spaced-out indicator)
        single_char_count = sum(1 for t in tokens if len(t) == 1)
        if single_char_count < 3 or len(tokens) < 3:
            return match.group(0)

        # Collapse consecutive single chars of same type (digit/alpha)
        result: list[str] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if len(tok) == 1 and (tok.isdigit() or tok.isalpha()):
                group = tok
                is_digit = tok.isdigit()
                j = i + 1
                while j < len(tokens) and len(tokens[j]) == 1:
                    nxt = tokens[j]
                    if (is_digit and nxt.isdigit()) or (not is_digit and nxt.isalpha()):
                        group += nxt
                        j += 1
                    else:
                        break
                result.append(group)
                i = j
            else:
                result.append(tok)
                i += 1

        collapsed = " ".join(result)
        if collapsed != inner.strip():
            logger.warning(
                f"Fixed spaced-out range: [{inner.strip()}] -> [{collapsed}]"
            )
        return f"[{collapsed}]"

    return re.sub(r"\[([^\]]+)\]", fix_bracket, query)


def _fix_unbalanced_quotes(query: str) -> str:
    """Fix unbalanced quotation marks by adding a missing closing quote.

    Common LLM error: abs:"dark matter → abs:"dark matter"
    Only acts when an opening quote after a field: prefix is unclosed.
    """
    if query.count('"') % 2 == 0:
        return query

    # Walk to find the last unmatched opening quote
    in_quote = False
    last_open = -1
    for i, ch in enumerate(query):
        if ch == '"':
            if in_quote:
                in_quote = False
            else:
                in_quote = True
                last_open = i

    if not in_quote or last_open < 0:
        return query

    # Only fix if the unclosed quote follows a field: prefix
    before = query[:last_open]
    if not re.search(r"\w+:\s*$", before):
        return query  # Stray quote in unexpected position, leave alone

    # Add closing quote before next field: prefix or at end of string
    remaining = query[last_open + 1 :]
    field_match = re.search(r"\s+(?=[a-zA-Z_]+:)", remaining)
    if field_match:
        close_pos = last_open + 1 + field_match.start()
        query = query[:close_pos] + '"' + query[close_pos:]
    else:
        query = query.rstrip() + '"'
    logger.warning("Fixed unbalanced quotes: added missing closing quote")

    return query


def _strip_non_ads_syntax(query: str) -> str:
    """Remove syntax that is never valid in ADS queries.

    1. Curly braces {} — not part of ADS/Solr syntax (ranges use [], groups use ())
    2. Unknown field names — field:value where field is not in the Solr schema
    """
    if not query:
        return query

    # Strip balanced {...} blocks (JSON fragments)
    if '{' in query or '}' in query:
        result = []
        depth = 0
        for ch in query:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth = max(0, depth - 1)
            elif depth == 0:
                result.append(ch)
        cleaned = ''.join(result).strip()
        if cleaned != query.strip():
            logger.warning("Stripped curly-brace block from query")
        query = cleaned

    # Strip unknown field:value pairs
    unknown_field_pattern = re.compile(
        r'(?<![.\d])(\^?[a-z_]{2,}):"[^"]*"'        # field:"quoted value"
        r'|(?<![.\d])(\^?[a-z_]{2,}):(\([^)]*\))'    # field:(grouped)
        r'|(?<![.\d])(\^?[a-z_]{2,}):(\[[^\]]*\])'   # field:[range]
        r'|(?<![.\d])(\^?[a-z_]{2,}):([^\s()]+)',     # field:unquoted
        re.IGNORECASE,
    )

    def check_field(m):
        # Extract the field name from whichever group matched
        field = (m.group(1) or m.group(2) or m.group(4) or m.group(6) or '').lower()
        if field and field not in VALID_FIELD_PREFIXES:
            logger.warning(f"Stripped unknown field from query: {m.group(0)[:60]}")
            return ''
        return m.group(0)

    query = unknown_field_pattern.sub(check_field, query)

    # Strip bare [X TO Y] ranges not preceded by a field: prefix
    # (e.g., "[100 TO *]" free-floating is meaningless without citation_count: etc.)
    query = re.sub(
        r'(?<![:\w])\[[\w*]+\s+TO\s+[\w*]+\]',
        lambda m: (logger.warning(f"Stripped bare range without field prefix: {m.group(0)}") or ''),
        query,
    )

    # Clean up extra whitespace from removals
    query = re.sub(r'\s+', ' ', query).strip()
    return query


def constrain_query_output(query: str) -> str:
    """Clean up model-generated query by removing invalid field values.

    Applies structural repairs (caret placement, year ranges, operator quoting,
    enum misspellings) then removes field:value pairs where the value is not in
    FIELD_ENUMS. Preserves valid field combinations. Handles OR lists, quoted
    values, and parenthesized groups.

    Args:
        query: The raw model-generated query string

    Returns:
        Cleaned query with invalid field values removed

    Example:
        >>> constrain_query_output('doctype:preprint property:refereed')
        'doctype:eprint property:refereed'
        >>> constrain_query_output('doctype:(article OR journal) abs:exoplanets')
        'doctype:article abs:exoplanets'
    """
    if not query or not query.strip():
        return ""

    result = query.strip()

    # Phase 1: Structural repairs (order matters — low-level fixes first)
    result = _fix_spaced_out_ranges(result)
    result = _fix_unbalanced_quotes(result)
    result = _fix_malformed_operators(result)
    result = _fix_first_author_caret(result)
    result = _fix_backwards_year_range(result)
    result = _fix_unquoted_operator_values(result)
    result = _fix_misplaced_field_values(result)
    result = _fix_common_enum_misspellings(result)

    # Phase 1.5: Strip non-ADS syntax (curly braces, unknown fields)
    result = _strip_non_ads_syntax(result)

    # Phase 2: Enum constraint filtering
    for field_name, valid_values in FIELD_ENUMS.items():
        valid_lower = {v.lower() for v in valid_values}
        result = _filter_field(result, field_name, valid_lower)

    # Phase 3: Cleanup artifacts
    result = _cleanup_query(result)

    return result


def _filter_field(query: str, field_name: str, valid_lower: set[str]) -> str:
    """Filter out invalid values for a specific field.

    Handles:
    - field:value (unquoted)
    - field:"value" (quoted)
    - field:(val1 OR val2 OR val3) (OR list)
    """
    # Pattern for OR list: field:(val1 OR val2)
    or_pattern = rf"\b{field_name}:\s*\(([^)]+)\)"

    def process_or_list(match: re.Match[str]) -> str:
        inner = match.group(1)
        # Split on OR, preserving whitespace for reconstruction
        parts = re.split(r"\s+OR\s+", inner, flags=re.IGNORECASE)
        valid_parts = []
        for part in parts:
            # Strip quotes if present
            clean = part.strip().strip('"')
            if clean.lower() in valid_lower:
                valid_parts.append(part.strip())
            else:
                logger.warning(f"Removed invalid {field_name} value: '{clean}'")

        if not valid_parts:
            # All values invalid - remove entire field expression
            return ""
        elif len(valid_parts) == 1:
            # Single value - no parens needed
            return f"{field_name}:{valid_parts[0]}"
        else:
            return f"{field_name}:({' OR '.join(valid_parts)})"

    query = re.sub(or_pattern, process_or_list, query, flags=re.IGNORECASE)

    # Pattern for quoted value: field:"value"
    quoted_pattern = rf'\b{field_name}:\s*"([^"]*)"'

    def process_quoted(match: re.Match[str]) -> str:
        value = match.group(1)
        if value.lower() in valid_lower:
            return match.group(0)  # Keep as-is
        else:
            logger.warning(f"Removed invalid {field_name} value: '{value}'")
            return ""

    query = re.sub(quoted_pattern, process_quoted, query, flags=re.IGNORECASE)

    # Pattern for unquoted value: field:value
    # Must not match already-processed patterns (quotes, parens)
    unquoted_pattern = rf'\b{field_name}:([^\s()"]+)'

    def process_unquoted(match: re.Match[str]) -> str:
        value = match.group(1)
        if value.lower() in valid_lower:
            return match.group(0)  # Keep as-is
        else:
            logger.warning(f"Removed invalid {field_name} value: '{value}'")
            return ""

    query = re.sub(unquoted_pattern, process_unquoted, query, flags=re.IGNORECASE)

    return query


def _cleanup_query(query: str) -> str:
    """Clean up artifacts from field removal.

    Handles:
    - Trailing/leading operators (AND, OR, NOT)
    - Double operators (AND AND, OR OR)
    - Empty parentheses
    - Extra whitespace
    """
    # Remove empty parentheses (possibly with whitespace)
    query = re.sub(r"\(\s*\)", "", query)

    # Remove leading boolean operators
    query = re.sub(r"^\s*(AND|OR|NOT)\s+", "", query, flags=re.IGNORECASE)

    # Remove trailing boolean operators
    query = re.sub(r"\s+(AND|OR|NOT)\s*$", "", query, flags=re.IGNORECASE)

    # Remove double boolean operators (AND AND -> AND, OR OR -> OR)
    # Also handles AND OR, OR AND combinations
    while True:
        new_query = re.sub(
            r"\b(AND|OR|NOT)\s+(AND|OR)\b",
            r"\2",  # Keep the second operator
            query,
            flags=re.IGNORECASE,
        )
        if new_query == query:
            break
        query = new_query

    # Handle "field:value AND" at start becoming "AND" orphan
    query = re.sub(r"^\s*(AND|OR)\s+", "", query, flags=re.IGNORECASE)

    # Handle "AND field:value" at end becoming orphan "AND"
    query = re.sub(r"\s+(AND|OR|NOT)\s*$", "", query, flags=re.IGNORECASE)

    # Collapse multiple spaces into one
    query = re.sub(r"\s+", " ", query)

    # Remove whitespace inside parentheses edges: "( X )" → "(X)"
    query = re.sub(r"\(\s+", "(", query)
    query = re.sub(r"\s+\)", ")", query)

    # Remove parentheses that now contain only a single term (no operators)
    # e.g., "(article)" -> "article"
    # BUT preserve operator calls like citations(), trending(), similar(), etc.
    operator_names = r"(citations|references|trending|useful|similar|reviews|topn)"

    def unwrap_single_term(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        full_match = match.group(0)
        start_pos = match.start()

        # Check if this is preceded by an operator name (e.g., citations(), trending())
        # Look at what's before the opening paren in the original query
        prefix = query[:start_pos]
        if re.search(rf"{operator_names}$", prefix, re.IGNORECASE):
            # This is an operator call - preserve the parentheses
            return full_match

        # Check if inner contains no boolean operators (AND, OR, NOT)
        if not re.search(r"\b(AND|OR|NOT)\b", inner, re.IGNORECASE):
            return inner
        return full_match

    query = re.sub(r"\(([^()]+)\)", unwrap_single_term, query)

    # Fix malformed parentheses - remove unbalanced ones
    while True:
        open_count = query.count("(")
        close_count = query.count(")")
        if open_count == close_count:
            break

        if open_count > close_count:
            # Remove rightmost unmatched opening paren
            idx = query.rfind("(")
            query = query[:idx] + query[idx + 1 :]
        else:
            # Remove leftmost unmatched closing paren
            idx = query.find(")")
            query = query[:idx] + query[idx + 1 :]

    return query.strip()
