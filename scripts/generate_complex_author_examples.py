#!/usr/bin/env python3
"""
Generate training data for complex author name queries.

Creates NL-query pairs for authors with hyphens, particles, apostrophes, and
accented characters. Training data uses exact author names — runtime wildcarding
is handled deterministically by assembler.py's _wildcard_complex_author().

This addresses the "Hyphenated / Complex Author Names" gap (Issue Type 5) from
the SciX vs Google Scholar gap analysis.

Usage:
    python scripts/generate_complex_author_examples.py \
        --output data/datasets/generated/complex_author_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Complex author name seed data
# Each entry: (display_name, ads_format, topics, is_first_author_examples)
# ads_format: how the name appears in ADS queries (accents stripped, etc.)
# ---------------------------------------------------------------------------
COMPLEX_AUTHORS = [
    {
        "display": "de Groot-Hedlin",
        "ads_name": "de Groot-Hedlin",
        "topics": [("magnetotellurics", "magnetotelluric"), ("seismic", "seismic")],
        "type": "hyphenated_particle",
    },
    {
        "display": "van der Waals",
        "ads_name": "van der Waals",
        "topics": [("equation of state", "equation of state"), ("intermolecular forces", "intermolecular")],
        "type": "particle",
        "year_pool": [1970, 1975, 1980, 1985, 1990],
    },
    {
        "display": "García-Pérez",
        "ads_name": "Garcia Perez",
        "topics": [("stellar atmospheres", "stellar atmosphere"), ("chemical abundances", "chemical abundance")],
        "type": "accented_hyphenated",
    },
    {
        "display": "López-Morales",
        "ads_name": "Lopez-Morales",
        "topics": [("exoplanets", "exoplanet"), ("transiting planets", "transit")],
        "type": "accented_hyphenated",
    },
    {
        "display": "Martín-Pintado",
        "ads_name": "Martin-Pintado",
        "topics": [("millimeter observations", "millimeter"), ("molecular clouds", "molecular cloud")],
        "type": "accented_hyphenated",
    },
    {
        "display": "Ruiz-Lapuente",
        "ads_name": "Ruiz-Lapuente",
        "topics": [("Type Ia supernovae", "Type Ia supernova"), ("supernova remnants", "supernova remnant")],
        "type": "hyphenated",
    },
    {
        "display": "de la Fuente Marcos",
        "ads_name": "de la Fuente Marcos",
        "topics": [("asteroid dynamics", "asteroid"), ("near-Earth objects", "near-Earth")],
        "type": "particle",
    },
    {
        "display": "El-Badry",
        "ads_name": "El-Badry",
        "topics": [("binary stars", "binary"), ("stellar companions", "companion")],
        "type": "short_prefix_hyphen",
    },
    {
        "display": "van de Hulst",
        "ads_name": "van de Hulst",
        "topics": [("scattering", "scattering"), ("interstellar medium", "interstellar")],
        "type": "particle",
        "year_pool": [1957, 1970, 1975, 1981, 1990],
    },
    {
        "display": "de Gregorio-Monsalvo",
        "ads_name": "de Gregorio-Monsalvo",
        "topics": [("protoplanetary disks", "protoplanetary disk"), ("ALMA observations", "ALMA")],
        "type": "particle_hyphenated",
    },
    {
        "display": "Pérez-González",
        "ads_name": "Perez-Gonzalez",
        "topics": [("high-redshift galaxies", ["high-redshift", "galaxy"]), ("galaxy evolution", ["galaxy evolution"])],
        "type": "accented_hyphenated",
    },
    {
        "display": "Le Floc'h",
        "ads_name": "Le Floc'h",
        "topics": [("infrared luminosity function", ["infrared", "luminosity function"]), ("galaxy surveys", ["galaxy survey"])],
        "type": "apostrophe",
    },
    # Additional complex authors for variety
    {
        "display": "García-Burillo",
        "ads_name": "Garcia-Burillo",
        "topics": [("AGN feeding", "AGN"), ("molecular gas", "molecular gas")],
        "type": "accented_hyphenated",
    },
    {
        "display": "Ortiz-León",
        "ads_name": "Ortiz-Leon",
        "topics": [("VLBI astrometry", "VLBI"), ("star-forming regions", "star-forming region")],
        "type": "accented_hyphenated",
    },
    {
        "display": "al-Naimiy",
        "ads_name": "al-Naimiy",
        "topics": [("eclipsing binaries", "eclipsing binary"), ("limb darkening", "limb darkening")],
        "type": "short_prefix_hyphen",
    },
    {
        "display": "O'Brien",
        "ads_name": "O'Brien",
        "topics": [("stellar evolution", "stellar evolution"), ("nova eruptions", "nova")],
        "type": "apostrophe",
    },
    {
        "display": "O'Connell",
        "ads_name": "O'Connell",
        "topics": [("UV astronomy", "ultraviolet"), ("galaxy photometry", "galaxy photometry")],
        "type": "apostrophe",
    },
    {
        "display": "van den Bergh",
        "ads_name": "van den Bergh",
        "topics": [("galaxy classification", "galaxy classification"), ("supernova rates", "supernova rate")],
        "type": "particle",
        "year_pool": [1990, 1995, 2000, 2005, 2010],
    },
    {
        "display": "Di Matteo",
        "ads_name": "Di Matteo",
        "topics": [("black hole mergers", "black hole merger"), ("galaxy simulations", "galaxy simulation")],
        "type": "particle",
    },
    {
        "display": "Saint-Hilaire",
        "ads_name": "Saint-Hilaire",
        "topics": [("solar flares", "solar flare"), ("hard X-rays", "hard X-ray")],
        "type": "hyphenated",
    },
]

# NL templates for author + topic
AUTHOR_TOPIC_TEMPLATES = [
    "papers by {display} on {topic_display}",
    "{display} {topic_display} papers",
    "{display} work on {topic_display}",
    "research by {display} about {topic_display}",
    "find papers by {display} on {topic_display}",
    "{display} papers about {topic_display}",
]

# NL templates for first-author
FIRST_AUTHOR_TEMPLATES = [
    "papers by {display} as first author",
    "{display} first author papers",
    "first author papers by {display}",
]

# NL templates for author + year
AUTHOR_YEAR_TEMPLATES = [
    "recent publications by {display}",
    "papers by {display} from {year}",
    "{display} {year} papers",
]

# NL templates for multi-author
MULTI_AUTHOR_TEMPLATES = [
    "{display1} and {display2} papers on {topic_display}",
    "papers by {display1} and {display2} about {topic_display}",
]


def generate_examples() -> list[dict]:
    """Generate all complex author name training examples."""
    examples: list[dict] = []

    for author in COMPLEX_AUTHORS:
        display = author["display"]
        ads_name = author["ads_name"]

        # --- Author + topic examples ---
        for topic_display, topic_abs in author["topics"]:
            template = random.choice(AUTHOR_TOPIC_TEMPLATES)
            nl = template.format(display=display, topic_display=topic_display)
            # topic_abs can be a string or list of strings
            if isinstance(topic_abs, list):
                abs_clause = " ".join(f'abs:"{t}"' for t in topic_abs)
            else:
                abs_clause = f'abs:"{topic_abs}"'
            query = f'author:"{ads_name}" {abs_clause}'
            examples.append({
                "natural_language": nl,
                "ads_query": query,
                "category": "author",
            })

        # --- First-author example (one per author) ---
        template = random.choice(FIRST_AUTHOR_TEMPLATES)
        nl = template.format(display=display)
        query = f'author:"^{ads_name}" doctype:article'
        examples.append({
            "natural_language": nl,
            "ads_query": query,
            "category": "first_author",
        })

        # --- Author + year example (one per author) ---
        year_pool = author.get("year_pool", [2018, 2019, 2020, 2021, 2022, 2023, 2024])
        year = random.choice(year_pool)
        template = random.choice(AUTHOR_YEAR_TEMPLATES)
        nl = template.format(display=display, year=year)
        if "recent" in template:
            query = f'author:"{ads_name}" pubdate:[2020 TO *] doctype:article'
        else:
            query = f'author:"{ads_name}" year:{year} doctype:article'
        examples.append({
            "natural_language": nl,
            "ads_query": query,
            "category": "author",
        })

    # --- Multi-author examples ---
    # Pairs of (author_dict_or_simple, author_dict_or_simple, topic_display, abs_terms)
    multi_author_specs = [
        # Complex + simple author (real collaborators)
        (COMPLEX_AUTHORS[0]["display"], COMPLEX_AUTHORS[0]["ads_name"],
         "Constable", "Constable",
         "magnetotellurics", ["magnetotelluric"]),
        (COMPLEX_AUTHORS[7]["display"], COMPLEX_AUTHORS[7]["ads_name"],
         "Rix", "Rix",
         "binary stars", ["binary"]),
        # Complex + simple author (matches gold: "Pinte and de Gregorio-Monsalvo")
        ("Pinte", "Pinte",
         COMPLEX_AUTHORS[9]["display"], COMPLEX_AUTHORS[9]["ads_name"],
         "protoplanetary disks", ["protoplanetary disk"]),
    ]
    for d1, ads1, d2, ads2, topic_display, abs_terms in multi_author_specs:
        template = random.choice(MULTI_AUTHOR_TEMPLATES)
        nl = template.format(display1=d1, display2=d2, topic_display=topic_display)
        abs_clause = " ".join(f'abs:"{t}"' for t in abs_terms)
        query = f'author:"{ads1}" author:"{ads2}" {abs_clause}'
        examples.append({
            "natural_language": nl,
            "ads_query": query,
            "category": "author",
        })

    return examples


def main():
    parser = argparse.ArgumentParser(
        description="Generate complex author name training examples"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/datasets/generated/complex_author_examples.json"),
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
    types = {}
    for a in COMPLEX_AUTHORS:
        t = a["type"]
        types[t] = types.get(t, 0) + 1

    print(f"Generated {len(unique)} complex author examples")
    print(f"  Authors covered: {len(COMPLEX_AUTHORS)}")
    print(f"  Author types:")
    for t, c in sorted(types.items()):
        print(f"    {t}: {c}")


if __name__ == "__main__":
    main()
