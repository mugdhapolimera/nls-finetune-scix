#!/usr/bin/env python3
"""Fix validation issues found in the 210 coverage-gap training examples.

Issues identified by scix-query-validator and validate_gold_examples.py:
1. CRITICAL: Nested operator references(... useful(...)) — not supported by ADS
2. MODERATE: collection: → database: inconsistency in new examples
3. MODERATE: NL/query mismatch for keyword "accretion disks"
4. MODERATE: grant:CSA abs:"space debris" returns 0 results

Usage:
    python scripts/fix_validation_issues.py

This script is idempotent — it matches by query content, so re-running is safe.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_FILE = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples.json"

with open(GOLD_FILE) as f:
    examples = json.load(f)

fixes = 0

for i, ex in enumerate(examples):
    q = ex.get("ads_query", "")

    # Fix 1: CRITICAL - Nested operator
    if 'references(abs:"dark energy" useful(abs:"dark energy"))' in q:
        ex["natural_language"] = "what papers are referenced by dark energy studies"
        ex["ads_query"] = 'references(abs:"dark energy")'
        fixes += 1
        print(f"Fixed {i}: nested operator")

    # Fix 2: collection: -> database: in new examples only (i >= 4637)
    if i >= 4637 and "collection:" in q:
        old = q
        ex["ads_query"] = q.replace("collection:", "database:")
        if old != ex["ads_query"]:
            fixes += 1
            print(f"Fixed {i}: collection: -> database:")

    # Fix 3: keyword accretion mismatch
    if q == 'keyword:"accretion" pubdate:[2015 TO 2026] doctype:article':
        ex["ads_query"] = 'keyword:"accretion disks" pubdate:[2015 TO 2026] doctype:article'
        fixes += 1
        print(f"Fixed {i}: keyword accretion -> accretion disks")

    # Fix 4: grant:CSA space debris
    if q == 'grant:CSA abs:"space debris"':
        ex["ads_query"] = 'grant:CSA abs:"satellite"'
        ex["natural_language"] = "CSA-funded research on satellites"
        fixes += 1
        print(f"Fixed {i}: grant:CSA topic")

with open(GOLD_FILE, "w") as f:
    json.dump(examples, f, indent=2)

print(f"\nTotal fixes applied: {fixes}")
print(f"Total examples: {len(examples)}")
