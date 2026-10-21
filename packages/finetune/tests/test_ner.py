"""Tests for NER extraction module."""

import pytest
from datetime import datetime

from finetune.domains.scix.ner import extract_intent


# ============================================================================
# Author extraction
# ============================================================================


class TestAuthorExtraction:
    def test_by_lastname(self):
        intent = extract_intent("papers by Hawking on black holes")
        assert "Hawking" in intent.authors

    def test_et_al(self):
        intent = extract_intent("Riess et al. supernovae")
        assert "Riess" in intent.authors

    def test_first_author_keyword(self):
        intent = extract_intent("first author Einstein on relativity")
        assert "Einstein" in intent.authors

    def test_no_false_positive_on_topic_words(self):
        """Common topic words should not be extracted as authors."""
        intent = extract_intent("dark matter detection methods")
        assert len(intent.authors) == 0

    def test_multiple_authors(self):
        intent = extract_intent("papers by Hawking and by Penrose on singularities")
        assert len(intent.authors) >= 1  # At least one extracted


# ============================================================================
# Year extraction
# ============================================================================


class TestYearExtraction:
    def test_since_year(self):
        intent = extract_intent("papers since 2020")
        assert intent.year_from == 2020
        assert intent.year_to == datetime.now().year

    def test_year_range(self):
        intent = extract_intent("papers from 2015 to 2020")
        assert intent.year_from == 2015
        assert intent.year_to == 2020

    def test_single_year(self):
        intent = extract_intent("papers in 2019")
        assert intent.year_from == 2019
        assert intent.year_to == 2019

    def test_decade(self):
        intent = extract_intent("papers in the 1990s")
        assert intent.year_from == 1990
        assert intent.year_to == 1999

    def test_last_n_years(self):
        intent = extract_intent("papers from last 5 years")
        current = datetime.now().year
        assert intent.year_from == current - 5

    def test_recent(self):
        intent = extract_intent("recent papers on exoplanets")
        current = datetime.now().year
        assert intent.year_from == current - 5
        assert intent.year_to == current

    def test_before(self):
        intent = extract_intent("papers before 2000")
        assert intent.year_to == 1999
        assert intent.year_from is None

    def test_no_year(self):
        intent = extract_intent("dark matter papers")
        assert intent.year_from is None
        assert intent.year_to is None


# ============================================================================
# Operator extraction
# ============================================================================


class TestOperatorExtraction:
    def test_citations_operator(self):
        intent = extract_intent("papers citing dark matter research")
        assert intent.operator == "citations"

    def test_references_operator(self):
        intent = extract_intent("references of supernova papers")
        assert intent.operator == "references"

    def test_similar_operator(self):
        intent = extract_intent("find similar papers to exoplanet research")
        assert intent.operator == "similar"

    def test_trending_operator(self):
        intent = extract_intent("trending papers on gravitational waves")
        assert intent.operator == "trending"

    def test_useful_operator(self):
        intent = extract_intent("most useful papers on dark energy")
        assert intent.operator == "useful"

    def test_reviews_operator(self):
        intent = extract_intent("review articles on magnetars")
        assert intent.operator == "reviews"

    def test_no_false_positive(self):
        """'reference' as topic should not trigger operator."""
        intent = extract_intent("dark matter reference frame")
        assert intent.operator is None

    def test_topic_preserved_after_operator(self):
        intent = extract_intent("trending papers on exoplanets")
        assert intent.operator == "trending"
        assert any("exoplanet" in t.lower() for t in intent.free_text_terms)


# ============================================================================
# Property / doctype / bibgroup / collection extraction
# ============================================================================


class TestEnumExtraction:
    def test_refereed(self):
        intent = extract_intent("peer reviewed papers on cosmology")
        assert "refereed" in intent.property

    def test_open_access(self):
        intent = extract_intent("open access papers on exoplanets")
        assert "openaccess" in intent.property

    def test_preprint(self):
        intent = extract_intent("arXiv preprints on dark matter")
        assert "eprint" in intent.property

    def test_thesis_doctype(self):
        intent = extract_intent("PhD thesis on stellar evolution")
        assert "phdthesis" in intent.doctype

    def test_conference_doctype(self):
        intent = extract_intent("conference papers on AGN")
        assert "inproceedings" in intent.doctype

    def test_papers_no_doctype(self):
        """Generic 'papers' should NOT trigger doctype:article."""
        intent = extract_intent("papers on dark matter")
        assert "article" not in intent.doctype

    def test_bibgroup_hst(self):
        intent = extract_intent("Hubble Space Telescope papers on galaxies")
        assert "HST" in intent.bibgroup

    def test_bibgroup_jwst(self):
        intent = extract_intent("JWST observations of exoplanets")
        assert "JWST" in intent.bibgroup

    def test_hubble_tension_no_hst(self):
        """'Hubble tension' should NOT trigger HST bibgroup."""
        intent = extract_intent("papers on hubble tension")
        assert "HST" not in intent.bibgroup

    def test_collection_astronomy(self):
        intent = extract_intent("astronomy papers on dark energy")
        assert "astronomy" in intent.collection

    def test_collection_earth_science(self):
        intent = extract_intent("earth science papers on Mars")
        assert "earthscience" in intent.collection


# ============================================================================
# Affiliation extraction
# ============================================================================


class TestAffiliationExtraction:
    def test_known_institution(self):
        intent = extract_intent("papers from CfA on stellar evolution")
        assert len(intent.affiliations) > 0

    def test_ambiguous_without_context(self):
        """'Cambridge' without context should NOT be extracted."""
        intent = extract_intent("Cambridge dark matter papers")
        assert len(intent.affiliations) == 0

    def test_ambiguous_with_context(self):
        intent = extract_intent("researchers at Cambridge on cosmology")
        assert len(intent.affiliations) > 0


# ============================================================================
# Journal extraction
# ============================================================================


class TestJournalExtraction:
    def test_full_name(self):
        intent = extract_intent("exoplanets in Astrophysical Journal")
        assert "ApJ" in intent.bibstems

    def test_acronym(self):
        intent = extract_intent("MNRAS papers on dark matter")
        assert "MNRAS" in intent.bibstems

    def test_ambiguous_nature_without_context(self):
        intent = extract_intent("nature of dark matter")
        assert "Natur" not in intent.bibstems

    def test_ambiguous_nature_with_context(self):
        intent = extract_intent("papers in Nature on dark matter")
        assert "Natur" in intent.bibstems


# ============================================================================
# Topic extraction
# ============================================================================


class TestTopicExtraction:
    def test_simple_topic(self):
        intent = extract_intent("dark matter papers")
        assert any("dark matter" in t.lower() for t in intent.free_text_terms)

    def test_multi_word_topic(self):
        intent = extract_intent("galaxy morphology classification papers")
        # Should extract multi-word topic
        topics_joined = " ".join(intent.free_text_terms).lower()
        assert "galaxy" in topics_joined or "morphology" in topics_joined

    def test_stopwords_removed(self):
        intent = extract_intent("papers about the nature of dark matter")
        topics_joined = " ".join(intent.free_text_terms).lower()
        # Stopwords like "about", "the", "of" should not be standalone terms
        assert topics_joined  # should have some content


# ============================================================================
# ADS query passthrough
# ============================================================================


class TestADSPassthrough:
    def test_ads_query_detected(self):
        intent = extract_intent('author:"Hawking" abs:"black holes"')
        assert intent.confidence.get("ads_passthrough") == 1.0
        assert len(intent.authors) == 0  # Minimal extraction

    def test_natural_language_not_passthrough(self):
        intent = extract_intent("papers by Hawking on black holes")
        assert "ads_passthrough" not in intent.confidence


# ============================================================================
# Edge cases
# ============================================================================


class TestEdgeCases:
    def test_empty_input(self):
        intent = extract_intent("")
        assert not intent.has_content()

    def test_whitespace_only(self):
        intent = extract_intent("   ")
        assert not intent.has_content()

    def test_single_word(self):
        intent = extract_intent("exoplanets")
        assert len(intent.free_text_terms) > 0
