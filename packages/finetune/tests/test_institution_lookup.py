"""Tests for institution lookup module and its integration with NER/assembler."""

import pytest

from finetune.domains.scix.institution_lookup import (
    build_inst_or_aff_clause,
    lookup_inst_abbrevs,
    rewrite_aff_to_inst_or_aff,
)


# ============================================================================
# lookup_inst_abbrevs
# ============================================================================


class TestLookupInstAbbrevs:
    def test_direct_acronym(self):
        assert lookup_inst_abbrevs("MIT") == ["MIT"]

    def test_full_name(self):
        assert lookup_inst_abbrevs("Massachusetts Institute of Technology") == ["MIT"]

    def test_case_insensitive(self):
        assert lookup_inst_abbrevs("mit") == ["MIT"]
        assert lookup_inst_abbrevs("Mit") == ["MIT"]

    def test_umbrella_nasa(self):
        result = lookup_inst_abbrevs("NASA")
        assert set(result) == {"JPL", "GSFC", "NASA Ames", "MSFC"}

    def test_umbrella_max_planck(self):
        result = lookup_inst_abbrevs("Max Planck")
        assert set(result) == {"MPA", "MPE", "MPIA"}

    def test_umbrella_kavli(self):
        result = lookup_inst_abbrevs("Kavli")
        assert set(result) == {"KIPAC", "KITP"}

    def test_umbrella_harvard(self):
        assert lookup_inst_abbrevs("Harvard") == ["CfA"]

    def test_umbrella_goddard(self):
        assert lookup_inst_abbrevs("Goddard") == ["GSFC"]

    def test_unknown_returns_none(self):
        assert lookup_inst_abbrevs("University of Nowhere") is None

    def test_whitespace_stripped(self):
        assert lookup_inst_abbrevs("  MIT  ") == ["MIT"]


# ============================================================================
# build_inst_or_aff_clause
# ============================================================================


class TestBuildInstOrAffClause:
    def test_known_single(self):
        result = build_inst_or_aff_clause("MIT")
        assert result == '(inst:"MIT" OR aff:"MIT")'

    def test_known_umbrella(self):
        result = build_inst_or_aff_clause("NASA")
        assert 'inst:"JPL"' in result
        assert 'inst:"GSFC"' in result
        assert 'aff:"NASA"' in result
        assert result.startswith("(")
        assert result.endswith(")")

    def test_unknown_falls_back(self):
        result = build_inst_or_aff_clause("Unknown Place")
        assert result == 'aff:"Unknown Place"'

    def test_full_name(self):
        result = build_inst_or_aff_clause("European Southern Observatory")
        assert result == '(inst:"ESO" OR aff:"European Southern Observatory")'


# ============================================================================
# rewrite_aff_to_inst_or_aff
# ============================================================================


class TestRewriteAffToInstOrAff:
    def test_simple_quoted(self):
        query = 'aff:"MIT" abs:"exoplanets"'
        result = rewrite_aff_to_inst_or_aff(query)
        assert result == '(inst:"MIT" OR aff:"MIT") abs:"exoplanets"'

    def test_pos_not_rewritten(self):
        query = 'pos(aff:"MIT", 1)'
        result = rewrite_aff_to_inst_or_aff(query)
        assert result == query  # unchanged

    def test_trending_rewritten(self):
        query = "trending(aff:MIT)"
        result = rewrite_aff_to_inst_or_aff(query)
        assert 'inst:"MIT"' in result
        assert 'aff:"MIT"' in result

    def test_unknown_unchanged(self):
        query = 'aff:"unknown place"'
        result = rewrite_aff_to_inst_or_aff(query)
        assert result == query

    def test_no_aff_passthrough(self):
        query = 'abs:"exoplanets" author:"Smith"'
        result = rewrite_aff_to_inst_or_aff(query)
        assert result == query

    def test_multiple_affs(self):
        query = 'aff:"MIT" aff:"ESO"'
        result = rewrite_aff_to_inst_or_aff(query)
        assert '(inst:"MIT" OR aff:"MIT")' in result
        assert '(inst:"ESO" OR aff:"ESO")' in result

    def test_umbrella_expansion(self):
        query = 'aff:"NASA" abs:"mars"'
        result = rewrite_aff_to_inst_or_aff(query)
        assert 'inst:"JPL"' in result
        assert 'inst:"GSFC"' in result
        assert 'aff:"NASA"' in result
        assert 'abs:"mars"' in result


# ============================================================================
# NER integration
# ============================================================================


class TestNERAffiliationExtraction:
    def test_acronym_extraction(self):
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("papers from MIT on exoplanets")
        assert "MIT" in intent.affiliations

    def test_multi_word_extraction(self):
        from finetune.domains.scix.ner import extract_intent

        intent = extract_intent("researchers at Space Telescope Science Institute studying galaxies")
        assert "STScI" in intent.affiliations

    def test_ambiguous_requires_context(self):
        """Single ambiguous names like 'Cambridge' need context words."""
        from finetune.domains.scix.ner import extract_intent

        # Without context — should NOT extract
        intent = extract_intent("Cambridge observations of pulsars")
        assert "U Cambridge" not in intent.affiliations

        # With context — should extract
        intent = extract_intent("papers from Cambridge on pulsars")
        assert "U Cambridge" in intent.affiliations

    def test_no_false_positive_on_topic(self):
        """Acronyms that are also institution names should still match."""
        from finetune.domains.scix.ner import extract_intent

        # ESO is always an acronym, should match without context
        intent = extract_intent("ESO telescope data on asteroids")
        assert "ESO" in intent.affiliations


# ============================================================================
# Assembler integration
# ============================================================================


class TestAssemblerAffiliation:
    def test_assembler_produces_inst_or_aff(self):
        from finetune.domains.scix.assembler import _build_affiliation_clause

        result = _build_affiliation_clause(["MIT"])
        assert '(inst:"MIT" OR aff:"MIT")' == result

    def test_assembler_unknown_affiliation(self):
        from finetune.domains.scix.assembler import _build_affiliation_clause

        result = _build_affiliation_clause(["Some Unknown Lab"])
        assert result == 'aff:"Some Unknown Lab"'

    def test_assembler_multiple(self):
        from finetune.domains.scix.assembler import _build_affiliation_clause

        result = _build_affiliation_clause(["MIT", "ESO"])
        assert '(inst:"MIT" OR aff:"MIT")' in result
        assert '(inst:"ESO" OR aff:"ESO")' in result
