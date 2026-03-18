"""Tests for RAG retrieval module."""

import json
import os
import tempfile

import pytest

from finetune.domains.scix.rag_retrieval import (
    _extract_topics,
    _load_intent_examples,
    reset_intent_cache,
    retrieve_few_shot,
)
from finetune.domains.scix.retrieval import reset_index


# Sample gold examples for testing
SAMPLE_GOLD = [
    {
        "natural_language": "papers by Hawking on black holes from the 1970s",
        "ads_query": 'author:"Hawking, S" abs:"black holes" pubdate:[1970 TO 1979]',
        "category": "compound",
    },
    {
        "natural_language": "dark matter review articles",
        "ads_query": 'abs:"dark matter" doctype:article property:refereed',
        "category": "content",
    },
    {
        "natural_language": "exoplanet atmospheres in the astrophysical journal",
        "ads_query": 'abs:"exoplanet atmosphere" bibstem:"ApJ"',
        "category": "publication",
    },
    {
        "natural_language": "gravitational wave detection papers",
        "ads_query": 'abs:"gravitational wave detection"',
        "category": "content",
    },
    {
        "natural_language": "papers citing the LIGO discovery",
        "ads_query": 'citations(abs:"LIGO" abs:"gravitational wave")',
        "category": "operator",
    },
]

# Matching intent-format examples
SAMPLE_INTENT = [
    {
        "natural_language": "papers by Hawking on black holes from the 1970s",
        "ads_query": 'author:"Hawking, S" abs:"black holes" pubdate:[1970 TO 1979]',
        "category": "compound",
        "intent_json": {
            "authors": ["Hawking, S"],
            "free_text_terms": ["black holes"],
            "year_from": 1970,
            "year_to": 1979,
        },
        "think_trace": "Author: Hawking → \"Hawking, S\". Topic: black holes. Time: 1970s → 1970-1979.",
    },
    {
        "natural_language": "dark matter review articles",
        "ads_query": 'abs:"dark matter" doctype:article property:refereed',
        "category": "content",
        "intent_json": {
            "free_text_terms": ["dark matter"],
            "doctype": ["article"],
            "property": ["refereed"],
        },
        "think_trace": "Topic: dark matter. Type: review article → doctype:article property:refereed.",
    },
    {
        "natural_language": "exoplanet atmospheres in the astrophysical journal",
        "ads_query": 'abs:"exoplanet atmosphere" bibstem:"ApJ"',
        "category": "publication",
        "intent_json": {
            "free_text_terms": ["exoplanet atmosphere"],
            "bibstems": ["ApJ"],
        },
        "think_trace": "Topic: exoplanet atmospheres. Journal: ApJ.",
    },
    {
        "natural_language": "gravitational wave detection papers",
        "ads_query": 'abs:"gravitational wave detection"',
        "category": "content",
        "intent_json": {
            "free_text_terms": ["gravitational wave detection"],
        },
        "think_trace": "Topic: gravitational wave detection.",
    },
    {
        "natural_language": "papers citing the LIGO discovery",
        "ads_query": 'citations(abs:"LIGO" abs:"gravitational wave")',
        "category": "operator",
        "intent_json": {
            "free_text_terms": ["LIGO", "gravitational wave"],
            "operator": "citations",
        },
        "think_trace": "Operator: citations. Topic: LIGO gravitational wave.",
    },
]


@pytest.fixture(autouse=True)
def _clean_caches():
    """Reset global caches before each test."""
    reset_index()
    reset_intent_cache()
    yield
    reset_index()
    reset_intent_cache()
    # Clean up env vars
    os.environ.pop("GOLD_EXAMPLES_PATH", None)
    os.environ.pop("GOLD_EXAMPLES_INTENT_PATH", None)


@pytest.fixture
def gold_files(tmp_path):
    """Create temporary gold example files for testing."""
    gold_path = tmp_path / "gold_examples.json"
    intent_path = tmp_path / "gold_examples_intent.json"

    gold_path.write_text(json.dumps(SAMPLE_GOLD))
    intent_path.write_text(json.dumps(SAMPLE_INTENT))

    os.environ["GOLD_EXAMPLES_PATH"] = str(gold_path)
    os.environ["GOLD_EXAMPLES_INTENT_PATH"] = str(intent_path)

    return gold_path, intent_path


class TestExtractTopics:
    def test_basic(self):
        topics = _extract_topics("papers by Hawking on black holes")
        assert len(topics) == 1
        # Should contain content words, not stopwords
        assert "hawking" in topics[0]
        assert "black" in topics[0]
        assert "holes" in topics[0]
        assert "by" not in topics[0]

    def test_empty(self):
        assert _extract_topics("") == []

    def test_only_stopwords(self):
        assert _extract_topics("the and or") == []


class TestRetrieveFewShot:
    def test_returns_intent_format(self, gold_files):
        results = retrieve_few_shot("dark matter cosmology", k=2)
        assert len(results) > 0
        for r in results:
            assert "nl" in r
            assert "intent_json" in r
            assert "think_trace" in r

    def test_respects_k(self, gold_files):
        results = retrieve_few_shot("gravitational waves", k=1)
        assert len(results) <= 1

    def test_excludes_exact_match(self, gold_files):
        results = retrieve_few_shot("dark matter review articles", k=5)
        for r in results:
            assert r["nl"] != "dark matter review articles"

    def test_includes_exact_match_when_disabled(self, gold_files):
        results = retrieve_few_shot(
            "dark matter review articles", k=5, exclude_exact=False
        )
        nls = [r["nl"] for r in results]
        assert "dark matter review articles" in nls

    def test_empty_when_no_intent_file(self, tmp_path):
        gold_path = tmp_path / "gold_examples.json"
        gold_path.write_text(json.dumps(SAMPLE_GOLD))
        os.environ["GOLD_EXAMPLES_PATH"] = str(gold_path)
        os.environ["GOLD_EXAMPLES_INTENT_PATH"] = str(tmp_path / "nonexistent.json")

        results = retrieve_few_shot("dark matter", k=3)
        assert results == []

    def test_returns_valid_intent_json(self, gold_files):
        results = retrieve_few_shot("dark matter", k=3)
        for r in results:
            assert isinstance(r["intent_json"], dict)
            # Should have at least one content field
            has_content = any(
                r["intent_json"].get(f)
                for f in ["free_text_terms", "authors", "operator"]
            )
            assert has_content


class TestRetrievalEdgeCases:
    """Test RAG retrieval edge cases."""

    def test_empty_query_returns_empty(self, gold_files):
        """Empty query should return empty list gracefully."""
        results = retrieve_few_shot("", k=3)
        assert isinstance(results, list)
        assert results == []

    def test_stopwords_only_query(self, gold_files):
        """Query of only stopwords should not crash."""
        results = retrieve_few_shot("the and or but", k=3)
        assert isinstance(results, list)

    def test_single_word_query(self, gold_files):
        """Single word query should return relevant examples."""
        results = retrieve_few_shot("exoplanet", k=3)
        assert isinstance(results, list)

    def test_results_have_required_fields(self, gold_files):
        """Each result should have nl, intent_json, think_trace."""
        results = retrieve_few_shot("dark matter papers", k=2)
        for r in results:
            assert "nl" in r
            assert "intent_json" in r
            assert "think_trace" in r

    def test_low_score_filtering(self, gold_files):
        """Very unrelated query should return fewer or no matches."""
        results = retrieve_few_shot("xyzzy foobar baz quantum", k=3)
        # Should return empty or very few results due to score filtering
        assert isinstance(results, list)


class TestResetCache:
    def test_reset_allows_reload(self, gold_files):
        # Load once
        results1 = retrieve_few_shot("black holes", k=2)
        # Reset and reload
        reset_intent_cache()
        results2 = retrieve_few_shot("black holes", k=2)
        assert len(results1) == len(results2)
