#!/usr/bin/env python3
"""Update gold_examples.json to use (inst:"X" OR aff:"Y") pattern for maximum recall.

For each training example containing aff:"...", if the affiliation value matches
a known institution in institution_synonyms.json, rewrite to:
  (inst:"ABBREV" OR aff:"VALUE")

Special cases:
- pos() operator: leave as aff: only (inst: not supported inside pos())
- NOT aff: → NOT (inst:"X" OR aff:"Y")
- Umbrella institutions (NASA, Max Planck, Harvard) → include all child inst: values
- trending() / citations() / references(): inst: works inside these operators
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = ROOT / "data" / "datasets" / "raw" / "gold_examples.json"
SYNONYMS_PATH = ROOT / "data" / "model" / "institution_synonyms.json"

# Load institution synonyms
with open(SYNONYMS_PATH) as f:
    syn_data = json.load(f)
synonyms = syn_data["synonyms"]

# Build lookup: common name (lowercase) -> list of inst abbreviations
# For umbrella orgs, also collect children
name_to_inst = {}
parent_to_children = {}

for abbrev, info in synonyms.items():
    parent = info.get("parent")
    if parent:
        parent_to_children.setdefault(parent, []).append(abbrev)
    for name in info["common_names"]:
        name_to_inst[name.lower()] = [info["inst_abbrev"]]

# Add umbrella mappings: "NASA" -> [JPL, GSFC, NASA Ames, MSFC] etc.
# Also map "Max Planck" -> [MPA, MPE, MPIA]
UMBRELLA_MAPPINGS = {
    "nasa": ["JPL", "GSFC", "NASA Ames", "MSFC"],
    "max planck": ["MPA", "MPE", "MPIA"],
    "harvard": ["CfA"],  # Harvard is broader than CfA but CfA is the canonical
    "harvard-smithsonian": ["CfA"],
    "harvard-smithsonia": ["CfA"],  # typo in training data
    "kavli": ["KIPAC", "KITP"],
    "kavli institute": ["KIPAC", "KITP"],
    "goddard": ["GSFC"],
    "nasa goddard": ["GSFC"],
}

for key, inst_list in UMBRELLA_MAPPINGS.items():
    name_to_inst[key] = inst_list


def find_inst_abbrevs(aff_value: str) -> list[str] | None:
    """Look up inst: abbreviations for an aff: value."""
    val_lower = aff_value.lower().strip()

    # Direct lookup
    if val_lower in name_to_inst:
        return name_to_inst[val_lower]

    # Try matching against common names
    for abbrev, info in synonyms.items():
        for name in info["common_names"]:
            if val_lower == name.lower():
                return [info["inst_abbrev"]]

    return None


def build_inst_or_aff(inst_abbrevs: list[str], aff_value: str) -> str:
    """Build (inst:"X" OR ... OR aff:"Y") clause."""
    parts = [f'inst:"{a}"' for a in inst_abbrevs]
    parts.append(f'aff:"{aff_value}"')
    return "(" + " OR ".join(parts) + ")"


def transform_query(query: str) -> tuple[str, list[str]]:
    """Transform aff: fields to (inst: OR aff:) where possible.

    Returns (new_query, list_of_changes).
    """
    changes = []
    new_query = query

    # Pattern 1: aff:"value" (quoted) — but NOT inside pos()
    # First, handle pos() separately — leave those alone
    pos_pattern = re.compile(r'pos\(aff:[^)]+\)')
    pos_matches = list(pos_pattern.finditer(new_query))

    # Find all aff:"value" patterns
    aff_quoted = re.compile(r'aff:"([^"]+)"')

    # Process from right to left to preserve positions
    replacements = []
    for m in aff_quoted.finditer(new_query):
        # Check if this match is inside a pos() — if so, skip
        inside_pos = False
        for pm in pos_matches:
            if pm.start() <= m.start() and m.end() <= pm.end():
                inside_pos = True
                break

        if inside_pos:
            changes.append(f"  SKIP (inside pos()): aff:\"{m.group(1)}\"")
            continue

        aff_val = m.group(1)
        inst_abbrevs = find_inst_abbrevs(aff_val)

        if inst_abbrevs:
            replacement = build_inst_or_aff(inst_abbrevs, aff_val)
            replacements.append((m.start(), m.end(), replacement))
            changes.append(f"  aff:\"{aff_val}\" → {replacement}")
        else:
            changes.append(f"  NO MATCH: aff:\"{aff_val}\"")

    # Pattern 2: aff:value (unquoted, e.g., in trending(aff:Harvard))
    aff_unquoted = re.compile(r'aff:([A-Za-z][A-Za-z0-9_-]*)(?=[)\s,]|$)')
    for m in aff_unquoted.finditer(new_query):
        # Skip if already handled as quoted
        already_handled = any(
            start <= m.start() < end for start, end, _ in replacements
        )
        if already_handled:
            continue

        # Check if inside pos()
        inside_pos = False
        for pm in pos_matches:
            if pm.start() <= m.start() and m.end() <= pm.end():
                inside_pos = True
                break

        if inside_pos:
            changes.append(f"  SKIP (inside pos()): aff:{m.group(1)}")
            continue

        aff_val = m.group(1)
        inst_abbrevs = find_inst_abbrevs(aff_val)

        if inst_abbrevs:
            # For unquoted inside operators, use: inst:"X" OR aff:"Y"
            replacement = build_inst_or_aff(inst_abbrevs, aff_val)
            replacements.append((m.start(), m.end(), replacement))
            changes.append(f"  aff:{aff_val} → {replacement}")
        else:
            changes.append(f"  NO MATCH: aff:{aff_val}")

    # Apply replacements from right to left
    for start, end, replacement in sorted(replacements, key=lambda x: x[0], reverse=True):
        new_query = new_query[:start] + replacement + new_query[end:]

    return new_query, changes


def main():
    dry_run = "--dry-run" in sys.argv

    with open(GOLD_PATH) as f:
        examples = json.load(f)

    total = 0
    modified = 0
    skipped_pos = 0
    no_match = 0
    all_changes = []

    for i, ex in enumerate(examples):
        query = ex["ads_query"]
        if "aff:" not in query:
            continue

        total += 1
        new_query, changes = transform_query(query)

        if new_query != query:
            modified += 1
            all_changes.append({
                "index": i,
                "nl": ex["natural_language"],
                "old": query,
                "new": new_query,
                "changes": changes,
            })
            if not dry_run:
                examples[i]["ads_query"] = new_query

        for c in changes:
            if "SKIP" in c:
                skipped_pos += 1
            elif "NO MATCH" in c:
                no_match += 1

    # Print summary
    print(f"\n{'DRY RUN — no files modified' if dry_run else 'APPLIED CHANGES'}")
    print(f"{'=' * 60}")
    print(f"Total examples with aff: {total}")
    print(f"Modified: {modified}")
    print(f"Skipped (inside pos()): {skipped_pos}")
    print(f"No inst: match found: {no_match}")
    print()

    for ch in all_changes:
        print(f"### Example {ch['index']}: \"{ch['nl'][:60]}...\"")
        print(f"  OLD: {ch['old']}")
        print(f"  NEW: {ch['new']}")
        for c in ch["changes"]:
            print(f"  {c}")
        print()

    if not dry_run:
        with open(GOLD_PATH, "w") as f:
            json.dump(examples, f, indent=2, ensure_ascii=False)
        print(f"Wrote updated examples to {GOLD_PATH}")
    else:
        print("Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
