# NLS Fine-Tune SciX

## Current Focus: Phase B — IntentSpec JSON Training Format

We have a hybrid architecture where NER and NLS (fine-tuned LLM) run in parallel. Results are merged at the **intent level** (not string level) and the **assembler** always produces the final syntax.

**Phase B (implemented):** LLM can now output **compact IntentSpec JSON** directly (with `<think>` reasoning block), instead of raw ADS query strings. The server auto-detects the format and routes to the appropriate merge path. Training data conversion script produces intent-format JSONL with think traces.

## Task

Convert natural language → ADS/SciX structured search queries for [SciXplorer.org](https://scixplorer.org/).

- Input: "papers by Hawking on black hole radiation from the 1970s"
- Output: `author:"Hawking, S" abs:"black hole radiation" pubdate:[1970 TO 1979]`

## Hybrid Architecture

### How It Works
1. **Nectar** calls our `/pipeline` endpoint (2s timeout), falls back to `/v1/chat/completions`
2. **Server** runs NER + NLS in parallel when `HYBRID_MODE=true` (default)
3. **Parse**: LLM's raw query string → `parse_query_to_intent()` → IntentSpec
4. **Merge**: `merge_intents(ner_intent, llm_intent, nl_text)` with per-field policies
5. **Assemble**: merged IntentSpec → `assemble_query()` → clean ADS query
6. **Post-processing** rewrites apply to final output: inst expansion, bibstem normalization, author wildcarding, UAT augmentation
7. **ADS query passthrough**: if input is already ADS syntax, skip NER/NLS and apply post-processing only

### Data Flow
```
NL text ──→ NER ──────────→ IntentSpec_NER ──┐
                                              ├─→ merge_intents() → IntentSpec_merged → assembler → clean query
NL text ──→ LLM → raw query → parse_query() → IntentSpec_LLM ──┘
```

### Phase B Data Flow (IntentSpec JSON output)
```
NL text ──→ NER ──────────→ IntentSpec_NER ──┐
                                              ├─→ merge_intents() → IntentSpec_merged → assembler → clean query
NL text ──→ LLM → <think>...</think> + JSON → IntentSpec_LLM ──┘
```
Server auto-detects format: IntentSpec JSON skips `parse_query_to_intent()` and 3 string rewrites (inst, bibstem, author wildcarding — assembler handles these). UAT augmentation still runs post-assembly.

### Phase C Data Flow (RAG-augmented LLM)
```
NL text ──→ NER ──────────→ IntentSpec_NER ──┐
         │                                    ├─→ merge_intents() → IntentSpec_merged → assembler → clean query
         └→ [RAG: few-shot examples + field cards]
              ↓
            LLM (with context) ──→ IntentSpec_LLM ──┘
```
RAG retrieval (<20ms) runs in parallel with NER. Injects 2-3 similar gold examples as few-shot user/assistant pairs + 1-2 field reference cards into the LLM prompt. No new dependencies (reuses existing BM25 index).

### Merge Per-Field Policies
| Field | Preferred Source | Rationale |
|-------|-----------------|-----------|
| authors | NER | Better name formatting |
| free_text_terms | LLM | Understands context better |
| year_from/year_to | NER if extracted | Validated against patterns |
| affiliations | NER | Validated against institution_synonyms |
| bibstems | NER | Validated against bibstem_synonyms |
| operator | LLM | Handles nested/complex operators |
| negation/has/citation_count | LLM only | NER can't detect these |
| doctype/property | Union | But strips doctype:article from generic "papers" |

### Merge Module (`merge.py`)
- `merge_intents(ner, llm, nl_text)` → IntentSpec — per-field merge with clear policies
- `merge_ner_and_nls(ner_result, nls_query, nl_text)` → `MergeResult` — orchestrator
- Returns `MergeResult` with: query, source ("hybrid"/"nls_only"/"ner_only"/"fallback"), fields_injected, timing, ner_intent, llm_intent, merged_intent (debug traces)
- **Fallback:** When both NER and LLM fail, returns `abs:"<original text>"` with `source="fallback"` and `confidence=0.1` instead of empty query

### Query Repair (`constrain.py`)
Post-assembly deterministic repairs applied before enum constraint filtering:
- **First-author caret fix:** `^author:"Last"` → `author:"^Last"` (prevents ADS 400 error)
- **Backwards year range:** `pubdate:[2025 TO 2020]` → `pubdate:[2020 TO 2025]`
- **Unquoted operator values:** `citations(abs:dark matter)` → `citations(abs:"dark matter")`
- **Enum misspelling correction:** 21 common misspellings auto-corrected (e.g., `doctype:preprint`→`eprint`, `property:peer-reviewed`→`refereed`, `database:astrophysics`→`astronomy`)

### Parse Query Module (`parse_query.py`)
- `parse_query_to_intent(query)` → IntentSpec — inverse of assembler
- Extracts all field:value pairs, validates enum values, handles negation, operators, ranges

### Reliability Features
- **LLM timeout:** `asyncio.wait_for()` with 1.5s timeout on LLM generation; on timeout, returns NER-only result
- **Empty query fallback:** Both NER+LLM fail → `abs:"<original user text>"` instead of empty query
- **Input validation:** Queries >500 chars truncated, null bytes stripped, non-printable chars removed
- **Large response guard:** LLM responses >10KB skip JSON parsing (returns raw text)
- **Production telemetry:** Structured JSON logging for every query via `nls.telemetry` logger (source, confidence, latency, errors, repairs)

### Debug Endpoints
- `GET /debug/hybrid?q=...` — Run hybrid merge, returns: final query, source, raw NLS/NER queries, **intent traces** (NER/LLM/merged IntentSpec dicts), fields_injected, timing
- `GET /debug/pipeline?q=...` — Run NER pipeline only, returns result or error

### Environment Variables
- `HYBRID_MODE=true` — Enable hybrid merge (default). Set `false` for NER-only when pipeline available.
- `RAG_ENABLED=true` — Enable RAG few-shot augmentation on the LLM path (default). Set `false` to disable.
- `RAG_NUM_EXAMPLES=3` — Number of few-shot examples to inject (default: 3).
- `RAG_MAX_CARDS=2` — Maximum field reference cards to inject (default: 2).
- `LLM_TIMEOUT=1.5` — LLM generation timeout in seconds (default: 1.5). Set to `10` for local MPS/CPU demos.

## Training Data

- **Format:** JSONL with chat messages (system/user/assistant)
- **Gold examples:** `data/datasets/raw/gold_examples.json` (4,924 pairs)
- **Processed train/val:** `data/datasets/processed/train.jsonl` (5,185) / `val.jsonl` (577)
- **Categories:** 21 types (first_author, unfielded, author, content, publication, operator, filters, compound, conversational, etc.)

### Example pair (gold_examples.json)
```json
{
  "natural_language": "brown dwarfs papers from 2016",
  "ads_query": "abs:\"brown dwarfs\" pubdate:2016 doctype:article",
  "category": "publication"
}
```

## ADS Search Syntax

### Fields
| Field | Syntax | Notes |
|-------|--------|-------|
| Author | `author:"Last, F"` | Always quoted, "Last, F" format |
| First author | `author:"^Last"` | Caret INSIDE quotes |
| Abstract/title/keywords | `abs:"topic"` | Virtual field |
| Title only | `title:"exact phrase"` | Quoted |
| Date range | `pubdate:[2020 TO 2023]` | Bracket range |
| Journal | `bibstem:"ApJ"` | MUST be quoted |
| Object | `object:M31` | Astronomical object |
| UAT | `uat:"Dark matter"` | Unified Astronomy Thesaurus controlled vocabulary; **runtime-augmented via `uat_lookup.py`** |
| Planetary feature | `planetary_feature:"crater"` | Planetary nomenclature (target, feature type, or feature name); **runtime-augmented via `planetary_feature_lookup.py`** |
| Citation count | `citation_count:[100 TO *]` | Numeric range |
| Affiliation (virtual) | `aff:"Berkeley"` | Free-text affiliation search |
| Institution (curated) | `inst:"MIT"` | Curated institutional abbreviation |
| Metadata presence | `has:body` | Filter by field presence |
| Mention count | `mention_count:[5 TO *]` | Software/data mentions |
| Credit count | `credit_count:[20 TO *]` | Credits received |

Full syntax: https://ui.adsabs.harvard.edu/help/search/search-syntax

### Non-functional Fields
- `mention:` and `credit:` do NOT work as search fields (e.g., `mention:"astropy"` fails). Use `abs:"astropy" mention_count:[1 TO *]` instead.
- `mentions()` and `credits()` second-order operators are NOT live.

### Operators
| Operator | Example |
|----------|---------|
| `citations()` | `citations(abs:"gravitational wave")` |
| `references()` | `references(abs:"supernova")` |
| `trending()` | `trending(abs:"exoplanet")` |
| `useful()` | `useful(abs:"cosmology")` |
| `similar()` | `similar(abs:"black hole merger")` |
| `reviews()` | `reviews(abs:"magnetar")` |

**Rule:** All field values inside operators MUST be quoted.

### Advanced Syntax Patterns (from blog posts)

**Nested operators** — operators can be composed:
- `trending(useful(abs:"exoplanet"))` — trending among the most useful papers
- `reviews(useful(abs:"cosmology"))` — reviews citing key papers
- `citations(topn(100, abs:"dark energy", "citation_count desc"))` — papers citing the top-100
- `similar(citations(bibcode:2016PhRvL.116f1102A))` — papers similar to citing papers

**`similar()` with `entdate:`** — find new papers related to a topic:
- `similar(abs:"fast radio bursts") entdate:[NOW-7DAYS TO *]` — this week's related papers
- `similar(abs:"exoplanet atmospheres") entdate:[NOW-1MONTH TO *] bibstem:"arXiv"` — recent preprints

**`property:(...)` multi-value syntax** — combine multiple properties in parens:
- `property:(refereed openaccess)` — equivalent to `property:refereed property:openaccess`
- `property:(refereed openaccess data)` — all three required

**`bibstem:` wildcards and multi-OR**:
- `bibstem:jgr*` — all JGR journals (unquoted, trailing wildcard)
- `bibstem:(ApJ OR ApJL OR ApJS)` — multiple specific journals
- `bibstem:yCat` — VizieR catalog entries
- `bibstem:"hst..prop"` — HST proposals
- **Note:** `bibstem:*prop*` (leading wildcard) returns 400 error

**`full:` field** — searches full text (body + metadata):
- `full:"MUSE" full:"VLT"` — instrument co-occurrence
- `full:"urn:nasa:pds"` — PDS URN references
- `full:"10.5281"` — DOI prefix in text

**`=` exact match modifier** — disables synonym expansion:
- `=keyword:"accretion"` — exact keyword, no synonyms
- `=abs:"supernova"` — exact abstract match
- `=author:"Smith, J"` — no name variants

**`docs(library/...)` syntax** — use library contents in operators:
- `useful(docs(library/LIBRARY_ID))` — useful papers from a library
- `citations(docs(library/LIBRARY_ID))` — papers citing library contents

### Constrained Enum Fields
| Field | Count | Examples |
|-------|-------|---------|
| `doctype` | 22 | article, eprint, phdthesis, inproceedings, software |
| `property` | 21 | refereed, openaccess, eprint, nonarticle |
| `database` | 4 | astronomy, physics, general, earthscience |
| `bibgroup` | 53 | HST, JWST, Chandra, SDSS, ALMA, Gaia, LIGO |
| `esources` | 8 | PUB_PDF, EPRINT_PDF, ADS_SCAN |
| `data` | 24 | MAST, NED, SIMBAD, VizieR, IRSA |
| `has` | 34 | body, ack, data, grant, orcid_pub, mention |

Full enum lists: `packages/finetune/src/finetune/domains/scix/field_constraints.py`

### Affiliation Queries: `(inst: OR aff:)` Pattern

For known institutions, queries use both curated `inst:` and free-text `aff:` for maximum recall:
- `(inst:"MIT" OR aff:"MIT")` — single known institution
- `(inst:"JPL" OR inst:"GSFC" OR inst:"NASA Ames" OR inst:"MSFC" OR aff:"NASA")` — umbrella org
- `aff:"Unknown Lab"` — fallback for unrecognized institutions

**Runtime behavior:** The `institution_lookup` module automatically rewrites `aff:` → `(inst: OR aff:)` at:
1. **NER pipeline path** — assembler calls `build_inst_or_aff_clause()` for extracted affiliations
2. **LLM output path** — `rewrite_aff_to_inst_or_aff()` post-processes model output in `server.py`

**Exception:** `inst:` is NOT supported inside `pos()` operators — those are left as `aff:` only.

### Complex Author Name Wildcarding

Names with hyphens or apostrophes have inconsistent ADS indexing (e.g., "de Groot-Hedlin" vs "de GrootHedlin"). The `_wildcard_complex_author()` function in `assembler.py` adds a trailing `*` inside quotes to catch variants:

| Input | Output | Why |
|-------|--------|-----|
| `de Groot-Hedlin` | `author:"de*Groot*Hedlin*"` | All separators → `*` |
| `Garcia-Perez` | `author:"Garcia*Perez*"` | Hyphen → `*`, trailing `*` |
| `Le Floc'h` | `author:"Le*Floc*h*"` | Space + apostrophe → `*` |
| `El-Badry` | `author:"El*Badry*"` | Catches "El Badry", "ElBadry", "El-Badry" |
| `al-Sufi` | `author:"al*Sufi*"` | Catches "alSufi", "al Sufi", "al-Sufi" |
| `Hawking` | `author:"Hawking"` | Simple name → no change |
| `Hawking, S` | `author:"Hawking, S"` | Comma-formatted → no change |

**Runtime behavior:** Applied at two points (same pattern as `(inst: OR aff:)` rewriting):
1. **NER pipeline path** — `_build_author_clause()` calls `_wildcard_complex_author()` during assembly
2. **LLM output path** — `rewrite_complex_author_wildcards()` post-processes model output in `server.py`

**ADS wildcard rules for authors:**
- Trailing `*` inside quotes works: `author:"de Groot*"` ✓
- Mid-name `*` inside quotes works: `author:"El*Badry*"` ✓ (catches El-Badry, El Badry, ElBadry)
- Unquoted wildcards with special chars do NOT work: `author:de*Groot*Hedlin` ✗
- ADS normalizes accents automatically: `author:"Garcia Perez"` matches `García Pérez` ✓

**Training data:** Keep exact author names in gold examples — wildcarding is handled deterministically at runtime, not learned by the model.

### Quoting Rules for Training Examples
- `bibstem`, `author`, `title`, `abs` → always quote values
- `doctype`, `property`, `database` → bare enum values OK
- Values inside operators → always quote

## Coverage Gaps (Priority)

### Recently addressed (2026-03-04, +210 examples)
- **esources** — now 21 examples covering all 8 values (was 5 examples, 3/8 values)
- **data** — now 27 examples covering 17/24 archives (was 3 examples)
- **NOT/negation** — now 41 examples (was 16)
- **has** — now 43 examples covering 20+ values (was 23)
- **grant** — now 15 examples (was 4)
- **ack** — now 14 examples (was 4)
- **keyword** — now 20 examples (was 5)
- **arxiv_class** — now 12 examples (was 2)
- **orcid** — now 10 examples (was 2)
- **entry_date** — now 8 examples (was 0)
- **object** — now 30 examples (was 20)
- **similar()** — now 45 examples (was 35)
- **references()** — now 43 examples (was 33)

### Recently addressed (2026-03-05, +112 examples)
- **Pasted reference parsing** — 30 examples (bibcode, DOI, arXiv ID, formatted citations with volume/page)
- **UAT field** — 10 examples + runtime `uat_lookup.py` module (4,144 terms, augments abs: with uat: at serving time)
- **planetary_feature:** — 15 examples (feature types, feature names, targets from USGS Gazetteer)
- **NOT/negation** — +20 examples (now ~71 total)
- **Software/data mentions** — 10 examples using `abs:` + `mention_count:`/`credit_count:` combo
- **Date diversity** — 10 examples (relative dates: "last 5 years", "since 2020", "this week", NOW- syntax)
- **caption:** — 5 examples (figure/table caption search, was zero)
- **arxiv: identifier** — 5 examples (arXiv ID lookup, was zero)
- **author_count:/page_count:** — 8 examples (single-author, large collaborations, short letters)

### Remaining gaps
1. **data field** — 7/24 archives still uncovered: ARI, BICEP2, GCPD, GTC, INES, ISO, NOAO
2. **has field** — ~14/34 values still uncovered
3. **lang, page (standalone), issue** — low/zero dedicated examples (page/volume covered via reference parsing)
4. **simbad, vizier (as fields)** — still zero examples (covered via `data:SIMBAD`, `data:VizieR`)

## SciX vs Google Scholar Gap Analysis

User experience testing identified 7 issue types. Some are addressable by NLS training, others need backend work.

### Addressable by training data (this repo)
- **Verbose NL → focused queries** — 15 examples added teaching distillation of long descriptions into effective multi-`abs:` queries (category: `compound`)
- **"Classical/seminal reference" intent** — 15 examples added for `useful()` + `pubdate:` year range patterns (e.g., "foundational paper on X" → `useful(abs:"X") pubdate:[1970 TO 1990]`)
- **Complex author names** — 12 examples added for hyphenated/particle names; wildcarding handled at runtime by assembler (see Complex Author Name Wildcarding above)
- **Cross-domain query shaping** — 12 examples added using `database:` filters and `useful()` for out-of-scope concepts (e.g., "physics papers on superconductivity" → `database:physics`)

### NOT addressable by NLS (infrastructure needed)
- **Full-text indexing gaps** — papers exist but key terms only in body text (not title/abstract)
- **Gray literature** — seminal publications not in ADS corpus at all
- **"Did you mean" / typo tolerance** — needs Solr suggest API + UI feature, NOT model wildcarding (model can't detect typos)
- **`reviews()` operator quality** — returns wrong-domain results (soil science for "electromagnetic induction")
- **Semantic/vector search** — "find the definitive reference" intent beyond keyword matching
- **Author name normalization** — Solr-level author aliasing system

## Important Rules

**Local-first docs rule:** Always check local files and the local `~/github/adsabs.github.io` repo before pinging external websites. External sites may rate-limit.

## External References
- Search help documents: https://scixplorer.org/scixhelp/ and all websites downstream
- Solr Schema: https://github.com/adsabs/montysolr/blob/main/deploy/adsabs/server/solr/collection1/conf/schema.xml

## Key Files

### Pipeline modules
- `packages/finetune/src/finetune/domains/scix/ner.py` — Rules-based NER extraction (authors, years, operators, affiliations, etc.)
- `packages/finetune/src/finetune/domains/scix/assembler.py` — Deterministic query assembly from IntentSpec
- `packages/finetune/src/finetune/domains/scix/intent_spec.py` — IntentSpec dataclass (NER→assembler contract)
- `packages/finetune/src/finetune/domains/scix/institution_lookup.py` — Institution RAG lookup for `(inst: OR aff:)` clauses
- `packages/finetune/src/finetune/domains/scix/bibstem_lookup.py` — Journal bibstem lookup and `rewrite_bibstem_values()` post-processor
- `packages/finetune/src/finetune/domains/scix/rag_retrieval.py` — RAG few-shot retrieval for LLM prompt augmentation (Phase C)
- `packages/finetune/src/finetune/domains/scix/field_cards.py` — Static field reference cards for reducing enum hallucination (Phase C)
- `packages/finetune/src/finetune/domains/scix/retrieval.py` — BM25 retrieval index over gold examples (used by RAG and pipeline)
- `packages/finetune/src/finetune/domains/scix/uat_lookup.py` — UAT thesaurus lookup; `rewrite_abs_to_abs_or_uat()` augments abs: with uat: at serving time
- `packages/finetune/src/finetune/domains/scix/planetary_feature_lookup.py` — Planetary feature Gazetteer lookup; NER extraction of multi-word feature names + `rewrite_abs_to_abs_or_planetary_feature()` augments abs: with planetary_feature: at serving time
- `packages/finetune/src/finetune/domains/scix/fields.py` — ADS field definitions
- `packages/finetune/src/finetune/domains/scix/field_constraints.py` — Enum values
- `packages/finetune/src/finetune/domains/scix/validate.py` — Query validation
- `packages/finetune/src/finetune/domains/scix/constrain.py` — Post-assembly query repair + constraint filter (caret fix, year range swap, unquoted operator values, enum misspelling correction, then enum validation)
- `packages/finetune/src/finetune/domains/scix/parse_query.py` — Parses LLM raw query string back into IntentSpec (inverse of assembler)
- `packages/finetune/src/finetune/domains/scix/merge.py` — Intent-level merge (parse LLM→IntentSpec, merge with NER IntentSpec, assembler produces final query)
- `packages/finetune/src/finetune/domains/scix/pipeline.py` — End-to-end NER pipeline orchestration
- `docker/server.py` — Inference server (hybrid NER+NLS endpoints); runs NER and NLS in parallel, merges results; post-processes LLM output with `rewrite_aff_to_inst_or_aff()`, `rewrite_bibstem_values()`, `rewrite_complex_author_wildcards()`, `rewrite_abs_to_abs_or_uat()`, and `rewrite_abs_to_abs_or_planetary_feature()`

### Scripts
- `scripts/generate_nl.py` — NL generation from queries
- `scripts/build_dataset.py` — Dataset build pipeline
- `scripts/audit_training_coverage.py` — Coverage analysis
- `scripts/collect_help_docs.py` — Collects/cleans SciX help docs from adsabs.github.io
- `scripts/collect_bibstems.py` — Collects journal bibstem data from ADS Journals API
- `scripts/collect_institutions.py` — Parses CanonicalAffiliations into institution_synonyms.json
- `scripts/update_aff_to_inst_or_aff.py` — Batch rewrite training data `aff:` → `(inst: OR aff:)`

### Training Data Generation Scripts
All template-based, deterministic (seeded), output to `data/datasets/generated/`:
- `scripts/generate_bibgroup_examples.py` — Bibgroup/telescope queries (uses bibgroup_synonyms.json)
- `scripts/generate_collection_examples.py` — Database/collection filter queries
- `scripts/generate_doctype_examples.py` — Document type queries
- `scripts/generate_operator_examples.py` — Operator queries (citations, references, trending, etc.)
- `scripts/generate_property_examples.py` — Property filter queries (refereed, openaccess, etc.)
- `scripts/generate_synthetic.py` — Conversational/unfielded patterns
- `scripts/generate_seminal_reference_examples.py` — `useful()` + pubdate year range for "seminal/classical reference" intent (60 examples)
- `scripts/generate_complex_author_examples.py` — Hyphenated/particle/accented author names (83 examples, 20 authors)
- `scripts/generate_verbose_nl_examples.py` — Verbose NL → focused multi-`abs:` query distillation (60 examples)
- `scripts/generate_cross_domain_examples.py` — `database:` filters + `useful()` for cross-domain/out-of-scope topics (45 examples)
- `scripts/generate_filters_examples.py` — esources, has:, grant:, ack:, keyword:, arxiv_class:, lang:, vizier: (130 examples)
- `scripts/generate_data_archive_examples.py` — data: field queries for 15 archives (34 examples)
- `scripts/generate_bibstem_examples.py` — Journal bibstem queries for 27 journals (27 examples)
- `scripts/generate_affiliation_examples.py` — inst:, aff:, affil:, multi-institution queries (25 examples)
- `scripts/generate_compound_examples.py` — Multi-field combinations, negation, grant+topic, credit/mention (104 examples)
- `scripts/generate_misc_field_examples.py` — temporal, object, syntax (NEAR/=author:), orcid, pos(), metrics, second-order ops, similar() (76 examples)
- `scripts/merge_examples.py` — Deduplicates and merges generated files into gold_examples.json
- `scripts/normalize_year_syntax.py` — Converts `year:YYYY` → `pubdate:YYYY` and `year:YYYY-YYYY` → `pubdate:[YYYY TO YYYY]` in gold_examples.json (dry-run default, `--apply` to write)
- `scripts/validate_gold_examples.py` — Syntax + API validation of training examples
- `scripts/analyze_telemetry.py` — Parses structured telemetry JSON logs → summary report (source distribution, error rate, latency percentiles, NER injection frequency, repair frequency)
- `scripts/generate_coverage_gap_examples.py` — Coverage audit gap-fill: 210 examples across 17 categories (esources, data, NOT, has, grant, ack, keyword, arxiv_class, orcid, entry_date, object, proximity, exact author, cross-domain, mentions, verbose NL, similar, references)
- `scripts/fix_validation_issues.py` — Fixes for validation issues in coverage-gap examples (idempotent)
- `scripts/generate_blog_examples.py` — Blog-sourced patterns: nested operators (trending(useful(...))), similar()+entdate, property:(...) multi-value, bibstem wildcards/OR, full: field, data-linking, earth science collection (91 examples)
- `scripts/clean_gold_examples.py` — Removes non-academic entries, fixes encoding/authors/alignment in gold_examples.json
- `scripts/realism_cleanup.py` — Realism cleanup: removes broken queries (docs hashes, DOIs in abs, year:1641), deduplicates content-field cross-products, rewrites template NL (bibgroup, field-reference, syntax, has:, exact-match), reduces OA subtype over-representation (118 removed, 205 rewritten)
- `scripts/generate_training_improvements.py` — Coverage gap improvements: reference parsing, UAT, negation, software mentions, date diversity, caption, arxiv IDs, count filters (98 examples + 15 planetary_feature)
- `scripts/convert_to_intent_format.py` — Converts gold_examples.json to intent format (IntentSpec JSON + think traces) for Phase B training
- `scripts/remove_synonym_expansion.py` — Removes 24 examples teaching LLM synonym expansion (OR-lists, fabricated abs: terms, broken queries), fixes 4 abbreviation swaps, adds 13 clean replacements
- `scripts/build_rag_dataset.py` — Builds RAG-augmented training JSONL: for each example, retrieves k nearest neighbors as few-shot context (Phase C)

## Reference Material for Training Data Generation

We use two reference sources to generate NL-to-query training pairs.

### Source 1: SciX Help Documentation

Cleaned help docs live in `data/reference/help/` (one `.md` per category, 18 categories, 60 docs total). Collected from the local `adsabs.github.io` clone at `_includes/_help/{category}/_posts/*.md`.

Categories include:
- `search/` — search syntax, fields, operators, author search, parser, filters
- `gettingstarted/` — beginner search tutorials
- `actions/` — export, sort, visualize, article view
- `libraries/` — library management, sharing, set operations
- `data_faq/` — bibgroups, data FAQ, curation
- `faq/` — common questions
- `orcid/` — ORCID claiming, searching
- `userpreferences/` — settings, library servers
- `policies/` — terms, privacy, accessibility
- `troubleshooting/` — HAR files, etc.

**To regenerate:**
```bash
python scripts/collect_help_docs.py \
    --source ~/github/adsabs.github.io \
    --output data/reference/
```

The script strips Jekyll front matter, template directives (`{% %}`, `{{ }}`), and HTML entities, preserving markdown content, code blocks, and tables.

### Source 2: Solr Schema / Field Inventory

`data/model/ads_field_inventory.json` (1,096 lines) already contains:
- 60+ fields with metadata (name, aliases, type, group, description)
- Example values, syntax capabilities (wildcards, proximity, phrase, range)
- Valid enum values for constrained fields
- Operator definitions (citations, references, trending, etc.)

No need to parse `schema.xml` directly — manual updates to the JSON inventory are preferred since we add domain context that raw XML doesn't have. The schema.xml source is at: `https://github.com/adsabs/montysolr/blob/main/deploy/adsabs/server/solr/collection1/conf/schema.xml`

### Source 3: Bibstem Synonyms

`data/model/bibstem_synonyms.json` maps journal names to ADS bibstem abbreviations (~70 journals). Can be expanded via:
```bash
python scripts/collect_bibstems.py --merge  # Needs ADS_API_KEY in .env
```

### Source 4: Institution Synonyms

`data/model/institution_synonyms.json` maps institution names to `inst:` abbreviations (~56 institutions, ~170 synonyms). Loaded at runtime by both `institution_lookup.py` (assembler/server) and `ner.py` (NER extraction). Includes umbrella mappings for parent orgs (NASA→JPL/GSFC/etc., Max Planck→MPA/MPE/MPIA, etc.). Can be expanded via:
```bash
python scripts/collect_institutions.py \
    --source ~/github/CanonicalAffiliations \
    --merge
```

### Source 5: Mentions/Credits Design Doc

`data/reference/Indexing and searching mentions.md` documents the mentions/credits system (software/data tracking). Key fields: `mention_count`, `credit_count`. Note: `mention:` and `credit:` do NOT work as search fields; `mentions()` and `credits()` operators are NOT live. Use `abs:"software_name" mention_count:[1 TO *]` for software-mention queries.

### Source 6: Blog Post Query Examples

`data/reference/blog_query_examples.md` contains ~101 query examples extracted from 14 ADS/SciX blog posts (2018–2025). Covers patterns like nested operators, `similar()` with `entdate:`, `property:(...)` multi-value syntax, `bibstem:` wildcards, `full:` instrument searches, data linking, and earth science collection queries.

Raw blog posts are archived in `data/reference/blog/` (60 files, 2015–2025) for future reference. Key HIGH-priority posts for training data:
- `2020-08-10-the_new_myADS.md` — richest source: nested operators, `topn()`, `arxiv_class:`, `entdate:`, `object:`
- `2024-07-01-data-linking-II.md` — `property:data`, `data:`, `full:` URN, compound property filters
- `2024-08-01-data-linking-III.md` — `doctype:dataset`, `doi:` wildcards, `bibstem:yCat`, `similar()` with bibcodes
- `2025-03-25-what-i-wish-i-knew-about-ads-scix-during-my-phd.md` — `similar()` with `entdate:`, `useful(docs(library/...))`, `ack:`
- `2022-09-06-ads-object-search.md` — `object:` search, `=` modifier, Boolean within `object:`
- `2020-04-06-nasa-open-access.md` — complex property/ack/aff/bibstem combinations, `=keyword:`
- `2020-01-15-affiliations-feature.md` and `2021-04-15-affils-update.md` — `aff:`, `inst:`, `aff_id:`, `affil:` differences

### Source 7: UAT (Unified Astronomy Thesaurus)

`data/model/uat_synonyms.json` maps 4,144 terms (prefLabels + altLabels) to canonical UAT concepts. Built from `data/reference/aas_the-unified-astronomy-thesaurus_6-0-0.json` (UAT v6.0, 2,312 concepts). Runtime module `uat_lookup.py` augments `abs:"topic"` with `OR uat:"UAT Label"` when there's a match. Source: https://vocabs.ardc.edu.au/viewById/119

### Source 8: Planetary Feature Gazetteer

`data/reference/Gazetteer_of_Planetary_Nomenclature_Exported_Nov_7_2024.csv` — USGS planetary nomenclature (16,243 features, 48 targets, 56 feature types). Used as reference for `planetary_feature:` training examples. Source: https://github.com/adsabs/ADSPlanetaryNamesPipeline

`data/model/planetary_feature_synonyms.json` maps 8,915 terms (feature names, feature types, targets) to canonical forms from the USGS Gazetteer. Runtime module `planetary_feature_lookup.py` augments `abs:"feature name"` with `OR planetary_feature:"Canonical Name"` when there's a match. NER also extracts multi-word feature names (e.g. "Olympus Mons", "Valles Marineris") directly into IntentSpec.

