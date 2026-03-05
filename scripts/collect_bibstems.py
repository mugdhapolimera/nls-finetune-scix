#!/usr/bin/env python3
"""Collect journal bibstem data from the ADS Journals API.

Searches for top astronomy and physics journals, fetches metadata
(full name, abbreviations, ISSNs), and outputs bibstem_synonyms.json.

Requires ADS_API_KEY in environment or .env file.

Usage:
    python scripts/collect_bibstems.py
    python scripts/collect_bibstems.py --output data/model/bibstem_synonyms.json
    python scripts/collect_bibstems.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ADS Journals API base
ADS_JOURNALS_API = "https://api.adsabs.harvard.edu/v1/journals"

# Search terms to cover the major journals
SEARCH_TERMS = [
    "Astrophysical Journal",
    "Monthly Notices",
    "Astronomy Astrophysics",
    "Astronomical Journal",
    "Physical Review",
    "Nature Astronomy",
    "Solar Physics",
    "Icarus",
    "Geophysical Research",
    "Space Science Reviews",
    "Astrobiology",
    "Classical Quantum Gravity",
    "Nuclear Physics",
    "European Physical Journal",
    "Journal High Energy",
    "Journal Cosmology",
    "Living Reviews",
    "Planetary Science",
    "Experimental Astronomy",
    "New Astronomy",
    "Advances Space Research",
    "Annual Review",
    "Physics Reports",
    "Reviews Modern Physics",
    "SPIE",
    "IAU Symposium",
    "ASP Conference",
    "arXiv",
    "Bulletin American Astronomical",
    "Meteoritics",
    "Earth Planetary Science",
    "Applied Optics",
    "Celestial Mechanics",
]


def load_api_key() -> str:
    """Load ADS API key from environment or .env file."""
    key = os.environ.get("ADS_API_KEY")
    if key:
        return key

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("ADS_API_KEY=") and not line.endswith("="):
                val = line.split("=", 1)[1].strip().strip("'\"")
                if val:
                    return val

    print("ERROR: ADS_API_KEY not found in environment or .env file.", file=sys.stderr)
    print("Set it in .env or export ADS_API_KEY=your_key", file=sys.stderr)
    sys.exit(1)


def search_journals(api_key: str, term: str) -> list[dict]:
    """Search ADS Journals API for journals matching a term."""
    import urllib.request
    import urllib.error

    url = f"{ADS_JOURNALS_API}/journal/{urllib.parse.quote(term)}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data if isinstance(data, list) else data.get("results", [])
    except urllib.error.HTTPError as e:
        print(f"  API error for '{term}': {e.code} {e.reason}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  Error for '{term}': {e}", file=sys.stderr)
        return []


def get_journal_summary(api_key: str, bibstem: str) -> dict | None:
    """Get full metadata for a specific bibstem."""
    import urllib.request
    import urllib.error

    url = f"{ADS_JOURNALS_API}/summary/{urllib.parse.quote(bibstem)}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def build_synonyms(api_key: str, dry_run: bool = False) -> dict:
    """Build the bibstem synonyms mapping from the API."""
    import urllib.parse  # noqa: F811

    synonyms = {}

    for term in SEARCH_TERMS:
        if dry_run:
            print(f"Would search: {term}")
            continue

        print(f"Searching: {term}...")
        results = search_journals(api_key, term)

        for result in results[:5]:  # Top 5 per search
            bibstem = result.get("bibstem", "")
            name = result.get("name", result.get("title", ""))
            if not bibstem or bibstem in synonyms:
                continue

            common_names = [name] if name else []

            # Try to get more details
            summary = get_journal_summary(api_key, bibstem)
            if summary:
                for key in ("title", "name", "pubname"):
                    val = summary.get(key)
                    if val and val not in common_names:
                        common_names.append(val)

            synonyms[bibstem] = {
                "common_names": common_names,
                "description": name or bibstem,
            }

        time.sleep(0.2)  # Rate limit

    return synonyms


def main():
    parser = argparse.ArgumentParser(description="Collect bibstem data from ADS Journals API")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "data/model/bibstem_synonyms.json",
        help="Output path for bibstem_synonyms.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print search terms without making API calls",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge with existing bibstem_synonyms.json instead of overwriting",
    )
    args = parser.parse_args()

    api_key = load_api_key() if not args.dry_run else "dry-run"

    synonyms = build_synonyms(api_key, dry_run=args.dry_run)

    if args.dry_run:
        print(f"\nWould search {len(SEARCH_TERMS)} terms")
        return

    # Merge with existing if requested
    if args.merge and args.output.exists():
        existing = json.loads(args.output.read_text())
        existing_synonyms = existing.get("synonyms", {})
        # New API results fill in gaps; don't overwrite curated entries
        for bibstem, data in synonyms.items():
            if bibstem not in existing_synonyms:
                existing_synonyms[bibstem] = data
        synonyms = existing_synonyms

    output = {
        "version": "1.0.0",
        "description": "Journal name to bibstem abbreviation mappings for common astronomy and physics journals",
        "last_updated": "2026-03-04",
        "references": [
            "https://scixplorer.org/journalsdb",
            "https://ui.adsabs.harvard.edu/help/search/search-syntax",
        ],
        "notes": "These mappings allow natural language queries using full journal names to match official ADS bibstem abbreviations. Can be expanded via scripts/collect_bibstems.py using the ADS Journals API.",
        "synonyms": synonyms,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(synonyms)} bibstem entries to {args.output}")


if __name__ == "__main__":
    main()
