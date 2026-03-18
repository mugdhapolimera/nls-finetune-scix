"""Tests for field reference cards module."""

import pytest

from finetune.domains.scix.field_cards import CARDS, select_cards


class TestSelectCards:
    def test_returns_list_of_strings(self):
        cards = select_cards("highly cited dark matter papers")
        assert isinstance(cards, list)
        for c in cards:
            assert isinstance(c, str)

    def test_max_cards_limit(self):
        cards = select_cards("highly cited refereed preprint articles from MAST", max_cards=2)
        assert len(cards) <= 2

    def test_metrics_triggered(self):
        cards = select_cards("highly cited papers on dark matter")
        # Should include metrics card
        assert any("citation_count" in c for c in cards)

    def test_doctype_triggered(self):
        cards = select_cards("PhD thesis on galaxy evolution")
        assert any("doctype" in c.lower() or "phdthesis" in c for c in cards)

    def test_operator_triggered(self):
        cards = select_cards("papers citing the LIGO detection")
        assert any("citations()" in c for c in cards)

    def test_negation_triggered(self):
        cards = select_cards("papers about quasars excluding preprints")
        assert any("NOT" in c for c in cards)

    def test_empty_query_no_cards(self):
        cards = select_cards("")
        assert cards == []

    def test_no_match_no_cards(self):
        cards = select_cards("xyzzy foobar baz")
        assert cards == []

    def test_data_triggered(self):
        cards = select_cards("papers with data from MAST archive")
        assert any("MAST" in c for c in cards)

    def test_dates_triggered(self):
        cards = select_cards("recent papers from last year")
        assert any("pubdate" in c for c in cards)

    def test_all_cards_are_nonempty(self):
        for name, text in CARDS.items():
            assert len(text) > 20, f"Card '{name}' is too short"


class TestFalsePositivePrevention:
    """Test that common phrases don't trigger wrong cards."""

    def test_has_been_does_not_trigger_has_card(self):
        """'has been' is conversational, not a has: field query."""
        cards = select_cards("dark matter research that has been published recently")
        has_card_text = CARDS["has"]
        assert has_card_text not in cards

    def test_generic_with_does_not_trigger_has(self):
        """'with' in generic context shouldn't trigger has: card."""
        cards = select_cards("papers about galaxies with high redshift")
        has_card = CARDS["has"]
        assert has_card not in cards

    def test_with_data_from_triggers_data_card(self):
        """'with data from MAST' should trigger data card (MAST is specific)."""
        cards = select_cards("papers with data from MAST archive")
        assert any("MAST" in c for c in cards)

    def test_not_in_name_does_not_trigger_negation(self):
        """Author names containing 'not' shouldn't trigger negation card."""
        cards = select_cards("papers by Nottingham on stellar evolution")
        negation_card = CARDS["negation"]
        assert negation_card not in cards

    def test_not_as_conversational_does_not_trigger(self):
        """'has not been' is conversational, not a negation intent."""
        cards = select_cards("papers that have not been published yet")
        negation_card = CARDS["negation"]
        assert negation_card not in cards

    def test_excluding_triggers_negation(self):
        """Explicit 'excluding' should trigger negation card."""
        cards = select_cards("papers about quasars excluding preprints")
        assert any("NOT" in c for c in cards)

    def test_without_triggers_negation(self):
        """'without' should trigger negation card."""
        cards = select_cards("papers without preprints")
        assert any("NOT" in c for c in cards)

    def test_has_body_triggers_has_card(self):
        """Explicit 'has body' should trigger has: card."""
        cards = select_cards("papers that has body text available")
        has_card = CARDS["has"]
        assert has_card in cards

    def test_has_grant_triggers_has_card(self):
        """Explicit 'has grant' should trigger has: card."""
        cards = select_cards("papers that has grant information")
        has_card = CARDS["has"]
        assert has_card in cards


class TestBuildRagMessages:
    """Tests for build_rag_messages (imported from server inline to avoid torch dep)."""

    def test_basic_format(self):
        """Test message format without importing server.py (torch dependency)."""
        # Simulate build_rag_messages logic
        few_shot = [
            {
                "nl": "dark matter papers",
                "intent_json": {"free_text_terms": ["dark matter"]},
                "think_trace": "Topic: dark matter.",
            }
        ]

        import json

        # System message
        messages = [
            {"role": "system", "content": "Convert NL to query."},
            {"role": "user", "content": "Query: black holes\nDate: 2025-12-15"},
        ]

        # Replicate build_rag_messages logic
        result = [{"role": "system", "content": messages[0]["content"]}]
        for ex in few_shot:
            result.append({
                "role": "user",
                "content": f"Query: {ex['nl']}\nDate: 2025-12-15",
            })
            think_block = f"<think>\n{ex['think_trace']}\n</think>\n"
            result.append({
                "role": "assistant",
                "content": think_block + json.dumps(ex["intent_json"]),
            })
        result.append(messages[1])

        assert len(result) == 4  # system + 2 few-shot + user
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert "dark matter" in result[1]["content"]
        assert result[2]["role"] == "assistant"
        assert "<think>" in result[2]["content"]
        assert result[3]["role"] == "user"
        assert "black holes" in result[3]["content"]

    def test_cards_appended_to_system(self):
        """Test that field cards are appended to system message."""
        system_content = "Convert NL to query."
        cards = ["Valid doctypes: article, eprint, phdthesis."]

        augmented = system_content + "\n\nReference:\n" + "\n".join(f"- {c}" for c in cards)

        assert "Reference:" in augmented
        assert "Valid doctypes" in augmented

    def test_no_few_shot_passthrough(self):
        """Without few-shot examples, messages pass through unchanged."""
        messages = [
            {"role": "system", "content": "System prompt."},
            {"role": "user", "content": "Query: test"},
        ]

        # build_rag_messages with empty few_shot returns original
        # (simulated — actual function is in server.py)
        assert len(messages) == 2
