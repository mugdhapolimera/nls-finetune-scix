"""Intent-level merge module for combining NER and NLS query outputs.

Architecture: LLM for understanding, Assembler for syntax.

Instead of merging two query strings (brittle, needs heuristics), we:
1. Parse the LLM's raw query back into IntentSpec via parse_query
2. Merge the two IntentSpecs with per-field policies
3. Let the assembler produce the final clean query

This eliminates all string-level heuristics (dedup_bibgroup_and_aff,
remove_inst_from_abs, normalize_abs_and_clauses, strip_default_doctype, etc.)
because the assembler structurally prevents bad syntax.

Per-field merge policies:
- authors: prefer NER (better name formatting)
- free_text_terms: prefer LLM (understands context better)
- year_from/year_to: prefer NER if extracted, else LLM
- affiliations: prefer NER (validated against institution_synonyms)
- bibstems: prefer NER (validated against bibstem_synonyms)
- bibgroup: prefer NER, but keep LLM's if NER didn't extract
- doctype/property: union, but drop doctype:article if NL uses generic "papers"
- operator: prefer LLM (handles nested/complex operators)
- negation/has/citation_count/ack/grant: LLM only (NER can't detect)
- passthrough_clauses: LLM only
"""

import logging
import re
import time
from dataclasses import dataclass, field

from .assembler import assemble_query
from .intent_spec import IntentSpec
from .parse_query import parse_query_to_intent
from .pipeline import PipelineResult
from .validate import lint_query

logger = logging.getLogger(__name__)

# Institution abbreviations that also appear as bibgroups.
# When both bibgroup and affiliation match, the bibgroup is redundant.
_BIBGROUP_INSTITUTION_OVERLAP: set[str] = {
    "CfA", "ESO", "NOAO", "NOIRLab", "SETI",
}

# Institution abbreviations (loaded lazily)
_INST_ABBREVS: set[str] | None = None


def _get_inst_abbrevs() -> set[str]:
    """Lazily load institution abbreviations from institution_synonyms.json."""
    global _INST_ABBREVS
    if _INST_ABBREVS is not None:
        return _INST_ABBREVS
    try:
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[6] / "data" / "model" / "institution_synonyms.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            _INST_ABBREVS = set()
            for info in data.get("synonyms", {}).values():
                _INST_ABBREVS.add(info["inst_abbrev"].lower())
                for name in info["common_names"]:
                    _INST_ABBREVS.add(name.lower())
        else:
            _INST_ABBREVS = set()
    except Exception:
        _INST_ABBREVS = set()
    return _INST_ABBREVS


@dataclass
class MergeResult:
    """Result of merging NER and NLS outputs.

    Attributes:
        query: Final merged query
        source: "hybrid", "nls_only", "ner_only", "ner_preferred"
        nls_query: Raw NLS output (post-processed)
        ner_query: Raw NER output
        fields_injected: Fields added from NER
        confidence: Combined confidence
        timing: ner_ms, nls_ms, merge_ms, total_ms
    """

    query: str
    source: str  # "hybrid", "nls_only", "ner_only", "ner_preferred"
    nls_query: str
    ner_query: str
    fields_injected: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timing: dict = field(default_factory=dict)
    # Debug: intent traces for tracing merge decisions
    ner_intent: dict | None = None
    llm_intent: dict | None = None
    merged_intent: dict | None = None


def _strip_default_doctype(intent: IntentSpec, nl_text: str) -> None:
    """Remove doctype:article when the user said generic 'papers'/'publications'.

    Modifies the intent in-place.
    """
    if "article" not in intent.doctype:
        return

    nl_lower = nl_text.lower()

    # If the user explicitly requested a doctype, keep it
    _EXPLICIT_DOCTYPE_TERMS = {
        "journal article", "journal articles", "review article", "review articles",
        "thesis", "theses", "dissertation", "preprint", "preprints",
        "conference paper", "conference papers", "proceedings",
        "software", "book", "books", "monograph", "catalog", "circular",
        "eprint", "arxiv paper",
    }
    if any(term in nl_lower for term in _EXPLICIT_DOCTYPE_TERMS):
        return

    _GENERIC_TERMS = {"paper", "papers", "publication", "publications", "work", "studies", "study", "research"}
    has_generic = any(re.search(rf'\b{term}\b', nl_lower) for term in _GENERIC_TERMS)

    if has_generic:
        intent.doctype.discard("article")


def _remove_inst_from_free_text(intent: IntentSpec) -> None:
    """Remove institution names from free_text_terms when they appear in affiliations.

    At the intent level this is clean: if we have affiliations=["CfA"], then
    "cfa" in free_text_terms is a mistake.
    """
    if not intent.affiliations or not intent.free_text_terms:
        return

    inst_abbrevs = _get_inst_abbrevs()
    aff_lower = {a.lower() for a in intent.affiliations}
    combined = aff_lower | inst_abbrevs

    cleaned_terms = []
    for term in intent.free_text_terms:
        # Check if the entire term is an institution name
        if term.lower() in combined:
            logger.info(f"Removed institution '{term}' from free_text_terms")
            continue
        # Check if term contains institution name as a word and remove it
        words = term.split()
        if len(words) > 1:
            filtered = [w for w in words if w.lower() not in combined]
            if filtered and len(filtered) < len(words):
                cleaned = " ".join(filtered)
                logger.info(f"Removed institution from topic: '{term}' → '{cleaned}'")
                cleaned_terms.append(cleaned)
                continue
        cleaned_terms.append(term)

    intent.free_text_terms = cleaned_terms


def _dedup_bibgroup_and_aff(intent: IntentSpec) -> None:
    """Remove bibgroup when the same entity is also an affiliation.

    CfA, ESO, NOAO, NOIRLab, SETI appear as both bibgroups and institutions.
    When both are present, the intersection is too restrictive.
    """
    if not intent.bibgroup or not intent.affiliations:
        return

    aff_lower = {a.lower() for a in intent.affiliations}
    to_remove = set()
    for bg in intent.bibgroup:
        if bg in _BIBGROUP_INSTITUTION_OVERLAP and bg.lower() in aff_lower:
            to_remove.add(bg)
            logger.info(f"Removed redundant bibgroup:{bg} (already in affiliations)")

    intent.bibgroup -= to_remove


def _resolve_negation_conflicts(intent: IntentSpec) -> None:
    """Remove positive values that contradict negated values.

    NER cannot detect negation — it's pure regex pattern matching. When the user
    says "excluding conference proceedings", NER extracts doctype:inproceedings
    as a positive value. The LLM correctly puts it in negated_doctypes. Without
    this cleanup, the assembled query has both doctype:inproceedings AND NOT
    doctype:inproceedings, which cancels out to 0 results.

    This is a generic fix that handles ALL field types in one place, preventing
    whack-a-mole fixes every time a new negation pattern is encountered.

    Negation sources:
    1. Structured: negated_doctypes, negated_properties, negated_terms
    2. Passthrough: NOT field:"value" clauses (for fields without dedicated negation)
    """
    # --- Structured negation fields ---
    if intent.negated_doctypes:
        removed = intent.doctype & intent.negated_doctypes
        if removed:
            intent.doctype -= removed
            logger.info("Removed contradicted doctype(s): %s", removed)

    if intent.negated_properties:
        removed = intent.property & intent.negated_properties
        if removed:
            intent.property -= removed
            logger.info("Removed contradicted property(ies): %s", removed)

    if intent.negated_terms:
        negated_lower = {t.lower() for t in intent.negated_terms}
        original = intent.free_text_terms[:]
        intent.free_text_terms = [
            t for t in intent.free_text_terms if t.lower() not in negated_lower
        ]
        if len(intent.free_text_terms) < len(original):
            logger.info("Removed contradicted free_text_term(s)")

    # --- Passthrough NOT clauses (covers all remaining fields) ---
    if not intent.passthrough_clauses:
        return

    # Parse all NOT field:"value" from passthrough clauses
    negated_by_field: dict[str, set[str]] = {}
    not_pattern = re.compile(r'NOT\s+(\w+):"([^"]+)"', re.IGNORECASE)
    for clause in intent.passthrough_clauses:
        m = not_pattern.match(clause)
        if m:
            field = m.group(1).lower()
            value = m.group(2)
            negated_by_field.setdefault(field, set()).add(value.lower())

    if not negated_by_field:
        return

    # Map passthrough field names to IntentSpec list/set attributes
    _LIST_FIELDS = {
        "author": "authors",
        "aff": "affiliations",
        "inst": "affiliations",
        "bibstem": "bibstems",
        "object": "objects",
    }
    _SET_FIELDS = {
        "doctype": "doctype",
        "property": "property",
        "bibgroup": "bibgroup",
        "collection": "collection",
        "esources": "esources",
        "data": "data",
    }

    for neg_field, neg_values in negated_by_field.items():
        # Handle list fields (case-insensitive match)
        if neg_field in _LIST_FIELDS:
            attr = _LIST_FIELDS[neg_field]
            current = getattr(intent, attr)
            if current:
                filtered = [v for v in current if v.lower() not in neg_values]
                if len(filtered) < len(current):
                    setattr(intent, attr, filtered)
                    logger.info("Removed contradicted %s value(s) from %s", neg_field, attr)

        # Handle set fields (case-insensitive match)
        if neg_field in _SET_FIELDS:
            attr = _SET_FIELDS[neg_field]
            current = getattr(intent, attr)
            if current:
                to_remove = {v for v in current if v.lower() in neg_values}
                if to_remove:
                    setattr(intent, attr, current - to_remove)
                    logger.info("Removed contradicted %s value(s) from %s", neg_field, attr)


def merge_intents(
    ner: IntentSpec,
    llm: IntentSpec,
    nl_text: str,
) -> IntentSpec:
    """Merge two IntentSpecs with clear per-field precedence rules.

    Args:
        ner: IntentSpec from NER extraction
        llm: IntentSpec parsed from LLM's raw query output
        nl_text: Original natural language input

    Returns:
        Merged IntentSpec
    """
    merged = IntentSpec(raw_user_text=nl_text)

    # Authors: prefer NER (better name formatting via NER patterns)
    merged.authors = ner.authors if ner.authors else llm.authors

    # Free text: prefer LLM (understands context/intent better).
    # If LLM produced other fields (operator, citation_count, negation, etc.)
    # but left free_text_terms empty, trust that — don't backfill NER's residual
    # noise (NER dumps unrecognized text into free_text_terms as a catch-all).
    if llm.free_text_terms:
        merged.free_text_terms = llm.free_text_terms
    elif not llm.has_content():
        # LLM produced nothing at all — fall back to NER
        merged.free_text_terms = ner.free_text_terms
    # else: LLM has content in other fields but no free_text — intentionally empty
    merged.or_terms = llm.or_terms if llm.or_terms else ner.or_terms

    # Years: prefer NER if it extracted them
    merged.year_from = ner.year_from if ner.year_from is not None else llm.year_from
    merged.year_to = ner.year_to if ner.year_to is not None else llm.year_to

    # Affiliations: prefer NER (validated against institution_synonyms)
    merged.affiliations = ner.affiliations if ner.affiliations else llm.affiliations

    # Bibstems: prefer NER (validated against bibstem_synonyms)
    merged.bibstems = ner.bibstems if ner.bibstems else llm.bibstems

    # Objects: prefer NER if extracted, else LLM
    merged.objects = ner.objects if ner.objects else llm.objects

    # Planetary features: union (both NER and LLM can detect)
    seen_pf = set()
    merged_pf = []
    for pf in ner.planetary_features + llm.planetary_features:
        if pf.lower() not in seen_pf:
            seen_pf.add(pf.lower())
            merged_pf.append(pf)
    merged.planetary_features = merged_pf

    # Enum fields: union of NER and LLM
    merged.doctype = ner.doctype | llm.doctype
    merged.property = ner.property | llm.property
    merged.collection = ner.collection | llm.collection
    merged.bibgroup = ner.bibgroup | llm.bibgroup
    merged.esources = ner.esources | llm.esources
    merged.data = ner.data | llm.data

    # Operator: prefer LLM (handles nested/complex operators better)
    merged.operator = llm.operator if llm.operator else ner.operator
    merged.operator_target = llm.operator_target if llm.operator_target else ner.operator_target

    # LLM-only fields (NER can't detect these)
    merged.negated_terms = llm.negated_terms
    merged.negated_properties = llm.negated_properties
    merged.negated_doctypes = llm.negated_doctypes
    merged.has_fields = llm.has_fields
    merged.citation_count_min = llm.citation_count_min
    merged.citation_count_max = llm.citation_count_max
    merged.read_count_min = llm.read_count_min
    merged.mention_count_min = llm.mention_count_min
    merged.mention_count_max = llm.mention_count_max
    merged.credit_count_min = llm.credit_count_min
    merged.credit_count_max = llm.credit_count_max
    merged.author_count_min = llm.author_count_min
    merged.author_count_max = llm.author_count_max
    merged.page_count_min = llm.page_count_min
    merged.page_count_max = llm.page_count_max
    merged.ack_terms = llm.ack_terms
    merged.grant_terms = llm.grant_terms
    merged.title_terms = llm.title_terms
    merged.full_text_terms = llm.full_text_terms
    merged.exact_match_fields = llm.exact_match_fields
    merged.identifiers = llm.identifiers
    merged.keyword_terms = llm.keyword_terms
    merged.arxiv_classes = llm.arxiv_classes
    merged.orcid_ids = llm.orcid_ids
    merged.entdate_range = llm.entdate_range
    merged.passthrough_clauses = llm.passthrough_clauses

    # Post-merge cleanups at intent level
    _strip_default_doctype(merged, nl_text)
    _remove_inst_from_free_text(merged)
    _dedup_bibgroup_and_aff(merged)
    _resolve_negation_conflicts(merged)

    return merged


def merge_ner_and_nls_intent(
    ner_result: PipelineResult | None,
    llm_intent: IntentSpec,
    nl_text: str,
) -> MergeResult:
    """Merge NER pipeline result with LLM IntentSpec output directly.

    Like merge_ner_and_nls but skips parse_query_to_intent() because the LLM
    already outputs structured IntentSpec JSON.

    Args:
        ner_result: PipelineResult from NER pipeline (or None)
        llm_intent: IntentSpec parsed from LLM's JSON output
        nl_text: Original natural language input

    Returns:
        MergeResult with final query and metadata
    """
    merge_start = time.perf_counter()

    ner_query = ner_result.final_query if ner_result and ner_result.success else ""
    ner_intent = ner_result.intent if ner_result and ner_result.success else None

    # Case 1: No NER intent to merge — LLM-only
    if ner_intent is None or not ner_intent.has_content():
        clean_query = assemble_query(llm_intent)

        # Validate the assembled query
        assembled_lint = lint_query(clean_query)
        if not assembled_lint.valid or not clean_query.strip():
            # Assembly broke something — try raw passthrough
            clean_query = assemble_query(llm_intent)

        # Ultimate fallback if still empty
        used_fallback = False
        if not clean_query.strip():
            if nl_text and nl_text.strip():
                safe_text = nl_text.strip().replace('"', '\\"')
                clean_query = f'abs:"{safe_text}"'
                used_fallback = True

        merge_ms = (time.perf_counter() - merge_start) * 1000
        return MergeResult(
            query=clean_query,
            source="fallback" if used_fallback else "nls_only",
            nls_query="",
            ner_query=ner_query or "",
            confidence=0.1 if used_fallback else 0.8,
            timing={"merge_ms": merge_ms},
            ner_intent=ner_intent.to_dict() if ner_intent else None,
            llm_intent=llm_intent.to_dict(),
        )

    # Case 2: Both valid — intent-level merge
    merged_intent = merge_intents(ner_intent, llm_intent, nl_text)

    # Assemble clean query from merged intent
    merged_query = assemble_query(merged_intent)

    # Track which fields NER contributed
    fields_injected = []
    if ner_intent.authors and not llm_intent.authors:
        fields_injected.append("author")
    if (ner_intent.year_from is not None or ner_intent.year_to is not None) and llm_intent.year_from is None and llm_intent.year_to is None:
        fields_injected.append("pubdate")
    if ner_intent.bibstems and not llm_intent.bibstems:
        fields_injected.append("bibstem")
    if ner_intent.objects and not llm_intent.objects:
        fields_injected.append("object")
    if ner_intent.affiliations and not llm_intent.affiliations:
        fields_injected.append("aff")
    for enum_field in ("doctype", "property", "collection", "bibgroup", "esources", "data"):
        ner_vals = getattr(ner_intent, enum_field)
        llm_vals = getattr(llm_intent, enum_field)
        if ner_vals and not llm_vals:
            fields_injected.append(enum_field)

    # Validate merged result
    merged_lint = lint_query(merged_query)
    if not merged_lint.valid or not merged_query.strip():
        logger.warning(
            f"Merged query failed validation: {merged_lint.errors}. "
            f"Falling back to LLM-only."
        )
        clean_query = assemble_query(llm_intent)
        merge_ms = (time.perf_counter() - merge_start) * 1000
        return MergeResult(
            query=clean_query,
            source="nls_only",
            nls_query="",
            ner_query=ner_query,
            confidence=0.7,
            timing={"merge_ms": merge_ms},
            ner_intent=ner_intent.to_dict(),
            llm_intent=llm_intent.to_dict(),
            merged_intent=merged_intent.to_dict(),
        )

    # Confidence scoring
    ner_confidence = ner_result.confidence if ner_result else 0.0
    if fields_injected:
        confidence = 0.9
    elif ner_confidence >= 0.7:
        confidence = ner_confidence
    else:
        confidence = 0.8

    source = "hybrid" if fields_injected else "nls_only"

    merge_ms = (time.perf_counter() - merge_start) * 1000

    return MergeResult(
        query=merged_query,
        source=source,
        nls_query="",
        ner_query=ner_query,
        fields_injected=fields_injected,
        confidence=confidence,
        timing={"merge_ms": merge_ms},
        ner_intent=ner_intent.to_dict(),
        llm_intent=llm_intent.to_dict(),
        merged_intent=merged_intent.to_dict(),
    )


def merge_ner_and_nls(
    ner_result: PipelineResult | None,
    nls_query: str,
    nl_text: str,
) -> MergeResult:
    """Merge NER pipeline result with NLS model output.

    Strategy:
    1. Parse LLM output into IntentSpec via parse_query_to_intent()
    2. Merge the two IntentSpecs with per-field policies
    3. Assemble final query from the merged IntentSpec

    Falls back gracefully when either source is unavailable.

    Args:
        ner_result: PipelineResult from NER pipeline
        nls_query: Post-processed NLS model output
        nl_text: Original natural language input

    Returns:
        MergeResult with final query and metadata
    """
    merge_start = time.perf_counter()

    ner_query = ner_result.final_query if ner_result and ner_result.success else ""
    ner_intent = ner_result.intent if ner_result and ner_result.success else None

    nls_valid = bool(nls_query and nls_query.strip())
    ner_valid = bool(ner_query and ner_query.strip())

    # Validate syntax
    if nls_valid:
        nls_lint = lint_query(nls_query)
        nls_valid = nls_lint.valid

    if ner_valid:
        ner_lint = lint_query(ner_query)
        ner_valid = ner_lint.valid

    # Case 1: Both empty/invalid
    if not nls_valid and not ner_valid:
        merge_ms = (time.perf_counter() - merge_start) * 1000
        # Fallback: return abs:"original text" rather than empty
        fallback_query = ""
        source = "fallback"
        if nl_text and nl_text.strip():
            safe_text = nl_text.strip().replace('"', '\\"')
            fallback_query = f'abs:"{safe_text}"'
        return MergeResult(
            query=fallback_query,
            source=source,
            nls_query=nls_query or "",
            ner_query=ner_query or "",
            confidence=0.1,
            timing={"merge_ms": merge_ms},
        )

    # Case 2: Only NER valid
    if not nls_valid and ner_valid:
        merge_ms = (time.perf_counter() - merge_start) * 1000
        return MergeResult(
            query=ner_query,
            source="ner_only",
            nls_query=nls_query or "",
            ner_query=ner_query,
            confidence=ner_result.confidence if ner_result else 0.5,
            timing={"merge_ms": merge_ms},
        )

    # Case 3: Only NLS valid (no NER intent to merge)
    if nls_valid and (not ner_valid or ner_intent is None or not ner_intent.has_content()):
        # Parse LLM output, assemble through assembler for clean syntax
        llm_intent = parse_query_to_intent(nls_query)
        clean_query = assemble_query(llm_intent)

        # Validate the assembled query
        assembled_lint = lint_query(clean_query)
        if not assembled_lint.valid or not clean_query.strip():
            # Assembly broke something — fall back to raw NLS
            clean_query = nls_query

        merge_ms = (time.perf_counter() - merge_start) * 1000
        return MergeResult(
            query=clean_query,
            source="nls_only",
            nls_query=nls_query,
            ner_query=ner_query or "",
            confidence=0.8,
            timing={"merge_ms": merge_ms},
            ner_intent=ner_intent.to_dict() if ner_intent else None,
            llm_intent=llm_intent.to_dict(),
        )

    # Case 4: Both valid — intent-level merge
    llm_intent = parse_query_to_intent(nls_query)
    merged_intent = merge_intents(ner_intent, llm_intent, nl_text)

    # Assemble clean query from merged intent
    merged_query = assemble_query(merged_intent)

    # Track which fields NER contributed
    fields_injected = []
    if ner_intent.authors and not llm_intent.authors:
        fields_injected.append("author")
    if (ner_intent.year_from is not None or ner_intent.year_to is not None) and llm_intent.year_from is None and llm_intent.year_to is None:
        fields_injected.append("pubdate")
    if ner_intent.bibstems and not llm_intent.bibstems:
        fields_injected.append("bibstem")
    if ner_intent.objects and not llm_intent.objects:
        fields_injected.append("object")
    if ner_intent.affiliations and not llm_intent.affiliations:
        fields_injected.append("aff")
    for enum_field in ("doctype", "property", "collection", "bibgroup", "esources", "data"):
        ner_vals = getattr(ner_intent, enum_field)
        llm_vals = getattr(llm_intent, enum_field)
        if ner_vals and not llm_vals:
            fields_injected.append(enum_field)

    # Validate merged result
    merged_lint = lint_query(merged_query)
    if not merged_lint.valid or not merged_query.strip():
        # Merge/assembly broke syntax — fall back to NLS-only
        logger.warning(
            f"Merged query failed validation: {merged_lint.errors}. "
            f"Falling back to NLS-only."
        )
        merge_ms = (time.perf_counter() - merge_start) * 1000
        return MergeResult(
            query=nls_query,
            source="nls_only",
            nls_query=nls_query,
            ner_query=ner_query,
            confidence=0.7,
            timing={"merge_ms": merge_ms},
            ner_intent=ner_intent.to_dict() if ner_intent else None,
            llm_intent=llm_intent.to_dict(),
            merged_intent=merged_intent.to_dict(),
        )

    # Confidence scoring
    ner_confidence = ner_result.confidence if ner_result else 0.0
    if fields_injected:
        confidence = 0.9
    elif ner_confidence >= 0.7:
        confidence = ner_confidence
    else:
        confidence = 0.8

    source = "hybrid" if fields_injected else "nls_only"

    merge_ms = (time.perf_counter() - merge_start) * 1000

    return MergeResult(
        query=merged_query,
        source=source,
        nls_query=nls_query,
        ner_query=ner_query,
        fields_injected=fields_injected,
        confidence=confidence,
        timing={"merge_ms": merge_ms},
        ner_intent=ner_intent.to_dict(),
        llm_intent=llm_intent.to_dict(),
        merged_intent=merged_intent.to_dict(),
    )
