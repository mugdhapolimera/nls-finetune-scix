"""Journal bibstem lookup for generating bibstem:"X" query clauses.

Loads bibstem_synonyms.json once at module level and builds a reverse index
from common journal names to bibstem abbreviations. Provides:

- lookup_bibstem(journal_name) — find bibstem abbreviation for a journal name
- build_bibstem_clause(journal_name) — build bibstem:"X" clause or abs: fallback
- rewrite_bibstem_values(query) — regex post-processor for bibstem values in LLM output
"""

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Load bibstem synonyms JSON once at module level
# ---------------------------------------------------------------------------

_SYNONYMS_PATH = Path(__file__).resolve().parents[6] / "data" / "model" / "bibstem_synonyms.json"

_synonyms: dict = {}
_name_to_bibstem: dict[str, str] = {}

if _SYNONYMS_PATH.exists():
    with open(_SYNONYMS_PATH) as _f:
        _syn_data = json.load(_f)
    _synonyms = _syn_data.get("synonyms", {})

    # Build reverse index: common_name.lower() -> bibstem_key
    for _bibstem_key, _info in _synonyms.items():
        # Index the bibstem key itself (e.g., "MNRAS" -> "MNRAS")
        _name_to_bibstem[_bibstem_key.lower()] = _bibstem_key
        for _name in _info["common_names"]:
            _name_to_bibstem[_name.lower()] = _bibstem_key


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lookup_bibstem(journal_name: str) -> str | None:
    """Look up bibstem abbreviation for a journal name.

    Case-insensitive lookup against common names from bibstem_synonyms.json.

    Args:
        journal_name: Journal name (e.g. "Astrophysical Journal", "ApJ", "PRL")

    Returns:
        Bibstem abbreviation if found (e.g. "ApJ"), None otherwise.
    """
    val_lower = journal_name.lower().strip()

    if val_lower in _name_to_bibstem:
        return _name_to_bibstem[val_lower]

    return None


def build_bibstem_clause(journal_name: str) -> str:
    """Build a bibstem:"X" clause for a journal name.

    If the journal matches a known bibstem, returns bibstem:"ABBREV".
    Otherwise returns abs:"journal name" as fallback.

    Args:
        journal_name: Journal name text

    Returns:
        Query clause string, e.g. 'bibstem:"ApJ"'
    """
    bibstem = lookup_bibstem(journal_name)

    if bibstem:
        return f'bibstem:"{bibstem}"'

    return f'abs:"{journal_name}"'


def rewrite_bibstem_values(query: str) -> str:
    """Rewrite bibstem field values in LLM output to correct abbreviations.

    Handles two LLM failure modes:
    1. Full name in bibstem field: bibstem:"Astrophysical Journal" -> bibstem:"ApJ"
    2. Bare unquoted bibstem: bibstem:ApJ -> bibstem:"ApJ" (add quotes)

    Args:
        query: ADS query string potentially containing bibstem: fields

    Returns:
        Query with bibstem values corrected where possible.
    """
    if "bibstem:" not in query:
        return query

    replacements: list[tuple[int, int, str]] = []

    # Pattern 1: bibstem:"quoted value" — rewrite full names to abbreviations
    bibstem_quoted = re.compile(r'bibstem:"([^"]+)"')
    for m in bibstem_quoted.finditer(query):
        val = m.group(1)
        bibstem = lookup_bibstem(val)
        if bibstem and bibstem != val:
            replacements.append((m.start(), m.end(), f'bibstem:"{bibstem}"'))

    # Pattern 2: bibstem:unquoted_value — add quotes (and resolve if needed)
    bibstem_unquoted = re.compile(r"bibstem:([A-Za-z&][A-Za-z0-9&*]+)(?=[)\s,]|$)")
    for m in bibstem_unquoted.finditer(query):
        # Skip if already handled as quoted
        already_handled = any(s <= m.start() < e for s, e, _ in replacements)
        if already_handled:
            continue

        val = m.group(1)
        # Try to resolve the value to a canonical bibstem
        bibstem = lookup_bibstem(val)
        resolved = bibstem if bibstem else val
        replacements.append((m.start(), m.end(), f'bibstem:"{resolved}"'))

    # Apply replacements from right to left to preserve positions
    for start, end, replacement in sorted(replacements, key=lambda x: x[0], reverse=True):
        query = query[:start] + replacement + query[end:]

    return query
