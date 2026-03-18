#!/usr/bin/env python3
"""Normalize year: syntax to canonical pubdate: syntax in gold_examples.json.

Rewrites:
  - year:YYYY         → pubdate:YYYY
  - year:YYYY-YYYY    → pubdate:[YYYY TO YYYY]
  - year:YYYY-        → pubdate:[YYYY TO *]
  - year:-YYYY        → pubdate:[* TO YYYY]

Does NOT modify year: inside quoted strings.

Usage:
    python scripts/normalize_year_syntax.py              # Dry run
    python scripts/normalize_year_syntax.py --apply      # Apply changes
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_FILE = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples.json"


def _normalize_year_in_query(query: str) -> str:
    """Replace year: syntax with pubdate: syntax, skipping quoted strings."""
    # Strategy: split the query into quoted and unquoted segments,
    # only apply replacements to unquoted segments.
    result = []
    i = 0
    while i < len(query):
        if query[i] == '"':
            # Find matching close quote
            j = query.index('"', i + 1) if '"' in query[i + 1:] else len(query)
            result.append(query[i:j + 1])
            i = j + 1
        else:
            # Find next quote or end
            j = query.find('"', i)
            if j == -1:
                j = len(query)
            segment = query[i:j]
            segment = _replace_year_patterns(segment)
            result.append(segment)
            i = j
    return "".join(result)


def _replace_year_patterns(segment: str) -> str:
    """Apply year: → pubdate: replacements in an unquoted segment."""
    # Order matters: match ranges before single years

    # year:YYYY-YYYY (range)
    segment = re.sub(
        r'\byear:(\d{4})-(\d{4})\b',
        r'pubdate:[\1 TO \2]',
        segment,
    )

    # year:YYYY- (open-ended upper) — dash followed by non-digit
    segment = re.sub(
        r'\byear:(\d{4})-(?!\d)',
        r'pubdate:[\1 TO *]',
        segment,
    )

    # year:-YYYY (open-ended lower)
    segment = re.sub(
        r'\byear:-(\d{4})\b',
        r'pubdate:[* TO \1]',
        segment,
    )

    # year:YYYY (single year) — must come after range patterns
    segment = re.sub(
        r'\byear:(\d{4})\b',
        r'pubdate:\1',
        segment,
    )

    return segment


def main():
    parser = argparse.ArgumentParser(description="Normalize year: → pubdate: in gold_examples.json")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default: dry run)")
    parser.add_argument("--verbose", action="store_true", help="Show all changes")
    args = parser.parse_args()

    with open(GOLD_FILE) as f:
        examples = json.load(f)

    stats = defaultdict(int)
    changes = []

    for i, ex in enumerate(examples):
        query = ex.get("ads_query", "")
        new_query = _normalize_year_in_query(query)

        if new_query != query:
            # Classify the change
            if re.search(r'\byear:\d{4}-\d{4}\b', query):
                stats["year:YYYY-YYYY → pubdate:[YYYY TO YYYY]"] += 1
            elif re.search(r'\byear:\d{4}-(?!\d)', query):
                stats["year:YYYY- → pubdate:[YYYY TO *]"] += 1
            elif re.search(r'\byear:-\d{4}\b', query):
                stats["year:-YYYY → pubdate:[* TO YYYY]"] += 1
            elif re.search(r'\byear:\d{4}\b', query):
                stats["year:YYYY → pubdate:YYYY"] += 1

            changes.append({
                "index": i,
                "nl": ex.get("natural_language", ""),
                "before": query,
                "after": new_query,
            })

            if args.apply:
                ex["ads_query"] = new_query

    # Print summary
    mode = "APPLYING" if args.apply else "DRY RUN"
    print(f"\n=== {mode} ===\n")
    print(f"Total examples: {len(examples)}")
    print(f"Examples changed: {len(changes)}")
    print()

    if stats:
        print("Pattern breakdown:")
        for pattern, count in sorted(stats.items()):
            print(f"  {pattern}: {count}")
        print()

    # Show changes
    for c in changes:
        print(f"  [{c['index']}] {c['nl'][:60]}...")
        print(f"    BEFORE: {c['before']}")
        print(f"    AFTER:  {c['after']}")
        print()

    if args.apply and changes:
        with open(GOLD_FILE, "w") as f:
            json.dump(examples, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Wrote {len(changes)} changes to {GOLD_FILE}")
    elif not args.apply and changes:
        print(f"Re-run with --apply to write {len(changes)} changes.")


if __name__ == "__main__":
    main()
