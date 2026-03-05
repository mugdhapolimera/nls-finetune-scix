# NLS Fine-tune SciX

Fine-tuning infrastructure for converting natural language to ADS/SciX scientific literature search queries.

**Example:** "papers by Hawking on black hole radiation from the 1970s" → `author:"Hawking, S" abs:"black hole radiation" pubdate:[1970 TO 1979]`

**Target:** Complementary search feature for [SciXplorer.org](https://scixplorer.org/)

## Training Data Update (2026-03-04)

### What changed

#### New gold standard examples
Gold examples: 4,557 (from Stephanie's original work) -->  **4,938 pairs**


**Of the 4,557 original examples:**

| | Count | Details |
|---|---|---|
| Kept unchanged | 4,157 | Passed all checks as-is |
| Query modified | 284 | 178 were `collection:` → `database:` renames; 106 were substantive fixes (author format/spelling, encoding, operator direction, alignment, nested operators causing 502s, zero-result queries) |
| NL rewritten | 5 | Query kept, natural language corrected |
| Removed | 116 | Non-academic entries: bag-of-OR title queries, Russian government documents, biographical/entertainment content |
| **Total touched** | **400** | **~9% of the original dataset needed fixes** |

**New examples added: 491.** Coverage gap expansions across 17 underrepresented categories (`esources`, `data` archives, `has` field, `grant`, `ack`, `keyword`, `arxiv_class`, `orcid`, `entry_date`, NOT/negation, `similar()`, `references()`), plus blog-sourced patterns, bibstem queries, affiliation queries, and misc field examples. All template-based with fixed seeds for reproducibility.

#### Three runtime rewriting systems built.
Handle transformations that are deterministic and shouldn't be learned by the model — they run at serving time in `server.py`, post-processing both the NER pipeline output and raw LLM output:

- **Bibstem lookup** (`bibstem_lookup.py` + `bibstem_synonyms.json`): 70 journals, 157 synonym names. Maps natural language journal references ("Monthly Notices", "Nature Astronomy", "Physical Review Letters") to ADS bibstem abbreviations (`MNRAS`, `NatAs`, `PhRvL`). The model outputs whatever journal name it sees in the NL; `rewrite_bibstem_values()` corrects it to the canonical abbreviation. Also supports bibstem wildcards (`bibstem:jgr*` for all JGR journals) and multi-OR syntax (`bibstem:(ApJ OR ApJL OR ApJS)`). Synonym data collected from the ADS Journals API via `scripts/collect_bibstems.py`.
- **Institution lookup** (`institution_lookup.py` + `institution_synonyms.json`): 56 institutions, 148 synonym names. Maps institution references ("Caltech", "Jet Propulsion Laboratory", "Max Planck Institute for Astrophysics") to curated `inst:` abbreviations and builds dual `(inst:"CfA" OR aff:"CfA")` clauses for maximum recall — `inst:` catches the curated canonical form, `aff:` catches free-text variants. Includes umbrella mappings for parent organizations (NASA → JPL/GSFC/NASA Ames/MSFC, Max Planck → MPA/MPE/MPIA). Falls back to `aff:` only for unrecognized institutions. Exception: `inst:` is not supported inside `pos()` operators, so those stay as `aff:` only. Synonym data parsed from ADS CanonicalAffiliations via `scripts/collect_institutions.py`.
- **Complex author wildcarding** (`assembler.py` → `rewrite_complex_author_wildcards()`): Handles hyphenated and apostrophe-containing author names that have inconsistent ADS indexing (e.g., "de Groot-Hedlin" may be indexed as "de GrootHedlin"). Adds a trailing `*` inside quotes to catch variants: `author:"de Groot-Hedlin"` → `author:"de Groot*"`. Short prefixes like "El-" or "al-" keep the full name plus wildcard: `author:"El-Badry*"`. Training data keeps exact author names — wildcarding is applied deterministically at runtime.

#### SciX Query Validator Agent built ("Dr. Query").
We created a specialized Claude Code agent (`.claude/agents/scix-query-validator.md`) for validating training examples. It connects to the live ADS/SciX API via the `scix-mcp` MCP server (`.mcp.json`), which gives it direct access to `search()`, `get_paper()`, `get_citations()`, `get_references()`, and `search_docs()` tools — no curl or API key management needed. The agent operates in two modes:

- **Small-batch mode (<100 examples):** Reviews examples individually using MCP `search` calls with `rows: 1`. For each pair, it checks syntax validity, tests the query against the live API, verifies NL-to-query semantic alignment, and suggests improvements. Output follows a structured PASS/WARN/FAIL format.
- **Bulk mode (100+ examples):** Writes and runs a batch Python script (`scripts/validate_gold_examples.py`) with resume support, rate limiting, and incremental checkpointing. Static syntax checks run first (no API cost), then API-tests only for examples that pass syntax. This is how we validated the full 4,938-example dataset.

The agent has persistent memory (`.claude/agent-memory/scix-query-validator/MEMORY.md`) that accumulates findings across sessions — confirmed API quirks, bibstem mappings, institution abbreviations, operator nesting limitations, and common error patterns. Issues it caught that static validation or manual review wouldn't have:

- `has:` field is completely non-functional via the ADS API (all 34 values return 0 results) — invisible to static checks, only surfaced through live API testing during the pilot audit
- `citations()` vs `references()` semantic direction errors — "software used in X studies" should use `references()` not `citations()`, a subtle mistake that reads correctly to a human
- Author name misspellings causing 0 results ("Chiape" vs "Chiappe") — only catchable by API testing
- Some nested second-order operators cause 502s (`useful(similar(...))`) — discovered by testing generated examples against the live API
- `object:` and `uat:` fields silently require `d=astrophysics` discipline parameter — returns HTTP 400 without it

The batch script and the agent complement each other: 
- the script handles scale (4,938 examples with rate limiting, checkpointing, resume) but only checks what it's programmed to check (balanced brackets, known field names, enum values, NL syntax leakage). 
- the agent catches semantic issues that require domain understanding — operator direction, author existence, query specificity. In practice, we used the agent for the initial pilot audit (10 examples, found 6 critical issues), for validating each new batch of generated examples (~210 at a time), and for spot-checking failures from the batch script.

**Validator hardened: 4 bug fixes, 0 data changes.** The validator (`scripts/validate_gold_examples.py`) had false positives from regex edge cases — colons inside quoted strings, trailing commas from `topn()` args, space-separated parenthesized enums, and NL quality checks over-flagging legitimate identifiers. Final pass rate: **4,938/4,938 (100%)**.

### Core learnings

- **Iterative validation finds different bugs each round.** The pilot audit caught semantic issues (operator direction, misspellings) that static checks miss. Static checks caught syntax and enum issues across 4,800+ examples that manual review can't scale to. API testing caught zero-result queries that look syntactically correct. Each layer reveals problems invisible to the others.
- **Runtime rewriting > model learning** for deterministic transformations. Author name wildcarding (`de Groot-Hedlin` → `author:"de Groot*"`) and institution expansion (`aff:"MIT"` → `(inst:"MIT" OR aff:"MIT")`) are handled at serving time by `server.py`, not baked into training data. This keeps examples clean and avoids teaching the model inconsistent heuristics.
- **ADS syntax has sharp edges** that training data must respect: first-author caret must be inside quotes (`author:"^Last"`), `object:` and `uat:` require a discipline parameter, `mentions()`/`credits()` operators aren't live, nested second-order operators cause 502s, and ADS handles stemming internally (don't truncate stems in `abs:` values).
- **A validator with false positives is worse than no validator** — people learn to ignore it. Fixing the 23 false positives (all regex edge cases) means the pass/fail signal is now trustworthy. Any future failure is a real issue worth investigating.
- **Coverage breadth matters more than depth** for underrepresented fields. Going from 0 → 10 examples for a field (e.g., `entry_date`, `arxiv_class`) has far more impact on model behavior than going from 200 → 210 for `author`. The original dataset had zero examples for 8+ fields.

### What's left

Remaining coverage gaps: 7/24 `data` archives (ARI, BICEP2, GCPD, GTC, INES, ISO, NOAO), ~14/34 `has` values with few dedicated examples, and zero examples for `lang`, `page`, `volume`, `issue`, `caption` fields. See CLAUDE.md for the full gap inventory.

## Prerequisites

- **macOS** (Apple Silicon recommended) - Linux/Windows not currently supported
- **[mise](https://mise.jdx.dev/)** - Runtime manager for Python and Bun
- **ADS API Key** - For query validation and evaluation
- **Google Colab** (optional) - For model training (A100 GPU via Colab Pro)

```bash
brew install mise
```

### ADS API Key

Get your API key from [ADS User Settings](https://ui.adsabs.harvard.edu/user/settings/token) and add it to your `.env` file.

## Quick Start

```bash
# Clone and install
git clone <repo-url>
cd nls-finetune-scix
mise run install

# Configure environment
cp .env.example .env
# Edit .env with your API keys (see below)

# Start development
mise run dev
```

- **Web UI**: http://localhost:5173
- **API**: http://localhost:8000

## API Keys

Configure in `.env`. Not all keys are required depending on what you're doing:

| Key | Required For | Where to Get |
|-----|-------------|--------------|
| `ADS_API_KEY` | Query validation, evaluation | [ADS User Settings](https://ui.adsabs.harvard.edu/user/settings/token) |
| `ANTHROPIC_API_KEY` | Dataset generation | [console.anthropic.com](https://console.anthropic.com/) |

## Commands

All commands use `mise run <task>`. Run `mise tasks` to see all available tasks.

### Development

```bash
mise run dev          # Start API + web servers (parallel)
mise run dev-api      # Start API only (port 8000)
mise run dev-web      # Start web only (port 5173)
```

### Verification

```bash
mise run verify       # Run all checks (lint, types, JSON validation)
mise run verify-full  # All checks + frontend build
mise run lint         # Linters only
mise run format       # Auto-format Python code
mise run test         # Run tests
```

### Fine-Tuning (via Google Colab)

Training is done via the provided Colab notebook:

1. Open `scripts/train_colab.ipynb` in Google Colab
2. Select an A100 GPU runtime (Colab Pro)
3. Upload `data/datasets/processed/train.jsonl`
4. Run all cells (~90 minutes for 50-80k pairs)
5. Model is uploaded to HuggingFace (`adsabs/scix-nls-translator`)

See [docs/fine-tuning-cli.md](docs/fine-tuning-cli.md) for detailed training and deployment documentation.

### Dataset Management

```bash
mise run generate-data   # Full pipeline: curate → generate NL → validate
mise run validate-data   # Validate and create train/val JSONL
```

## Project Structure

```
├── packages/
│   ├── web/            # React frontend (Vite + TanStack Query)
│   ├── api/            # FastAPI backend
│   └── finetune/       # Fine-tuning package (src layout)
│       └── src/finetune/
│           ├── cli/    # scix-finetune CLI commands
│           ├── eval/   # Evaluation modules
│           └── domains/
│               └── scix/  # ADS/SciX-specific logic
│                   ├── fields.py    # ADS field definitions
│                   ├── validate.py  # Query validation
│                   └── eval.py      # Result-set evaluation
├── data/
│   ├── datasets/raw/   # Source data (curated examples, synthetic queries)
│   ├── datasets/processed/  # Training data (train.jsonl, val.jsonl)
│   └── datasets/evaluations/  # Evaluation results
├── scripts/            # Data processing scripts
├── docs/               # Documentation
└── .mise.toml          # Task runner configuration
```

## ADS Search Syntax Reference

The model learns to generate queries using [ADS Search Syntax](https://ui.adsabs.harvard.edu/help/search/search-syntax):

| Field | Example | Description |
|-------|---------|-------------|
| `author:` | `author:"Einstein, A"` | Author name |
| `^author:` | `^author:"Hawking"` | First author only |
| `abs:` | `abs:"dark matter"` | Abstract, title, keywords |
| `title:` | `title:"exoplanet"` | Title only |
| `pubdate:` | `pubdate:[2020 TO 2023]` | Publication date range |
| `bibstem:` | `bibstem:ApJ` | Journal abbreviation |
| `object:` | `object:M31` | Astronomical object |
| `keyword:` | `keyword:"galaxies"` | Keywords |
| `aff:` | `aff:"Harvard"` | Affiliation |
| `citation_count:` | `citation_count:[100 TO *]` | Citation count range |

## Key Files

| File | Purpose |
|------|---------|
| `.mise.toml` | All available commands (`mise tasks` to list) |
| `features.json` | Feature tracking - find failing features to work on |
| `.env.example` | Environment variables template |

## How the System Works

A **fine-tuned Qwen3-1.7B model** ([adsabs/scix-nls-translator](https://huggingface.co/adsabs/scix-nls-translator)) converts natural language to ADS queries end-to-end. The model is served locally via an OpenAI-compatible endpoint and integrated into the [nectar](https://github.com/adsabs/nectar) frontend.

```
User NL query → Nectar (:8000) → Model Server (:8001) → ADS query
```

### Model

The translator is a **Qwen3-1.7B** base model fine-tuned with **LoRA** (r=16, alpha=32) using [Unsloth](https://github.com/unslothai/unsloth) + TRL on Google Colab (A100 GPU, ~90 minutes).

- **Model**: [adsabs/scix-nls-translator](https://huggingface.co/adsabs/scix-nls-translator) on HuggingFace
- **Input format**: `Query: <natural language>\nDate: <YYYY-MM-DD>`
- **Output format**: `{"query": "<ADS query>"}`
- **Training notebook**: `scripts/train_colab.ipynb`

### Training Dataset

**Dataset**: [adsabs/nls-query-training-data](https://huggingface.co/datasets/adsabs/nls-query-training-data) on HuggingFace

The training data (61,652 pairs — 55.4k train / 6.2k val) is assembled from three sources:

| Source | Description |
|--------|-------------|
| **NL pairs from query logs** | Real ADS queries from search logs, paired with natural language descriptions generated by Claude Sonnet 4. Validated to prevent query syntax leaking into NL text. |
| **Gold examples** | Hand-curated NL-to-query pairs covering diverse query patterns (topics, authors, operators, date ranges, compound queries). |
| **Synthetic pairs** | Programmatically generated from templates using seed lists of topics, astronomers, objects, journals, and institutions. Covers edge cases and common patterns. |

The combined dataset is validated, deduplicated by both NL text and query text, and split 90/10 into train/val sets with a fixed seed for reproducibility.

Each example uses standard chat completion format (system/user/assistant messages):

```jsonl
{"messages": [
  {"role": "system", "content": "Convert natural language to ADS search query. Output JSON: {\"query\": \"...\"}"},
  {"role": "user", "content": "Query: papers by Hawking on black holes from the 1970s\nDate: 2026-01-15"},
  {"role": "assistant", "content": "{\"query\": \"author:\\\"Hawking, S\\\" abs:\\\"black holes\\\" pubdate:[1970 TO 1979]\"}"}
]}
```

### Serving

The model server (`docker/server.py`) provides an OpenAI-compatible `/v1/chat/completions` endpoint. Nectar's `NL_SEARCH_VLLM_ENDPOINT` points to it.

```bash
# Start the model server (port 8001, auto-detects MPS/CUDA/CPU)
mise run dev-model

# In another terminal, start nectar
cd ~/ads-dev/nectar && pnpm dev
```

The model server loads from HuggingFace on first startup (~30s, cached after).

```bash
# Or run directly
MODEL_NAME=adsabs/scix-nls-translator PORT=8001 python docker/server.py

# Or with Docker (GPU)
docker run --gpus all -p 8001:8000 nls-server
```

Nectar `.env.local` configuration:
```bash
NEXT_PUBLIC_NL_SEARCH=enabled
NL_SEARCH_VLLM_ENDPOINT=http://localhost:8001/v1/chat/completions
```

See [docker/README.md](docker/README.md) for deployment options.

### Training a New Model

1. Open `scripts/train_colab.ipynb` in Google Colab
2. Select an A100 GPU runtime (Colab Pro)
3. Upload `data/datasets/processed/train.jsonl`
4. Run all cells (~90 minutes)
5. Model is uploaded to HuggingFace

See [docs/fine-tuning-cli.md](docs/fine-tuning-cli.md) for detailed training documentation.

## Tech Stack

- **Model**: Qwen3-1.7B + LoRA, trained via Unsloth/TRL on Google Colab
- **Serving**: FastAPI, OpenAI-compatible API, Docker
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend**: FastAPI, Pydantic, Python 3.12
- **Validation**: ADS Search API
- **Tools**: mise (runtimes), uv (Python), Bun (Node)

## Colab Notebooks

| Notebook | Purpose |
|----------|---------|
| [`scripts/train_colab.ipynb`](https://colab.research.google.com/github/sjarmak/nls-finetune-scix/blob/main/scripts/train_colab.ipynb) | Train / retrain the model (A100 GPU, ~90 min) |
| [`scripts/serve_colab.ipynb`](https://colab.research.google.com/github/sjarmak/nls-finetune-scix/blob/main/scripts/serve_colab.ipynb) | Serve the model for testing (free T4 GPU + ngrok) |

## Annotation & Review

### Web UI (Playground, Dataset Browser, Evaluation)

```bash
mise run dev   # starts API (:8000) + web (:5173)
```

- **Playground** — test queries against the model interactively
- **Dataset Browser** — browse training examples by category, view gold vs generated splits
- **Evaluation** — review model accuracy metrics, inspect pass/fail per test case

### NER Annotation Dashboard

A standalone HTML dashboard for reviewing and curating named entity annotations on scientific abstracts.

```bash
# Generate the dashboard
python scripts/generate_annotation_dashboard.py

# Open in browser
open data/evaluation/review_ner_annotations.html
```

Features: accept/reject entity spans, filter by domain/status, keyboard shortcuts, export to JSONL for training. See [docs/annotation-guide.md](docs/annotation-guide.md) for annotation guidelines.

### Exporting Annotations to Training Data

```bash
python scripts/export_annotations_to_training.py \
  --input ner_annotations_export.jsonl \
  --output-dir data/datasets/enrichment
```

## Documentation

- [Docker Deployment](docker/README.md) - Local and Docker deployment
- [Fine-Tuning & Training Guide](docs/fine-tuning-cli.md) - Model training and deployment
- [Annotation Guidelines](docs/annotation-guide.md) - How to annotate scientific abstracts
- [Hybrid Pipeline Architecture](docs/HYBRID_PIPELINE.md) - Deterministic NER pipeline (alternative to model)
- [ADS Search Syntax](https://ui.adsabs.harvard.edu/help/search/search-syntax) - Official ADS docs
