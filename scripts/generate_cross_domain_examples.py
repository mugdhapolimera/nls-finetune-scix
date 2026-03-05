#!/usr/bin/env python3
"""
Generate training data for cross-domain query shaping.

Creates NL-query pairs that teach the model to use database: filters and
useful() operators when users ask about topics outside core astrophysics
(physics, general science, earth science, statistics, etc.).

This addresses the "Cross-Domain / Out-of-Scope Queries" gap (Issue Type 7)
from the SciX vs Google Scholar gap analysis.

Usage:
    python scripts/generate_cross_domain_examples.py \
        --output data/datasets/generated/cross_domain_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Database-specific topics
# Each entry: (topic_display, abs_term, database)
# ---------------------------------------------------------------------------
DATABASE_TOPICS = {
    "physics": [
        ("superconductivity", "superconductivity"),
        ("quantum computing", "quantum computing"),
        ("condensed matter", "condensed matter"),
        ("particle physics", "particle physics"),
        ("quantum field theory", "quantum field theory"),
        ("plasma physics", "plasma physics"),
        ("nuclear physics", "nuclear physics"),
        ("optics", "optics"),
        ("semiconductor", "semiconductor"),
        ("topological insulator", "topological insulator"),
        ("Bose-Einstein condensate", "Bose-Einstein condensate"),
        ("lattice QCD", "lattice QCD"),
    ],
    "general": [
        ("climate modeling", "climate model"),
        ("neural networks", "neural network"),
        ("bioinformatics", "bioinformatics"),
        ("epidemiology", "epidemiology"),
        ("ocean circulation", "ocean circulation"),
        ("seismology", "seismology"),
        ("atmospheric chemistry", "atmospheric chemistry"),
        ("remote sensing", "remote sensing"),
        ("materials science", "materials science"),
        ("fluid dynamics", "fluid dynamics"),
    ],
    "astronomy": [
        ("statistical methods", "statistical method"),
        ("data analysis techniques", "data analysis"),
        ("signal processing", "signal processing"),
        ("Bayesian statistics", "Bayesian"),
        ("time series analysis", "time series"),
    ],
}

# Domain-label mappings for NL phrasing
DOMAIN_LABELS = {
    "physics": [
        "physics papers on {topic}",
        "physics database papers on {topic}",
        "find {topic} papers in the physics database",
        "{topic} research in physics",
        "physics literature on {topic}",
    ],
    "general": [
        "general science papers on {topic}",
        "{topic} papers in the general science database",
        "find {topic} in general science",
        "non-astronomy papers about {topic}",
        "general science literature on {topic}",
    ],
    "astronomy": [
        "{topic} used in astronomy",
        "astronomy papers about {topic}",
        "{topic} in the astronomy database",
    ],
}

# Earth science / geophysics are mapped to database:physics in ADS
EARTH_SCIENCE_TOPICS = [
    ("seismic tomography", "seismic tomography"),
    ("mantle convection", "mantle convection"),
    ("plate tectonics", "plate tectonics"),
    ("geodynamics", "geodynamics"),
    ("paleoclimate", "paleoclimate"),
    ("volcanology", "volcanology"),
    ("geodesy", "geodesy"),
    ("geomagnetism", "geomagnetism"),
]

EARTH_SCIENCE_TEMPLATES = [
    "geophysics papers on {topic}",
    "earth science papers on {topic}",
    "geoscience research about {topic}",
    "find {topic} papers in earth science",
]

# Cross-domain methods that benefit from useful() + property:refereed
CROSS_DOMAIN_METHODS = [
    ("linear regression", "linear regression"),
    ("the bootstrap method", "bootstrap"),
    ("maximum likelihood estimation", "maximum likelihood estimation"),
    ("Monte Carlo simulation", "Monte Carlo"),
    ("Fourier analysis", "Fourier"),
    ("principal component analysis", "principal component analysis"),
    ("neural network classification", "neural network"),
    ("random forest", "random forest"),
    ("Kalman filter", "Kalman filter"),
    ("support vector machine", "support vector machine"),
]

CROSS_DOMAIN_METHOD_TEMPLATES = [
    "{topic} reference paper",
    "reference paper for {topic} in statistics",
    "definitive reference for {topic}",
    "find the key paper on {topic}",
    "{topic} methods review",
]


def generate_database_examples() -> list[dict]:
    """Generate database:X filter examples."""
    examples: list[dict] = []

    for db, topics in DATABASE_TOPICS.items():
        templates = DOMAIN_LABELS[db]

        for topic_display, topic_abs in topics:
            template = random.choice(templates)
            nl = template.format(topic=topic_display)
            query = f'abs:"{topic_abs}" database:{db} doctype:article'

            examples.append({
                "natural_language": nl,
                "ads_query": query,
                "category": "collection",
            })

    return examples


def generate_earth_science_examples() -> list[dict]:
    """Generate earth science examples (mapped to database:physics)."""
    examples: list[dict] = []

    for topic_display, topic_abs in EARTH_SCIENCE_TOPICS:
        template = random.choice(EARTH_SCIENCE_TEMPLATES)
        nl = template.format(topic=topic_display)
        query = f'abs:"{topic_abs}" database:physics doctype:article'

        examples.append({
            "natural_language": nl,
            "ads_query": query,
            "category": "collection",
        })

    return examples


def generate_cross_domain_method_examples() -> list[dict]:
    """Generate useful() + property:refereed examples for cross-domain methods."""
    examples: list[dict] = []

    for topic_display, topic_abs in CROSS_DOMAIN_METHODS:
        template = random.choice(CROSS_DOMAIN_METHOD_TEMPLATES)
        nl = template.format(topic=topic_display)
        query = f'useful(abs:"{topic_abs}") property:refereed'

        examples.append({
            "natural_language": nl,
            "ads_query": query,
            "category": "operator",
        })

    return examples


def generate_examples() -> list[dict]:
    """Generate all cross-domain training examples."""
    examples: list[dict] = []
    examples.extend(generate_database_examples())
    examples.extend(generate_earth_science_examples())
    examples.extend(generate_cross_domain_method_examples())
    return examples


def main():
    parser = argparse.ArgumentParser(
        description="Generate cross-domain query shaping training examples"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/datasets/generated/cross_domain_examples.json"),
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

    # Deduplicate
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

    # Summary
    cats = {}
    for e in unique:
        c = e["category"]
        cats[c] = cats.get(c, 0) + 1

    print(f"Generated {len(unique)} cross-domain examples")
    print(f"  By category:")
    for c, n in sorted(cats.items()):
        print(f"    {c}: {n}")
    print(f"  Database topics: {sum(len(v) for v in DATABASE_TOPICS.values())}")
    print(f"  Earth science topics: {len(EARTH_SCIENCE_TOPICS)}")
    print(f"  Cross-domain methods: {len(CROSS_DOMAIN_METHODS)}")


if __name__ == "__main__":
    main()
