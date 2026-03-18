# NLS Fine-Tune SciX — Weekly Progress (March 10–17, 2026)

## Table of Contents

1. [Summary](#1-summary)
2. [Training Data Quality](#2-training-data-quality)
3. [Intent-Level Merge Architecture (Phase A)](#3-intent-level-merge-architecture-phase-a)
4. [Phase B: IntentSpec JSON Training Format](#4-phase-b-intentspec-json-training-format)
5. [Runtime Augmentation Modules](#5-runtime-augmentation-modules)
6. [Phase C: RAG-Augmented LLM Path](#6-phase-c-rag-augmented-llm-path)
7. [Running the Server](#7-running-the-server)
8. [Building Datasets for Retraining](#8-building-datasets-for-retraining)
9. [Benchmark Evaluation](#9-benchmark-evaluation)
10. [Decisions Needed](#10-decisions-needed)
11. [**Live Demo Outline**](#11-live-demo-outline) — Step-by-step with copy-paste commands

---

## 1. Summary

### What shipped (no retraining needed)

| Improvement | What it does |
|---|---|
| Training data cleanup | 4,924 clean, validated examples (was ~5,200 noisy) |
| Coverage gap fills | +322 examples for 17+ underrepresented categories |
| Intent-level merge | Structural merge replaces ~300 lines of regex heuristics |
| Phase B server support | Server auto-detects IntentSpec JSON from LLM output |
| UAT augmentation | `abs:"dark matter"` → `(abs:"dark matter" OR uat:"Dark matter")` at runtime |
| Planetary feature augmentation | `abs:"Olympus Mons"` → `(abs:"Olympus Mons" OR planetary_feature:"Olympus Mons")` at runtime |
| Institution expansion | `aff:"NASA"` → `(inst:"JPL" OR inst:"GSFC" OR ... OR aff:"NASA")` at runtime |
| Bibstem normalization | `bibstem:Nature` → `bibstem:"Natur"` at runtime |
| Author wildcarding | `author:"de Groot-Hedlin"` → `author:"de Groot*"` at runtime |
| RAG few-shot retrieval | Injects 2-3 similar gold examples into LLM prompt |
| Field reference cards | Injects valid enum values into LLM prompt to reduce hallucination |

### Ready for retraining (needs GPU time)

| Dataset | Command | Description |
|---|---|---|
| Intent format | `python scripts/build_dataset.py --format intent` | LLM outputs `<think>` + IntentSpec JSON |
| RAG-augmented intent | `python scripts/build_rag_dataset.py --k 3` | Same + 3 few-shot neighbors per example |

### Interactive demo script

```bash
# Full demo with pauses between sections
PYTHONPATH=packages/finetune/src python scripts/demo_improvements.py

# Skip pauses
PYTHONPATH=packages/finetune/src python scripts/demo_improvements.py --no-pause

# Run a specific section (1-7)
PYTHONPATH=packages/finetune/src python scripts/demo_improvements.py --section 5

# List available sections
PYTHONPATH=packages/finetune/src python scripts/demo_improvements.py --list
```

---

## 2. Training Data Quality

### Cleanup rounds

| Round | Date | Action | Examples affected |
|---|---|---|---|
| 1 | Mar 4 | Removed non-academic entries, fixed authors/queries/encoding | -116, 30+ fixes |
| 2 | Mar 4 | Standardized `collection:`→`database:`, fixed broken queries | 203 rewrites |
| Realism | Mar 5 | Removed broken/duplicate, rewrote template NL strings | -118, 205 rewrites |
| Synonym | Mar 17 | Removed bad synonym-expansion examples | -24, +13 clean replacements |

**Net result:** 5,200 noisy → 4,924 clean, syntax-validated examples.

### Coverage gap fills

| Date | Script | Examples added | Categories |
|---|---|---|---|
| Mar 4 | `generate_coverage_gap_examples.py` | +210 | esources, data, NOT, has, grant, ack, keyword, arxiv_class, orcid, entry_date, object, similar, references |
| Mar 5 | `generate_training_improvements.py` | +112 | reference parsing, UAT, negation, software mentions, date diversity, caption, arxiv IDs, count filters, planetary_feature |

### Current category distribution (top 10)

| Category | Count |
|---|---|
| first_author | 809 |
| filters | 701 |
| author | 563 |
| publication | 397 |
| topic | 354 |
| operator | 346 |
| bibgroup | 328 |
| content | 315 |
| compound | 258 |
| property | 155 |

### Remaining gaps

- 7/24 data archives still uncovered: ARI, BICEP2, GCPD, GTC, INES, ISO, NOAO
- ~14/34 `has:` values still uncovered
- `lang`, `page` (standalone), `issue` — low/zero dedicated examples
- `simbad`, `vizier` as standalone fields — zero examples

---

## 3. Intent-Level Merge Architecture (Phase A)

### Before (string-level merge)

```
NER → query string ──┐
                      ├─→ string merge (dedup, regex, heuristics) → query
LLM → query string ──┘
```

~300 lines of regex heuristics for dedup, normalization, field injection. Every LLM artifact (e.g., `abs:(w1 AND w2)`, institution names in abs:) needed a new fix.

### After (intent-level merge)

```
NER → IntentSpec ──────────────┐
                                ├─→ merge_intents() → assembler → query
LLM → query → parse_query() ──┘
```

Assembler always produces valid syntax. Per-field merge policies. Eliminated ~300 lines of heuristics.

### Per-field merge policies

| Field | Preferred Source | Rationale |
|---|---|---|
| authors | NER | Better name formatting |
| free_text_terms | LLM | Understands context better |
| year_from/year_to | NER if extracted | Validated against patterns |
| affiliations | NER | Validated against institution_synonyms |
| bibstems | NER | Validated against bibstem_synonyms |
| operator | LLM | Handles nested/complex operators |
| negation/has/citation_count | LLM only | NER can't detect these |
| doctype/property | Union | Strips `doctype:article` if NL uses generic "papers" |

### Key modules

| Module | Purpose |
|---|---|
| `parse_query.py` | Parses LLM's raw query string → IntentSpec (inverse of assembler) |
| `merge.py` | Per-field merge of NER + LLM IntentSpecs |
| `assembler.py` | Deterministic IntentSpec → valid ADS query |
| `intent_spec.py` | IntentSpec dataclass (contract between NER, merge, assembler) |

---

## 4. Phase B: IntentSpec JSON Training Format

### Before (LLM outputs query string)

```
Input:  "papers by Hawking on black holes"
Output: {"query": "author:\"Hawking, S\" abs:\"black holes\""}
→ must reverse-engineer via parse_query_to_intent() → IntentSpec
```

### After (LLM outputs IntentSpec JSON directly)

```
Input:  "papers by Hawking on black holes"
Output: <think>
        Author: Hawking → "Hawking, S". Topic: black holes.
        </think>
        {"authors": ["Hawking, S"], "free_text_terms": ["black holes"]}
→ direct merge, no parsing needed
```

The server auto-detects the format — supports both old and new models simultaneously.

### Training data conversion

| Stat | Value |
|---|---|
| Total examples converted | 4,924 |
| With intent_json | 4,867 (98.8%) |
| With think_trace | 4,867 (98.8%) |
| Conversion errors | 0 |

### How to generate

```bash
# Convert gold examples to intent format
python scripts/convert_to_intent_format.py

# Build training JSONL with intent format
python scripts/build_dataset.py --format intent --output-dir data/datasets/processed
```

---

## 5. Runtime Augmentation Modules

These run at serving time in `server.py`. They transparently augment queries regardless of which model version is deployed. **No retraining needed.**

### 5a. UAT (Unified Astronomy Thesaurus) Augmentation

- **Module:** `uat_lookup.py` (4,144 terms from UAT v6.0)
- **Effect:** `abs:"dark matter"` → `(abs:"dark matter" OR uat:"Dark matter")`
- **When:** Applied post-assembly on all queries with `abs:` clauses

### 5b. Planetary Feature Augmentation

- **Module:** `planetary_feature_lookup.py` (8,915 terms from USGS Gazetteer)
- **Effect:** `abs:"Olympus Mons"` → `(abs:"Olympus Mons" OR planetary_feature:"Olympus Mons")`
- **When:** Applied post-assembly + NER extracts multi-word features directly

### 5c. Institution Expansion

- **Module:** `institution_lookup.py` (~56 institutions, ~170 synonyms)
- **Effect:** `aff:"NASA"` → `(inst:"JPL" OR inst:"GSFC" OR inst:"NASA Ames" OR inst:"MSFC" OR aff:"NASA")`
- **When:** Applied to NER-assembled queries + LLM output string rewrites

### 5d. Bibstem Normalization

- **Module:** `bibstem_lookup.py` (~70 journal mappings)
- **Effect:** `bibstem:"Astrophysical Journal"` → `bibstem:"ApJ"`
- **When:** Applied to NER-assembled queries + LLM output string rewrites

### 5e. Complex Author Name Wildcarding

- **Module:** `assembler.py` → `rewrite_complex_author_wildcards()`
- **Effect:** `author:"de Groot-Hedlin"` → `author:"de Groot*"` (catches indexing variants)
- **When:** Applied to NER-assembled queries + LLM output string rewrites

---

## 6. Phase C: RAG-Augmented LLM Path

### Architecture

```
NL text → NER ─────────────────→ IntentSpec_NER ──┐
       │                                           ├─→ merge → assembler → query
       └→ [RAG: few-shot + field cards]            │
            ↓                                      │
          LLM (with context) ──→ IntentSpec_LLM ──┘
```

RAG retrieval (<20ms) runs **in parallel** with NER. No new dependencies — reuses existing BM25 index over the 4,924 gold examples.

### Few-shot retrieval

For a given NL query, retrieves 2-3 similar gold examples with their IntentSpec JSON and think traces. These are injected as user/assistant pairs before the actual query in the LLM prompt.

**Example:** query "PhD theses about galaxy evolution" retrieves:
- "PhD theses on galaxy evolution" → `{"free_text_terms": ["galaxy evolution"], "doctype": ["phdthesis"]}`
- "looking for masters theses" → `{"doctype": ["mastersthesis"]}`

### Field reference cards

12 compact cards listing valid enum values. 1-2 are selected per query based on keyword triggers and appended to the system prompt.

| Card | Triggers |
|---|---|
| doctype | thesis, preprint, conference, software, book... |
| property | refereed, open access, peer review... |
| operators | citing, referenced, trending, similar... |
| negation | not, excluding, without, except... |
| data | archive, MAST, NED, SIMBAD... |
| has | full text, grant, orcid, acknowledgment... |
| metrics | highly cited, citation count, read count... |
| dates | recent, last year, since, between... |
| esources | pdf, full text, scan, publisher version... |
| collection | astronomy, physics, earth science... |
| bibgroup | hubble, jwst, chandra, kepler, telescope... |

### Augmented prompt format

```
┌──────────────────────────────────────────────────────┐
│ System: Convert NL to intent JSON...                 │
│   + Reference: [1-2 field cards if relevant]         │
│                                                      │
│ User: Query: [similar example 1]                     │
│ Asst: <think>...</think> {intent_json_1}             │
│                                                      │
│ User: Query: [similar example 2]                     │
│ Asst: <think>...</think> {intent_json_2}             │
│                                                      │
│ User: Query: [similar example 3]                     │
│ Asst: <think>...</think> {intent_json_3}             │
│                                                      │
│ User: Query: [actual user query]  ← model generates  │
└──────────────────────────────────────────────────────┘
```

**Token budget:** ~420 tokens total (system ~150 + 3×80 few-shot + 30 query). Qwen3-1.7B has 32K context.

**Latency:** ~50ms extra generation time for the expanded prompt. Retrieval runs in parallel with NER, so adds ~0ms wall time.

---

## 7. Running the Server

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_NAME` | `adsabs/NLQT-Qwen3-1.7B` | HuggingFace model to load |
| `DEVICE` | auto-detect | `cuda`, `mps`, or `cpu` |
| `PORT` | `8000` | Server port |
| `HYBRID_MODE` | `true` | NER + LLM in parallel, merge results |
| `RAG_ENABLED` | `true` | Few-shot RAG on the LLM path |
| `RAG_NUM_EXAMPLES` | `3` | Number of few-shot examples to inject |
| `RAG_MAX_CARDS` | `2` | Max field reference cards to inject |
| `LLM_TIMEOUT` | `1.5` | LLM generation timeout in seconds. Raise to `10` for local MPS/CPU demos |

### Configuration combos

Below are the meaningful configurations for comparison. Each row is a different way to run the server. Use the "How to run" commands to start the server, then test with curl or the benchmark script.

---

#### Config 1: NER-only (no model needed)

The heuristic NER pipeline only. Fast, deterministic, no GPU. Good baseline.

```bash
# Local Python
HYBRID_MODE=false \
PYTHONPATH=packages/finetune/src \
PORT=8001 \
python docker/server.py
```

> Note: The server will print `Pipeline not available` warnings if torch can't load a model, but NER pipeline still works via the `/debug/pipeline` endpoint.

```bash
# Test it
curl "http://localhost:8001/debug/pipeline?q=papers+by+Hawking+on+black+holes"
```

---

#### Config 2: Hybrid NER + LLM (no RAG)

The baseline hybrid mode: NER and LLM run in parallel, results merged.

```bash
# Local Python (auto-detect device)
HYBRID_MODE=true \
RAG_ENABLED=false \
PYTHONPATH=packages/finetune/src \
PORT=8001 \
python docker/server.py
```

```bash
# Docker (GPU)
docker run --gpus all -p 8000:8000 \
  -e HYBRID_MODE=true \
  -e RAG_ENABLED=false \
  nls-server
```

```bash
# Test it
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llm",
    "messages": [
      {"role": "user", "content": "Query: papers by Hawking on black holes\nDate: 2026-03-17"}
    ]
  }'
```

---

#### Config 3: Hybrid + RAG few-shot (no field cards)

Adds few-shot example retrieval to the LLM prompt, but no field reference cards.

```bash
HYBRID_MODE=true \
RAG_ENABLED=true \
RAG_MAX_CARDS=0 \
PYTHONPATH=packages/finetune/src \
PORT=8001 \
python docker/server.py
```

---

#### Config 4: Hybrid + RAG few-shot + field cards (full Phase C)

The full pipeline with all features enabled. This is the default.

```bash
# Local Python (this is the default — all features on)
HYBRID_MODE=true \
RAG_ENABLED=true \
RAG_NUM_EXAMPLES=3 \
RAG_MAX_CARDS=2 \
PYTHONPATH=packages/finetune/src \
PORT=8001 \
python docker/server.py
```

```bash
# Or simply (defaults are all true):
PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py
```

```bash
# Docker (GPU)
docker run --gpus all -p 8000:8000 \
  -e RAG_ENABLED=true \
  -e RAG_NUM_EXAMPLES=3 \
  -e RAG_MAX_CARDS=2 \
  nls-server
```

```bash
# Docker Compose — add to environment section:
#   - RAG_ENABLED=true
#   - RAG_NUM_EXAMPLES=3
#   - RAG_MAX_CARDS=2
```

---

#### Config 5: LLM-only (no NER, no RAG)

Model output only — no NER validation, no merge, no runtime augmentation. Useful to isolate model quality.

```bash
HYBRID_MODE=false \
RAG_ENABLED=false \
PYTHONPATH=packages/finetune/src \
PORT=8001 \
python docker/server.py
```

> The `/v1/chat/completions` endpoint will use the model directly. No NER fallback.

---

#### Config 6: Tuning RAG parameters

Experiment with different numbers of few-shot examples and field cards.

```bash
# More examples, more cards
RAG_NUM_EXAMPLES=5 RAG_MAX_CARDS=3 \
PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py

# Fewer examples
RAG_NUM_EXAMPLES=1 RAG_MAX_CARDS=1 \
PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py
```

---

### Using `run_local.sh`

The existing helper script auto-detects your device. To add RAG env vars:

```bash
export RAG_ENABLED=true
export RAG_NUM_EXAMPLES=3
export RAG_MAX_CARDS=2
./docker/run_local.sh        # auto-detect device
./docker/run_local.sh mps    # Apple Silicon
./docker/run_local.sh cpu    # CPU only
```

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check (shows `hybrid_mode`, `rag_enabled`) |
| `/v1/chat/completions` | POST | vLLM-compatible chat (hybrid when enabled) |
| `/pipeline` | POST | Hybrid NER+NLS pipeline |
| `/debug/pipeline?q=...` | GET | NER pipeline only |
| `/debug/hybrid?q=...` | GET | Full debug: query, merge source, intent traces, RAG context |
| `/v1/models` | GET | List models |

### Debug endpoint output

`/debug/hybrid?q=recent+papers+on+dark+matter+in+MNRAS` returns:

```json
{
  "query": "abs:\"dark matter\" bibstem:\"MNRAS\" pubdate:[2023 TO 2026]",
  "source": "hybrid",
  "nls_query": "...",
  "ner_query": "...",
  "fields_injected": ["bibstem"],
  "intents": {
    "ner": {"free_text_terms": ["dark matter"], "bibstems": ["MNRAS"], ...},
    "llm": {"free_text_terms": ["dark matter"], ...},
    "merged": {"free_text_terms": ["dark matter"], "bibstems": ["MNRAS"], ...}
  },
  "rag": {
    "enabled": true,
    "few_shot_count": 3,
    "few_shot_examples": [
      {"nl": "dark matter papers", "intent_json": {...}},
      ...
    ],
    "field_cards": ["Date syntax: pubdate:[2020 TO 2023], ..."]
  }
}
```

---

## 8. Building Datasets for Retraining

### Three training formats

#### Format 1: Original (query string output)

```
System: Convert NL to query. Output JSON: {"query": "..."}
User:   Query: papers by Hawking on black holes
Asst:   {"query": "author:\"Hawking, S\" abs:\"black holes\""}
```

```bash
python scripts/build_dataset.py --format query --output-dir data/datasets/processed
```

#### Format 2: Intent (Phase B — recommended next step)

```
System: Convert NL to structured search intent...
User:   Query: papers by Hawking on black holes
Asst:   <think>Author: Hawking → "Hawking, S"...</think>
        {"authors": ["Hawking, S"], "free_text_terms": ["black holes"]}
```

```bash
python scripts/build_dataset.py --format intent --output-dir data/datasets/processed
```

#### Format 3: RAG-augmented intent (Phase C)

```
System: Convert NL to structured search intent... + [field cards]
User:   Query: [similar example 1]
Asst:   <think>...</think> {intent_json_1}
User:   Query: [similar example 2]
Asst:   <think>...</think> {intent_json_2}
User:   Query: [similar example 3]
Asst:   <think>...</think> {intent_json_3}
User:   Query: papers by Hawking on black holes
Asst:   <think>Author: Hawking → "Hawking, S"...</think>
        {"authors": ["Hawking, S"], "free_text_terms": ["black holes"]}
```

```bash
python scripts/build_rag_dataset.py --k 3 --output data/datasets/processed/train_rag.jsonl

# Dry-run (see stats without writing)
python scripts/build_rag_dataset.py --k 3 --dry-run
```

### Dataset sizes

| Dataset | Examples | Avg messages/example | Relative GPU time |
|---|---|---|---|
| Format 1 (query) | 5,185 train / 577 val | 3 | 1× |
| Format 2 (intent) | ~4,924 | 3 | 1× |
| Format 3 (RAG intent) | ~4,924 | 8.8 | ~2-3× |

---

## 9. Benchmark Evaluation

### Current NER-only baseline (301 benchmark queries, Jan 23)

| Metric | Value |
|---|---|
| Pass rate | 98.7% (297/301) |
| Exact match | 11.6% (35/301) |
| Syntax valid | 98.0% |
| Constraint valid | 100% |

### How to run comparisons

```bash
# NER-only baseline (no model needed)
python scripts/evaluate_benchmark.py \
    --output data/datasets/evaluations/baseline_ner.json

# With the server running (any config from Section 7):
# ... benchmark against it (requires server running with model loaded)
```

### Expected improvement trajectory

| Configuration | Pass Rate | Exact Match | Notes |
|---|---|---|---|
| NER-only baseline | 98.7% | 11.6% | Measured Jan 23 |
| Hybrid NER+LLM (current model) | ~98-99% | ~15-20%? | Needs measurement |
| + Phase C RAG (no retrain) | ~99% | ~20-25%? | Needs measurement |
| + Intent format retrain | ~99% | ~25-35%? | Needs GPU |
| + RAG-augmented retrain | ~99% | ~30-40%? | Needs GPU |

> The benchmark was created Jan 22 and predates UAT, planetary features, coverage gap fills, intent format, and RAG. **Consider updating the benchmark.**

---

## 10. Decisions Needed

1. **Retrain with intent format?**
   - Recommended. Training data is ready (`--format intent`). ~3 hours GPU.
   - The model needs to be retrained to produce IntentSpec JSON instead of query strings.

2. **Deploy RAG with current model or wait for retrain?**
   - Option A: Deploy now → immediate improvement, no GPU needed
   - Option B: Retrain first → model learns to leverage few-shot context
   - Option C: Both → deploy now, retrain later for further improvement

3. **Update the benchmark?**
   - Current benchmark (301 queries) predates UAT, planetary features, coverage gap fills, intent format, and RAG.
   - Should add queries testing these new capabilities.

4. **Adjust merge policies?**
   - Current policies prefer NER for authors/affiliations/bibstems and LLM for topics/operators/negation.
   - After benchmarking with the model, we can shift trust toward the LLM for fields where it outperforms.

5. **Fill remaining coverage gaps?**
   - 7/24 data archives, ~14/34 has: values, lang/page/issue fields.
   - Low priority unless these come up in production.

6. **Update Dockerfile for new files?**
   - Need to add: `planetary_feature_synonyms.json`, `gold_examples_intent.json` (for RAG)
   - Current Dockerfile is missing these.

---

## 11. Live Demo Outline (Nectar UI)

> Estimated time: 25-30 minutes.
> You type queries into the Nectar search bar and show results in the browser.
> A second terminal shows the debug endpoint to explain what happened under the hood.

### Before the demo — Setup (do this 10 min before)

You need **three terminal tabs** and a **browser**:

| Tab | What | Command |
|---|---|---|
| **Tab 1** | NLS server | Runs the model + pipeline |
| **Tab 2** | Nectar | The SciX frontend UI |
| **Tab 3** | Debug curl | Inspect what happened under the hood |
| **Browser** | http://localhost:8000 | Where you type queries |

**Step 1 — Start the NLS server (Tab 1):**

```bash
cd ~/github/nls-finetune-scix

# All features ON (hybrid + RAG + field cards)
# LLM_TIMEOUT=10 gives the model enough time on MPS/CPU (default 1.5s is for production GPU)
LLM_TIMEOUT=10 PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py
```

Wait for `Model loaded successfully on ...` before continuing.

> **Important:** The default `LLM_TIMEOUT=1.5` is tuned for production GPU (A10G ~50ms).
> On MPS (~500ms) or CPU (~2000ms), the LLM times out and falls back to NER-only,
> which can't handle negation, operators, or metrics. Set `LLM_TIMEOUT=10` for demos.

Verify it's working:

```bash
# In Tab 3:
curl -s http://localhost:8001/health | python -m json.tool
```

You should see `"hybrid_mode": true` and `"rag_enabled": true`.

**Step 2 — Configure Nectar to point to your server (Tab 2):**

Edit `~/ads-dev/nectar/.env.local` (create it if it doesn't exist):

```bash
cat > ~/ads-dev/nectar/.env.local << 'EOF'
NEXT_PUBLIC_NL_SEARCH=enabled
NL_SEARCH_PIPELINE_ENDPOINT=http://localhost:8001
NL_SEARCH_VLLM_ENDPOINT=http://localhost:8001/v1/chat/completions
EOF
```

**Step 3 — Start Nectar (Tab 2):**

```bash
cd ~/ads-dev/nectar
pnpm dev
```

**Step 4 — Open browser:**

Go to **http://localhost:8000** (or wherever Nectar runs). You should see the SciX search bar with NL search enabled.

**Step 5 — Open Tab 3 for debug commands** (keep it ready):

```bash
cd ~/github/nls-finetune-scix
```

---

### Demo Flow

#### Part 1: The Big Picture (2 min, talk)

Before typing anything, explain the architecture:

> "When you type natural language into the search bar, Nectar sends it to our server.
> The server runs two things in parallel: a fast rules-based NER (<20ms) and a fine-tuned
> 1.7B LLM (~500ms). Both produce a structured intent — authors, topics, dates, operators —
> which get merged. Then the assembler builds a valid ADS query, and runtime augmentation
> adds UAT thesaurus terms, planetary features, institution codes, etc. All within the
> 2-second timeout Nectar expects."

---

#### Part 2: Basic Queries (3 min, type in search bar)

Type each query into the Nectar search bar. Point out the ADS query that appears in the results page URL / search bar.

**Type in Nectar:**

> `papers by Hawking on black holes from the 1970s`

**Point out:** The URL/query bar now shows something like `author:"Hawking" abs:"black holes" pubdate:[1970 TO 1979]`. Results are real papers.

**Then in Tab 3, show what happened under the hood:**

```bash
curl -s "http://localhost:8001/debug/hybrid?q=papers+by+Hawking+on+black+holes+from+the+1970s" | python -m json.tool
```

Point out: `source`, `intents.ner`, `intents.llm`, `intents.merged`, and `rag.few_shot_examples`.

**More queries to type in Nectar (one at a time):**

> `dark matter review articles since 2020`

> `JWST exoplanet atmosphere observations from STScI`

---

#### Part 3: Runtime Augmentation — UAT (2 min, type in search bar)

> `exoplanet atmospheres spectroscopy`

**In Tab 3:**

```bash
curl -s "http://localhost:8001/debug/hybrid?q=exoplanet+atmospheres+spectroscopy" | python -m json.tool
```

**Point out:** The final query contains `(abs:"exoplanet atmospheres" OR uat:"Exoplanet atmospheres")`. The UAT thesaurus augmentation added this automatically. It matches papers tagged with the controlled vocabulary term even if they don't use that exact phrase.

> "This is one of 4,144 UAT terms we augment at runtime. No retraining needed."

---

#### Part 4: Runtime Augmentation — Planetary Features (2 min)

> `Olympus Mons crater morphology on Mars`

**In Tab 3:**

```bash
curl -s "http://localhost:8001/debug/hybrid?q=Olympus+Mons+crater+morphology+on+Mars" | python -m json.tool
```

**Point out:** The query contains `planetary_feature:"Olympus Mons"`. The NER recognized "Olympus Mons" as a feature from the USGS Gazetteer (8,915 terms) and the assembler added the planetary_feature clause.

---

#### Part 5: Runtime Augmentation — Institutions (2 min)

> `dark matter papers from NASA`

**In Tab 3:**

```bash
curl -s "http://localhost:8001/debug/hybrid?q=dark+matter+papers+from+NASA" | python -m json.tool
```

**Point out:** The query expands `NASA` into `(inst:"JPL" OR inst:"GSFC" OR inst:"NASA Ames" OR inst:"MSFC" OR aff:"NASA")`. This catches papers from any NASA center. The `inst:` field uses curated institutional abbreviations with much better recall than free-text `aff:` alone.

> `cosmology papers from Max Planck`

Shows `(inst:"MPA" OR inst:"MPE" OR inst:"MPIA" OR aff:"Max Planck")`.

---

#### Part 6: LLM-Only Capabilities (3 min)

These features only work because of the LLM — NER alone can't handle them.

**Operators:**

> `papers citing the LIGO discovery`

Tab 3: `curl -s "http://localhost:8001/debug/hybrid?q=papers+citing+the+LIGO+discovery" | python -m json.tool`

Point out: `citations()` operator wrapping the inner query. NER contributed the topic; LLM contributed the operator.

**Negation:**

> `cosmology papers excluding preprints`

Tab 3: `curl -s "http://localhost:8001/debug/hybrid?q=cosmology+papers+excluding+preprints" | python -m json.tool`

Point out: `NOT doctype:eprint` or `NOT property:eprint`. The LLM understands "excluding preprints" = negation.

**Metrics:**

> `highly cited cosmology papers with more than 500 citations`

Tab 3: `curl -s "http://localhost:8001/debug/hybrid?q=highly+cited+cosmology+papers+with+more+than+500+citations" | python -m json.tool`

Point out: `citation_count:[500 TO *]`. Only the LLM can extract this from natural language.

---

#### Part 7: Complex Author Names (1 min)

> `papers by El-Badry on binary stars`

Tab 3: `curl -s "http://localhost:8001/debug/hybrid?q=papers+by+El-Badry+on+binary+stars" | python -m json.tool`

Point out: The query uses `author:"El-Badry*"` — the trailing wildcard catches ADS indexing variants for hyphenated names. This is deterministic runtime processing, not learned.

---

#### Part 8: RAG In Action (3 min, show debug output)

Show what few-shot examples the model received for a query:

> `PhD theses about galaxy evolution`

```bash
curl -s "http://localhost:8001/debug/hybrid?q=PhD+theses+about+galaxy+evolution" | python -m json.tool
```

**Point out the `rag` section:**
- `few_shot_examples`: the 3 similar gold examples the model saw before generating
- `field_cards`: any enum reference cards injected (e.g., the doctype card listing `phdthesis`)
- The model saw examples with `doctype: ["phdthesis"]` and produced the right output

> "The RAG retriever found 3 similar queries in <20ms from our 4,924 gold examples.
> The model sees these worked examples before it generates, like an open-book exam."

**To show RAG matters, compare with RAG off:**

Stop the server in Tab 1 (Ctrl+C), restart without RAG:

```bash
RAG_ENABLED=false PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py
```

Then re-type `PhD theses about galaxy evolution` in Nectar and compare the result.

```bash
curl -s "http://localhost:8001/debug/hybrid?q=PhD+theses+about+galaxy+evolution" | python -m json.tool
```

Point out: `rag.enabled: false`, `few_shot_count: 0`. Compare the query quality.

**Restart with RAG on for remaining demos:**

```bash
# Ctrl+C, then:
PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py
```

---

#### Part 9: Doctype, Property, Bibstem (2 min)

These show the NER + LLM + runtime pipeline working together:

> `open access refereed cosmology papers in Nature`

Tab 3: `curl -s "http://localhost:8001/debug/hybrid?q=open+access+refereed+cosmology+papers+in+Nature" | python -m json.tool`

Point out: `property:openaccess property:refereed` (from LLM), `abs:"cosmology"` (LLM), `bibstem:"Natur"` (NER recognized "Nature", bibstem_lookup normalized it).

> `trending machine learning astronomy papers`

Point out: `trending(abs:"machine learning")` — the `trending()` operator.

---

#### Part 10: Edge Cases & Date Handling (2 min)

> `recent JWST papers from this week`

Tab 3: `curl -s "http://localhost:8001/debug/hybrid?q=recent+JWST+papers+from+this+week" | python -m json.tool`

Point out: Uses `entdate:[NOW-7DAYS TO *]` for "this week" — searches by entry date, not publication date.

> `supernova light curves in Nature or Science`

Point out: Handles OR between two journals, bibstem normalization for both.

---

#### Part 11: Wrap-up & Decisions (3 min, discussion)

**Summarize what you just showed:**

> "Everything you just saw runs within the 2-second Nectar timeout. NER provides the fast
> backbone, the LLM adds operators/negation/metrics the regex can't handle, and 5 runtime
> augmentation modules add UAT, planetary features, institutions, bibstems, and author
> wildcarding — all without retraining."

**Key questions for the team:**

1. **Retrain with intent format?** — Training data is ready, ~3 hours GPU. The model would output structured JSON instead of query strings.
2. **Deploy RAG now or after retrain?** — It works with the current model (you just saw it). Better after retrain.
3. **Update benchmark?** — Current 301 queries predate all new features. Should we add test queries for UAT, planetary features, etc.?
4. **Merge policy adjustments?** — Currently NER-preferred for authors/affiliations. Should we change?
5. **More coverage gaps to fill?** — Any real user queries we're missing?

---

### Quick-Reference: All Demo Queries

Copy-paste these into the **Nectar search bar**. Each showcases a different feature.

| # | Type in Nectar | What to point out |
|---|---|---|
| 1 | `papers by Hawking on black holes from the 1970s` | Basic: author + topic + date range |
| 2 | `dark matter review articles since 2020` | Compound: topic + doctype + year |
| 3 | `JWST exoplanet atmosphere observations from STScI` | Institution + bibgroup + topic |
| 4 | `exoplanet atmospheres spectroscopy` | UAT augmentation adds `uat:"..."` |
| 5 | `Olympus Mons crater morphology on Mars` | Planetary feature from USGS Gazetteer |
| 6 | `dark matter papers from NASA` | Institution: NASA → JPL/GSFC/Ames/MSFC |
| 7 | `cosmology papers from Max Planck` | Institution: → MPA/MPE/MPIA |
| 8 | `papers citing the LIGO discovery` | LLM: `citations()` operator |
| 9 | `cosmology papers excluding preprints` | LLM: negation (NOT doctype:eprint) |
| 10 | `highly cited cosmology papers with more than 500 citations` | LLM: citation_count:[500 TO *] |
| 11 | `papers by El-Badry on binary stars` | Author wildcarding for hyphenated names |
| 12 | `PhD theses about galaxy evolution` | RAG: model sees similar examples, gets doctype right |
| 13 | `open access refereed cosmology papers in Nature` | Property + bibstem normalization |
| 14 | `trending machine learning astronomy papers` | Operator: `trending()` |
| 15 | `recent JWST papers from this week` | Date: `entdate:[NOW-7DAYS TO *]` |
| 16 | `supernova light curves in Nature or Science` | OR journals + bibstem normalization |

### Quick-Reference: Debug Commands

Run these in **Tab 3** after typing a query in Nectar to show what happened:

```bash
# Replace QUERY with the URL-encoded query (spaces → +)

# Full debug (shows NER intent, LLM intent, merged intent, RAG context)
curl -s "http://localhost:8001/debug/hybrid?q=QUERY" | python -m json.tool

# NER only (what the rules-based pipeline produces alone)
curl -s "http://localhost:8001/debug/pipeline?q=QUERY" | python -m json.tool

# Health check (shows what features are enabled)
curl -s http://localhost:8001/health | python -m json.tool
```

### Quick-Reference: Server Configurations

To restart the server with different features, Ctrl+C in Tab 1 then:

```bash
# All features ON (default) — use LLM_TIMEOUT=10 for MPS/CPU
LLM_TIMEOUT=10 PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py

# RAG OFF (compare quality without few-shot examples)
LLM_TIMEOUT=10 RAG_ENABLED=false PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py

# Hybrid OFF, NER only (no LLM — shows NER baseline, instant)
HYBRID_MODE=false PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py

# LLM only, no NER (shows raw model quality)
LLM_TIMEOUT=10 HYBRID_MODE=false RAG_ENABLED=false PYTHONPATH=packages/finetune/src PORT=8001 python docker/server.py
```

> After restarting the server, you do NOT need to restart Nectar. It reconnects automatically.

---

## Files Changed This Week

### New modules

| File | Purpose |
|---|---|
| `packages/.../parse_query.py` | Parses LLM query string → IntentSpec |
| `packages/.../merge.py` | Intent-level merge (NER + LLM IntentSpecs) |
| `packages/.../rag_retrieval.py` | Few-shot retrieval for RAG |
| `packages/.../field_cards.py` | Static field reference cards |
| `packages/.../uat_lookup.py` | UAT thesaurus lookup + rewriting |
| `packages/.../planetary_feature_lookup.py` | Planetary feature lookup + rewriting |

### Modified modules

| File | Changes |
|---|---|
| `docker/server.py` | Phase B auto-detect, Phase C RAG integration, new env vars |
| `packages/.../intent_spec.py` | `to_compact_dict()`, `from_compact_dict()`, new fields |
| `packages/.../assembler.py` | `rewrite_complex_author_wildcards()` |
| `packages/.../retrieval.py` | Fixed `get_index()` env var handling |
| `packages/.../prompts.py` | Added `SYSTEM_PROMPT_INTENT` |

### New scripts

| File | Purpose |
|---|---|
| `scripts/convert_to_intent_format.py` | Gold examples → intent format |
| `scripts/build_rag_dataset.py` | RAG-augmented training JSONL |
| `scripts/remove_synonym_expansion.py` | Cleanup bad synonym examples |
| `scripts/demo_improvements.py` | Interactive demo of all improvements |

### New data files

| File | Purpose |
|---|---|
| `data/datasets/raw/gold_examples_intent.json` | 4,924 examples with IntentSpec JSON + think traces |
| `data/model/uat_synonyms.json` | 4,144 UAT terms |
| `data/model/planetary_feature_synonyms.json` | 8,915 planetary feature terms |

### Tests

| File | Tests |
|---|---|
| `tests/test_rag_retrieval.py` | 10 tests (retrieval, dedup, cache, edge cases) |
| `tests/test_field_cards.py` | 14 tests (card selection, triggers, format) |
| `tests/test_parse_query.py` | Parse query → IntentSpec |
| `tests/test_merge.py` | Intent-level merge |
| `tests/test_server_parse.py` | LLM response parsing |
| `tests/test_intent_spec.py` | IntentSpec serialization |
| `tests/test_convert_intent.py` | Intent format conversion |

```bash
# Run all tests
PYTHONPATH=packages/finetune/src python -m pytest packages/finetune/tests/ -v -p no:celery
```
