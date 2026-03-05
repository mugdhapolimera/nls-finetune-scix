#!/usr/bin/env python3
"""
Generate training data for "seminal/classical reference" queries.

Creates NL-query pairs that teach the model to use useful() + pubdate year
range patterns when users ask for foundational, classical, or landmark papers.

This addresses the "Concept-Based / Semantic Search" gap (Issue Type 3) from
the SciX vs Google Scholar gap analysis.

Usage:
    python scripts/generate_seminal_reference_examples.py \
        --output data/datasets/generated/seminal_reference_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Seed data: each entry is (topic phrase, abs terms, year range, optional OR)
# ---------------------------------------------------------------------------
SEMINAL_TOPICS = [
    # Methods & statistics
    {
        "topic": "magnetotellurics",
        "abs_terms": ["magnetotelluric"],
        "year_range": (1950, 1980),
    },
    {
        "topic": "Occam's inversion",
        "abs_terms": ["Occam", "inversion"],
        "year_range": (1980, 2000),
    },
    {
        "topic": "Bayesian inference in astrophysics",
        "abs_terms": ["Bayesian inference"],
        "year_range": (1980, 2005),
    },
    {
        "topic": "the Lomb-Scargle periodogram",
        "abs_terms": ["Lomb", "periodogram"],
        "year_range": (1970, 1990),
    },
    {
        "topic": "MCMC methods in astronomy",
        "abs_terms": ["Markov chain Monte Carlo"],
        "year_range": (1990, 2005),
    },
    {
        "topic": "wavelet transforms in signal processing",
        "abs_terms": ["wavelet transform"],
        "year_range": (1985, 2000),
    },
    {
        "topic": "adaptive optics",
        "abs_terms": ["adaptive optics"],
        "year_range": (1980, 2000),
    },
    {
        "topic": "principal component analysis",
        "abs_terms": ["principal component analysis"],
        "year_range": (1980, 2005),
    },
    {
        "topic": "stellar nucleosynthesis",
        "abs_terms": ["nucleosynthesis"],
        "year_range": (1950, 1975),
    },
    {
        "topic": "the Navarro-Frenk-White profile",
        "abs_terms": ["NFW"],
        "or_terms": ["Navarro-Frenk-White"],
        "year_range": (1995, 2000),
    },
    {
        "topic": "chi-squared fitting techniques",
        "abs_terms": ["chi-squared", "fitting"],
        "year_range": (1970, 2000),
    },
    {
        "topic": "the tipper in magnetotellurics",
        "abs_terms": ["tipper", "magnetotelluric"],
        "year_range": (1950, 1990),
    },
    {
        "topic": "the CMB power spectrum",
        "abs_terms": ["CMB", "power spectrum"],
        "year_range": (1990, 2005),
    },
    {
        "topic": "galaxy morphological classification",
        "abs_terms": ["galaxy", "morphological classification"],
        "year_range": (1920, 1970),
    },
    {
        "topic": "the Kolmogorov-Smirnov test in astronomy",
        "abs_terms": ["Kolmogorov-Smirnov"],
        "year_range": (1970, 2000),
    },
    {
        "topic": "least squares fitting",
        "abs_terms": ["least squares"],
        "year_range": (1960, 1990),
    },
    # Cross-domain methods (useful + property:refereed instead of year range)
    {
        "topic": "linear regression methods",
        "abs_terms": ["linear regression"],
        "use_refereed": True,
    },
    {
        "topic": "the bootstrap method in statistics",
        "abs_terms": ["bootstrap", "resampling"],
        "use_refereed": True,
    },
    {
        "topic": "the Fourier transform",
        "abs_terms": ["Fourier transform"],
        "year_range": (1960, 1990),
    },
    {
        "topic": "maximum likelihood estimation",
        "abs_terms": ["maximum likelihood estimation"],
        "use_refereed": True,
    },
    # Additional topics for variety
    {
        "topic": "the Salpeter initial mass function",
        "abs_terms": ["Salpeter", "initial mass function"],
        "year_range": (1950, 1970),
    },
    {
        "topic": "the Chandrasekhar limit",
        "abs_terms": ["Chandrasekhar limit"],
        "year_range": (1930, 1960),
    },
    {
        "topic": "Bondi accretion",
        "abs_terms": ["Bondi", "accretion"],
        "year_range": (1940, 1970),
    },
    {
        "topic": "the Press-Schechter formalism",
        "abs_terms": ["Press-Schechter"],
        "year_range": (1970, 1985),
    },
    {
        "topic": "the Kennicutt-Schmidt star formation law",
        "abs_terms": ["Kennicutt", "star formation"],
        "year_range": (1980, 2000),
    },
    {
        "topic": "the Tully-Fisher relation",
        "abs_terms": ["Tully-Fisher"],
        "year_range": (1975, 1990),
    },
    {
        "topic": "the Shakura-Sunyaev accretion disk model",
        "abs_terms": ["Shakura", "accretion disk"],
        "year_range": (1970, 1985),
    },
    {
        "topic": "the Eddington luminosity",
        "abs_terms": ["Eddington luminosity"],
        "year_range": (1920, 1960),
    },
    {
        "topic": "Jeans instability",
        "abs_terms": ["Jeans", "instability"],
        "year_range": (1900, 1950),
    },
    {
        "topic": "the Schwarzschild metric",
        "abs_terms": ["Schwarzschild", "metric"],
        "year_range": (1916, 1960),
    },
]

# NL templates — the {intent_phrase} slot gets a trigger word/phrase
# and {topic} gets the topic description
NL_TEMPLATES = [
    "the original paper on {topic}",
    "seminal paper on {topic}",
    "classical reference for {topic}",
    "foundational paper on {topic}",
    "the landmark paper on {topic}",
    "pioneering work on {topic}",
    "foundational reference for {topic}",
    "the definitive early paper on {topic}",
    "original paper on {topic}",
    "seminal work on {topic}",
    "who first proposed {topic}",
    "key early papers on {topic}",
    "the classic paper on {topic}",
    "authoritative reference for {topic}",
    "{topic} reference paper",
    "classic {topic} reference",
    "the groundbreaking paper on {topic}",
    "the canonical reference for {topic}",
    "the first paper introducing {topic}",
    "the influential early work on {topic}",
]


def _build_abs_clause(abs_terms: list[str]) -> str:
    """Build abs:... clause(s) from a list of terms."""
    return " ".join(f'abs:"{t}"' for t in abs_terms)


def _build_query(entry: dict) -> str:
    """Build the ADS query from a seed entry."""
    abs_clause = _build_abs_clause(entry["abs_terms"])

    # Handle OR terms — no extra parens, just abs:"X" OR abs:"Y"
    if "or_terms" in entry:
        or_parts = " OR ".join(
            f'abs:"{t}"' for t in [entry["abs_terms"][0]] + entry["or_terms"]
        )
        abs_clause = or_parts
        # If there are more abs_terms beyond the first, add them
        if len(entry["abs_terms"]) > 1:
            extra = " ".join(f'abs:"{t}"' for t in entry["abs_terms"][1:])
            abs_clause = f"{abs_clause} {extra}"

    inner = abs_clause

    if entry.get("use_refereed"):
        return f"useful({inner}) property:refereed"
    else:
        y_from, y_to = entry["year_range"]
        return f"useful({inner}) pubdate:[{y_from} TO {y_to}]"


def generate_examples() -> list[dict]:
    """Generate all seminal reference training examples."""
    examples: list[dict] = []

    for entry in SEMINAL_TOPICS:
        query = _build_query(entry)
        topic = entry["topic"]

        # Pick 2 NL templates per topic for variety
        templates = random.sample(NL_TEMPLATES, min(2, len(NL_TEMPLATES)))

        for template in templates:
            nl = template.format(topic=topic)
            examples.append(
                {
                    "natural_language": nl,
                    "ads_query": query,
                    "category": "operator",
                }
            )

    return examples


def main():
    parser = argparse.ArgumentParser(
        description="Generate seminal/classical reference training examples"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/datasets/generated/seminal_reference_examples.json"),
        help="Output JSON file path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    args = parser.parse_args()

    random.seed(args.seed)

    examples = generate_examples()

    # Deduplicate by normalized NL
    seen: set[str] = set()
    unique: list[dict] = []
    for ex in examples:
        key = ex["natural_language"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(ex)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(unique)} seminal reference examples")
    print(f"  Topics covered: {len(SEMINAL_TOPICS)}")
    print(f"  With year range: {sum(1 for t in SEMINAL_TOPICS if 'year_range' in t)}")
    print(f"  With property:refereed: {sum(1 for t in SEMINAL_TOPICS if t.get('use_refereed'))}")


if __name__ == "__main__":
    main()
