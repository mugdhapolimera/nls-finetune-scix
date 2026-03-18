"""Tests for the deterministic query assembler."""

import pytest

from finetune.domains.scix.assembler import (
    _build_abs_clause,
    _build_affiliation_clause,
    _build_author_clause,
    _build_bibstem_clause,
    _build_enum_clause,
    _build_object_clause,
    _build_year_clause,
    _wildcard_complex_author,
    _wrap_with_operator,
    assemble_query,
    rewrite_complex_author_wildcards,
    validate_query_syntax,
)
from finetune.domains.scix.intent_spec import IntentSpec


# ============================================================================
# Clause builders
# ============================================================================


class TestBuildAuthorClause:
    def test_single_author(self):
        assert _build_author_clause(["Hawking"]) == 'author:"Hawking"'

    def test_multiple_authors(self):
        result = _build_author_clause(["Hawking", "Penrose"])
        assert 'author:"Hawking"' in result
        assert 'author:"Penrose"' in result

    def test_empty(self):
        assert _build_author_clause([]) == ""


class TestBuildAbsClause:
    def test_single_term(self):
        assert _build_abs_clause(["dark matter"]) == 'abs:"dark matter"'

    def test_multiple_and(self):
        result = _build_abs_clause(["dark matter", "galaxy clusters"])
        assert 'abs:"dark matter"' in result
        assert 'abs:"galaxy clusters"' in result

    def test_multiple_or(self):
        result = _build_abs_clause(["rocks", "volcanoes"], use_or=True)
        assert "abs:(rocks OR volcanoes)" == result

    def test_empty(self):
        assert _build_abs_clause([]) == ""

    def test_single_word_no_quotes(self):
        assert _build_abs_clause(["exoplanets"]) == "abs:exoplanets"


class TestBuildYearClause:
    def test_range(self):
        assert _build_year_clause(2020, 2023) == "pubdate:[2020 TO 2023]"

    def test_from_only(self):
        assert _build_year_clause(2020, None) == "pubdate:[2020 TO *]"

    def test_to_only(self):
        assert _build_year_clause(None, 2023) == "pubdate:[* TO 2023]"

    def test_none(self):
        assert _build_year_clause(None, None) == ""


class TestBuildEnumClause:
    def test_single_value(self):
        assert _build_enum_clause("doctype", {"article"}) == "doctype:article"

    def test_multiple_values(self):
        result = _build_enum_clause("doctype", {"article", "eprint"})
        assert "doctype:" in result
        assert "article" in result
        assert "eprint" in result

    def test_empty(self):
        assert _build_enum_clause("doctype", set()) == ""

    def test_invalid_filtered(self):
        result = _build_enum_clause("doctype", {"article", "INVALID_VALUE"})
        assert "INVALID" not in result
        assert "article" in result


class TestBuildObjectClause:
    def test_single_object(self):
        assert _build_object_clause(["M31"]) == "object:M31"

    def test_multi_word_object(self):
        assert _build_object_clause(["NGC 1234"]) == 'object:"NGC 1234"'

    def test_empty(self):
        assert _build_object_clause([]) == ""


class TestBuildBibstemClause:
    def test_single(self):
        assert _build_bibstem_clause(["ApJ"]) == 'bibstem:"ApJ"'

    def test_multiple(self):
        result = _build_bibstem_clause(["ApJ", "MNRAS"])
        assert 'bibstem:"ApJ"' in result
        assert 'bibstem:"MNRAS"' in result
        assert "OR" in result


# ============================================================================
# Complex author wildcarding
# ============================================================================


class TestWildcardComplexAuthor:
    def test_simple_name_unchanged(self):
        assert _wildcard_complex_author("Hawking") == "Hawking"

    def test_comma_format_unchanged(self):
        assert _wildcard_complex_author("Hawking, S") == "Hawking, S"

    def test_hyphen_long_prefix(self):
        assert _wildcard_complex_author("de Groot-Hedlin") == "de*Groot*Hedlin*"

    def test_hyphen_short_prefix(self):
        assert _wildcard_complex_author("El-Badry") == "El*Badry*"

    def test_apostrophe(self):
        assert _wildcard_complex_author("Le Floc'h") == "Le*Floc*h*"

    def test_garcia_perez(self):
        assert _wildcard_complex_author("Garcia-Perez") == "Garcia*Perez*"

    def test_al_sufi(self):
        assert _wildcard_complex_author("al-Sufi") == "al*Sufi*"

    def test_first_author_caret(self):
        result = _wildcard_complex_author("^Hawking")
        assert result == "^Hawking"

    def test_first_author_caret_with_hyphen(self):
        result = _wildcard_complex_author("^El-Badry")
        assert result == "^El*Badry*"

    def test_already_wildcarded(self):
        assert _wildcard_complex_author("Garcia*") == "Garcia*"


class TestRewriteComplexAuthorWildcards:
    def test_rewrites_hyphenated(self):
        query = 'author:"Garcia-Perez" abs:"exoplanets"'
        result = rewrite_complex_author_wildcards(query)
        assert 'author:"Garcia*Perez*"' in result

    def test_rewrites_el_badry(self):
        query = 'author:"El-Badry" abs:"binary star"'
        result = rewrite_complex_author_wildcards(query)
        assert 'author:"El*Badry*"' in result

    def test_simple_name_unchanged(self):
        query = 'author:"Hawking" abs:"black holes"'
        result = rewrite_complex_author_wildcards(query)
        assert result == query


# ============================================================================
# Operator wrapping
# ============================================================================


class TestWrapWithOperator:
    def test_citations(self):
        assert _wrap_with_operator('abs:"dark matter"', "citations") == 'citations(abs:"dark matter")'

    def test_invalid_operator(self):
        with pytest.raises(ValueError):
            _wrap_with_operator("query", "invalid_op")

    def test_empty_query(self):
        assert _wrap_with_operator("", "citations") == ""


# ============================================================================
# Full assembly
# ============================================================================


class TestAssembleQuery:
    def test_simple_topic(self):
        intent = IntentSpec(free_text_terms=["dark matter"])
        query = assemble_query(intent)
        assert "abs:" in query
        assert "dark matter" in query

    def test_author_and_topic(self):
        intent = IntentSpec(
            authors=["Hawking"],
            free_text_terms=["black holes"],
        )
        query = assemble_query(intent)
        assert 'author:"Hawking"' in query
        assert "abs:" in query

    def test_full_intent(self):
        intent = IntentSpec(
            authors=["Hawking"],
            free_text_terms=["black holes"],
            year_from=2020,
            year_to=2023,
            doctype={"article"},
            property={"refereed"},
        )
        query = assemble_query(intent)
        assert 'author:"Hawking"' in query
        assert "pubdate:[2020 TO 2023]" in query
        assert "doctype:article" in query
        assert "property:refereed" in query

    def test_operator_wrapping(self):
        intent = IntentSpec(
            free_text_terms=["dark matter"],
            operator="citations",
        )
        query = assemble_query(intent)
        assert "citations(" in query

    def test_bibstem(self):
        intent = IntentSpec(
            free_text_terms=["exoplanets"],
            bibstems=["ApJ"],
        )
        query = assemble_query(intent)
        assert 'bibstem:"ApJ"' in query

    def test_object(self):
        intent = IntentSpec(
            objects=["M31"],
            free_text_terms=["rotation curve"],
        )
        query = assemble_query(intent)
        assert "object:M31" in query


# ============================================================================
# validate_query_syntax
# ============================================================================


class TestAssembleNewFields:
    """Test assembly of identifiers, keywords, arxiv_classes, orcid_ids, entdate, metric counts."""

    def test_identifiers_bibcode(self):
        intent = IntentSpec(identifiers=["bibcode:2020ApJ...900..100D"])
        query = assemble_query(intent)
        assert "bibcode:2020ApJ...900..100D" in query

    def test_identifiers_doi(self):
        intent = IntentSpec(identifiers=["doi:10.1038/s41586-020-2649-2"])
        query = assemble_query(intent)
        assert "doi:" in query
        assert "10.1038/s41586-020-2649-2" in query

    def test_identifiers_arxiv(self):
        intent = IntentSpec(identifiers=["arxiv:2301.12345"])
        query = assemble_query(intent)
        assert "arxiv:2301.12345" in query

    def test_identifiers_plain(self):
        intent = IntentSpec(identifiers=["2020ApJ...123L..45S"])
        query = assemble_query(intent)
        assert "identifier:" in query
        assert "2020ApJ...123L..45S" in query

    def test_keyword_terms(self):
        intent = IntentSpec(keyword_terms=["dark matter", "accretion"])
        query = assemble_query(intent)
        assert 'keyword:"dark matter"' in query
        assert "keyword:accretion" in query

    def test_arxiv_classes(self):
        intent = IntentSpec(arxiv_classes=["astro-ph.HE"])
        query = assemble_query(intent)
        assert "arxiv_class:astro-ph.HE" in query

    def test_orcid_ids(self):
        intent = IntentSpec(orcid_ids=["0000-0001-2345-6789"])
        query = assemble_query(intent)
        assert "orcid:0000-0001-2345-6789" in query

    def test_entdate_range(self):
        intent = IntentSpec(entdate_range="[NOW-7DAYS TO *]")
        query = assemble_query(intent)
        assert "entdate:[NOW-7DAYS TO *]" in query

    def test_mention_count(self):
        intent = IntentSpec(mention_count_min=5)
        query = assemble_query(intent)
        assert "mention_count:[5 TO *]" in query

    def test_credit_count(self):
        intent = IntentSpec(credit_count_min=20, credit_count_max=100)
        query = assemble_query(intent)
        assert "credit_count:[20 TO 100]" in query

    def test_author_count(self):
        intent = IntentSpec(author_count_min=100)
        query = assemble_query(intent)
        assert "author_count:[100 TO *]" in query

    def test_page_count(self):
        intent = IntentSpec(page_count_min=1, page_count_max=10)
        query = assemble_query(intent)
        assert "page_count:[1 TO 10]" in query

    def test_roundtrip_new_fields(self):
        """Parse → assemble round-trip for new fields."""
        from finetune.domains.scix.parse_query import parse_query_to_intent

        q = 'keyword:"dark matter" arxiv_class:astro-ph.HE orcid:0000-0001-2345-6789 entdate:[NOW-7DAYS TO *] mention_count:[5 TO *]'
        intent = parse_query_to_intent(q)
        result = assemble_query(intent)
        assert 'keyword:"dark matter"' in result
        assert "arxiv_class:astro-ph.HE" in result
        assert "orcid:0000-0001-2345-6789" in result
        assert "entdate:[NOW-7DAYS TO *]" in result
        assert "mention_count:[5 TO *]" in result


class TestValidateQuerySyntax:
    def test_valid_query(self):
        is_valid, errors = validate_query_syntax('author:"Hawking" abs:"black holes"')
        assert is_valid
        assert errors == []

    def test_unbalanced_parens(self):
        is_valid, errors = validate_query_syntax('citations(abs:"dark matter"')
        assert not is_valid
        assert any("parentheses" in e.lower() for e in errors)
