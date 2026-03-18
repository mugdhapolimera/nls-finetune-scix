"""Tests for constrain_query_output function - post-processing filter for model output."""

import logging


from finetune.domains.scix.constrain import constrain_query_output


class TestConstrainQueryOutput:
    """Tests for constrain_query_output function."""

    # ============================================================
    # Basic valid queries - should remain unchanged
    # ============================================================

    def test_valid_doctype_article_unchanged(self):
        """Valid doctype should remain unchanged."""
        assert constrain_query_output("doctype:article") == "doctype:article"

    def test_valid_property_refereed_unchanged(self):
        """Valid property should remain unchanged."""
        assert constrain_query_output("property:refereed") == "property:refereed"

    def test_valid_database_astronomy_unchanged(self):
        """Valid database should remain unchanged."""
        assert constrain_query_output("database:astronomy") == "database:astronomy"

    def test_valid_combination_preserved(self):
        """Valid field combinations should be preserved."""
        query = "doctype:article AND property:refereed"
        assert constrain_query_output(query) == "doctype:article AND property:refereed"

    # ============================================================
    # Invalid field values - should be removed
    # ============================================================

    def test_invalid_doctype_journal_corrected(self):
        """'journal' is corrected to 'article' via enum misspelling repair."""
        assert constrain_query_output("doctype:journal") == "doctype:article"

    def test_invalid_doctype_paper_corrected(self):
        """'paper' is corrected to 'article' via enum misspelling repair."""
        assert constrain_query_output("doctype:paper") == "doctype:article"

    def test_invalid_property_peerreviewed_corrected(self):
        """'peerreviewed' is corrected to 'refereed' via enum misspelling repair."""
        assert constrain_query_output("property:peerreviewed") == "property:refereed"

    def test_invalid_database_astro_corrected(self):
        """'astro' is corrected to 'astronomy' via enum misspelling repair."""
        assert constrain_query_output("database:astro") == "database:astronomy"

    def test_invalid_property_reviewed_corrected(self):
        """'reviewed' is corrected to 'refereed' via enum misspelling repair."""
        assert constrain_query_output("property:reviewed") == "property:refereed"

    # ============================================================
    # Mixed valid and invalid - only invalid removed
    # ============================================================

    def test_mixed_valid_invalid_preserves_valid(self):
        """Mix of valid and correctable should keep both parts."""
        query = "doctype:article AND property:peerreviewed"
        assert constrain_query_output(query) == "doctype:article AND property:refereed"

    def test_invalid_between_valid_fields(self):
        """Invalid field between valid ones should be removed."""
        query = "doctype:article property:fake database:astronomy"
        assert constrain_query_output(query) == "doctype:article database:astronomy"

    def test_multiple_invalid_all_corrected(self):
        """Multiple correctable values all fixed."""
        query = "doctype:journal database:astro"
        assert constrain_query_output(query) == "doctype:article database:astronomy"

    # ============================================================
    # OR list handling
    # ============================================================

    def test_or_list_all_valid(self):
        """OR list with all valid values preserved."""
        query = "doctype:(article OR eprint)"
        assert constrain_query_output(query) == "doctype:(article OR eprint)"

    def test_or_list_partial_valid(self):
        """OR list with some invalid values filters them out."""
        query = "doctype:(article OR journal OR eprint)"
        result = constrain_query_output(query)
        assert result == "doctype:(article OR eprint)"

    def test_or_list_single_valid_unwrapped(self):
        """OR list reducing to single value removes parens."""
        query = "doctype:(article OR journal)"
        # journal is invalid, only article remains
        assert constrain_query_output(query) == "doctype:article"

    def test_or_list_all_invalid_removed(self):
        """OR list with all invalid values removed entirely."""
        query = "doctype:(journal OR paper)"
        assert constrain_query_output(query) == ""

    # ============================================================
    # Quoted values
    # ============================================================

    def test_quoted_valid_value_preserved(self):
        """Quoted valid values should be preserved."""
        assert constrain_query_output('doctype:"article"') == 'doctype:"article"'

    def test_quoted_invalid_value_corrected(self):
        """Quoted invalid values should be corrected via misspelling repair."""
        assert constrain_query_output('doctype:"journal"') == "doctype:article"

    # ============================================================
    # Trailing/leading operator cleanup
    # ============================================================

    def test_trailing_and_with_correction(self):
        """Both sides corrected/valid, AND preserved."""
        query = "doctype:journal AND property:refereed"
        assert constrain_query_output(query) == "doctype:article AND property:refereed"

    def test_leading_and_with_correction(self):
        """Both sides corrected/valid, AND preserved."""
        query = "property:refereed AND doctype:journal"
        assert constrain_query_output(query) == "property:refereed AND doctype:article"

    def test_double_and_with_correction(self):
        """journal corrected to article, all valid."""
        query = "doctype:article AND doctype:journal AND property:refereed"
        assert (
            constrain_query_output(query)
            == "doctype:article AND doctype:article AND property:refereed"
        )

    def test_trailing_or_with_correction(self):
        """journal corrected to article, OR preserved."""
        query = "property:refereed OR doctype:journal"
        assert constrain_query_output(query) == "property:refereed OR doctype:article"

    # ============================================================
    # Edge cases - empty, whitespace, unconstrained fields
    # ============================================================

    def test_empty_string(self):
        """Empty string returns empty."""
        assert constrain_query_output("") == ""

    def test_whitespace_only(self):
        """Whitespace only returns empty."""
        assert constrain_query_output("   ") == ""

    def test_unconstrained_fields_preserved(self):
        """Fields without constraints are preserved."""
        query = 'author:"Einstein" abs:relativity'
        assert constrain_query_output(query) == 'author:"Einstein" abs:relativity'

    def test_mixed_constrained_unconstrained(self):
        """Mix of constrained and unconstrained fields."""
        query = 'author:"Hawking" doctype:journal abs:"black holes"'
        result = constrain_query_output(query)
        assert result == 'author:"Hawking" doctype:article abs:"black holes"'

    # ============================================================
    # Common model hallucinations
    # ============================================================

    def test_hallucination_doctype_research(self):
        """Model might output 'research' - corrected to 'article'."""
        assert constrain_query_output("doctype:research") == "doctype:article"

    def test_hallucination_property_peer_reviewed(self):
        """Model might output 'peer_reviewed' - corrected to 'refereed'."""
        assert constrain_query_output("property:peer_reviewed") == "property:refereed"

    def test_hallucination_doctype_publication(self):
        """Model might output 'publication' - corrected to 'article'."""
        assert constrain_query_output("doctype:publication") == "doctype:article"

    def test_hallucination_database_astrophysics(self):
        """Model might confuse 'astrophysics' - corrected to 'astronomy'."""
        assert constrain_query_output("database:astrophysics") == "database:astronomy"

    def test_hallucination_property_open_access(self):
        """Model might output 'open_access' - corrected to 'openaccess'."""
        assert constrain_query_output("property:open_access") == "property:openaccess"

    def test_hallucination_bibgroup_hubble(self):
        """Model might use 'Hubble' instead of 'HST'."""
        assert constrain_query_output("bibgroup:Hubble") == ""

    def test_hallucination_esources_pdf(self):
        """Model might hallucinate simple 'pdf'."""
        assert constrain_query_output("esources:pdf") == ""

    # ============================================================
    # Complex queries with multiple issues
    # ============================================================

    def test_complex_query_partial_cleanup(self):
        """Complex query with correctable and valid fields."""
        query = 'doctype:article AND property:peerreviewed AND database:astronomy abs:"cosmology"'
        result = constrain_query_output(query)
        assert "doctype:article" in result
        assert "property:refereed" in result
        assert "database:astronomy" in result
        assert 'abs:"cosmology"' in result
        assert "peerreviewed" not in result

    def test_multiple_or_lists(self):
        """Multiple OR lists in same query."""
        query = "doctype:(article OR journal) property:(refereed OR reviewed)"
        result = constrain_query_output(query)
        assert result == "doctype:article property:refereed"

    # ============================================================
    # Parentheses handling
    # ============================================================

    def test_empty_parens_removed(self):
        """Empty parentheses from removal should be cleaned."""
        query = "doctype:(journal)"
        result = constrain_query_output(query)
        assert result == ""
        assert "()" not in result

    def test_unbalanced_parens_fixed(self):
        """Unbalanced parentheses should be handled."""
        query = "doctype:article ("
        result = constrain_query_output(query)
        assert result.count("(") == result.count(")")

    # ============================================================
    # Case sensitivity
    # ============================================================

    def test_case_insensitive_valid(self):
        """Validation should be case-insensitive."""
        assert constrain_query_output("doctype:ARTICLE") == "doctype:ARTICLE"

    def test_case_insensitive_invalid(self):
        """Invalid check should be case-insensitive (corrected)."""
        assert constrain_query_output("doctype:JOURNAL") == "doctype:article"

    # ============================================================
    # Logging warnings
    # ============================================================

    def test_logs_warning_for_corrected_field(self, caplog):
        """Should log warning when correcting misspelled enum value."""
        with caplog.at_level(logging.WARNING):
            constrain_query_output("doctype:journal")
        assert "Fixed enum value" in caplog.text
        assert "doctype" in caplog.text

    def test_logs_multiple_warnings(self, caplog):
        """Should log warning for each corrected value."""
        with caplog.at_level(logging.WARNING):
            constrain_query_output("doctype:journal database:astro")
        assert "doctype" in caplog.text
        assert "database" in caplog.text


class TestFirstAuthorCaretRepair:
    """Tests for _fix_first_author_caret."""

    def test_caret_before_author_field(self):
        """^author:"Last" -> author:"^Last"."""
        assert constrain_query_output('^author:"Hawking"') == 'author:"^Hawking"'

    def test_caret_between_field_and_quote(self):
        """author:^"Last" -> author:"^Last"."""
        assert constrain_query_output('author:^"Hawking"') == 'author:"^Hawking"'

    def test_correct_caret_unchanged(self):
        """Correctly placed caret should not change."""
        assert constrain_query_output('author:"^Hawking"') == 'author:"^Hawking"'

    def test_caret_with_full_name(self):
        """Caret with full name format."""
        assert constrain_query_output('^author:"Hawking, S"') == 'author:"^Hawking, S"'

    def test_caret_in_complex_query(self):
        """Caret fix in multi-field query."""
        result = constrain_query_output('^author:"Hawking" abs:"black holes"')
        assert 'author:"^Hawking"' in result
        assert 'abs:"black holes"' in result


class TestBackwardsYearRangeRepair:
    """Tests for _fix_backwards_year_range."""

    def test_backwards_range_swapped(self):
        """pubdate:[2025 TO 2020] -> pubdate:[2020 TO 2025]."""
        result = constrain_query_output("pubdate:[2025 TO 2020]")
        assert result == "pubdate:[2020 TO 2025]"

    def test_correct_range_unchanged(self):
        """Correct range should not change."""
        assert constrain_query_output("pubdate:[2020 TO 2025]") == "pubdate:[2020 TO 2025]"

    def test_same_year_unchanged(self):
        """Same year range should not change."""
        assert constrain_query_output("pubdate:[2020 TO 2020]") == "pubdate:[2020 TO 2020]"

    def test_backwards_range_in_complex_query(self):
        """Backwards range fix in multi-field query."""
        result = constrain_query_output('abs:"dark matter" pubdate:[2025 TO 2020]')
        assert "pubdate:[2020 TO 2025]" in result
        assert 'abs:"dark matter"' in result


class TestUnquotedOperatorValueRepair:
    """Tests for _fix_unquoted_operator_values."""

    def test_unquoted_multi_word_in_citations(self):
        """citations(abs:dark matter) -> citations(abs:"dark matter")."""
        result = constrain_query_output("citations(abs:dark matter)")
        assert 'citations(abs:"dark matter")' == result

    def test_unquoted_multi_word_in_trending(self):
        """trending(abs:exoplanet atmospheres) -> trending(abs:"exoplanet atmospheres")."""
        result = constrain_query_output("trending(abs:exoplanet atmospheres)")
        assert 'trending(abs:"exoplanet atmospheres")' == result

    def test_already_quoted_unchanged(self):
        """Already quoted values should not change."""
        query = 'citations(abs:"dark matter")'
        assert constrain_query_output(query) == query

    def test_single_word_unchanged(self):
        """Single-word values don't need quoting."""
        query = "trending(abs:exoplanet)"
        result = constrain_query_output(query)
        assert "exoplanet" in result


class TestEnumMisspellingRepair:
    """Tests for _fix_common_enum_misspellings."""

    def test_preprint_to_eprint(self):
        """doctype:preprint -> doctype:eprint."""
        assert constrain_query_output("doctype:preprint") == "doctype:eprint"

    def test_journal_to_article(self):
        """doctype:journal -> doctype:article (via correction)."""
        assert constrain_query_output("doctype:journal") == "doctype:article"

    def test_peer_reviewed_to_refereed(self):
        """property:peer-reviewed -> property:refereed."""
        assert constrain_query_output("property:peer-reviewed") == "property:refereed"

    def test_astrophysics_to_astronomy(self):
        """database:astrophysics -> database:astronomy."""
        assert constrain_query_output("database:astrophysics") == "database:astronomy"

    def test_open_access_to_openaccess(self):
        """property:open_access -> property:openaccess."""
        assert constrain_query_output("property:open_access") == "property:openaccess"

    def test_correction_in_complex_query(self):
        """Corrections applied within complex queries."""
        result = constrain_query_output('doctype:preprint abs:"gravitational waves"')
        assert "doctype:eprint" in result
        assert 'abs:"gravitational waves"' in result

    def test_conference_to_inproceedings(self):
        """doctype:conference -> doctype:inproceedings."""
        assert constrain_query_output("doctype:conference") == "doctype:inproceedings"
