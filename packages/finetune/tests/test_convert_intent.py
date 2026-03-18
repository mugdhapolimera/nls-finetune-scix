"""Tests for convert_to_intent_format.py conversion logic."""

import sys
from pathlib import Path

import pytest

# Add scripts to path so we can import the conversion functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
from convert_to_intent_format import convert_example, generate_think_trace


class TestConvertExample:
    def test_simple_author_query(self):
        result = convert_example({
            "natural_language": "papers by Hawking on black holes",
            "ads_query": 'author:"Hawking" abs:"black holes"',
            "category": "author",
        })
        assert result is not None
        assert "error" not in result
        assert "Hawking" in result["intent_json"]["authors"]
        assert "black holes" in result["intent_json"]["free_text_terms"]
        assert result["think_trace"]

    def test_year_range(self):
        result = convert_example({
            "natural_language": "dark matter papers from 2020 to 2023",
            "ads_query": 'abs:"dark matter" pubdate:[2020 TO 2023]',
            "category": "content",
        })
        assert result is not None
        assert "error" not in result
        assert result["intent_json"]["year_from"] == 2020
        assert result["intent_json"]["year_to"] == 2023

    def test_operator_query(self):
        result = convert_example({
            "natural_language": "papers citing dark matter research",
            "ads_query": 'citations(abs:"dark matter")',
            "category": "operator",
        })
        assert result is not None
        assert "error" not in result
        assert result["intent_json"]["operator"] == "citations"

    def test_negation_query(self):
        result = convert_example({
            "natural_language": "dark matter not axions",
            "ads_query": 'abs:"dark matter" NOT abs:"axion"',
            "category": "negation",
        })
        assert result is not None
        assert "error" not in result
        assert "axion" in result["intent_json"]["negated_terms"]

    def test_enum_fields(self):
        result = convert_example({
            "natural_language": "refereed articles on cosmology",
            "ads_query": 'abs:"cosmology" doctype:article property:refereed',
            "category": "filters",
        })
        assert result is not None
        assert "error" not in result
        assert "article" in result["intent_json"]["doctype"]
        assert "refereed" in result["intent_json"]["property"]

    def test_passthrough_clauses(self):
        result = convert_example({
            "natural_language": "papers by ORCID 0000-0001-2345-6789",
            "ads_query": 'orcid:0000-0001-2345-6789',
            "category": "orcid",
        })
        assert result is not None
        assert "error" not in result
        assert "0000-0001-2345-6789" in result["intent_json"].get("orcid_ids", [])

    def test_affiliation_query(self):
        result = convert_example({
            "natural_language": "papers from MIT",
            "ads_query": '(inst:"MIT" OR aff:"MIT")',
            "category": "affiliation",
        })
        assert result is not None
        assert "error" not in result
        assert "MIT" in result["intent_json"]["affiliations"]

    def test_has_field_query(self):
        result = convert_example({
            "natural_language": "papers with full text on galaxies",
            "ads_query": 'abs:"galaxies" has:body',
            "category": "has",
        })
        assert result is not None
        assert "error" not in result
        assert "body" in result["intent_json"]["has_fields"]

    def test_empty_query_handled(self):
        result = convert_example({
            "natural_language": "",
            "ads_query": "",
            "category": "unknown",
        })
        # Should still succeed (empty intent is valid)
        assert result is not None

    def test_preserves_category(self):
        result = convert_example({
            "natural_language": "test",
            "ads_query": 'abs:"test"',
            "category": "my_category",
        })
        assert result is not None
        assert result["category"] == "my_category"


class TestGenerateThinkTrace:
    def test_simple_trace(self):
        intent = {"authors": ["Hawking, S"], "free_text_terms": ["black holes"]}
        trace = generate_think_trace("papers by Hawking on black holes", intent)
        assert "Hawking" in trace
        assert "black holes" in trace
        assert "Author" in trace

    def test_year_range_trace(self):
        intent = {"year_from": 2020, "year_to": 2023}
        trace = generate_think_trace("papers from 2020 to 2023", intent)
        assert "2020" in trace
        assert "2023" in trace

    def test_operator_trace(self):
        intent = {"operator": "citations", "free_text_terms": ["dark matter"]}
        trace = generate_think_trace("papers citing dark matter", intent)
        assert "citations" in trace

    def test_negation_trace(self):
        intent = {"negated_terms": ["axion"]}
        trace = generate_think_trace("not axions", intent)
        assert "axion" in trace
        assert "Exclude" in trace

    def test_empty_intent(self):
        trace = generate_think_trace("hello", {})
        assert "The user wants" in trace

    def test_complex_intent(self):
        intent = {
            "authors": ["Hawking, S"],
            "free_text_terms": ["black holes"],
            "year_from": 1970,
            "year_to": 1979,
            "doctype": ["article"],
            "property": ["refereed"],
            "operator": "citations",
        }
        trace = generate_think_trace("cited refereed articles by Hawking on black holes from the 1970s", intent)
        assert "Hawking" in trace
        assert "black holes" in trace
        assert "1970" in trace
        assert "article" in trace
        assert "refereed" in trace
        assert "citations" in trace
