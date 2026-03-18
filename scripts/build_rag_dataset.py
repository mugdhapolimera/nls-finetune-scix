#!/usr/bin/env python3
"""Build RAG-augmented training dataset.

For each training example, retrieves k nearest-neighbor examples (excluding self)
and includes them as few-shot user/assistant pairs in the training JSONL.
This teaches the model to actively leverage provided examples at inference time.

Usage:
    python scripts/build_rag_dataset.py [--k 3] [--output data/datasets/processed/train_rag.jsonl]

Input:
    data/datasets/raw/gold_examples_intent.json  (intent-format examples)

Output:
    JSONL with chat messages: system + k few-shot pairs + user/assistant for actual example.
"""

import argparse
import json
import sys
from pathlib import Path

# Add finetune package to path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "packages" / "finetune" / "src"))

from finetune.domains.scix.prompts import SYSTEM_PROMPT_INTENT
from finetune.domains.scix.retrieval import GoldExampleIndex, tokenize
from finetune.domains.scix.intent_spec import IntentSpec


def load_intent_examples(path: Path) -> list[dict]:
    """Load intent-format gold examples."""
    with open(path) as f:
        return json.load(f)


def build_nl_to_intent_map(examples: list[dict]) -> dict[str, dict]:
    """Build NL → intent example lookup."""
    return {ex["natural_language"]: ex for ex in examples if ex.get("intent_json")}


def retrieve_neighbors(
    nl_text: str,
    index: GoldExampleIndex,
    intent_map: dict[str, dict],
    k: int = 3,
) -> list[dict]:
    """Retrieve k nearest neighbors, excluding exact NL match."""
    # Create lightweight intent for scoring
    tokens = tokenize(nl_text)
    intent = IntentSpec(free_text_terms=[" ".join(sorted(tokens))] if tokens else [])

    candidates = index.retrieve(intent, k=k * 3)

    results = []
    nl_lower = nl_text.strip().lower()
    for ex in candidates:
        if ex.nl_query.strip().lower() == nl_lower:
            continue
        if ex.nl_query in intent_map:
            results.append(intent_map[ex.nl_query])
            if len(results) >= k:
                break

    return results


def build_rag_training_example(
    example: dict,
    neighbors: list[dict],
    system_prompt: str,
) -> dict:
    """Build a single RAG-augmented training example in chat format.

    Args:
        example: The target example with intent_json and think_trace.
        neighbors: Similar examples to use as few-shot context.
        system_prompt: System prompt text.

    Returns:
        {"messages": [...]} in chat JSONL format.
    """
    messages = [{"role": "system", "content": system_prompt}]

    # Add few-shot neighbor examples
    for n in neighbors:
        messages.append({
            "role": "user",
            "content": f"Query: {n['natural_language']}\nDate: 2025-12-15",
        })
        think_block = ""
        if n.get("think_trace"):
            think_block = f"<think>\n{n['think_trace']}\n</think>\n"
        messages.append({
            "role": "assistant",
            "content": think_block + json.dumps(n["intent_json"], ensure_ascii=False),
        })

    # Add the actual target example
    messages.append({
        "role": "user",
        "content": f"Query: {example['natural_language']}\nDate: 2025-12-15",
    })
    think_block = ""
    if example.get("think_trace"):
        think_block = f"<think>\n{example['think_trace']}\n</think>\n"
    messages.append({
        "role": "assistant",
        "content": think_block + json.dumps(example["intent_json"], ensure_ascii=False),
    })

    return {"messages": messages}


def main():
    parser = argparse.ArgumentParser(description="Build RAG-augmented training dataset")
    parser.add_argument(
        "--input",
        type=Path,
        default=_project_root / "data" / "datasets" / "raw" / "gold_examples_intent.json",
        help="Path to intent-format gold examples",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_project_root / "data" / "datasets" / "processed" / "train_rag.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument("--k", type=int, default=3, help="Number of few-shot neighbors")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing")
    args = parser.parse_args()

    print(f"Loading intent examples from {args.input}...")
    examples = load_intent_examples(args.input)
    print(f"  {len(examples)} examples loaded")

    # Build retrieval index from the raw gold examples (NL + ADS query)
    gold_path = args.input.parent / "gold_examples.json"
    print(f"Building retrieval index from {gold_path}...")
    index = GoldExampleIndex(filepath=gold_path)
    print(f"  {index.num_examples} examples indexed")

    intent_map = build_nl_to_intent_map(examples)
    print(f"  {len(intent_map)} examples have intent_json")

    # Build RAG-augmented training examples
    rag_examples = []
    no_neighbors = 0

    for i, ex in enumerate(examples):
        if not ex.get("intent_json"):
            continue

        neighbors = retrieve_neighbors(
            ex["natural_language"], index, intent_map, k=args.k
        )

        if not neighbors:
            no_neighbors += 1

        rag_ex = build_rag_training_example(ex, neighbors, SYSTEM_PROMPT_INTENT)
        rag_examples.append(rag_ex)

        if (i + 1) % 1000 == 0:
            print(f"  Processed {i + 1}/{len(examples)}...")

    print(f"\nResults:")
    print(f"  Total RAG examples: {len(rag_examples)}")
    print(f"  Examples with 0 neighbors: {no_neighbors}")
    print(f"  Avg messages per example: {sum(len(e['messages']) for e in rag_examples) / max(len(rag_examples), 1):.1f}")

    if args.dry_run:
        # Show a sample
        if rag_examples:
            print(f"\nSample (first example):")
            print(json.dumps(rag_examples[0], indent=2, ensure_ascii=False)[:1000])
        return

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        for ex in rag_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nWritten to {args.output}")


if __name__ == "__main__":
    main()
