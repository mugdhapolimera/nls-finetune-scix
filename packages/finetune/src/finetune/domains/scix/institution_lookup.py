"""Institution lookup for generating (inst: OR aff:) query clauses.

Loads institution_synonyms.json once at module level and builds a reverse index
from common names to inst: abbreviations. Provides:

- lookup_inst_abbrevs(affiliation) — find inst: abbreviations for an affiliation string
- build_inst_or_aff_clause(affiliation) — build (inst:"X" OR aff:"Y") clause
- rewrite_aff_to_inst_or_aff(query) — regex post-processor for aff: → (inst: OR aff:)
"""

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Load institution synonyms JSON once at module level
# ---------------------------------------------------------------------------

_SYNONYMS_PATH = Path(__file__).resolve().parents[6] / "data" / "model" / "institution_synonyms.json"

_synonyms: dict = {}
_name_to_inst: dict[str, list[str]] = {}

if _SYNONYMS_PATH.exists():
    with open(_SYNONYMS_PATH) as _f:
        _syn_data = json.load(_f)
    _synonyms = _syn_data.get("synonyms", {})

    # Build reverse index: common_name.lower() -> [inst_abbrev, ...]
    for _abbrev, _info in _synonyms.items():
        for _name in _info["common_names"]:
            _name_to_inst[_name.lower()] = [_info["inst_abbrev"]]

# ---------------------------------------------------------------------------
# Umbrella mappings (parent orgs → child inst: abbreviations)
# ---------------------------------------------------------------------------

_UMBRELLA_MAPPINGS: dict[str, list[str]] = {
    "nasa": ["JPL", "GSFC", "NASA Ames", "MSFC"],
    "max planck": ["MPA", "MPE", "MPIA"],
    "harvard": ["CfA"],
    "harvard-smithsonian": ["CfA"],
    "kavli": ["KIPAC", "KITP"],
    "kavli institute": ["KIPAC", "KITP"],
    "goddard": ["GSFC"],
    "nasa goddard": ["GSFC"],
}

for _key, _inst_list in _UMBRELLA_MAPPINGS.items():
    _name_to_inst[_key] = _inst_list


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lookup_inst_abbrevs(affiliation: str) -> list[str] | None:
    """Look up inst: abbreviations for an affiliation string.

    Case-insensitive lookup against common names from institution_synonyms.json
    and hardcoded umbrella mappings.

    Args:
        affiliation: Affiliation text (e.g. "MIT", "NASA", "Max Planck")

    Returns:
        List of inst: abbreviations if found, None otherwise.
    """
    val_lower = affiliation.lower().strip()

    # Direct lookup in reverse index
    if val_lower in _name_to_inst:
        return _name_to_inst[val_lower]

    return None


def build_inst_or_aff_clause(affiliation: str) -> str:
    """Build an (inst:"X" OR aff:"Y") clause for an affiliation.

    If the affiliation matches a known institution, returns a combined clause.
    Otherwise returns a plain aff:"Y" clause.

    Args:
        affiliation: Affiliation text

    Returns:
        Query clause string, e.g. '(inst:"MIT" OR aff:"MIT")'
    """
    inst_abbrevs = lookup_inst_abbrevs(affiliation)

    if inst_abbrevs:
        parts = [f'inst:"{a}"' for a in inst_abbrevs]
        parts.append(f'aff:"{affiliation}"')
        return "(" + " OR ".join(parts) + ")"

    return f'aff:"{affiliation}"'


def rewrite_aff_to_inst_or_aff(query: str) -> str:
    """Rewrite aff: fields to (inst: OR aff:) where possible.

    Regex-based post-processor for LLM output. Matches aff:"value" and
    aff:value patterns and rewrites them if the value matches a known
    institution.

    Skips aff: inside pos() operators (inst: not supported in pos()).

    Args:
        query: ADS query string potentially containing aff: fields

    Returns:
        Query with aff: rewritten to (inst: OR aff:) where matches found.
    """
    if "aff:" not in query:
        return query

    # Identify pos() regions to skip
    pos_pattern = re.compile(r"pos\(aff:[^)]+\)")
    pos_matches = list(pos_pattern.finditer(query))

    def _inside_pos(start: int, end: int) -> bool:
        for pm in pos_matches:
            if pm.start() <= start and end <= pm.end():
                return True
        return False

    # Collect replacements (start, end, replacement_text)
    replacements: list[tuple[int, int, str]] = []

    # Pattern 1: aff:"quoted value"
    aff_quoted = re.compile(r'aff:"([^"]+)"')
    for m in aff_quoted.finditer(query):
        if _inside_pos(m.start(), m.end()):
            continue
        aff_val = m.group(1)
        inst_abbrevs = lookup_inst_abbrevs(aff_val)
        if inst_abbrevs:
            parts = [f'inst:"{a}"' for a in inst_abbrevs]
            parts.append(f'aff:"{aff_val}"')
            replacement = "(" + " OR ".join(parts) + ")"
            replacements.append((m.start(), m.end(), replacement))

    # Pattern 2: aff:unquoted_value (e.g. inside operators like trending(aff:MIT))
    aff_unquoted = re.compile(r"aff:([A-Za-z][A-Za-z0-9_-]*)(?=[)\s,]|$)")
    for m in aff_unquoted.finditer(query):
        # Skip if already handled as quoted
        already_handled = any(s <= m.start() < e for s, e, _ in replacements)
        if already_handled:
            continue
        if _inside_pos(m.start(), m.end()):
            continue

        aff_val = m.group(1)
        inst_abbrevs = lookup_inst_abbrevs(aff_val)
        if inst_abbrevs:
            parts = [f'inst:"{a}"' for a in inst_abbrevs]
            parts.append(f'aff:"{aff_val}"')
            replacement = "(" + " OR ".join(parts) + ")"
            replacements.append((m.start(), m.end(), replacement))

    # Apply replacements from right to left to preserve positions
    for start, end, replacement in sorted(replacements, key=lambda x: x[0], reverse=True):
        query = query[:start] + replacement + query[end:]

    return query
