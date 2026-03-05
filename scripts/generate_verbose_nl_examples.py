#!/usr/bin/env python3
"""
Generate training data for verbose natural language → focused query distillation.

Creates NL-query pairs where the natural language is a long, descriptive
sentence and the query distills it into focused multi-abs: terms. This teaches
the model to extract the essential keywords from wordy descriptions.

This addresses the "Multi-Keyword Precision for Niche Topics" gap (Issue Type 6)
from the SciX vs Google Scholar gap analysis.

Usage:
    python scripts/generate_verbose_nl_examples.py \
        --output data/datasets/generated/verbose_nl_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Each entry: (verbose_nl, abs_terms, optional extra filters)
# The verbose NL should be >80 chars and conversational/descriptive.
# The abs_terms are the distilled keywords.
# ---------------------------------------------------------------------------
VERBOSE_PAIRS = [
    # Geophysics / Earth science
    {
        "nl": "I'm looking for papers about using high-impedance preamplifiers to measure electric fields in snow and ice for magnetotelluric surveys",
        "abs_terms": ["preamplifier", "electric field", "magnetotelluric"],
    },
    {
        "nl": "research on two-dimensional magnetotelluric inversion using the rapid relaxation inverse method",
        "abs_terms": ["magnetotelluric", "inversion", "2D", "RRI"],
    },
    {
        "nl": "papers about using regularization methods for solving ill-posed inverse problems in geophysics",
        "abs_terms": ["regularization", "inverse problem", "geophysics"],
    },
    {
        "nl": "investigations of the crustal structure beneath the Himalayan orogen using receiver function analysis and joint inversion with surface wave data",
        "abs_terms": ["receiver function", "surface wave", "Himalaya", "crustal structure"],
    },
    {
        "nl": "how do scientists use the Occam inversion approach for smooth models from magnetotelluric sounding data",
        "abs_terms": ["Occam", "inversion", "magnetotelluric"],
    },
    {
        "nl": "experimental measurements of the thermal conductivity of iron alloys at extreme pressures relevant to Earth's core",
        "abs_terms": ["thermal conductivity", "iron", "high pressure", "core"],
    },
    # Astrophysics
    {
        "nl": "studies on the application of machine learning techniques to classify galaxy morphologies in large photometric surveys",
        "abs_terms": ["machine learning", "galaxy morphology", "classification"],
        "extra": "doctype:article",
    },
    {
        "nl": "what papers discuss the effects of stellar winds on the habitability of exoplanets orbiting M dwarf stars",
        "abs_terms": ["stellar wind", "habitability", "M dwarf"],
        "extra": "doctype:article",
    },
    {
        "nl": "I want to find studies comparing different methods for estimating photometric redshifts of galaxies using deep learning",
        "abs_terms": ["photometric redshift", "deep learning"],
        "extra": "doctype:article",
    },
    {
        "nl": "research about the correlation between supermassive black hole mass and host galaxy bulge velocity dispersion",
        "abs_terms": ["black hole mass", "velocity dispersion", "bulge"],
        "extra": "doctype:article",
    },
    {
        "nl": "papers on how coronal mass ejections interact with planetary magnetospheres and what effects they have on upper atmospheres",
        "abs_terms": ["coronal mass ejection", "magnetosphere", "upper atmosphere"],
    },
    {
        "nl": "observations of quasi-periodic oscillations in the X-ray light curves of accreting neutron stars in low-mass X-ray binaries",
        "abs_terms": ["quasi-periodic oscillation", "neutron star", "X-ray binary"],
    },
    {
        "nl": "studies examining the role of turbulence in the process of star formation within giant molecular clouds",
        "abs_terms": ["turbulence", "star formation", "molecular cloud"],
    },
    {
        "nl": "papers discussing the systematic uncertainties in Type Ia supernova distance measurements for cosmological parameter estimation",
        "abs_terms": ["Type Ia supernova", "systematic", "distance", "cosmological"],
    },
    {
        "nl": "can you find research on numerical simulations of binary neutron star mergers and their gravitational wave signatures",
        "abs_terms": ["binary neutron star", "merger", "gravitational wave", "simulation"],
    },
    # Additional topics for scaling
    {
        "nl": "I'm interested in papers that describe methods for detecting and characterizing exoplanet atmospheres using transmission spectroscopy during transit events",
        "abs_terms": ["exoplanet", "atmosphere", "transmission spectroscopy", "transit"],
    },
    {
        "nl": "what research has been done on the formation of supermassive black holes in the early universe through direct collapse of pristine gas clouds",
        "abs_terms": ["supermassive black hole", "formation", "direct collapse", "early universe"],
    },
    {
        "nl": "papers about how the circumgalactic medium around galaxies is enriched with metals through galactic winds and outflows from star formation",
        "abs_terms": ["circumgalactic medium", "metal enrichment", "galactic wind", "outflow"],
    },
    {
        "nl": "studies that use weak gravitational lensing measurements to constrain the total matter content and distribution in galaxy clusters",
        "abs_terms": ["weak lensing", "galaxy cluster", "mass distribution"],
    },
    {
        "nl": "I want to find work on reconstructing the cosmic star formation rate density across redshift using ultraviolet and infrared galaxy surveys",
        "abs_terms": ["star formation rate", "cosmic", "redshift", "ultraviolet", "infrared"],
    },
    {
        "nl": "research examining the effects of magnetic fields on the fragmentation of molecular cloud cores during the early stages of protostellar collapse",
        "abs_terms": ["magnetic field", "fragmentation", "molecular cloud", "protostellar collapse"],
    },
    {
        "nl": "papers investigating the chemical evolution of the Milky Way disk using detailed abundance patterns from high-resolution spectroscopic surveys",
        "abs_terms": ["chemical evolution", "Milky Way", "abundance", "spectroscopic survey"],
    },
    {
        "nl": "how do scientists model the accretion of material onto compact objects in X-ray binaries and what role does the magnetic field play",
        "abs_terms": ["accretion", "compact object", "X-ray binary", "magnetic field"],
    },
    {
        "nl": "studies of the dynamical evolution of globular clusters and the role of two-body relaxation in driving mass segregation",
        "abs_terms": ["globular cluster", "dynamical evolution", "mass segregation"],
    },
    {
        "nl": "I'm looking for theoretical predictions of the gravitational wave background from the population of unresolved compact binary mergers",
        "abs_terms": ["gravitational wave background", "compact binary", "merger"],
    },
    {
        "nl": "what observations constrain the epoch of reionization and how do Lyman-alpha emitting galaxies help trace the ionization state of the intergalactic medium",
        "abs_terms": ["reionization", "Lyman-alpha", "intergalactic medium", "ionization"],
    },
    {
        "nl": "papers about measuring the Hubble constant using gravitational wave standard sirens from neutron star mergers with electromagnetic counterparts",
        "abs_terms": ["Hubble constant", "standard siren", "gravitational wave", "neutron star merger"],
    },
    {
        "nl": "research on how dust grains grow in protoplanetary disks through coagulation and how this relates to the formation of planetesimals",
        "abs_terms": ["dust grain", "protoplanetary disk", "coagulation", "planetesimal"],
    },
    {
        "nl": "studies analyzing the impact of active galactic nuclei feedback on the suppression of star formation in massive elliptical galaxies",
        "abs_terms": ["AGN feedback", "star formation", "quenching", "elliptical galaxy"],
    },
    {
        "nl": "papers about using asteroseismology to determine the internal structure and evolutionary state of red giant stars",
        "abs_terms": ["asteroseismology", "red giant", "internal structure"],
    },
]

# Variation templates: rephrase the same query differently
REPHRASE_PREFIXES = [
    "",                                    # Use NL as-is
    "find me ",                            # Prepend casual prefix
    "I need ",                             # Prepend need
    "search for ",                         # Prepend search
    "can you look up ",                    # Prepend lookup
]


def _build_query(entry: dict) -> str:
    """Build the ADS query from abs terms + optional extra filters."""
    parts = [f'abs:"{t}"' for t in entry["abs_terms"]]
    if entry.get("extra"):
        parts.append(entry["extra"])
    return " ".join(parts)


def generate_examples() -> list[dict]:
    """Generate all verbose NL training examples."""
    examples: list[dict] = []

    for entry in VERBOSE_PAIRS:
        query = _build_query(entry)

        # Primary NL (as written)
        examples.append({
            "natural_language": entry["nl"],
            "ads_query": query,
            "category": "compound",
        })

        # One rephrased variation
        prefix = random.choice([p for p in REPHRASE_PREFIXES if p])
        nl_lower = entry["nl"][0].lower() + entry["nl"][1:]
        # Strip leading "I'm looking for", "I want to find", etc. before adding prefix
        for strip_prefix in ["i'm looking for ", "i want to find ", "can you find ",
                             "i need ", "find me ", "search for ", "can you look up "]:
            if nl_lower.startswith(strip_prefix):
                nl_lower = nl_lower[len(strip_prefix):]
                break
        rephrased = prefix + nl_lower
        if rephrased != entry["nl"].lower():
            examples.append({
                "natural_language": rephrased,
                "ads_query": query,
                "category": "compound",
            })

    return examples


def main():
    parser = argparse.ArgumentParser(
        description="Generate verbose NL → focused query training examples"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/datasets/generated/verbose_nl_examples.json"),
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

    print(f"Generated {len(unique)} verbose NL examples")
    print(f"  Seed pairs: {len(VERBOSE_PAIRS)}")
    print(f"  Avg NL length: {sum(len(e['natural_language']) for e in unique) / len(unique):.0f} chars")


if __name__ == "__main__":
    main()
