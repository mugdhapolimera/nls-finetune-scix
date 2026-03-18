#!/usr/bin/env python3
"""Demo script: Walk through all improvements made this week.

Run this script to see side-by-side comparisons of the different
pipeline modes and architecture improvements. No GPU or model required —
uses the NER pipeline and offline modules only.

Usage:
    python scripts/demo_improvements.py              # Full demo
    python scripts/demo_improvements.py --section 3  # Just section 3
    python scripts/demo_improvements.py --list        # List sections

Sections:
    1. Training Data Quality (cleanup + coverage)
    2. Intent-Level Merge Architecture (Phase A)
    3. Phase B: IntentSpec JSON Training Format
    4. Runtime Augmentation (UAT, planetary features, inst, bibstem, author wildcards)
    5. Phase C: RAG-Augmented LLM Path
    6. Benchmark Evaluation & Comparison
    7. Building Datasets for Retraining

Team decision points are flagged with [DECISION] markers.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "packages" / "finetune" / "src"))

# ============================================================================
# Utility helpers
# ============================================================================

def banner(title: str, section: int):
    width = 72
    print()
    print("=" * width)
    print(f"  SECTION {section}: {title}")
    print("=" * width)
    print()


def sub_banner(title: str):
    print(f"\n--- {title} ---\n")


def show_comparison(label_a: str, val_a: str, label_b: str, val_b: str):
    print(f"  {label_a:20s}: {val_a}")
    print(f"  {label_b:20s}: {val_b}")
    print()


def show_example(nl: str, result: str, label: str = "Result"):
    print(f"  NL:     {nl}")
    print(f"  {label:6s}: {result}")
    print()


def decision(text: str):
    print(f"  [DECISION] {text}")
    print()


def pause():
    input("  Press Enter to continue...")
    print()


# ============================================================================
# Section 1: Training Data Quality
# ============================================================================

def section_1():
    banner("Training Data Quality Improvements", 1)

    gold_path = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples.json"
    with open(gold_path) as f:
        gold = json.load(f)

    print(f"  Current gold examples: {len(gold)}")

    # Category distribution
    from collections import Counter
    cats = Counter(ex.get("category", "unknown") for ex in gold)
    print(f"  Categories: {len(cats)}")
    print()
    print("  Top 10 categories:")
    for cat, count in cats.most_common(10):
        print(f"    {cat:25s} {count:5d}")

    sub_banner("Data Cleanup Summary")
    print("  Round 1 (Mar 4): Removed 116 non-academic entries, fixed 30+ queries")
    print("  Round 2 (Mar 4): Standardized collection:→database:, fixed broken queries")
    print("  Realism cleanup (Mar 5): Removed 118 broken/duplicate, rewrote 205 NL strings")
    print("  Synonym cleanup (Mar 17): Removed 24 bad synonym-expansion examples")
    print()
    print("  Net result: Went from ~5,200 noisy examples → 4,924 clean examples")
    print("  Every example validated for syntax correctness and API result count")

    sub_banner("Coverage Gap Fills")
    print("  Mar 4: +210 examples (esources, data archives, NOT/negation, has:, grant,")
    print("         ack, keyword, arxiv_class, orcid, entry_date, object, similar, refs)")
    print("  Mar 5: +112 examples (reference parsing, UAT, planetary_feature, caption,")
    print("         arxiv IDs, count filters, date diversity, software mentions)")
    print()
    print("  Key: previously zero/near-zero coverage for esources, data archives,")
    print("  has: field, entry_date, caption — all now have 5-43 examples each")

    decision("Are there categories we should add more examples for?")
    print("  Remaining gaps: 7/24 data archives uncovered, ~14/34 has: values,")
    print("  lang/page/issue fields, simbad/vizier as standalone fields")


# ============================================================================
# Section 2: Intent-Level Merge Architecture
# ============================================================================

def section_2():
    banner("Intent-Level Merge Architecture (Phase A)", 2)

    print("  BEFORE: String-level merge (fragile heuristics)")
    print("  ─────────────────────────────────────────────────")
    print("  NER → query string ──┐")
    print("                       ├─→ string merge (dedup, regex, heuristics) → final query")
    print("  LLM → query string ──┘")
    print()
    print("  Problems: ~300 lines of regex heuristics for dedup, normalization,")
    print("  field injection, abs-clause cleanup. Every LLM artifact needed a new fix.")
    print()
    print("  AFTER: Intent-level merge (structural)")
    print("  ─────────────────────────────────────────────────")
    print("  NER → IntentSpec ──────────────┐")
    print("                                 ├─→ merge_intents() → assembler → query")
    print("  LLM → query → parse_query() ──┘")
    print()
    print("  Benefits: Assembler always produces valid syntax. Per-field merge policies.")
    print("  Eliminated ~300 lines of string heuristics.")

    sub_banner("Live Demo: NER Pipeline → IntentSpec → Assembly")

    from finetune.domains.scix.pipeline import process_query
    from finetune.domains.scix.intent_spec import IntentSpec

    test_queries = [
        "papers by Hawking on black holes from the 1970s",
        "highly cited dark matter reviews in MNRAS",
        "papers citing the LIGO detection excluding preprints",
        "recent JWST exoplanet atmosphere observations from STScI",
    ]

    for nl in test_queries:
        t0 = time.time()
        result = process_query(nl)
        elapsed = (time.time() - t0) * 1000
        print(f"  NL:     {nl}")
        print(f"  Query:  {result.final_query}")
        print(f"  Intent: {result.intent}")
        print(f"  Time:   {elapsed:.1f}ms")
        print()

    sub_banner("Per-Field Merge Policies")
    print("  ┌──────────────────────┬──────────────┬────────────────────────────────┐")
    print("  │ Field                │ Preferred    │ Rationale                      │")
    print("  ├──────────────────────┼──────────────┼────────────────────────────────┤")
    print("  │ authors              │ NER          │ Better name formatting         │")
    print("  │ free_text_terms      │ LLM          │ Understands context            │")
    print("  │ year_from/year_to    │ NER          │ Validated against patterns     │")
    print("  │ affiliations         │ NER          │ Validated against inst list    │")
    print("  │ bibstems             │ NER          │ Validated against bibstem list │")
    print("  │ operator             │ LLM          │ Handles nested/complex ops     │")
    print("  │ negation/has/metrics │ LLM only     │ NER can't detect these         │")
    print("  │ doctype/property     │ Union        │ Strips doctype:article if      │")
    print("  │                      │              │ NL uses generic 'papers'       │")
    print("  └──────────────────────┴──────────────┴────────────────────────────────┘")

    decision("Should we adjust any merge policies based on production experience?")


# ============================================================================
# Section 3: Phase B — IntentSpec JSON Output
# ============================================================================

def section_3():
    banner("Phase B: IntentSpec JSON Training Format", 3)

    print("  BEFORE: LLM outputs raw ADS query string")
    print("    Input:  'papers by Hawking on black holes'")
    print('    Output: {"query": "author:\\"Hawking, S\\" abs:\\"black holes\\""}')
    print("    → must reverse-engineer via parse_query_to_intent() → IntentSpec")
    print()
    print("  AFTER: LLM outputs compact IntentSpec JSON directly")
    print("    Input:  'papers by Hawking on black holes'")
    print("    Output: <think>")
    print('            Author: Hawking → "Hawking, S". Topic: black holes.')
    print("            </think>")
    print('            {"authors": ["Hawking, S"], "free_text_terms": ["black holes"]}')
    print("    → direct merge, no parsing needed")
    print()
    print("  Server auto-detects format — supports both old and new models")

    sub_banner("Training Data Conversion Stats")

    intent_path = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples_intent.json"
    with open(intent_path) as f:
        intent_data = json.load(f)

    total = len(intent_data)
    with_intent = sum(1 for ex in intent_data if ex.get("intent_json"))
    with_think = sum(1 for ex in intent_data if ex.get("think_trace"))

    print(f"  Total examples:         {total}")
    print(f"  With intent_json:       {with_intent} ({100*with_intent/total:.1f}%)")
    print(f"  With think_trace:       {with_think} ({100*with_think/total:.1f}%)")

    sub_banner("Sample Intent-Format Example")

    # Show a compound example
    for ex in intent_data:
        if ex.get("category") == "compound" and len(ex.get("intent_json", {}).get("authors", [])) > 0:
            print(f"  NL:          {ex['natural_language']}")
            print(f"  ADS query:   {ex['ads_query']}")
            print(f"  Intent JSON: {json.dumps(ex['intent_json'], indent=2)}")
            print(f"  Think trace: {ex.get('think_trace', '')[:120]}...")
            break
    print()

    sub_banner("How to Build Training Data")
    print("  # Old format (raw query strings):")
    print("  python scripts/build_dataset.py --format query")
    print()
    print("  # New format (IntentSpec JSON with <think> blocks):")
    print("  python scripts/build_dataset.py --format intent")
    print()

    decision("Do we retrain with --format intent next? This is the recommended path.")
    decision("The model needs to be retrained to use Phase B format.")


# ============================================================================
# Section 4: Runtime Augmentation Modules
# ============================================================================

def section_4():
    banner("Runtime Augmentation (No Retraining Needed)", 4)

    print("  These modules run at serving time in server.py, transparently")
    print("  augmenting queries regardless of which model version is deployed.")
    print()

    sub_banner("4a. UAT (Unified Astronomy Thesaurus) Augmentation")
    print("  Module: uat_lookup.py (4,144 terms from UAT v6.0)")
    print('  abs:"dark matter" → (abs:"dark matter" OR uat:"Dark matter")')
    print()

    from finetune.domains.scix.uat_lookup import rewrite_abs_to_abs_or_uat, lookup_uat

    test_terms = ["dark matter", "exoplanets", "gravitational waves", "galaxy formation"]
    for term in test_terms:
        result = lookup_uat(term)
        if result:
            print(f'  "{term}" → uat:"{result}"')
        else:
            print(f'  "{term}" → no UAT match')

    print()
    query = 'abs:"dark matter" abs:"galaxy clusters"'
    rewritten = rewrite_abs_to_abs_or_uat(query)
    print(f"  Before: {query}")
    print(f"  After:  {rewritten}")

    sub_banner("4b. Planetary Feature Augmentation")
    print("  Module: planetary_feature_lookup.py (8,915 terms from USGS Gazetteer)")
    print('  abs:"Olympus Mons" → (abs:"Olympus Mons" OR planetary_feature:"Olympus Mons")')
    print()

    from finetune.domains.scix.planetary_feature_lookup import (
        lookup_planetary_feature,
        rewrite_abs_to_abs_or_planetary_feature,
    )

    pf_terms = ["Olympus Mons", "Valles Marineris", "Jezero", "Gale Crater"]
    for term in pf_terms:
        result = lookup_planetary_feature(term)
        if result:
            print(f'  "{term}" → planetary_feature:"{result}"')
        else:
            print(f'  "{term}" → no match')

    sub_banner("4c. Institution Expansion")
    print("  Module: institution_lookup.py (~56 institutions, ~170 synonyms)")
    print('  aff:"MIT" → (inst:"MIT" OR aff:"MIT")')
    print()

    from finetune.domains.scix.institution_lookup import rewrite_aff_to_inst_or_aff

    inst_examples = [
        'aff:"MIT"',
        'aff:"NASA"',
        'aff:"Max Planck"',
        'aff:"Unknown Lab"',
    ]
    for q in inst_examples:
        rewritten = rewrite_aff_to_inst_or_aff(q)
        print(f"  {q:25s} → {rewritten}")

    sub_banner("4d. Bibstem Normalization")
    print("  Module: bibstem_lookup.py (~70 journal mappings)")
    print('  bibstem:Nature → bibstem:"Natur"')
    print()

    from finetune.domains.scix.bibstem_lookup import rewrite_bibstem_values

    bib_examples = [
        'abs:"dark matter" bibstem:Nature',
        'abs:"exoplanets" bibstem:"Astrophysical Journal"',
        'abs:"cosmology" bibstem:MNRAS',
    ]
    for q in bib_examples:
        rewritten = rewrite_bibstem_values(q)
        print(f"  {q}")
        print(f"    → {rewritten}")
        print()

    sub_banner("4e. Complex Author Name Wildcarding")
    print("  Module: assembler.py → rewrite_complex_author_wildcards()")
    print('  author:"de Groot-Hedlin" → author:"de Groot*"')
    print()

    from finetune.domains.scix.assembler import rewrite_complex_author_wildcards

    author_examples = [
        'author:"de Groot-Hedlin"',
        'author:"Le Floc\'h"',
        'author:"El-Badry"',
        'author:"Garcia-Perez"',
        'author:"Hawking, S"',
    ]
    for q in author_examples:
        rewritten = rewrite_complex_author_wildcards(q)
        changed = " (unchanged)" if rewritten == q else ""
        print(f"  {q:35s} → {rewritten}{changed}")

    print()
    decision("All 5 runtime augmentations are live. Any concerns about behavior?")
    decision("These run on EVERY query — are there edge cases we should test?")


# ============================================================================
# Section 5: Phase C — RAG-Augmented LLM
# ============================================================================

def section_5():
    banner("Phase C: RAG-Augmented LLM Path", 5)

    print("  Architecture:")
    print("  NL text → NER ──────────────────→ IntentSpec_NER ──┐")
    print("         │                                            ├→ merge → assembler → query")
    print("         └→ [RAG: few-shot + cards]                   │")
    print("              ↓                                       │")
    print("            LLM (with context) ──→ IntentSpec_LLM ───┘")
    print()
    print("  RAG retrieval (<20ms) runs in parallel with NER.")
    print("  Injects 2-3 similar examples + 1-2 field cards into LLM prompt.")
    print("  No new dependencies — reuses existing BM25 index.")
    print()

    sub_banner("5a. Few-Shot Retrieval Demo")

    import os
    os.environ.setdefault("GOLD_EXAMPLES_PATH",
        str(PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples.json"))
    os.environ.setdefault("GOLD_EXAMPLES_INTENT_PATH",
        str(PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples_intent.json"))

    from finetune.domains.scix.rag_retrieval import retrieve_few_shot

    test_queries = [
        "recent papers on dark matter in MNRAS",
        "PhD theses about galaxy evolution",
        "papers citing the LIGO discovery excluding preprints",
        "highly cited exoplanet atmospheres from last 5 years",
        "JWST proposals for stellar nurseries",
    ]

    for nl in test_queries:
        t0 = time.time()
        examples = retrieve_few_shot(nl, k=3)
        elapsed = (time.time() - t0) * 1000
        print(f"  Query: {nl}")
        print(f"  Retrieved {len(examples)} examples in {elapsed:.1f}ms:")
        for ex in examples:
            print(f"    • \"{ex['nl'][:60]}...\"")
            print(f"      → {json.dumps(ex['intent_json'])[:80]}...")
        print()

    sub_banner("5b. Field Reference Cards Demo")

    from finetune.domains.scix.field_cards import select_cards, CARDS

    print(f"  Total cards available: {len(CARDS)}")
    print(f"  Cards: {', '.join(sorted(CARDS.keys()))}")
    print()

    card_queries = [
        "PhD thesis on galaxy formation",
        "highly cited open access papers",
        "papers excluding preprints from MAST",
        "recent gravitational wave papers this week",
    ]

    for nl in card_queries:
        cards = select_cards(nl, max_cards=2)
        print(f"  Query: {nl}")
        for c in cards:
            print(f"    Card: {c[:80]}...")
        if not cards:
            print("    (no matching cards)")
        print()

    sub_banner("5c. Augmented Prompt Format")
    print("  The LLM prompt becomes:")
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │ System: Convert NL to intent JSON...            │")
    print("  │   + Reference: [field cards if relevant]        │")
    print("  │                                                 │")
    print("  │ User: Query: [similar example 1]                │")
    print("  │ Asst: <think>...</think> {intent_json_1}        │")
    print("  │                                                 │")
    print("  │ User: Query: [similar example 2]                │")
    print("  │ Asst: <think>...</think> {intent_json_2}        │")
    print("  │                                                 │")
    print("  │ User: Query: [actual user query]  ← generate →  │")
    print("  └─────────────────────────────────────────────────┘")
    print()
    print("  Token budget: ~420 tokens total (system ~150 + 3×80 few-shot + 30 query)")
    print("  Qwen3-1.7B has 32K context — well within limits")
    print("  Latency: ~50ms extra generation time for expanded prompt")

    print()
    decision("Should we deploy Phase C (RAG) with current model first (no retraining)?")
    decision("Or wait and retrain with RAG format first (Phase 3)?")
    print("  Option A: Deploy now → immediate improvement, no GPU needed")
    print("  Option B: Retrain first → model learns to leverage few-shot context")
    print("  Option C: Both → deploy now, retrain later for further improvement")


# ============================================================================
# Section 6: Benchmark & Comparison
# ============================================================================

def section_6():
    banner("Benchmark Evaluation & Comparison", 6)

    sub_banner("Current NER-only Baseline (301 benchmark queries)")
    results_path = PROJECT_ROOT / "data" / "datasets" / "evaluations" / "benchmark_results.json"
    if results_path.exists():
        with open(results_path) as f:
            results = json.load(f)
        stats = results["overall_stats"]
        print(f"  Pass rate:       {stats['pass_rate']:.1f}% ({stats['passed_tests']}/{stats['total_tests']})")
        print(f"  Exact match:     {stats['exact_match_rate']:.1f}% ({stats['exact_match_count']}/{stats['total_tests']})")
        print(f"  Syntax valid:    {stats['syntax_valid_rate']:.1f}%")
        print(f"  Constraint valid: {stats['constraint_valid_rate']:.1f}%")
        print()

        print("  Category breakdown:")
        for cat, cat_stats in results.get("category_stats", {}).items():
            print(f"    {cat:20s}  pass={cat_stats['pass_rate']:5.1f}%  exact={cat_stats['exact_match_rate']:5.1f}%  (n={cat_stats['total']})")
    else:
        print("  No benchmark results found. Run:")
        print("  python scripts/evaluate_benchmark.py")

    sub_banner("How to Run Comparisons")
    print("  # 1. NER-only baseline (no model needed)")
    print("  python scripts/evaluate_benchmark.py \\")
    print("      --output data/datasets/evaluations/baseline_ner.json")
    print()
    print("  # 2. Hybrid NER+LLM (needs running server with model)")
    print("  #    Start server first:")
    print("  #    MODEL_NAME=adsabs/NLQT-Qwen3-1.7B python docker/server.py")
    print("  #    Then benchmark against it")
    print()
    print("  # 3. After retraining with intent format:")
    print("  python scripts/build_dataset.py --format intent \\")
    print("      --output-dir data/datasets/processed")
    print("  #    Train model, then benchmark")
    print()
    print("  # 4. After retraining with RAG-augmented format:")
    print("  python scripts/build_rag_dataset.py --k 3 \\")
    print("      --output data/datasets/processed/train_rag.jsonl")
    print("  #    Train model, then benchmark")

    sub_banner("Expected Improvement Trajectory")
    print("  ┌───────────────────────────────────┬───────────┬──────────────┐")
    print("  │ Configuration                     │ Pass Rate │ Exact Match  │")
    print("  ├───────────────────────────────────┼───────────┼──────────────┤")
    print("  │ NER-only baseline (Jan 23)        │ 98.7%     │ 11.6%        │")
    print("  │ Hybrid NER+LLM (current model)    │ ~98-99%   │ ~15-20%?     │")
    print("  │ + Phase C RAG (no retrain)         │ ~99%      │ ~20-25%?     │")
    print("  │ + Intent format retrain             │ ~99%      │ ~25-35%?     │")
    print("  │ + RAG-augmented retrain             │ ~99%      │ ~30-40%?     │")
    print("  └───────────────────────────────────┴───────────┴──────────────┘")
    print("  Note: Exact match % estimates. Need to measure with model running.")
    print()

    decision("Which configurations should we benchmark with the model?")
    decision("Do we need additional benchmark queries for new capabilities?")
    print("  Current benchmark (301 queries) was created Jan 22 — predates:")
    print("  - UAT augmentation, planetary features, coverage gap fills,")
    print("  - intent format, RAG augmentation")


# ============================================================================
# Section 7: Building Datasets for Retraining
# ============================================================================

def section_7():
    banner("Building Datasets for Retraining", 7)

    sub_banner("Available Training Formats")
    print("  1. Original (query string output):")
    print('     System: Convert NL to query. Output JSON: {"query": "..."}')
    print('     User:   Query: papers by Hawking on black holes')
    print('     Asst:   {"query": "author:\\"Hawking, S\\" abs:\\"black holes\\""}')
    print()
    print("  2. Intent format (Phase B):")
    print("     System: Convert NL to structured search intent...")
    print("     User:   Query: papers by Hawking on black holes")
    print("     Asst:   <think>Author: Hawking → \"Hawking, S\"...</think>")
    print('             {"authors": ["Hawking, S"], "free_text_terms": ["black holes"]}')
    print()
    print("  3. RAG-augmented intent format (Phase C):")
    print("     System: Convert NL to structured search intent... + [field cards]")
    print("     User:   Query: [similar example 1]")
    print("     Asst:   <think>...</think> {intent_json_1}")
    print("     User:   Query: [similar example 2]")
    print("     Asst:   <think>...</think> {intent_json_2}")
    print("     User:   Query: papers by Hawking on black holes")
    print("     Asst:   <think>Author: Hawking → \"Hawking, S\"...</think>")
    print('             {"authors": ["Hawking, S"], "free_text_terms": ["black holes"]}')

    sub_banner("Build Commands")
    print("  # Format 1: Original (baseline)")
    print("  python scripts/build_dataset.py --format query \\")
    print("      --output-dir data/datasets/processed")
    print()
    print("  # Format 2: Intent (recommended next step)")
    print("  python scripts/build_dataset.py --format intent \\")
    print("      --output-dir data/datasets/processed")
    print()
    print("  # Format 3: RAG-augmented intent")
    print("  python scripts/build_rag_dataset.py --k 3 \\")
    print("      --output data/datasets/processed/train_rag.jsonl")

    sub_banner("Dataset Sizes")

    gold_path = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples.json"
    intent_path = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples_intent.json"
    train_path = PROJECT_ROOT / "data" / "datasets" / "processed" / "train.jsonl"
    val_path = PROJECT_ROOT / "data" / "datasets" / "processed" / "val.jsonl"

    print(f"  Gold examples:     {_count_json(gold_path)} pairs")
    print(f"  Intent examples:   {_count_json(intent_path)} pairs")
    print(f"  Current train set: {_count_lines(train_path)} examples")
    print(f"  Current val set:   {_count_lines(val_path)} examples")
    print()

    # Estimate RAG dataset size
    print("  RAG-augmented dataset (estimate):")
    print("    ~4,924 examples × 8.8 messages avg = ~43K messages total")
    print("    ~3× more tokens per example (few-shot context)")
    print("    Training time estimate: ~2-3× longer than current")

    print()
    decision("Which format should we retrain with first?")
    decision("Training priority: Format 2 (intent) is the minimal useful upgrade.")
    decision("Format 3 (RAG) gives the biggest improvement but costs more GPU time.")


def _count_json(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path) as f:
        return len(json.load(f))


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path) as f:
        return sum(1 for _ in f)


# ============================================================================
# Summary
# ============================================================================

def summary():
    width = 72
    print()
    print("=" * width)
    print("  SUMMARY: What's New This Week")
    print("=" * width)
    print()
    print("  Shipped (no retraining needed):")
    print("  ✓ Training data: 4,924 clean, validated examples (was ~5,200 noisy)")
    print("  ✓ Intent-level merge: structural merge replaces ~300 lines of regex")
    print("  ✓ Runtime augmentation: UAT, planetary features, inst, bibstem, authors")
    print("  ✓ Phase B: server auto-detects IntentSpec JSON from LLM")
    print("  ✓ Phase C: RAG few-shot retrieval + field cards in LLM prompt")
    print()
    print("  Ready for retraining:")
    print("  → Intent format training data (gold_examples_intent.json)")
    print("  → RAG-augmented training data (build_rag_dataset.py)")
    print("  → Dataset builder: build_dataset.py --format intent")
    print()
    print("  Key decisions needed:")
    print("  1. Retrain with intent format? (recommended, ~3 hours GPU)")
    print("  2. Deploy RAG with current model or wait for retrain?")
    print("  3. Update benchmark queries for new capabilities?")
    print("  4. Adjust merge policies based on production experience?")
    print("  5. Fill remaining coverage gaps (data archives, has: values)?")
    print()
    print("  Environment variables for deployment:")
    print("    HYBRID_MODE=true      (NER + LLM in parallel)")
    print("    RAG_ENABLED=true      (few-shot RAG on LLM path)")
    print("    RAG_NUM_EXAMPLES=3    (number of few-shot examples)")
    print("    RAG_MAX_CARDS=2       (max field reference cards)")
    print()


# ============================================================================
# Main
# ============================================================================

SECTIONS = {
    1: ("Training Data Quality", section_1),
    2: ("Intent-Level Merge Architecture", section_2),
    3: ("Phase B: IntentSpec JSON Format", section_3),
    4: ("Runtime Augmentation Modules", section_4),
    5: ("Phase C: RAG-Augmented LLM", section_5),
    6: ("Benchmark & Comparison", section_6),
    7: ("Building Datasets for Retraining", section_7),
}


def main():
    parser = argparse.ArgumentParser(description="Demo all improvements from this week")
    parser.add_argument("--section", type=int, help="Run specific section (1-7)")
    parser.add_argument("--list", action="store_true", help="List available sections")
    parser.add_argument("--no-pause", action="store_true", help="Don't pause between sections")
    args = parser.parse_args()

    if args.list:
        print("Available sections:")
        for num, (title, _) in SECTIONS.items():
            print(f"  {num}. {title}")
        return

    if args.section:
        if args.section not in SECTIONS:
            print(f"Invalid section {args.section}. Use --list to see options.")
            return
        _, func = SECTIONS[args.section]
        func()
        return

    # Run all sections
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║          NLS Fine-Tune SciX — Weekly Improvements Demo             ║")
    print("║                   Week of March 10-17, 2026                        ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    for num, (_, func) in SECTIONS.items():
        func()
        if not args.no_pause and num < len(SECTIONS):
            pause()

    summary()


if __name__ == "__main__":
    main()
