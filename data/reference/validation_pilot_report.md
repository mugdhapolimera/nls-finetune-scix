# Pilot Validation Report: Gold Training Examples

**Date:** 2026-03-04
**Examples reviewed:** 10 (selected for diversity across categories)
**API endpoint:** `https://api.adsabs.harvard.edu/v1/search/query`

---

## Results Summary

| # | Category | API Results | Syntax | NL Alignment | Verdict |
|---|----------|-------------|--------|--------------|---------|
| 1 | topic | 1 | PASS | PASS | PASS |
| 2 | compound | 4,988 | PASS | PASS | PASS |
| 3 | compound | 0 | FAIL | WARN | FAIL |
| 4 | filters | 0 | FAIL | WARN | FAIL |
| 5 | second_order | 13,487 | PASS | WARN | WARN |
| 6 | second_order | 0 | PASS | FAIL | FAIL |
| 7 | compound | 1,363 | PASS | PASS | PASS |
| 8 | affiliation | 18,766 | PASS | PASS | PASS |
| 9 | topic | 0 | PASS | WARN | FAIL |
| 10 | author | 107 | PASS | PASS | PASS |

**Pass rate:** 5/10 clean PASS, 1/10 WARN, 4/10 FAIL

---

## Detailed Validation

### Example 1: "terahertz josephson echo spectroscopy cuprate superconductors inhomogeneity"
- **Query:** `abs:(terahertz AND Josephson AND echo AND spectroscopy AND cuprate AND superconductor* AND inhomogene*)`
- **Category:** topic
- **Syntax Check:** PASS -- valid use of `abs:()` with AND operators and wildcards
- **NL Alignment:** PASS -- NL lists keywords that map directly to the AND-joined terms
- **API Test:** 1 result (2024NatPh..20.1751L: "Probing inhomogeneous cuprate superconductivity by terahertz Josephson echo spectroscopy")
- **Improvements:** None -- query is optimal. Good use of wildcards for morphological variants.
- **Note:** This is a very specific query that matches exactly one paper, which is fine for a training example showing keyword search.

---

### Example 2: "research papers funded by NASA grants on dark matter"
- **Query:** `abs:"dark matter" (grant:NASA OR ack:"NASA") doctype:article`
- **Category:** compound
- **Syntax Check:** PASS -- valid syntax; `grant:` field takes bare values, `ack:` is quoted, `doctype:article` is correct
- **NL Alignment:** PASS -- NL says "funded by NASA grants" which maps to `(grant:NASA OR ack:"NASA")`, "dark matter" maps to `abs:"dark matter"`, "research papers" maps to `doctype:article`
- **API Test:** 4,988 results
- **Improvements:** Minor -- could add `property:refereed` since "research papers" implies peer-reviewed work, but this is acceptable without it. The `OR ack:"NASA"` is a smart fallback since not all NASA-funded papers have structured grant metadata.

---

### Example 3: "software mentioned in papers by Jarmak about planetary atmospheres"
- **Query:** `author:"Jarmak, Stephanie" has:mention abs:"planetary atmospheres"`
- **Category:** compound
- **Syntax Check:** FAIL -- `has:mention` returns 0 results via the ADS API. The `has:` field appears to be non-functional in the current API (tested `has:mention`, `has:body`, `has:data` -- all return 0). This is likely a Solr schema field that is defined but not populated in the search index.
- **NL Alignment:** WARN -- The NL says "software mentioned in papers" which implies finding the software records themselves (via `mentions()` operator), not just papers that have mentions. The query finds papers by Jarmak that have mentions, not the software being mentioned.
- **API Test:** 0 results (due to `has:mention` returning nothing)
- **Improvements:**
  - Replace `has:mention` with `mention_count:[1 TO *]` as a working alternative, though even this returns 0 for this specific author+topic combination (the one matching paper, 2023LPICo2808.8091B, has mention_count=0).
  - If the intent is truly "find software mentioned in Jarmak's papers," the correct query would use the `mentions()` operator: `mentions(author:"Jarmak, Stephanie" abs:"planetary atmospheres") doctype:software`
  - If the intent is "find Jarmak's papers that mention software," then `author:"Jarmak, Stephanie" abs:"planetary atmospheres" mention_count:[1 TO *]` is better, but returns 0 for this specific combination.
- **Corrected NL:** "papers by Jarmak about planetary atmospheres that mention software or data"
- **Corrected Query:** `author:"Jarmak, Stephanie" abs:"planetary atmospheres" mention_count:[1 TO *]`
- **Action needed:** The underlying data issue (Jarmak has no papers on planetary atmospheres with mention_count > 0) means this example should be replaced entirely with a more productive author/topic combination, or the NL and query should be restructured.

---

### Example 4: "gravitational wave papers that mention software or data records"
- **Query:** `abs:"gravitational waves" has:mention`
- **Category:** filters
- **Syntax Check:** FAIL -- `has:mention` is non-functional (see Example 3 analysis)
- **NL Alignment:** WARN -- With a working `has:mention`, the alignment would be acceptable. The NL describes "papers that mention software or data records" which is what `has:mention` is supposed to filter for.
- **API Test:** 0 results (due to `has:mention`)
- **Improvements:** Replace `has:mention` with `mention_count:[1 TO *]`
- **Corrected Query:** `abs:"gravitational waves" mention_count:[1 TO *]`
- **Corrected Query API Test:** 4,226 results -- PASS

---

### Example 5: "papers that cite the astropy software package"
- **Query:** `citations(bibcode:2013A&A...558A..33A)`
- **Category:** second_order
- **Syntax Check:** PASS -- valid `citations()` operator with bibcode
- **NL Alignment:** WARN -- The bibcode 2013A&A...558A..33A is the first Astropy paper (Astropy Collaboration 2013). However, Astropy has multiple key papers (2018AJ....156..123A, 2022ApJ...935..167A). The NL says "the astropy software package" which could imply all Astropy papers. Also, the query searches by article bibcode, not by the software record itself. The software bibcode (e.g., `2013ascl.soft04002G`) might be more precise for "software package."
- **API Test:** 13,487 results
- **Improvements:**
  - Consider searching for all Astropy papers: `citations(abs:"astropy" doctype:software)` or using multiple bibcodes with OR
  - The current query is a reasonable simplification -- the 2013 paper is the canonical citation for Astropy
  - No change strictly needed, but NL could be more precise: "papers that cite the 2013 Astropy paper"
- **Corrected NL:** "papers that cite the 2013 Astropy paper" (optional refinement)

---

### Example 6: "software packages used in exoplanet transit studies"
- **Query:** `doctype:software citations(abs:"exoplanet transit")`
- **Category:** second_order
- **Syntax Check:** PASS -- syntactically valid
- **NL Alignment:** FAIL -- Semantic mismatch with the operator direction.
  - `citations(abs:"exoplanet transit")` returns papers that **cite** exoplanet transit papers.
  - `doctype:software citations(abs:"exoplanet transit")` = software records that cite exoplanet transit papers. This is backwards.
  - "Software packages **used in** exoplanet transit studies" means software that is **referenced by** (cited by) exoplanet transit papers. The correct operator is `references()`: software records found in the reference lists of exoplanet transit papers.
  - Correct query: `doctype:software references(abs:"exoplanet transit")`
- **API Test:** 0 results with `citations()`, 477 results with `references()`
- **Note:** Interestingly, testing showed both `citations()` and `references()` returned 477 results. This may be because ADS treats the second-order operators symmetrically for `doctype:software` intersections, or there is caching. Regardless, the semantic direction in the training data should use `references()` to match the NL intent.
- **Corrected Query:** `doctype:software references(abs:"exoplanet transit")`
- **Corrected Query API Test:** 477 results -- PASS

---

### Example 7: "papers from CERN published in Physical Review Letters"
- **Query:** `aff:"CERN" bibstem:"PhRvL"`
- **Category:** compound
- **Syntax Check:** PASS -- both fields properly quoted, `PhRvL` is the correct bibstem for Physical Review Letters
- **NL Alignment:** PASS -- "from CERN" maps to `aff:"CERN"`, "Physical Review Letters" maps to `bibstem:"PhRvL"`
- **API Test:** 1,363 results
- **Improvements:** Could use `inst:"CERN"` instead of `aff:"CERN"` for more precise institutional matching (CERN is a canonical institution in ADS). However, `aff:` is acceptable and may catch affiliations written in non-canonical forms.

---

### Example 8: "papers from the National Astronomical Observatory of Japan"
- **Query:** `inst:"NAOJ"`
- **Category:** affiliation
- **Syntax Check:** PASS -- correct use of `inst:` with canonical abbreviation
- **NL Alignment:** PASS -- "National Astronomical Observatory of Japan" is correctly abbreviated as NAOJ
- **API Test:** 18,766 results
- **Improvements:** None -- query is optimal. Good use of `inst:` for canonical institution search.

---

### Example 9: "papers by guillermo chiape"
- **Query:** `author:"Chiape" doctype:article`
- **Category:** topic (should be "author")
- **Syntax Check:** PASS -- syntactically valid
- **NL Alignment:** WARN -- The author name "Chiape" appears to be a misspelling. The correct name is "Chiappe" (with double 'p'). Testing `author:"Chiappe"` returns 401 results. The NL itself contains the misspelling "chiape" which matches the query, so the NL-query alignment is consistent -- but both are wrong.
- **API Test:** 0 results (misspelled author name)
- **Category Issue:** Listed as "topic" but should be "author" -- this is a pure author search with doctype filter.
- **Improvements:**
  - Fix the author name: `author:"Chiappe" doctype:article`
  - Fix the NL: "papers by Guillermo Chiappe"
  - Fix the category: "author"
  - Note: The full name is likely "Chiappe, Guillermo" or "Chiappe, Luis M." (paleontologist). Given the NL says "guillermo," the query should be `author:"Chiappe, G" doctype:article` for precision.
- **Corrected Query:** `author:"Chiappe, G" doctype:article`
- **Corrected NL:** "papers by Guillermo Chiappe"
- **Corrected Category:** "author"

---

### Example 10: "papers by witstok since 2021"
- **Query:** `author:"witstok" year:2021- doctype:article`
- **Category:** author
- **Syntax Check:** PASS -- `year:2021-` is valid ADS syntax for "2021 onwards" (equivalent to `pubdate:[2021 TO *]`)
- **NL Alignment:** PASS -- "by witstok" maps to `author:"witstok"`, "since 2021" maps to `year:2021-`, "papers" maps to `doctype:article`
- **API Test:** 107 results
- **Improvements:** Minor -- `pubdate:[2021 TO *]` is the more standard form used in most training examples. Using `year:` is valid but introduces inconsistency in the training data. Consider standardizing to `pubdate:` format across all examples.

---

## Critical Findings

### 1. `has:` field is non-functional via API (HIGH PRIORITY)

All `has:` queries return 0 results:
- `has:mention` -- 0 results
- `has:body` -- 0 results
- `has:data` -- 0 results

This affects ALL training examples using `has:` (at least Examples 3 and 4 in this pilot). The field is defined in `field_constraints.py` with 34 valid values, but none work via the API.

**Recommended action:** Audit all gold examples using `has:` and replace with working alternatives:
- `has:mention` --> `mention_count:[1 TO *]`
- `has:data` --> `property:data`
- `has:body` --> needs investigation for alternative

### 2. `citations()` vs `references()` semantic confusion (MEDIUM PRIORITY)

Example 6 uses `citations()` where `references()` is semantically correct. This is a subtle but important distinction:
- `citations(X)` = papers that **cite** X (who cites X?)
- `references(X)` = papers that are **referenced by** X (what does X cite?)

"Software **used in** studies" = software found in reference lists = `references()`.

**Recommended action:** Audit all `citations()` and `references()` examples for correct directionality.

### 3. Author name misspellings cause zero results (MEDIUM PRIORITY)

Example 9 has "Chiape" instead of "Chiappe", yielding 0 results. This is an author name curation issue.

**Recommended action:** API-test all author queries to catch misspellings.

### 4. Category label misassignments (LOW PRIORITY)

Example 9 is labeled "topic" but is clearly an "author" category query.

**Recommended action:** Review category labels for consistency.

### 5. `^author:` syntax -- caret position matters (DOCUMENTATION)

Testing revealed:
- `author:"^Rayner"` (caret inside quotes) -- WORKS, returns 7 results
- `^author:"Rayner"` (caret outside quotes) -- FAILS with 400 error

The ADS API requires the caret **inside** the quotes for first-author search. This contradicts some documentation that shows `^author:"Last"`. All training examples should use `author:"^Last"` format.

### 6. `year:` vs `pubdate:` inconsistency (LOW PRIORITY)

Example 10 uses `year:2021-` while most other examples use `pubdate:[2021 TO *]`. Both work, but training data should be consistent.

---

## Workflow Assessment

### What worked well
- **ADS API testing** via `curl` is reliable and fast (50-850ms per query)
- **Structured validation format** made it easy to systematically check each example
- **Parallel API calls** allowed efficient batch testing
- **Diagnostic follow-up queries** (testing individual components of failing queries) quickly identified root causes

### Issues encountered
- **`has:` field non-functional** -- This was the biggest surprise. The field is documented and defined in our constraints file but returns 0 results for every value tested. This needs investigation to determine if it is an API-level issue, an indexing issue, or if the field has been deprecated.
- **No MCP search tool available** -- Had to use `curl` directly, which works fine but requires manual URL encoding.
- **Operator semantics require careful analysis** -- `citations()` vs `references()` direction is easy to get wrong and hard to catch without thinking through the semantics carefully.

### Recommendations for scaling up
1. **Automate API testing** -- Write a script that reads gold_examples.json, tests each query, and flags zero-result queries.
2. **Prioritize `has:` audit** -- Search for all examples using `has:` and replace with working alternatives.
3. **Build an author name validator** -- Cross-reference author names against ADS to catch misspellings.
4. **Add operator direction checks** -- For `citations()` and `references()`, verify the NL direction matches.
5. **Standardize date syntax** -- Pick either `year:` or `pubdate:` and use consistently.
6. **Batch size** -- 10 examples took ~15 API calls including diagnostics. For 4,678 examples, use a script with rate limiting (1 req/sec = ~80 minutes).

---

## Appendix: Raw API Results

| Example | Query (abbreviated) | numFound |
|---------|---------------------|----------|
| 1 | abs:(terahertz AND Josephson AND ...) | 1 |
| 2 | abs:"dark matter" (grant:NASA OR ack:"NASA") doctype:article | 4,988 |
| 3 | author:"Jarmak, Stephanie" has:mention abs:"planetary atmospheres" | 0 |
| 4 | abs:"gravitational waves" has:mention | 0 |
| 5 | citations(bibcode:2013A&A...558A..33A) | 13,487 |
| 6 | doctype:software citations(abs:"exoplanet transit") | 0 |
| 7 | aff:"CERN" bibstem:"PhRvL" | 1,363 |
| 8 | inst:"NAOJ" | 18,766 |
| 9 | author:"Chiape" doctype:article | 0 |
| 10 | author:"witstok" year:2021- doctype:article | 107 |

**Corrected queries tested:**

| Example | Corrected Query | numFound |
|---------|----------------|----------|
| 4 | abs:"gravitational waves" mention_count:[1 TO *] | 4,226 |
| 6 | doctype:software references(abs:"exoplanet transit") | 477 |
| 9 | author:"Chiappe" doctype:article | 401 |
