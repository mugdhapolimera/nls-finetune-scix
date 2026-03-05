#!/usr/bin/env python3
"""
Generate training data for data archive queries (data: field).

Covers: NED, VizieR, IRSA, HEASARC, MAST, PDS, NExScI, SIMBAD, ESO,
XMM, KOA, CXO, Herschel, ESA, TNS.

Usage:
    python scripts/generate_data_archive_examples.py \
        --output data/datasets/generated/data_archive_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# (archive, topic_nl, topic_abs)
DATA_ARCHIVE_PAIRS = [
    ("NED", "galaxy cluster", "galaxy cluster"),
    ("NED", "extragalactic distance", "extragalactic distance"),
    ("NED", "galaxy redshift", "galaxy redshift"),
    ("VizieR", "stellar photometry", "stellar photometry"),
    ("VizieR", "variable stars", "variable stars"),
    ("VizieR", "stellar catalog", "stellar catalog"),
    ("IRSA", "infrared survey", "infrared survey"),
    ("IRSA", "dust emission", "dust emission"),
    ("IRSA", "infrared photometry", "infrared photometry"),
    ("HEASARC", "X-ray binary", "X-ray binary"),
    ("HEASARC", "gamma-ray burst", "gamma-ray burst"),
    ("HEASARC", "X-ray source", "X-ray source"),
    ("MAST", "Hubble", "Hubble"),
    ("MAST", "planetary nebulae", "planetary nebulae"),
    ("MAST", "ultraviolet spectroscopy", "ultraviolet spectroscopy"),
    ("PDS", "Mars surface", "Mars surface"),
    ("PDS", "asteroid spectroscopy", "asteroid spectroscopy"),
    ("PDS", "lunar geology", "lunar geology"),
    ("NExScI", "exoplanet characterization", "exoplanet characterization"),
    ("NExScI", "transit photometry", "transit photometry"),
    ("SIMBAD", "globular clusters", "globular clusters"),
    ("SIMBAD", "stellar classification", "stellar classification"),
    ("SIMBAD", "binary stars", "binary stars"),
    ("ESO", "VLT spectroscopy", "VLT spectroscopy"),
    ("ESO", "galaxy morphology", "galaxy morphology"),
    ("XMM", "active galactic nuclei", "active galactic nuclei"),
    ("XMM", "galaxy cluster", "galaxy cluster"),
    ("KOA", "brown dwarfs", "brown dwarfs"),
    ("CXO", "Chandra X-ray", "Chandra X-ray"),
    ("CXO", "supernova remnant", "supernova remnant"),
    ("Herschel", "far-infrared", "far-infrared"),
    ("Herschel", "star formation", "star formation"),
    ("ESA", "Gaia astrometry", "Gaia astrometry"),
    ("TNS", "transient", "transient"),
]

NL_TEMPLATES = [
    "{topic} papers with {archive} data links",
    "papers with {archive} data on {topic}",
    "{topic} papers linked to {archive}",
    "papers using {archive} archive data on {topic}",
    "articles linked to {archive} catalogs about {topic}",
    "{archive} observations of {topic}",
]


def generate_examples() -> list[dict]:
    examples = []
    for archive, topic_nl, topic_abs in DATA_ARCHIVE_PAIRS:
        template = random.choice(NL_TEMPLATES)
        nl = template.format(topic=topic_nl, archive=archive)
        query = f'abs:"{topic_abs}" data:{archive}'
        if random.random() < 0.3:
            query += " doctype:article"
        examples.append({
            "natural_language": nl,
            "ads_query": query,
            "category": "data",
        })
    return examples


def main():
    parser = argparse.ArgumentParser(description="Generate data archive training examples")
    parser.add_argument("--output", type=Path, default=Path("data/datasets/generated/data_archive_examples.json"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    examples = generate_examples()
    seen: set[str] = set()
    unique = [e for e in examples if not (e["natural_language"].lower().strip() in seen or seen.add(e["natural_language"].lower().strip()))]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(unique)} data archive examples")


if __name__ == "__main__":
    main()
