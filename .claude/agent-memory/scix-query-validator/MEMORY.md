# SciX Query Validator - Agent Memory

## Critical API Findings (confirmed 2026-03-04)

### `has:` field is non-functional via API
- `has:mention`, `has:body`, `has:data` ALL return 0 results via the ADS search API
- The field is defined in `field_constraints.py` with 34 values but none work
- Working alternatives:
  - `has:mention` --> `mention_count:[1 TO *]` (261K results)
  - `has:data` --> `property:data` (598K results)
  - `has:body` --> needs further investigation
- See: `data/reference/validation_pilot_report.md`

### First-author caret position
- `author:"^Last"` (caret INSIDE quotes) -- WORKS
- `^author:"Last"` (caret OUTSIDE quotes) -- FAILS with 400 error
- All training examples must use caret inside quotes

### `year:` vs `pubdate:` both work
- `year:2021-` and `pubdate:[2021 TO *]` are equivalent
- Training data uses both; should standardize to `pubdate:` for consistency

## Common Error Patterns

### Author name misspellings
- "Chiape" vs "Chiappe" -- single letter causes 0 results
- Always API-test author queries to catch this

### `citations()` vs `references()` confusion
- `citations(X)` = papers that CITE X
- `references(X)` = papers REFERENCED BY X (what X cites)
- "software used in X studies" = `references(X)`, NOT `citations(X)`
- This is a frequent semantic error in training data

### Category label issues
- Pure author queries sometimes labeled "topic" instead of "author"

## Bibstem Confirmations
- `PhRvL` = Physical Review Letters (confirmed, 1363 results with aff:"CERN")

## Institution Abbreviations Confirmed
- `NAOJ` = National Astronomical Observatory of Japan (inst: field, 18766 results)
- `IUCAA` = Inter-University Centre for Astronomy and Astrophysics
  - `inst:"IUCAA"` returns 3,886 results
  - `aff:"IUCAA"` returns 1,356 results (less coverage)

## Field Alias Confirmations (2026-03-04)
- `collection:` and `database:` are aliases -- both work
- `entdate:` and `entry_date:` are aliases -- both work
- `database:earthscience` is valid (14.6M results)
- Codebase prefers `database:` over `collection:` per field_constraints.py comment

## Operator Nesting
- Nested second-order operators NOT supported: `references(useful(abs:"X"))` fails
- Each operator must be used independently or in sequence

## API Permission Notes
- `object:`, `similar()`, `references()`, `citations()`, `NEAR` queries return 405 via API
- These require special API permissions or work only via ADS web UI / bigquery endpoint
- AWS WAF rate-limits kick in after ~50 rapid requests (captcha challenge)

## Workflow Notes
- ADS API via curl is reliable, 50-850ms per query
- Rate limit: stay under ~1 req/sec for batch operations; WAF triggers around 50 rapid requests
- API key location: `.env` file, variable `ADS_API_KEY`
- Always URL-encode queries carefully (especially `&` in bibcodes)
