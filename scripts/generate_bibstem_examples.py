#!/usr/bin/env python3
"""
Generate training data for bibstem/journal queries.

Covers 27 journals with full name → bibstem abbreviation mappings.

Usage:
    python scripts/generate_bibstem_examples.py \
        --output data/datasets/generated/bibstem_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# (bibstem, journal_full_names, topic_nl, topic_abs)
JOURNAL_TOPICS = [
    ("ApJ", ["Astrophysical Journal", "ApJ"], "stellar evolution", "stellar evolution"),
    ("MNRAS", ["Monthly Notices of the Royal Astronomical Society", "MNRAS"], "AGN feedback", "AGN feedback"),
    ("A&A", ["Astronomy and Astrophysics", "A&A"], "chemical abundances", "chemical abundances"),
    ("Nature", ["Nature"], "gravitational waves", "gravitational waves"),
    ("Science", ["Science", "Science magazine"], "exoplanet discovery", "exoplanet"),
    ("PhRvL", ["Physical Review Letters", "PRL"], "neutrino oscillations", "neutrino oscillations"),
    ("PhRvD", ["Physical Review D"], "dark matter candidates", "dark matter"),
    ("AJ", ["Astronomical Journal", "AJ"], "proper motions", "proper motions"),
    ("ApJL", ["Astrophysical Journal Letters", "ApJ Letters"], "fast radio bursts", "fast radio bursts"),
    ("ApJS", ["Astrophysical Journal Supplement Series", "ApJS"], "survey catalogs", "survey catalog"),
    ("JCAP", ["Journal of Cosmology and Astroparticle Physics", "JCAP"], "dark energy", "dark energy"),
    ("PASJ", ["PASJ", "Publications of the Astronomical Society of Japan"], "X-ray binaries", "X-ray binaries"),
    ("SoPh", ["Solar Physics"], "coronal mass ejections", "coronal mass ejections"),
    ("SSRv", ["Space Science Reviews"], "magnetospheric physics", "magnetospheric physics"),
    ("NewAR", ["New Astronomy Reviews"], "galaxy morphology", "galaxy morphology"),
    ("GeoRL", ["Geophysical Research Letters", "GRL"], "atmospheric chemistry", "atmospheric chemistry"),
    ("CQGra", ["Classical and Quantum Gravity"], "black hole mergers", "black hole mergers"),
    ("LRR", ["Living Reviews in Relativity"], "general relativity tests", "general relativity"),
    ("ExA", ["Experimental Astronomy"], "detector technology", "detector technology"),
    ("AsBio", ["Astrobiology"], "habitability", "habitability"),
    ("ARA&A", ["Annual Review of Astronomy and Astrophysics", "ARA&A"], "star formation", "star formation"),
    ("PASP", ["Publications of the Astronomical Society of the Pacific", "PASP"], "photometric calibration", "photometric calibration"),
    ("PhRvC", ["Physical Review C"], "nuclear astrophysics", "nuclear astrophysics"),
    ("NuPhB", ["Nuclear Physics B"], "neutrino mass", "neutrino mass"),
    ("EPJC", ["European Physical Journal C"], "Higgs boson", "Higgs boson"),
    ("Icar", ["Icarus"], "Titan atmosphere", "Titan"),
    ("P&SS", ["Planetary and Space Science"], "Mars geology", "Mars"),
]

NL_TEMPLATES = [
    "papers in {journal} on {topic}",
    "{journal} papers on {topic}",
    "papers published in {journal} about {topic}",
    "{journal} articles on {topic}",
    "publications in {journal} on {topic}",
]

# Multi-abs journals
MULTI_ABS_JOURNALS = [
    ("Icar", "Titan", ["Titan", "atmosphere"]),
    ("P&SS", "Mars", ["Mars", "geology"]),
]


def generate_examples() -> list[dict]:
    examples = []
    for bibstem, names, topic_nl, topic_abs in JOURNAL_TOPICS:
        journal_name = random.choice(names)
        template = random.choice(NL_TEMPLATES)
        nl = template.format(journal=journal_name, topic=topic_nl)

        # Check if multi-abs
        multi = next((m for m in MULTI_ABS_JOURNALS if m[0] == bibstem), None)
        if multi:
            abs_clause = " ".join(f'abs:"{t}"' for t in multi[2])
            query = f'bibstem:"{bibstem}" {abs_clause}'
        else:
            query = f'bibstem:"{bibstem}" abs:"{topic_abs}"'

        examples.append({
            "natural_language": nl,
            "ads_query": query,
            "category": "publication",
        })

    return examples


def main():
    parser = argparse.ArgumentParser(description="Generate bibstem/journal training examples")
    parser.add_argument("--output", type=Path, default=Path("data/datasets/generated/bibstem_examples.json"))
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
    print(f"Generated {len(unique)} bibstem examples ({len(JOURNAL_TOPICS)} journals)")


if __name__ == "__main__":
    main()
