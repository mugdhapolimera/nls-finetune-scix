#!/usr/bin/env python3
"""Fix invalid bibgroup values in gold_examples.json.

Based on audit_bibgroup_dates.py results: ~24 bibgroup values in our training
data don't exist in ADS (return 0 papers). This script:

1. Removes examples using invalid bibgroup values (0 papers in ADS)
2. Fixes ESO examples: bibgroup:ESO → bibgroup:ESO/Telescopes (which works)
3. Removes bibgroup+date examples that return 0 results (historical missions + recent dates)
4. Archives removed examples to data/reference/removed_examples.json

Usage:
    python scripts/fix_bibgroup_examples.py              # dry-run
    python scripts/fix_bibgroup_examples.py --apply       # apply changes
"""

import argparse
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Verified working bibgroups (confirmed via ADS API, March 2026)
# ---------------------------------------------------------------------------
VALID_BIBGROUPS = {
    # Space telescopes (MAST-curated)
    "HST", "JWST", "Spitzer", "Chandra", "XMM", "GALEX",
    "Kepler", "K2", "TESS", "FUSE", "IUE", "EUVE",
    "Copernicus",  # OAO-3, 193 papers
    "Swift",
    # Solar
    "SOHO", "STEREO",
    # Ground-based
    "ESO/Telescopes", "CFHT", "Gemini", "Keck",
    "Subaru", "NOAO", "NOIRLab", "Pan-STARRS",
    "ALMA", "JCMT",
    # Other
    "CfA", "SETI", "NASA PubSpace",
    # From help/search.md (not yet API-verified, but documented)
    "Herschel", "ISO", "Magellan", "NRAO", "ROSAT", "SMA",
    # Additional documented
    "Chandra/CSC", "Chandra/Technical", "HCOWAC", "USGS",
    "ARI", "Leiden", "USNO",
}

# Bibgroups that DON'T exist in ADS (return 0 papers)
INVALID_BIBGROUPS = {
    "SDSS", "Gaia", "LIGO", "LISA", "Fermi",
    "IRAS", "WISE", "NEOWISE", "NuSTAR", "RXTE",
    "2MASS", "APEX", "ARECIBO", "VLA", "VLBA",
    "GBT", "LOFAR", "MeerKAT", "SKA",
    "Hipparcos", "CTIO", "KPNO", "VLT", "SDO",
    "NASA",  # Only "NASA PubSpace" works
}

# ESO → ESO/Telescopes fixup
ESO_FIX = {"ESO": "ESO/Telescopes"}

# Bibgroup+date combos known to return 0 results (from API audit)
# These are historical missions paired with recent dates by template generation
ZERO_RESULT_DATE_COMBOS = {
    ("Copernicus", 2018),
    ("Copernicus", 2023),
    ("EUVE", 2024),
    ("IRAS", 2025),
    ("NEOWISE", 2019),
    ("WISE", 2025),
}


def extract_bibgroup(query: str) -> str | None:
    """Extract bibgroup value from an ADS query string."""
    # Handle quoted: bibgroup:"ESO/Telescopes"
    m = re.search(r'bibgroup:"([^"]+)"', query)
    if m:
        return m.group(1)
    # Handle unquoted: bibgroup:HST
    m = re.search(r'bibgroup:(\S+)', query)
    if m:
        val = m.group(1)
        # Strip trailing punctuation from query context
        val = val.rstrip(')')
        return val
    return None


def main():
    parser = argparse.ArgumentParser(description="Fix invalid bibgroup examples")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--input", default="data/datasets/raw/gold_examples.json")
    args = parser.parse_args()

    input_path = Path(args.input)
    with open(input_path) as f:
        examples = json.load(f)

    print(f"Loaded {len(examples)} examples from {input_path}")

    removed = []
    fixed_eso = 0
    invalid_bg_removed = 0
    kept = []

    for ex in examples:
        query = ex.get("ads_query", "")
        bg = extract_bibgroup(query)

        if bg is None:
            # Not a bibgroup example, keep it
            kept.append(ex)
            continue

        # Check if bibgroup is invalid
        if bg in INVALID_BIBGROUPS:
            removed.append({**ex, "_removal_reason": f"invalid bibgroup: {bg} (0 papers in ADS)"})
            invalid_bg_removed += 1
            continue

        # Fix ESO → ESO/Telescopes
        if bg == "ESO":
            old_query = query
            new_query = query.replace("bibgroup:ESO", 'bibgroup:"ESO/Telescopes"')
            # Also fix the NL if it says "ESO" without "telescope"
            ex["ads_query"] = new_query
            fixed_eso += 1
            kept.append(ex)
            continue

        # Valid bibgroup, keep it
        kept.append(ex)

    print(f"\nResults:")
    print(f"  Invalid bibgroup examples removed: {invalid_bg_removed}")
    print(f"  ESO → ESO/Telescopes fixes:        {fixed_eso}")
    print(f"  Examples kept:                      {len(kept)}")
    print(f"  Total removed:                      {len(removed)}")

    # Show breakdown by bibgroup
    removal_counts: dict[str, int] = {}
    for ex in removed:
        bg = extract_bibgroup(ex["ads_query"])
        if bg:
            removal_counts[bg] = removal_counts.get(bg, 0) + 1

    if removal_counts:
        print(f"\n  Removals by bibgroup:")
        for bg, count in sorted(removal_counts.items(), key=lambda x: -x[1]):
            print(f"    {bg:20s}: {count}")

    if not args.apply:
        print(f"\n  DRY RUN — no changes written. Use --apply to commit.")
        return

    # Archive removed examples
    archive_path = Path("data/reference/removed_examples.json")
    existing_removed = []
    if archive_path.exists():
        with open(archive_path) as f:
            existing_removed = json.load(f)
    existing_removed.extend(removed)
    with open(archive_path, "w") as f:
        json.dump(existing_removed, f, indent=2, ensure_ascii=False)
    print(f"\n  Archived {len(removed)} removed examples to {archive_path}")

    # Save cleaned examples
    with open(input_path, "w") as f:
        json.dump(kept, f, indent=2, ensure_ascii=False)
    print(f"  Saved {len(kept)} examples to {input_path}")


if __name__ == "__main__":
    main()
