"""Tests for bibstem lookup module and its integration with NER/assembler."""

import pytest

from finetune.domains.scix.bibstem_lookup import (
    build_bibstem_clause,
    lookup_bibstem,
    rewrite_bibstem_values,
)


# ============================================================================
# lookup_bibstem
# ============================================================================


class TestLookupBibstem:
    def test_full_name(self):
        assert lookup_bibstem("Astrophysical Journal") == "ApJ"

    def test_abbreviation(self):
        assert lookup_bibstem("MNRAS") == "MNRAS"

    def test_common_acronym(self):
        assert lookup_bibstem("PRL") == "PhRvL"

    def test_case_insensitive(self):
        assert lookup_bibstem("astrophysical journal") == "ApJ"
        assert lookup_bibstem("ASTROPHYSICAL JOURNAL") == "ApJ"

    def test_unknown_returns_none(self):
        assert lookup_bibstem("Journal of Obscure Things") is None

    def test_whitespace_stripped(self):
        assert lookup_bibstem("  ApJ  ") == "ApJ"

    def test_the_prefix(self):
        assert lookup_bibstem("The Astrophysical Journal") == "ApJ"

    def test_abbreviated_form(self):
        assert lookup_bibstem("Phys. Rev. Lett.") == "PhRvL"

    def test_arxiv(self):
        assert lookup_bibstem("arXiv") == "arXiv"


# ============================================================================
# build_bibstem_clause
# ============================================================================


class TestBuildBibstemClause:
    def test_known_journal(self):
        assert build_bibstem_clause("Astrophysical Journal") == 'bibstem:"ApJ"'

    def test_unknown_falls_back(self):
        assert build_bibstem_clause("Unknown Journal") == 'abs:"Unknown Journal"'

    def test_acronym(self):
        assert build_bibstem_clause("MNRAS") == 'bibstem:"MNRAS"'


# ============================================================================
# rewrite_bibstem_values
# ============================================================================


class TestRewriteBibstemValues:
    def test_full_name_rewritten(self):
        query = 'bibstem:"Astrophysical Journal" abs:"exoplanets"'
        result = rewrite_bibstem_values(query)
        assert result == 'bibstem:"ApJ" abs:"exoplanets"'

    def test_already_correct_unchanged(self):
        query = 'bibstem:"ApJ" abs:"exoplanets"'
        result = rewrite_bibstem_values(query)
        assert result == query

    def test_bare_bibstem_quoted(self):
        query = "bibstem:ApJ abs:exoplanets"
        result = rewrite_bibstem_values(query)
        assert 'bibstem:"ApJ"' in result

    def test_no_bibstem_passthrough(self):
        query = 'abs:"exoplanets" author:"Smith"'
        result = rewrite_bibstem_values(query)
        assert result == query

    def test_multiple_bibstems(self):
        query = 'bibstem:"Astrophysical Journal" bibstem:"Monthly Notices of the Royal Astronomical Society"'
        result = rewrite_bibstem_values(query)
        assert 'bibstem:"ApJ"' in result
        assert 'bibstem:"MNRAS"' in result

    def test_unknown_bare_bibstem_just_quoted(self):
        query = "bibstem:UNKNOWN"
        result = rewrite_bibstem_values(query)
        assert result == 'bibstem:"UNKNOWN"'

    def test_prl_to_phrvl(self):
        query = 'bibstem:"Physical Review Letters"'
        result = rewrite_bibstem_values(query)
        assert result == 'bibstem:"PhRvL"'


# ============================================================================
# NER integration
# ============================================================================


class TestNERJournalExtraction:
    def test_multi_word_journal(self):
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("exoplanets in Astrophysical Journal")
        assert "ApJ" in intent.bibstems

    def test_acronym_journal(self):
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("MNRAS papers on dark matter")
        assert "MNRAS" in intent.bibstems

    def test_ambiguous_without_context_no_match(self):
        """'Nature' without context word should NOT be extracted as journal."""
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("nature of dark matter")
        assert "Natur" not in intent.bibstems

    def test_ambiguous_with_context_matches(self):
        """'Nature' with 'in' context should be extracted."""
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("papers in Nature on dark matter")
        assert "Natur" in intent.bibstems

    def test_science_ambiguous(self):
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("citizen science projects")
        assert "Sci" not in intent.bibstems

    def test_science_with_context(self):
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("published in Science about CRISPR")
        assert "Sci" in intent.bibstems

    def test_journal_removed_from_topics(self):
        """Journal name should be removed from text, not appear as topic."""
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("exoplanets in Astrophysical Journal")
        assert "ApJ" in intent.bibstems
        # "astrophysical journal" should NOT appear in free text
        for term in intent.free_text_terms:
            assert "astrophysical" not in term.lower()

    def test_arxiv_as_property(self):
        """arXiv is consumed by property extraction as eprint, not as bibstem."""
        from finetune.domains.scix.ner import extract_intent

        # "arxiv" maps to property:eprint before journal extraction runs
        intent = extract_intent("arXiv preprints on cosmology")
        assert "eprint" in intent.property

    def test_arxiv_bibstem_lookup_works(self):
        """Direct lookup of arXiv as bibstem still works."""
        assert lookup_bibstem("arXiv") == "arXiv"


# ============================================================================
# Assembler integration
# ============================================================================


class TestAssemblerBibstem:
    def test_single_bibstem(self):
        from finetune.domains.scix.assembler import _build_bibstem_clause

        result = _build_bibstem_clause(["ApJ"])
        assert result == 'bibstem:"ApJ"'

    def test_multiple_bibstems(self):
        from finetune.domains.scix.assembler import _build_bibstem_clause

        result = _build_bibstem_clause(["ApJ", "MNRAS"])
        assert result == '(bibstem:"ApJ" OR bibstem:"MNRAS")'

    def test_empty_bibstems(self):
        from finetune.domains.scix.assembler import _build_bibstem_clause

        assert _build_bibstem_clause([]) == ""

    def test_full_pipeline(self):
        """End-to-end: NER extraction -> assembler produces bibstem clause."""
        from finetune.domains.scix.ner import extract_intent
        from finetune.domains.scix.assembler import assemble_query

        intent = extract_intent("exoplanets in Astrophysical Journal since 2020")
        query = assemble_query(intent)
        assert 'bibstem:"ApJ"' in query
        assert "abs:" in query  # should have topic
