"""Tests for IntentSpec to_compact_dict(), from_compact_dict(), and from_dict() fixes."""

import pytest

from finetune.domains.scix.intent_spec import IntentSpec


class TestToCompactDict:
    def test_empty_intent_returns_empty(self):
        intent = IntentSpec()
        compact = intent.to_compact_dict()
        assert compact == {}

    def test_strips_metadata(self):
        intent = IntentSpec(
            free_text_terms=["dark matter"],
            raw_user_text="dark matter papers",
            confidence={"topic": 0.9},
        )
        compact = intent.to_compact_dict()
        assert "raw_user_text" not in compact
        assert "confidence" not in compact
        assert compact["free_text_terms"] == ["dark matter"]

    def test_strips_empty_fields(self):
        intent = IntentSpec(
            authors=["Hawking"],
            free_text_terms=[],
            doctype=set(),
            year_from=None,
        )
        compact = intent.to_compact_dict()
        assert "free_text_terms" not in compact
        assert "doctype" not in compact
        assert "year_from" not in compact
        assert compact["authors"] == ["Hawking"]

    def test_keeps_year_zero(self):
        """year_from=0 is falsy but should NOT be stripped — however, year 0
        is not a valid year for ADS, so stripping it is fine."""
        intent = IntentSpec(year_from=0)
        compact = intent.to_compact_dict()
        # 0 is stripped because the filter checks `v != 0`
        assert "year_from" not in compact

    def test_keeps_all_populated_fields(self):
        intent = IntentSpec(
            authors=["Hawking, S"],
            free_text_terms=["black holes"],
            year_from=1970,
            year_to=1979,
            doctype={"article"},
            property={"refereed"},
            operator="citations",
        )
        compact = intent.to_compact_dict()
        assert compact["authors"] == ["Hawking, S"]
        assert compact["free_text_terms"] == ["black holes"]
        assert compact["year_from"] == 1970
        assert compact["year_to"] == 1979
        assert "article" in compact["doctype"]
        assert "refereed" in compact["property"]
        assert compact["operator"] == "citations"

    def test_sets_become_sorted_lists(self):
        intent = IntentSpec(doctype={"eprint", "article"})
        compact = intent.to_compact_dict()
        assert compact["doctype"] == ["article", "eprint"]


class TestFromCompactDict:
    def test_empty_dict(self):
        intent = IntentSpec.from_compact_dict({})
        assert not intent.has_content()

    def test_basic_fields(self):
        intent = IntentSpec.from_compact_dict({
            "authors": ["Hawking, S"],
            "free_text_terms": ["black holes"],
            "year_from": 1970,
        })
        assert intent.authors == ["Hawking, S"]
        assert intent.free_text_terms == ["black holes"]
        assert intent.year_from == 1970

    def test_unknown_keys_filtered(self):
        """Extra keys from LLM output should not cause crashes."""
        intent = IntentSpec.from_compact_dict({
            "authors": ["Hawking"],
            "unknown_field": "should be ignored",
            "extra_metadata": 42,
        })
        assert intent.authors == ["Hawking"]

    def test_sets_restored_from_lists(self):
        intent = IntentSpec.from_compact_dict({
            "doctype": ["article", "eprint"],
            "property": ["refereed"],
        })
        assert intent.doctype == {"article", "eprint"}
        assert intent.property == {"refereed"}

    def test_round_trip(self):
        original = IntentSpec(
            authors=["Hawking, S"],
            free_text_terms=["black holes"],
            year_from=1970,
            year_to=1979,
            doctype={"article"},
            operator="citations",
            negated_terms=["axion"],
            has_fields={"body"},
            citation_count_min=100,
            passthrough_clauses=["orcid:0000-0001"],
        )
        compact = original.to_compact_dict()
        restored = IntentSpec.from_compact_dict(compact)

        assert restored.authors == original.authors
        assert restored.free_text_terms == original.free_text_terms
        assert restored.year_from == original.year_from
        assert restored.year_to == original.year_to
        assert restored.doctype == original.doctype
        assert restored.operator == original.operator
        assert restored.negated_terms == original.negated_terms
        assert restored.has_fields == original.has_fields
        assert restored.citation_count_min == original.citation_count_min
        assert restored.passthrough_clauses == original.passthrough_clauses


class TestFromDictUnknownKeys:
    def test_from_dict_filters_unknown_keys(self):
        """from_dict() should not crash on extra keys."""
        d = {
            "authors": ["Hawking"],
            "free_text_terms": ["black holes"],
            "unknown_field": "extra",
        }
        intent = IntentSpec.from_dict(d)
        assert intent.authors == ["Hawking"]

    def test_from_dict_handles_sets(self):
        d = {
            "doctype": ["article"],
            "property": ["refereed"],
        }
        intent = IntentSpec.from_dict(d)
        assert intent.doctype == {"article"}
        assert intent.property == {"refereed"}


class TestStringToListCoercion:
    """Tests for from_compact_dict / from_dict coercing strings to lists."""

    def test_string_passthrough_coerced_to_list(self):
        """String passthrough_clauses should be wrapped in a list."""
        intent = IntentSpec.from_compact_dict({
            "passthrough_clauses": "citation_count:[100 TO *]",
        })
        assert isinstance(intent.passthrough_clauses, list)
        assert intent.passthrough_clauses == ["citation_count:[100 TO *]"]

    def test_string_free_text_coerced_to_list(self):
        """String free_text_terms should be wrapped in a list."""
        intent = IntentSpec.from_compact_dict({
            "free_text_terms": "dark matter",
        })
        assert isinstance(intent.free_text_terms, list)
        assert intent.free_text_terms == ["dark matter"]

    def test_string_authors_coerced_to_list(self):
        """String authors should be wrapped in a list."""
        intent = IntentSpec.from_compact_dict({
            "authors": "Hawking, S",
        })
        assert isinstance(intent.authors, list)
        assert intent.authors == ["Hawking, S"]

    def test_list_values_unchanged(self):
        """Normal list values should not be changed."""
        intent = IntentSpec.from_compact_dict({
            "passthrough_clauses": ["citation_count:[100 TO *]"],
            "free_text_terms": ["dark matter", "cosmology"],
        })
        assert intent.passthrough_clauses == ["citation_count:[100 TO *]"]
        assert intent.free_text_terms == ["dark matter", "cosmology"]

    def test_from_dict_also_coerces(self):
        """from_dict should also coerce strings to lists."""
        intent = IntentSpec.from_dict({
            "passthrough_clauses": "[100 TO *]",
        })
        assert isinstance(intent.passthrough_clauses, list)
        assert intent.passthrough_clauses == ["[100 TO *]"]

    def test_no_character_explosion_in_assembler(self):
        """String passthrough should not explode into characters during assembly."""
        from finetune.domains.scix.assembler import assemble_query

        intent = IntentSpec.from_compact_dict({
            "operator": "useful",
            "free_text_terms": ["gravitational lensing"],
            "passthrough_clauses": "[100 TO *]",
        })
        query = assemble_query(intent)
        # Should NOT contain spaced-out characters
        assert "1 0 0" not in query
        # Bare range is stripped (no field prefix = meaningless)
        assert "[100 TO *]" not in query
        assert "gravitational lensing" in query


class TestRoundTripWithAssembler:
    def test_compact_dict_to_assembler(self):
        """IntentSpec → compact dict → from_compact_dict → assemble → valid query."""
        from finetune.domains.scix.assembler import assemble_query
        from finetune.domains.scix.validate import lint_query

        original = IntentSpec(
            authors=["Hawking, S"],
            free_text_terms=["black holes"],
            year_from=2020,
            year_to=2023,
            property={"refereed"},
        )
        compact = original.to_compact_dict()
        restored = IntentSpec.from_compact_dict(compact)
        query = assemble_query(restored)

        assert 'author:"Hawking, S"' in query
        assert "black holes" in query
        assert "pubdate:[2020 TO 2023]" in query
        assert "property:refereed" in query

        lint_result = lint_query(query)
        assert lint_result.valid
