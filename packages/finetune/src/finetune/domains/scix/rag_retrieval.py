"""RAG retrieval for few-shot LLM augmentation.

Retrieves similar gold examples to inject into the LLM prompt as
few-shot demonstrations. Reuses the existing BM25 retrieval index.

Performance target: <20ms for k=3 on ~5K examples.
"""

import json
import logging
import os
import re
from pathlib import Path

from .intent_spec import IntentSpec
from .retrieval import GoldExampleIndex, get_index, tokenize

logger = logging.getLogger(__name__)

# Cached intent-format examples, keyed by natural_language text
_intent_examples: dict[str, dict] | None = None


def _get_intent_examples_path() -> Path:
    """Get path to gold_examples_intent.json."""
    env_path = os.environ.get("GOLD_EXAMPLES_INTENT_PATH")
    if env_path:
        return Path(env_path)
    return (
        Path(__file__).parent.parent.parent.parent.parent.parent.parent
        / "data"
        / "datasets"
        / "raw"
        / "gold_examples_intent.json"
    )


def _load_intent_examples() -> dict[str, dict]:
    """Load gold_examples_intent.json, keyed by natural_language for fast lookup."""
    global _intent_examples
    if _intent_examples is not None:
        return _intent_examples

    path = _get_intent_examples_path()
    if not path.exists():
        logger.warning("Intent examples file not found: %s", path)
        _intent_examples = {}
        return _intent_examples

    with open(path) as f:
        examples = json.load(f)

    _intent_examples = {}
    for ex in examples:
        nl = ex.get("natural_language", "")
        intent_json = ex.get("intent_json")
        think_trace = ex.get("think_trace", "")
        if nl and intent_json:
            _intent_examples[nl] = {
                "nl": nl,
                "intent_json": intent_json,
                "think_trace": think_trace,
            }

    logger.info("Loaded %d intent-format examples for RAG", len(_intent_examples))
    return _intent_examples


def _extract_topics(nl_text: str) -> list[str]:
    """Extract likely topic phrases from natural language text.

    Simple heuristic: return non-stopword tokens as a single phrase.
    Used to create a lightweight IntentSpec for retrieval scoring.
    """
    tokens = tokenize(nl_text)
    return [" ".join(sorted(tokens))] if tokens else []


def retrieve_few_shot(
    nl_text: str,
    k: int = 3,
    exclude_exact: bool = True,
) -> list[dict]:
    """Retrieve k similar gold examples with IntentSpec JSON for few-shot prompting.

    Args:
        nl_text: Natural language query to find similar examples for.
        k: Number of examples to retrieve.
        exclude_exact: If True, exclude examples whose NL matches the input exactly.

    Returns:
        List of {"nl": str, "intent_json": dict, "think_trace": str}.
        Uses existing BM25 retrieval index for speed (<20ms).
    """
    index = get_index()
    intent_map = _load_intent_examples()

    if not intent_map:
        return []

    # Create minimal IntentSpec for retrieval scoring
    topics = _extract_topics(nl_text)
    if not topics or (len(topics) == 1 and not topics[0].strip()):
        # Very short or stopwords-only query — use raw text as fallback
        raw = nl_text.strip().lower()
        topics = [raw] if raw else []
    if not topics:
        return []
    intent = IntentSpec(free_text_terms=topics)

    # Retrieve more than k to account for filtering
    candidates = index.retrieve(intent, k=k * 3)

    # Filter out very low-scoring candidates (noise from short queries)
    if candidates:
        max_score = candidates[0].score
        min_threshold = max(0.5, max_score * 0.3)
        candidates = [c for c in candidates if c.score >= min_threshold]

    results = []
    nl_lower = nl_text.strip().lower()

    for ex in candidates:
        # Skip exact match (don't give the answer away)
        if exclude_exact and ex.nl_query.strip().lower() == nl_lower:
            continue

        # Map to intent format
        if ex.nl_query in intent_map:
            results.append(intent_map[ex.nl_query])
            if len(results) >= k:
                break

    return results


def reset_intent_cache() -> None:
    """Reset the intent examples cache (for testing)."""
    global _intent_examples
    _intent_examples = None
