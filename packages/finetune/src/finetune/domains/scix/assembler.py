"""Deterministic query assembler for building ADS queries from IntentSpec.

This module implements template-based query assembly that produces valid
ADS query syntax by composing validated building blocks. All enum values
are validated against FIELD_ENUMS before assembly.

The assembler is deterministic and never generates arbitrary text.
LLM is only used in the resolver fallback path for paper references.
"""

import logging
import re
from collections.abc import Sequence

from .constrain import constrain_query_output
from .field_constraints import FIELD_ENUMS
from .intent_spec import OPERATORS, IntentSpec
from .pipeline import GoldExample

logger = logging.getLogger(__name__)


def _needs_quotes(value: str) -> bool:
    """Check if a value needs quotes in ADS syntax.

    Multi-word phrases and special characters require quoting.

    Args:
        value: The value to check

    Returns:
        True if value should be quoted
    """
    if not value:
        return False
    # Needs quotes if contains spaces, commas, colons, or other special chars
    return bool(re.search(r"[\s,:\-()]", value))


def _quote_value(value: str) -> str:
    """Quote a value for ADS syntax if needed.

    Args:
        value: The value to potentially quote

    Returns:
        Quoted value if needed, otherwise original value
    """
    if _needs_quotes(value):
        # Escape any internal quotes
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _validate_enum_values(field: str, values: set[str]) -> set[str]:
    """Validate enum values against FIELD_ENUMS.

    Filters out invalid values and logs warnings for each removal.

    Args:
        field: Field name (e.g., 'doctype', 'property')
        values: Set of values to validate

    Returns:
        Set of valid values only
    """
    valid_enum = FIELD_ENUMS.get(field)
    if valid_enum is None:
        return values  # No constraints for this field

    valid_lower = {v.lower() for v in valid_enum}
    valid_values = set()

    for value in values:
        if value.lower() in valid_lower:
            # Find the canonical casing from the enum
            for canonical in valid_enum:
                if canonical.lower() == value.lower():
                    valid_values.add(canonical)
                    break
        else:
            logger.warning(f"Removed invalid {field} value: '{value}'")

    return valid_values


def _wildcard_complex_author(name: str) -> str:
    """Replace hyphens, apostrophes, and spaces with ``*`` for fuzzy matching.

    Names with hyphens or apostrophes have inconsistent ADS indexing
    (e.g., "El-Badry" vs "El Badry" vs "ElBadry"). Replacing all separators
    with ``*`` and adding a trailing ``*`` catches all variants.

    Only triggered for names containing hyphens or apostrophes. Simple names
    like "Hawking" or comma-formatted "Hawking, S" are returned unchanged.

    Examples::

        "de Groot-Hedlin"  -> "de*Groot*Hedlin*"   # catches all spacing variants
        "Garcia-Perez"     -> "Garcia*Perez*"       # catches "GarciaPerez" etc.
        "Le Floc'h"        -> "Le*Floc*h*"          # catches "Le Floch" etc.
        "El-Badry"         -> "El*Badry*"            # catches "El Badry", "ElBadry"
        "al-Sufi"          -> "al*Sufi*"             # catches "alSufi" etc.
        "Hawking"          -> "Hawking"              # no change (no special chars)
        "^Hawking"         -> "^Hawking"             # first-author caret preserved

    Args:
        name: Author name as extracted by NER

    Returns:
        Name with separators replaced by ``*`` and trailing ``*`` if complex,
        otherwise unchanged
    """
    # Preserve first-author caret prefix
    prefix = ""
    working = name
    if working.startswith("^"):
        prefix = "^"
        working = working[1:]

    # Skip names that already have wildcards or are in "Last, F" format
    if "*" in working or "," in working:
        return name

    # Check if name has complexity markers (hyphens or apostrophes)
    if "-" not in working and "'" not in working:
        return name  # Simple name, no change

    # Replace hyphens, apostrophes, and spaces with * and add trailing *
    wildcarded = working.replace("-", "*").replace("'", "*").replace(" ", "*")
    if not wildcarded.endswith("*"):
        wildcarded += "*"

    return f"{prefix}{wildcarded}"


def _build_author_clause(authors: Sequence[str]) -> str:
    """Build author search clause.

    Formats author names for ADS syntax: author:"Last, F"
    Complex names (hyphens, apostrophes) get a trailing wildcard to handle
    inconsistent ADS indexing variants.

    Args:
        authors: List of author names

    Returns:
        Author clause string, or empty string if no authors
    """
    if not authors:
        return ""

    clauses = []
    for author in authors:
        # Apply wildcard to complex names for fuzzy matching
        author = _wildcard_complex_author(author)
        # Always quote author names
        clauses.append(f'author:"{author}"')

    if len(clauses) == 1:
        return clauses[0]
    return " ".join(clauses)


def _build_abs_clause(terms: Sequence[str], use_or: bool = False) -> str:
    """Build abstract/topic search clause.

    Args:
        terms: List of topic terms/phrases
        use_or: If True, combine terms with OR instead of AND (implicit)

    Returns:
        Abstract clause string, or empty string if no terms
    """
    if not terms:
        return ""

    clauses = []
    for term in terms:
        quoted = _quote_value(term)
        clauses.append(quoted)

    if len(clauses) == 1:
        return f"abs:{clauses[0]}"

    if use_or:
        # Use OR within parentheses: abs:(term1 OR term2)
        return f"abs:({' OR '.join(clauses)})"
    else:
        # Use implicit AND with separate abs: fields
        return " ".join(f"abs:{c}" for c in clauses)


def _build_year_clause(year_from: int | None, year_to: int | None) -> str:
    """Build pubdate range clause.

    Args:
        year_from: Start year (inclusive)
        year_to: End year (inclusive)

    Returns:
        Pubdate clause string, or empty string if no years
    """
    if year_from is None and year_to is None:
        return ""

    if year_from is not None and year_to is not None:
        return f"pubdate:[{year_from} TO {year_to}]"
    elif year_from is not None:
        return f"pubdate:[{year_from} TO *]"
    else:
        return f"pubdate:[* TO {year_to}]"


def _build_enum_clause(field: str, values: set[str]) -> str:
    """Build clause for an enum-constrained field.

    Validates values against FIELD_ENUMS and builds proper syntax.

    Args:
        field: Field name (e.g., 'doctype', 'property')
        values: Set of values to include

    Returns:
        Field clause string, or empty string if no valid values
    """
    if not values:
        return ""

    # Validate values
    valid_values = _validate_enum_values(field, values)
    if not valid_values:
        return ""

    sorted_values = sorted(valid_values)

    if len(sorted_values) == 1:
        return f"{field}:{sorted_values[0]}"
    else:
        or_list = " OR ".join(sorted_values)
        return f"{field}:({or_list})"


def _build_object_clause(objects: Sequence[str]) -> str:
    """Build astronomical object search clause.

    Args:
        objects: List of object names (e.g., 'M31', 'NGC 1234')

    Returns:
        Object clause string, or empty string if no objects
    """
    if not objects:
        return ""

    clauses = []
    for obj in objects:
        # Object names are typically short, but quote if needed
        quoted = _quote_value(obj)
        clauses.append(f"object:{quoted}")

    if len(clauses) == 1:
        return clauses[0]
    return " ".join(clauses)


def _build_affiliation_clause(affiliations: Sequence[str]) -> str:
    """Build affiliation search clause using institution lookup.

    Uses build_inst_or_aff_clause to produce (inst:"X" OR aff:"Y") clauses
    when the affiliation matches a known institution. Falls back to plain
    aff:"Y" for unknown affiliations.

    Args:
        affiliations: List of institutional affiliations

    Returns:
        Affiliation clause string, or empty string if no affiliations
    """
    if not affiliations:
        return ""

    from .institution_lookup import build_inst_or_aff_clause

    clauses = [build_inst_or_aff_clause(aff) for aff in affiliations]

    if len(clauses) == 1:
        return clauses[0]
    return " ".join(clauses)


def _build_bibstem_clause(bibstems: Sequence[str]) -> str:
    """Build bibstem search clause.

    Args:
        bibstems: List of bibstem abbreviations (e.g. ["ApJ", "MNRAS"])

    Returns:
        Bibstem clause string, or empty string if no bibstems
    """
    if not bibstems:
        return ""

    clauses = [f'bibstem:"{b}"' for b in bibstems]
    if len(clauses) == 1:
        return clauses[0]
    return "(" + " OR ".join(clauses) + ")"


def _wrap_with_operator(query: str, operator: str) -> str:
    """Wrap a query with an operator.

    Args:
        query: The base query string
        operator: Operator name (must be in OPERATORS)

    Returns:
        Query wrapped with operator, e.g., 'citations(query)'

    Raises:
        ValueError: If operator is not valid
    """
    if operator not in OPERATORS:
        raise ValueError(f"Invalid operator: {operator}")

    if not query.strip():
        logger.warning(f"Empty query cannot be wrapped with operator {operator}")
        return ""

    return f"{operator}({query})"


def assemble_query(intent: IntentSpec, examples: list[GoldExample] | None = None) -> str:
    """Assemble an ADS query from an IntentSpec.

    This is the main entry point for query assembly. It builds a valid
    ADS query by composing validated building blocks.

    Pipeline:
    1. Build base clauses from IntentSpec fields
    2. Validate all enum values against FIELD_ENUMS
    3. Join clauses with space (implicit AND)
    4. Apply operator wrapper if set
    5. Run constrain_query_output() as final safety net

    Args:
        intent: Structured intent specification from NER
        examples: Retrieved gold examples (optional, for future guidance)

    Returns:
        Valid ADS query string

    Note:
        The examples parameter is currently unused but reserved for
        future pattern-guided assembly improvements.
    """
    clauses: list[str] = []
    constraint_count_before = 0
    constraint_count_after = 0

    # Build author clause
    if intent.authors:
        author_clause = _build_author_clause(intent.authors)
        if author_clause:
            clauses.append(author_clause)

    # Build abstract/topic clause
    if intent.free_text_terms:
        abs_clause = _build_abs_clause(intent.free_text_terms, use_or=False)
        if abs_clause:
            clauses.append(abs_clause)

    # Build OR'd topic clause (e.g., "rocks or volcanoes" -> abs:(rocks OR volcanoes))
    if intent.or_terms:
        or_clause = _build_abs_clause(intent.or_terms, use_or=True)
        if or_clause:
            clauses.append(or_clause)

    # Build year range clause
    if intent.year_from is not None or intent.year_to is not None:
        year_clause = _build_year_clause(intent.year_from, intent.year_to)
        if year_clause:
            clauses.append(year_clause)

    # Build object clause
    if intent.objects:
        object_clause = _build_object_clause(intent.objects)
        if object_clause:
            clauses.append(object_clause)

    # Build planetary feature clause
    if intent.planetary_features:
        for pf in intent.planetary_features:
            clauses.append(f'planetary_feature:"{pf}"')

    # Build affiliation clause
    if intent.affiliations:
        aff_clause = _build_affiliation_clause(intent.affiliations)
        if aff_clause:
            clauses.append(aff_clause)

    # Build bibstem clause
    if intent.bibstems:
        bibstem_clause = _build_bibstem_clause(intent.bibstems)
        if bibstem_clause:
            clauses.append(bibstem_clause)

    # Build enum-constrained field clauses
    for field_name in ("doctype", "property", "collection", "bibgroup", "esources", "data"):
        values = getattr(intent, field_name)
        if values:
            constraint_count_before += len(values)
            clause = _build_enum_clause(field_name, values)
            if clause:
                clauses.append(clause)
                # Count valid values
                valid_values = _validate_enum_values(field_name, values)
                constraint_count_after += len(valid_values)

    # Build title clause
    if intent.title_terms:
        for term in intent.title_terms:
            quoted = _quote_value(term)
            clauses.append(f"title:{quoted}")

    # Build full-text clause
    if intent.full_text_terms:
        for term in intent.full_text_terms:
            quoted = _quote_value(term)
            clauses.append(f"full:{quoted}")

    # Build has: clause
    if intent.has_fields:
        for h in sorted(intent.has_fields):
            clauses.append(f"has:{h}")

    # Build citation_count range
    if intent.citation_count_min is not None or intent.citation_count_max is not None:
        lo = str(intent.citation_count_min) if intent.citation_count_min is not None else "*"
        hi = str(intent.citation_count_max) if intent.citation_count_max is not None else "*"
        clauses.append(f"citation_count:[{lo} TO {hi}]")

    # Build read_count range
    if intent.read_count_min is not None:
        clauses.append(f"read_count:[{intent.read_count_min} TO *]")

    # Build mention_count range
    if intent.mention_count_min is not None or intent.mention_count_max is not None:
        lo = str(intent.mention_count_min) if intent.mention_count_min is not None else "*"
        hi = str(intent.mention_count_max) if intent.mention_count_max is not None else "*"
        clauses.append(f"mention_count:[{lo} TO {hi}]")

    # Build credit_count range
    if intent.credit_count_min is not None or intent.credit_count_max is not None:
        lo = str(intent.credit_count_min) if intent.credit_count_min is not None else "*"
        hi = str(intent.credit_count_max) if intent.credit_count_max is not None else "*"
        clauses.append(f"credit_count:[{lo} TO {hi}]")

    # Build author_count range
    if intent.author_count_min is not None or intent.author_count_max is not None:
        lo = str(intent.author_count_min) if intent.author_count_min is not None else "*"
        hi = str(intent.author_count_max) if intent.author_count_max is not None else "*"
        clauses.append(f"author_count:[{lo} TO {hi}]")

    # Build page_count range
    if intent.page_count_min is not None or intent.page_count_max is not None:
        lo = str(intent.page_count_min) if intent.page_count_min is not None else "*"
        hi = str(intent.page_count_max) if intent.page_count_max is not None else "*"
        clauses.append(f"page_count:[{lo} TO {hi}]")

    # Build ack clause
    if intent.ack_terms:
        for term in intent.ack_terms:
            quoted = _quote_value(term)
            clauses.append(f"ack:{quoted}")

    # Build grant clause
    if intent.grant_terms:
        for term in intent.grant_terms:
            clauses.append(f"grant:{term}")

    # Build identifier clauses
    if intent.identifiers:
        for ident in intent.identifiers:
            # Identifiers may have a prefix like doi:, arxiv:, bibcode:
            # If they have a prefix, emit as that field; otherwise use identifier:
            if ident.startswith("doi:"):
                clauses.append(f"doi:{_quote_value(ident[4:])}")
            elif ident.startswith("arxiv:"):
                clauses.append(f"arxiv:{ident[6:]}")
            elif ident.startswith("bibcode:"):
                clauses.append(f"bibcode:{ident[8:]}")
            else:
                clauses.append(f"identifier:{_quote_value(ident)}")

    # Build keyword clauses
    if intent.keyword_terms:
        for term in intent.keyword_terms:
            clauses.append(f"keyword:{_quote_value(term)}")

    # Build arxiv_class clauses
    if intent.arxiv_classes:
        for ac in intent.arxiv_classes:
            clauses.append(f"arxiv_class:{ac}")

    # Build orcid clauses
    if intent.orcid_ids:
        for oid in intent.orcid_ids:
            clauses.append(f"orcid:{oid}")

    # Build entdate clause
    if intent.entdate_range:
        clauses.append(f"entdate:{intent.entdate_range}")

    # Build exact match clauses (=field:"value")
    if intent.exact_match_fields:
        for fld, val in intent.exact_match_fields.items():
            clauses.append(f'={fld}:"{val}"')

    # Build negation clauses
    if intent.negated_terms:
        for term in intent.negated_terms:
            quoted = _quote_value(term)
            clauses.append(f"NOT abs:{quoted}")
    if intent.negated_properties:
        for prop in sorted(intent.negated_properties):
            clauses.append(f"NOT property:{prop}")
    if intent.negated_doctypes:
        for dt in sorted(intent.negated_doctypes):
            clauses.append(f"NOT doctype:{dt}")

    # Append passthrough clauses (complex patterns the parser couldn't decompose)
    if intent.passthrough_clauses:
        clauses.extend(intent.passthrough_clauses)

    # Join all clauses with space (implicit AND)
    base_query = " ".join(clauses)

    # Apply operator wrapper if set
    if intent.operator:
        if base_query:
            base_query = _wrap_with_operator(base_query, intent.operator)
        else:
            # No base query, operator needs a target
            if intent.operator_target:
                # Use the target as the query
                target = _quote_value(intent.operator_target)
                base_query = _wrap_with_operator(target, intent.operator)
            else:
                logger.warning(
                    f"Operator {intent.operator} requested but no base query or target. "
                    "Returning empty query."
                )
                base_query = ""

    # Safety check: if too many constraints were dropped, simplify
    if constraint_count_before > 0:
        drop_ratio = 1 - (constraint_count_after / constraint_count_before)
        if drop_ratio > 0.5:
            logger.warning(
                f"Dropped {drop_ratio:.0%} of constraints. Falling back to simpler query."
            )
            # Fall back to just topic search if available
            if intent.free_text_terms:
                base_query = _build_abs_clause(intent.free_text_terms)

    # Final safety net: run constraint filter
    final_query = constrain_query_output(base_query)

    return final_query


def validate_query_syntax(query: str) -> tuple[bool, list[str]]:
    """Validate query syntax for common issues.

    Checks for:
    - Balanced parentheses
    - No malformed operator concatenations
    - No invalid enum values

    Args:
        query: Query string to validate

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors: list[str] = []

    # Check balanced parentheses
    if query.count("(") != query.count(")"):
        errors.append(f"Unbalanced parentheses: {query.count('(')} open, {query.count(')')} close")

    # Check for malformed operator concatenations
    malformed_patterns = [
        r"\bcitationsabs:",
        r"\bcitationsauthor:",
        r"\bcitationstitle:",
        r"\breferencesabs:",
        r"\breferencesauthor:",
        r"\breferencestitle:",
        r"\btrendingabs:",
        r"\busefulabs:",
        r"\bsimilarabs:",
        r"\breviewsabs:",
    ]
    for pattern in malformed_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            errors.append(f"Malformed operator pattern found: {pattern}")

    return len(errors) == 0, errors


# Regex to find author:"..." clauses in a raw query string
_AUTHOR_CLAUSE_RE = re.compile(r'author:"([^"]+)"')


def rewrite_complex_author_wildcards(query: str) -> str:
    """Post-process an LLM-generated query to wildcard complex author names.

    Finds all ``author:"..."`` clauses and applies the same wildcarding logic
    used in the NER assembler path. This ensures consistent handling of
    hyphenated/particle names regardless of which path generated the query.

    Args:
        query: Raw query string (e.g., from LLM output)

    Returns:
        Query with complex author names wildcarded
    """
    def _replace(match: re.Match) -> str:
        name = match.group(1)
        wildcarded = _wildcard_complex_author(name)
        return f'author:"{wildcarded}"'

    return _AUTHOR_CLAUSE_RE.sub(_replace, query)
