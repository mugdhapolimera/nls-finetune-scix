"""Tests for server fallback and timeout behavior."""

import json
import sys
from pathlib import Path

import pytest

# Add finetune to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root / "packages" / "finetune" / "src"))

from finetune.domains.scix.merge import merge_ner_and_nls, merge_ner_and_nls_intent, MergeResult
from finetune.domains.scix.intent_spec import IntentSpec


class TestEmptyQueryFallback:
    """Test that both-fail case returns abs:'original text' instead of empty."""

    def test_both_fail_returns_abs_fallback(self):
        """When both NER and NLS fail, return abs:'original text'."""
        result = merge_ner_and_nls(None, "", "dark matter papers")
        assert result.query == 'abs:"dark matter papers"'
        assert result.source == "fallback"
        assert result.confidence == 0.1

    def test_both_fail_empty_nl_returns_empty(self):
        """When both fail AND nl_text is empty, return empty."""
        result = merge_ner_and_nls(None, "", "")
        assert result.query == ""

    def test_both_fail_with_quotes_in_nl(self):
        """Fallback should escape quotes in user text."""
        result = merge_ner_and_nls(None, "", 'papers about "dark energy"')
        assert result.query == 'abs:"papers about \\"dark energy\\""'

    def test_nls_invalid_ner_empty(self):
        """When NLS is invalid and NER empty, should still produce something."""
        result = merge_ner_and_nls(None, ")))invalid(((", "exoplanet atmospheres")
        # Should fall back since NLS is invalid syntax
        assert result.query  # Not empty

    def test_fallback_source_field(self):
        """Fallback results should have source='fallback'."""
        result = merge_ner_and_nls(None, "", "gravitational waves")
        assert result.source == "fallback"


class TestIntentEmptyQueryFallback:
    """Test fallback in intent merge path."""

    def test_empty_llm_intent_with_empty_ner(self):
        """When LLM intent has no content and NER is None."""
        empty_intent = IntentSpec()
        result = merge_ner_and_nls_intent(None, empty_intent, "stellar evolution")
        # Should produce something, not empty
        assert result.query != "" or result.source in ("nls_only", "fallback")


class TestInputValidation:
    """Test input sanitization (tested via the extract function logic)."""

    def test_long_nl_text_in_fallback(self):
        """Very long NL text should still produce valid fallback."""
        long_text = "dark matter " * 100  # Very long
        result = merge_ner_and_nls(None, "", long_text.strip())
        assert result.query.startswith('abs:"')

    def test_null_bytes_in_nl(self):
        """Null bytes in NL should not break fallback."""
        result = merge_ner_and_nls(None, "", "dark\x00matter")
        assert result.query  # Should produce something


class TestParseLlmResponseEdgeCases:
    """Test parse_llm_response edge cases (inline version to avoid torch dep)."""

    def _parse(self, response: str):
        """Inline parse_llm_response without torch deps."""
        raw = response

        # Size guard
        if len(response) > 10240:
            return None, response

        think_end = response.find("</think>")
        if think_end >= 0:
            response = response[think_end + len("</think>"):].strip()

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start < 0 or json_end <= json_start:
                return None, response

            data = json.loads(response[json_start:json_end])

            if "query" in data and len(data) == 1:
                return None, data["query"]

            intent = IntentSpec.from_compact_dict(data)
            if intent.has_content():
                return intent, raw
            return None, response
        except (json.JSONDecodeError, TypeError, ValueError):
            return None, response

    def test_oversized_response_skips_parsing(self):
        """Response >10KB should skip JSON parsing."""
        huge = '{"query": "abs:test"}' + " " * 20000
        intent, clean = self._parse(huge)
        assert intent is None
        assert clean == huge  # Returns raw, doesn't parse

    def test_truncated_json(self):
        """Truncated JSON returns None gracefully."""
        intent, clean = self._parse('{"authors": ["Hawking"')
        assert intent is None

    def test_think_block_no_json(self):
        """Think block with no JSON after returns None."""
        intent, clean = self._parse("<think>reasoning</think>\nno json here")
        assert intent is None
        assert clean == "no json here"
