#!/usr/bin/env python3
"""Audit bibgroup training examples with date filters for 0-result queries.

Checks all gold_examples that combine bibgroup: with pubdate: against the
ADS API to identify examples that return zero results (likely historical
missions paired with recent dates by template generation).

Also flags ambiguous bibgroup names that could be confused with publishers,
people, or non-telescope entities.

Usage:
    python scripts/audit_bibgroup_dates.py           # dry-run (API check)
    python scripts/audit_bibgroup_dates.py --fix     # remove 0-result examples
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# ADS API
# ---------------------------------------------------------------------------

try:
    import requests
except ImportError:
    print("ERROR: requests library required. pip install requests")
    sys.exit(1)

ADS_API_TOKEN = os.environ.get("ADS_DEV_KEY") or os.environ.get("ADS_API_KEY")
ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"

if not ADS_API_TOKEN:
    # Try loading from .env file
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ADS_DEV_KEY=") or line.startswith("ADS_API_KEY="):
                ADS_API_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not ADS_API_TOKEN:
    print("ERROR: Set ADS_DEV_KEY or ADS_API_KEY environment variable")
    sys.exit(1)


def query_ads(query: str, timeout: int = 30) -> int | None:
    """Query ADS API and return number of results, or None on error."""
    headers = {"Authorization": f"Bearer {ADS_API_TOKEN}"}
    params = {"q": query, "rows": 0, "fl": "bibcode"}
    try:
        resp = requests.get(ADS_API_URL, headers=headers, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json().get("response", {}).get("numFound", 0)
        elif resp.status_code == 429:
            print(f"  Rate limited, waiting 10s...")
            time.sleep(10)
            return query_ads(query, timeout)
        else:
            print(f"  API error {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.exceptions.Timeout:
        print(f"  Timeout for: {query[:80]}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


# ---------------------------------------------------------------------------
# Ambiguity detection
# ---------------------------------------------------------------------------

# Bibgroups that are also commonly used as non-telescope references
AMBIGUOUS_BIBGROUPS = {
    "Copernicus": [
        "Copernicus Publications (publisher)",
        "EU Copernicus Programme (Earth observation)",
        "Nicolaus Copernicus (astronomer)",
    ],
    "Einstein": [
        "Albert Einstein (physicist)",
        "Einstein Observatory (HEAO-2, 1978-1981)",
    ],
    "Gemini": [
        "Gemini Observatory (telescope) — valid, active",
        "Gemini (NASA space program)",
        "Gemini (zodiac constellation)",
    ],
    "Fermi": [
        "Enrico Fermi (physicist)",
        "Fermi Gamma-ray Space Telescope — valid, active",
    ],
    "Gaia": [
        "Gaia spacecraft — valid, active",
        "Gaia hypothesis (ecology)",
    ],
    "Kepler": [
        "Kepler space telescope — valid (ended 2018)",
        "Johannes Kepler (astronomer)",
    ],
}

# Historical missions — no new papers expected after these dates
HISTORICAL_MISSIONS = {
    "Copernicus": {"operated": "1972-1981", "last_paper_expected": 2005},
    "IUE": {"operated": "1978-1996", "last_paper_expected": 2015},
    "EUVE": {"operated": "1992-2001", "last_paper_expected": 2015},
    "IRAS": {"operated": "1983", "last_paper_expected": 2020},
    "ROSAT": {"operated": "1990-1999", "last_paper_expected": 2015},
    "Einstein": {"operated": "1978-1981", "last_paper_expected": 2005},
    "Hipparcos": {"operated": "1989-1993", "last_paper_expected": 2020},
    "FUSE": {"operated": "1999-2007", "last_paper_expected": 2025},
    "K2": {"operated": "2014-2018", "last_paper_expected": 2030},
    "Spitzer": {"operated": "2003-2020", "last_paper_expected": 2030},
    "ARECIBO": {"operated": "1963-2020", "last_paper_expected": 2030},
    "NEOWISE": {"operated": "2013-2024", "last_paper_expected": 2030},
}


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Audit bibgroup+date training examples")
    parser.add_argument("--fix", action="store_true", help="Remove 0-result examples")
    parser.add_argument("--input", default="data/datasets/raw/gold_examples.json")
    parser.add_argument("--skip-api", action="store_true", help="Skip API checks, only report ambiguity")
    args = parser.parse_args()

    input_path = Path(args.input)
    with open(input_path) as f:
        examples = json.load(f)

    print(f"Loaded {len(examples)} examples from {input_path}")

    # Find all bibgroup examples
    bibgroup_re = re.compile(r'bibgroup[:\s]+"?([^"\s]+)"?')
    pubdate_re = re.compile(r'pubdate[:\s]*[\[\(]?(\d{4})')

    bibgroup_examples = []
    bibgroup_date_examples = []
    all_bibgroups = set()

    for i, ex in enumerate(examples):
        query = ex.get("ads_query", "")
        bg_match = bibgroup_re.search(query)
        if bg_match:
            bg_name = bg_match.group(1)
            all_bibgroups.add(bg_name)
            bibgroup_examples.append((i, ex, bg_name))

            pd_match = pubdate_re.search(query)
            if pd_match or "pubdate:" in query:
                bibgroup_date_examples.append((i, ex, bg_name))

    print(f"\nFound {len(bibgroup_examples)} bibgroup examples across {len(all_bibgroups)} bibgroups")
    print(f"Found {len(bibgroup_date_examples)} bibgroup+date examples to audit\n")

    # Report ambiguous bibgroups
    print("=" * 70)
    print("AMBIGUOUS BIBGROUP NAMES")
    print("=" * 70)
    for bg in sorted(all_bibgroups):
        if bg in AMBIGUOUS_BIBGROUPS:
            count = sum(1 for _, _, b in bibgroup_examples if b == bg)
            print(f"\n  {bg} ({count} examples) — could also mean:")
            for meaning in AMBIGUOUS_BIBGROUPS[bg]:
                print(f"    - {meaning}")

    # Report historical missions with date examples
    print("\n" + "=" * 70)
    print("HISTORICAL MISSIONS WITH DATE FILTERS")
    print("=" * 70)
    for idx, ex, bg in bibgroup_date_examples:
        if bg in HISTORICAL_MISSIONS:
            info = HISTORICAL_MISSIONS[bg]
            print(f"\n  [{idx}] {bg} (operated {info['operated']})")
            print(f"    NL:    {ex['natural_language'][:80]}")
            print(f"    Query: {ex['ads_query'][:80]}")

    if args.skip_api:
        print("\n(Skipped API checks)")
        return

    # API validation
    print("\n" + "=" * 70)
    print("API VALIDATION: bibgroup+date examples")
    print("=" * 70)

    zero_result_indices = []
    low_result_indices = []

    for idx, ex, bg in bibgroup_date_examples:
        query = ex["ads_query"]
        time.sleep(0.3)  # Rate limiting
        num_results = query_ads(query)

        nl = ex["natural_language"][:60]
        if num_results is None:
            status = "ERROR"
        elif num_results == 0:
            status = "ZERO RESULTS"
            zero_result_indices.append(idx)
        elif num_results < 5:
            status = f"LOW ({num_results})"
            low_result_indices.append(idx)
        else:
            status = f"OK ({num_results})"

        print(f"  [{idx:5d}] {status:20s} | {bg:15s} | {nl}")

    # Also check all bibgroup-only examples (no date) for total counts
    print("\n" + "=" * 70)
    print("BIBGROUP TOTAL PAPER COUNTS (no date filter)")
    print("=" * 70)

    checked_bgs = set()
    for bg in sorted(all_bibgroups):
        if bg in checked_bgs:
            continue
        checked_bgs.add(bg)
        time.sleep(0.3)

        # Quote bibgroup name if it contains special chars
        if " " in bg or "/" in bg:
            q = f'bibgroup:"{bg}"'
        else:
            q = f"bibgroup:{bg}"
        num = query_ads(q)
        count_examples = sum(1 for _, _, b in bibgroup_examples if b == bg)
        status = f"{num:>6}" if num is not None else " ERROR"
        flag = " ← SMALL CORPUS" if num is not None and num < 500 else ""
        print(f"  {bg:20s}: {status} papers, {count_examples} training examples{flag}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total bibgroup+date examples: {len(bibgroup_date_examples)}")
    print(f"  Zero results:                 {len(zero_result_indices)}")
    print(f"  Low results (<5):             {len(low_result_indices)}")
    print(f"  OK:                           {len(bibgroup_date_examples) - len(zero_result_indices) - len(low_result_indices)}")

    if zero_result_indices:
        print(f"\n  Zero-result example indices: {zero_result_indices}")
        print("  These should be removed or fixed.")

    if low_result_indices:
        print(f"\n  Low-result example indices: {low_result_indices}")
        print("  These may be too specific — consider broadening.")

    # Fix mode
    if args.fix and zero_result_indices:
        print(f"\n  Removing {len(zero_result_indices)} zero-result examples...")
        removed = []
        for idx in sorted(zero_result_indices, reverse=True):
            removed.append(examples.pop(idx))
        print(f"  Removed {len(removed)} examples. New total: {len(examples)}")

        # Archive removed
        archive_path = Path("data/reference/removed_bibgroup_date_examples.json")
        existing = []
        if archive_path.exists():
            with open(archive_path) as f:
                existing = json.load(f)
        existing.extend(removed)
        with open(archive_path, "w") as f:
            json.dump(existing, f, indent=2)
        print(f"  Archived to {archive_path}")

        # Save
        with open(input_path, "w") as f:
            json.dump(examples, f, indent=2, ensure_ascii=False)
        print(f"  Saved {len(examples)} examples to {input_path}")


if __name__ == "__main__":
    main()
