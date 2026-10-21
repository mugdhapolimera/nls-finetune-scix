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


class TestMisplacedFieldValueRepair:
    """Tests for _fix_misplaced_field_values — abs:/title: terms that belong in doctype:/property:."""

    def test_not_abs_preprint_to_not_doctype_eprint(self):
        """NOT abs:"preprint" -> NOT doctype:eprint."""
        result = constrain_query_output('abs:"cosmology" NOT abs:"preprint"')
        assert 'NOT doctype:eprint' in result
        assert 'abs:"cosmology"' in result
        assert 'abs:"preprint"' not in result

    def test_abs_preprint_positive(self):
        """abs:"preprint" alone -> doctype:eprint."""
        result = constrain_query_output('abs:"preprint"')
        assert result == "doctype:eprint"

    def test_not_abs_refereed(self):
        """NOT abs:"refereed" -> NOT property:refereed."""
        result = constrain_query_output('abs:"dark matter" NOT abs:"refereed"')
        assert "NOT property:refereed" in result
        assert 'abs:"refereed"' not in result

    def test_abs_open_access(self):
        """abs:"open access" -> property:openaccess."""
        result = constrain_query_output('abs:"open access"')
        assert result == "property:openaccess"

    def test_dash_negation_abs_preprint(self):
        """-abs:"preprint" -> -doctype:eprint."""
        result = constrain_query_output('abs:"cosmology" -abs:"preprint"')
        assert "-doctype:eprint" in result
        assert 'abs:"preprint"' not in result

    def test_unquoted_abs_preprint(self):
        """abs:preprint -> doctype:eprint (unquoted form)."""
        result = constrain_query_output("abs:preprint")
        assert result == "doctype:eprint"

    def test_title_preprint(self):
        """title:"preprint" -> doctype:eprint (also catches title: field)."""
        result = constrain_query_output('title:"preprint"')
        assert result == "doctype:eprint"

    def test_preserves_real_abs_terms(self):
        """Real abstract terms should NOT be redirected."""
        query = 'abs:"dark matter" abs:"cosmology"'
        assert constrain_query_output(query) == query

    def test_complex_query_with_redirect(self):
        """Full query: cosmology papers excluding preprints."""
        result = constrain_query_output(
            'abs:"cosmology" property:eprint NOT abs:"preprint"'
        )
        assert 'abs:"cosmology"' in result
        assert "property:eprint" in result
        assert "NOT doctype:eprint" in result
        assert 'abs:"preprint"' not in result

    def test_not_abs_peer_reviewed(self):
        """NOT abs:"peer-reviewed" -> NOT property:refereed."""
        result = constrain_query_output('abs:"galaxy" NOT abs:"peer-reviewed"')
        assert "NOT property:refereed" in result

    def test_abs_software_not_redirected(self):
        """abs:"software" should NOT be redirected — software is a valid abstract topic."""
        query = 'abs:"software"'
        result = constrain_query_output(query)
        assert result == query  # Unchanged — "software" is ambiguous

    # ============================================================
    # Data-driven redirect: auto-detected enum values
    # ============================================================

    def test_abs_nonarticle_redirected(self):
        """abs:"nonarticle" -> property:nonarticle (auto-detected from FIELD_ENUMS)."""
        result = constrain_query_output('abs:"nonarticle"')
        assert result == "property:nonarticle"

    def test_abs_notrefereed_redirected(self):
        """abs:"notrefereed" -> property:notrefereed (auto-detected)."""
        result = constrain_query_output('abs:"notrefereed"')
        assert result == "property:notrefereed"

    def test_abs_phdthesis_redirected(self):
        """abs:"phdthesis" -> doctype:phdthesis (auto-detected)."""
        result = constrain_query_output('abs:"phdthesis"')
        assert result == "doctype:phdthesis"

    def test_abs_erratum_redirected(self):
        """abs:"erratum" -> doctype:erratum (auto-detected)."""
        result = constrain_query_output('abs:"erratum"')
        assert result == "doctype:erratum"

    def test_abs_pressrelease_redirected(self):
        """abs:"pressrelease" -> doctype:pressrelease (auto-detected)."""
        result = constrain_query_output('abs:"pressrelease"')
        assert result == "doctype:pressrelease"

    def test_abs_pub_pdf_redirected(self):
        """abs:"PUB_PDF" -> esources:PUB_PDF (auto-detected)."""
        result = constrain_query_output('abs:"PUB_PDF"')
        assert result == "esources:PUB_PDF"

    def test_abs_ads_scan_redirected(self):
        """abs:"ADS_SCAN" -> esources:ADS_SCAN (auto-detected)."""
        result = constrain_query_output('abs:"ADS_SCAN"')
        assert result == "esources:ADS_SCAN"

    def test_abs_eprint_redirected(self):
        """abs:"eprint" -> doctype:eprint (via reverse index, not just synonym)."""
        result = constrain_query_output('abs:"eprint"')
        assert result == "doctype:eprint"

    def test_abs_openaccess_redirected(self):
        """abs:"openaccess" -> property:openaccess (via reverse index)."""
        result = constrain_query_output('abs:"openaccess"')
        assert result == "property:openaccess"

    def test_not_abs_nonarticle(self):
        """NOT abs:"nonarticle" -> NOT property:nonarticle."""
        result = constrain_query_output('abs:"dark energy" NOT abs:"nonarticle"')
        assert "NOT property:nonarticle" in result
        assert 'abs:"dark energy"' in result

    def test_unquoted_eprint_redirected(self):
        """abs:eprint -> doctype:eprint (unquoted, auto-detected)."""
        result = constrain_query_output("abs:eprint")
        assert result == "doctype:eprint"

    # ============================================================
    # Safelist: values that must NOT be redirected
    # ============================================================

    def test_abs_astronomy_not_redirected(self):
        """abs:"astronomy" should NOT be redirected (common topic word)."""
        query = 'abs:"astronomy"'
        assert constrain_query_output(query) == query

    def test_abs_book_not_redirected(self):
        """abs:"book" should NOT be redirected (common English word)."""
        query = 'abs:"book"'
        assert constrain_query_output(query) == query

    def test_abs_data_not_redirected(self):
        """abs:"data" should NOT be redirected (common word)."""
        query = 'abs:"data"'
        assert constrain_query_output(query) == query

    def test_abs_circular_not_redirected(self):
        """abs:"circular" should NOT be redirected (circular polarization, etc.)."""
        query = 'abs:"circular"'
        assert constrain_query_output(query) == query

    def test_abs_kepler_not_redirected(self):
        """abs:"kepler" should NOT be redirected (telescope name in abstracts)."""
        query = 'abs:"kepler"'
        assert constrain_query_output(query) == query

    def test_abs_chandra_not_redirected(self):
        """abs:"Chandra" should NOT be redirected (telescope name in abstracts)."""
        query = 'abs:"Chandra"'
        assert constrain_query_output(query) == query

    def test_abs_mast_not_redirected(self):
        """abs:"MAST" should NOT be redirected (archive name in abstracts)."""
        query = 'abs:"MAST"'
        assert constrain_query_output(query) == query

    def test_abs_grant_not_redirected(self):
        """abs:"grant" should NOT be redirected (has: value, semantic mismatch)."""
        query = 'abs:"grant"'
        assert constrain_query_output(query) == query

    def test_multiple_redirects_in_one_query(self):
        """Multiple misplaced values should all be redirected."""
        result = constrain_query_output(
            'abs:"phdthesis" NOT abs:"preprint" abs:"dark matter"'
        )
        assert "doctype:phdthesis" in result
        assert "NOT doctype:eprint" in result
        assert 'abs:"dark matter"' in result


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


class TestSpacedOutRangeRepair:
    """Tests for _fix_spaced_out_ranges — LLM tokenization artifact."""

    def test_spaced_out_numeric_range(self):
        """[1 0 0 T O *] → [100 TO *]."""
        result = constrain_query_output("citation_count:[1 0 0 T O *]")
        assert result == "citation_count:[100 TO *]"

    def test_spaced_out_year_range(self):
        """[2 0 2 0 T O 2 0 2 5] → [2020 TO 2025]."""
        result = constrain_query_output("pubdate:[2 0 2 0 T O 2 0 2 5]")
        assert result == "pubdate:[2020 TO 2025]"

    def test_spaced_out_with_star(self):
        """[1 0 T O *] → [10 TO *]."""
        result = constrain_query_output("citation_count:[1 0 T O *]")
        assert result == "citation_count:[10 TO *]"

    def test_normal_range_unchanged(self):
        """Already correct range should not change."""
        query = "pubdate:[2020 TO 2025]"
        assert constrain_query_output(query) == query

    def test_normal_star_range_unchanged(self):
        """Star range should not change."""
        query = "citation_count:[100 TO *]"
        assert constrain_query_output(query) == query

    def test_spaced_out_in_complex_query(self):
        """Spaced-out range in larger query."""
        result = constrain_query_output(
            'abs:"dark matter" citation_count:[1 0 0 T O *]'
        )
        assert 'abs:"dark matter"' in result
        assert "[100 TO *]" in result

    def test_spaced_out_inside_operator(self):
        """Spaced-out bare range inside operator parens is stripped (no field prefix)."""
        result = constrain_query_output('useful(abs:"test") [1 0 T O *]')
        # Bare range without field prefix is meaningless — gets stripped
        assert "[10 TO *]" not in result
        assert 'useful(abs:"test")' in result

    def test_chains_with_backwards_year_fix(self):
        """Spaced-out range that is also backwards gets both fixes."""
        result = constrain_query_output("pubdate:[2 0 2 5 T O 2 0 2 0]")
        assert result == "pubdate:[2020 TO 2025]"


class TestUnbalancedQuoteRepair:
    """Tests for _fix_unbalanced_quotes — missing closing quote."""

    def test_missing_closing_quote_at_end(self):
        """abs:"dark matter → abs:"dark matter"."""
        result = constrain_query_output('abs:"dark matter')
        assert result == 'abs:"dark matter"'

    def test_missing_closing_quote_before_field(self):
        """Missing close before next field."""
        result = constrain_query_output('abs:"dark matter pubdate:[2020 TO 2025]')
        assert 'abs:"dark matter"' in result
        assert "pubdate:[2020 TO 2025]" in result

    def test_balanced_quotes_unchanged(self):
        """Balanced quotes should not change."""
        query = 'abs:"dark matter" author:"Hawking"'
        assert constrain_query_output(query) == query

    def test_stray_quote_not_after_field_left_alone(self):
        """Stray quote not preceded by field: is left alone."""
        # Odd quote count but not after a field: — don't try to fix
        query = '"dark matter'
        result = constrain_query_output(query)
        # Should not crash; exact behavior depends on downstream cleanup
        assert result is not None

    def test_missing_quote_with_title_field(self):
        """title:"gravitational waves → title:"gravitational waves"."""
        result = constrain_query_output('title:"gravitational waves')
        assert result == 'title:"gravitational waves"'


class TestStripNonAdsSyntax:
    """Tests for _strip_non_ads_syntax via constrain_query_output."""

    def test_strip_json_fragment(self):
        """JSON fragment appended to valid query should be stripped."""
        result = constrain_query_output('abs:"test" {"k": "v"}')
        assert result == 'abs:"test"'

    def test_strip_complex_json(self):
        """Complex JSON object should be stripped."""
        result = constrain_query_output('abs:"supernova" {"journals": ["Nature", "Science"]}')
        assert result == 'abs:"supernova"'

    def test_strip_unknown_field(self):
        """Unknown field:value pairs should be stripped."""
        result = constrain_query_output('abs:"test" journals:"Nature"')
        assert result == 'abs:"test"'

    def test_strip_unknown_field_topics(self):
        """Unknown field 'topics' should be stripped."""
        result = constrain_query_output('abs:"test" topics:"exoplanets"')
        assert result == 'abs:"test"'

    def test_preserve_known_fields(self):
        """Known fields should be preserved."""
        query = 'abs:"test" bibstem:"ApJ"'
        assert constrain_query_output(query) == query

    def test_preserve_pubdate_range(self):
        """pubdate range should be preserved."""
        query = "pubdate:[2020 TO 2025]"
        assert constrain_query_output(query) == query

    def test_preserve_citation_count(self):
        """citation_count field should be preserved."""
        query = "citation_count:[100 TO *]"
        assert constrain_query_output(query) == query

    def test_strip_json_keep_valid_query(self):
        """JSON + valid query: JSON stripped, valid part kept."""
        result = constrain_query_output(
            'abs:"supernova light curves" bibstem:"Natur" {"journals": ["Nature", "Science"]}'
        )
        assert "abs:" in result
        assert "bibstem:" in result
        assert "{" not in result
        assert "}" not in result

    def test_empty_after_strip(self):
        """Query that is entirely JSON should become empty."""
        result = constrain_query_output('{"query": "test"}')
        assert result == ""

    def test_nested_json(self):
        """Nested JSON should be fully stripped."""
        result = constrain_query_output('abs:"test" {"a": {"b": "c"}}')
        assert result == 'abs:"test"'


class TestBareRangeStripping:
    """Tests for stripping bare [X TO Y] ranges without a field prefix."""

    def test_bare_range_stripped(self):
        """[100 TO *] without field prefix should be stripped."""
        result = constrain_query_output('abs:"test" [100 TO *]')
        assert result == 'abs:"test"'

    def test_bare_range_with_field_preserved(self):
        """citation_count:[100 TO *] should be preserved."""
        query = 'abs:"test" citation_count:[100 TO *]'
        assert constrain_query_output(query) == query

    def test_bare_pubdate_range_with_field_preserved(self):
        """pubdate:[2020 TO 2025] should be preserved."""
        query = "pubdate:[2020 TO 2025]"
        assert constrain_query_output(query) == query

    def test_bare_range_inside_operator(self):
        """Bare range after operator should be stripped."""
        result = constrain_query_output('useful(abs:"test") [100 TO *]')
        assert result == 'useful(abs:"test")'

    def test_multiple_bare_ranges_stripped(self):
        """Multiple bare ranges should all be stripped."""
        result = constrain_query_output('abs:"test" [10 TO *] [2020 TO 2025]')
        assert result == 'abs:"test"'
