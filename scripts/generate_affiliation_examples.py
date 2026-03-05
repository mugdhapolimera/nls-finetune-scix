#!/usr/bin/env python3
"""
Generate training data for affiliation/institution queries.

Covers inst:, aff:, affil:, and (inst: OR aff:) patterns.

Usage:
    python scripts/generate_affiliation_examples.py \
        --output data/datasets/generated/affiliation_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# (inst_code, display_names, topic_nl, topic_abs, query_pattern)
# query_pattern: "inst" for simple inst:, "inst_or_aff" for (inst: OR aff:), "affil" for affil:
INSTITUTIONS = [
    ("MIT", ["MIT", "Massachusetts Institute of Technology"], "gravitational waves", "gravitational waves", "inst"),
    ("CfA", ["Harvard-Smithsonian Center for Astrophysics", "CfA"], None, None, "inst"),
    ("Caltech", ["Caltech", "California Institute of Technology"], "exoplanets", "exoplanets", "inst"),
    ("STScI", ["Space Telescope Science Institute", "STScI"], None, None, "inst"),
    ("ESO", ["European Southern Observatory", "ESO"], "extragalactic astronomy", "extragalactic", "inst"),
    ("MPA", ["Max Planck Institute for Astrophysics"], None, None, "inst"),
    ("Princeton U", ["Princeton", "Princeton University"], "cosmology", "cosmology", "inst"),
    ("JPL", ["Jet Propulsion Laboratory", "JPL"], "Mars rovers", "Mars rover", "inst"),
    ("Stanford U", ["Stanford", "Stanford University"], "particle physics", "particle physics", "inst"),
    ("NOAO", ["National Optical Astronomy Observatory", "NOAO"], None, None, "inst"),
    ("GSFC", ["Goddard Space Flight Center", "NASA Goddard"], "X-ray astronomy", "X-ray", "inst"),
    ("NRAO", ["National Radio Astronomy Observatory", "NRAO"], None, None, "inst"),
    ("IAS", ["Institute for Advanced Study"], "string theory", "string theory", "inst"),
    ("NAOJ", ["National Astronomical Observatory of Japan", "NAOJ"], None, None, "inst"),
    ("STScI", ["Space Telescope Science Institute"], "Hubble observations", "Hubble", "inst"),
    ("IPAC", ["IPAC"], "infrared surveys", "infrared survey", "inst"),
    # inst_or_aff patterns
    ("U Tokyo", ["University of Tokyo"], "neutrinos", "neutrinos", "inst_or_aff"),
    ("CERN", ["CERN"], "dark matter detection", "dark matter detection", "inst_or_aff"),
    ("U Cambridge", ["University of Cambridge", "Cambridge"], "quasars", "quasars", "inst_or_aff"),
    ("IUCAA", ["Inter-University Centre for Astronomy and Astrophysics", "IUCAA"], None, None, "inst_or_aff"),
    ("U Hawaii", ["University of Hawaii"], "telescope", "telescope", "inst_or_aff"),
]

# affil: examples (fuzzy, non-curated)
AFFIL_EXAMPLES = [
    ("NASA Goddard", "gamma-ray bursts", "gamma-ray burst"),
    ("Berkeley", "supernovae", "supernova"),
]

# Multi-institution
MULTI_INST = [
    (["MIT", "Caltech"], "LIGO", "LIGO"),
    (["ESO", "ESA"], "space missions", "space mission"),
]

NL_TEMPLATES_SIMPLE = [
    "papers from {name}",
    "publications from {name}",
    "papers from the {name}",
    "research from {name}",
]

NL_TEMPLATES_TOPIC = [
    "papers from {name} on {topic}",
    "publications from {name} about {topic}",
    "research from {name} on {topic}",
    "{name} papers on {topic}",
]


def generate_examples() -> list[dict]:
    examples = []

    for inst_code, names, topic_nl, topic_abs, pattern in INSTITUTIONS:
        name = random.choice(names)

        if topic_nl:
            template = random.choice(NL_TEMPLATES_TOPIC)
            nl = template.format(name=name, topic=topic_nl)
        else:
            template = random.choice(NL_TEMPLATES_SIMPLE)
            nl = template.format(name=name)

        if pattern == "inst":
            if topic_abs:
                query = f'inst:"{inst_code}" abs:"{topic_abs}"'
            else:
                query = f'inst:"{inst_code}"'
        elif pattern == "inst_or_aff":
            aff_name = names[0]  # Use full name for aff:
            if topic_abs:
                query = f'(inst:"{inst_code}" OR aff:"{aff_name}") abs:"{topic_abs}"'
            else:
                query = f'(inst:"{inst_code}" OR aff:"{aff_name}")'

        if random.random() < 0.2:
            query += " property:refereed"

        examples.append({"natural_language": nl, "ads_query": query, "category": "affiliation"})

    # affil: examples
    for affil_name, topic_nl, topic_abs in AFFIL_EXAMPLES:
        nl = f"papers from any institution matching {affil_name} on {topic_nl}"
        query = f'affil:"{affil_name}" abs:"{topic_abs}"'
        examples.append({"natural_language": nl, "ads_query": query, "category": "affiliation"})

    # Multi-inst
    for insts, topic_nl, topic_abs in MULTI_INST:
        inst_clause = " ".join(f'inst:"{i}"' for i in insts)
        nl = f"joint {' and '.join(insts)} publications on {topic_nl}"
        query = f'{inst_clause} abs:"{topic_abs}"'
        examples.append({"natural_language": nl, "ads_query": query, "category": "affiliation"})

    return examples


def main():
    parser = argparse.ArgumentParser(description="Generate affiliation training examples")
    parser.add_argument("--output", type=Path, default=Path("data/datasets/generated/affiliation_examples.json"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    examples = generate_examples()
    seen: set[str] = set()
    unique = []
    for e in examples:
        key = e["natural_language"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(e)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(unique)} affiliation examples")


if __name__ == "__main__":
    main()
