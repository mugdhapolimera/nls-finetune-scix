# NLS Fine-Tune SciX

## Current Focus: Expanding Training Data

We are generating NL-to-query training pairs using SciX help documentation and the Solr schema as references.

## Task

Convert natural language → ADS/SciX structured search queries for [SciXplorer.org](https://scixplorer.org/).

- Input: "papers by Hawking on black hole radiation from the 1970s"
- Output: `author:"Hawking, S" abs:"black hole radiation" pubdate:[1970 TO 1979]`

## Training Data

- **Format:** JSONL with chat messages (system/user/assistant)
- **Gold examples:** `data/datasets/raw/gold_examples.json` (4,938 pairs)
- **Processed train/val:** `data/datasets/processed/train.jsonl` (1,074) / `val.jsonl` (120)
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
| Object | `object:M31` | Astronomical object; **requires `d=astrophysics` discipline param** |
| Citation count | `citation_count:[100 TO *]` | Numeric range |
| Affiliation (virtual) | `aff:"Berkeley"` | Free-text affiliation search |
| Institution (curated) | `inst:"MIT"` | Curated institutional abbreviation |
| Metadata presence | `has:body` | Filter by field presence |
| Mention count | `mention_count:[5 TO *]` | Software/data mentions |
| Credit count | `credit_count:[20 TO *]` | Credits received |

Full syntax: https://ui.adsabs.harvard.edu/help/search/search-syntax

### Discipline-Dependent Fields

Some fields only work when the `d=astrophysics` discipline parameter is set in the search request:
- `object:` — astronomical object search (e.g., `object:"M31"`, `object:"Crab Nebula"`)
- `uat:` — Unified Astronomy Thesaurus terms

Without the discipline param, these fields return HTTP 400. The server (`docker/server.py`) must pass `d=astrophysics` when the query contains these fields.

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
| `de Groot-Hedlin` | `author:"de Groot*"` | Truncate at hyphen (long prefix) |
| `Garcia-Perez` | `author:"Garcia*"` | Truncate at hyphen (long prefix) |
| `Le Floc'h` | `author:"Le Floc*"` | Truncate at apostrophe |
| `El-Badry` | `author:"El-Badry*"` | Short prefix (El-) → keep full + `*` |
| `al-Sufi` | `author:"al-Sufi*"` | Short prefix (al-) → keep full + `*` |
| `Hawking` | `author:"Hawking"` | Simple name → no change |
| `Hawking, S` | `author:"Hawking, S"` | Comma-formatted → no change |

**Runtime behavior:** Applied at two points (same pattern as `(inst: OR aff:)` rewriting):
1. **NER pipeline path** — `_build_author_clause()` calls `_wildcard_complex_author()` during assembly
2. **LLM output path** — `rewrite_complex_author_wildcards()` post-processes model output in `server.py`

**ADS wildcard rules for authors:**
- Trailing `*` inside quotes works: `author:"de Groot*"` ✓
- Mid-name `*` inside quotes does NOT work: `author:"Garcia*Perez"` ✗
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

### Remaining gaps
1. **data field** — 7/24 archives still uncovered: ARI, BICEP2, GCPD, GTC, INES, ISO, NOAO
2. **has field** — ~14/34 values still uncovered (identifier, keyword, pub, title, abstract, author, etc. have few dedicated examples)
3. **lang, page, volume, issue, caption** — still zero dedicated examples
4. **simbad, vizier (as fields)** — still zero examples (covered via `data:SIMBAD`, `data:VizieR`)
5. **NOT/negation** — improved but still underrepresented relative to AND/OR

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
- `packages/finetune/src/finetune/domains/scix/fields.py` — ADS field definitions
- `packages/finetune/src/finetune/domains/scix/field_constraints.py` — Enum values
- `packages/finetune/src/finetune/domains/scix/validate.py` — Query validation
- `packages/finetune/src/finetune/domains/scix/constrain.py` — Post-assembly constraint filter
- `packages/finetune/src/finetune/domains/scix/pipeline.py` — End-to-end NER pipeline orchestration
- `docker/server.py` — Inference server (vLLM-compatible + pipeline endpoints); post-processes LLM output with `rewrite_aff_to_inst_or_aff()`, `rewrite_bibstem_values()`, and `rewrite_complex_author_wildcards()`

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
- `scripts/validate_gold_examples.py` — Syntax + API validation of training examples
- `scripts/generate_coverage_gap_examples.py` — Coverage audit gap-fill: 210 examples across 17 categories (esources, data, NOT, has, grant, ack, keyword, arxiv_class, orcid, entry_date, object, proximity, exact author, cross-domain, mentions, verbose NL, similar, references)
- `scripts/fix_validation_issues.py` — Fixes for validation issues in coverage-gap examples (idempotent)
- `scripts/generate_blog_examples.py` — Blog-sourced patterns: nested operators (trending(useful(...))), similar()+entdate, property:(...) multi-value, bibstem wildcards/OR, full: field, data-linking, earth science collection (91 examples)
- `scripts/clean_gold_examples.py` — Removes non-academic entries, fixes encoding/authors/alignment in gold_examples.json

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

`data/reference/Indexing and searching mentions.md` documents the mentions/credits system (software/data tracking). Key fields: `mention`, `credit`, `mention_count`, `credit_count`. Note: `mentions()` and `credits()` second-order operators are documented in the design doc but are NOT live — use `has:mention`, `has:credit`, `mention_count`, and `credit_count` instead.

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

