#!/usr/bin/env python3
"""Parse CanonicalAffiliations parent_child.tsv into institution_synonyms.json.

Reads the parent_child.tsv file from the CanonicalAffiliations repository
and generates a JSON mapping of institution abbreviations to common names.

Usage:
    python scripts/collect_institutions.py \
        --source ~/github/CanonicalAffiliations \
        --output data/model/institution_synonyms.json

    # Merge with existing curated file:
    python scripts/collect_institutions.py \
        --source ~/github/CanonicalAffiliations \
        --output data/model/institution_synonyms.json \
        --merge

    # Dry run (show what would be parsed):
    python scripts/collect_institutions.py \
        --source ~/github/CanonicalAffiliations \
        --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def parse_parent_child(source_dir: Path) -> dict[str, dict]:
    """Parse parent_child.tsv from CanonicalAffiliations repo.

    The TSV format has columns: child_abbrev, parent_abbrev, child_name
    (tab-separated, no header row).

    Returns:
        Dict mapping inst abbreviation to metadata.
    """
    tsv_path = source_dir / "parent_child.tsv"
    if not tsv_path.exists():
        print(f"ERROR: {tsv_path} not found.", file=sys.stderr)
        print("Clone the repo: git clone https://github.com/adsabs/CanonicalAffiliations.git", file=sys.stderr)
        sys.exit(1)

    institutions = {}

    with tsv_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 3:
                continue

            child_abbrev = row[0].strip()
            parent_abbrev = row[1].strip() if row[1].strip() != "-" else None
            child_name = row[2].strip()

            if not child_abbrev:
                continue

            # Build common_names list
            common_names = [child_name] if child_name else []
            if child_abbrev not in common_names:
                common_names.append(child_abbrev)

            institutions[child_abbrev] = {
                "inst_abbrev": child_abbrev,
                "common_names": common_names,
                "parent": parent_abbrev,
            }

    return institutions


def main():
    parser = argparse.ArgumentParser(
        description="Parse CanonicalAffiliations into institution_synonyms.json"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "github/CanonicalAffiliations",
        help="Path to local CanonicalAffiliations repo",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "data/model/institution_synonyms.json",
        help="Output path for institution_synonyms.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print stats without writing output",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge with existing institution_synonyms.json (curated entries take priority)",
    )
    args = parser.parse_args()

    print(f"Parsing {args.source / 'parent_child.tsv'}...")
    institutions = parse_parent_child(args.source)
    print(f"Found {len(institutions)} institutions")

    # Show stats
    with_parent = sum(1 for v in institutions.values() if v["parent"])
    print(f"  Top-level: {len(institutions) - with_parent}")
    print(f"  With parent: {with_parent}")

    if args.dry_run:
        # Print a sample
        for abbrev, data in list(institutions.items())[:20]:
            parent = f" (parent: {data['parent']})" if data["parent"] else ""
            print(f"  {abbrev}: {data['common_names'][0]}{parent}")
        return

    # Merge with existing curated file if requested
    if args.merge and args.output.exists():
        existing = json.loads(args.output.read_text())
        existing_synonyms = existing.get("synonyms", {})
        # Curated entries take priority over parsed ones
        for abbrev, data in institutions.items():
            if abbrev not in existing_synonyms:
                existing_synonyms[abbrev] = data
        synonyms = existing_synonyms
    else:
        synonyms = institutions

    output = {
        "version": "1.0.0",
        "description": "Institution common name to ADS inst: abbreviation mappings",
        "last_updated": "2026-03-04",
        "references": [
            "https://github.com/adsabs/CanonicalAffiliations",
            "https://ui.adsabs.harvard.edu/help/search/search-syntax",
        ],
        "notes": "These mappings allow natural language queries using institution names to match curated inst: abbreviations. Can be expanded via scripts/collect_institutions.py parsing CanonicalAffiliations/parent_child.tsv.",
        "synonyms": synonyms,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(synonyms)} institution entries to {args.output}")


if __name__ == "__main__":
    main()
