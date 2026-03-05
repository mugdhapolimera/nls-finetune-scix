#!/usr/bin/env python3
"""
Generate training data for miscellaneous fields.

Covers: temporal (entdate:), object:, syntax (NEAR, =author:),
identifier (orcid:), positional (pos()), metrics (mention_count,
credit_count), and doctype:book.

Usage:
    python scripts/generate_misc_field_examples.py \
        --output data/datasets/generated/misc_field_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# --- temporal (entdate:) ---
TEMPORAL = [
    ("new papers published in the last week", "entdate:[NOW-7DAYS TO *]"),
    ("papers added to ADS in the last month", "entdate:[NOW-1MONTH TO NOW]"),
    ('recently indexed papers on gravitational waves', 'entdate:[NOW-7DAYS TO NOW] abs:"gravitational waves"'),
    ('papers added to ADS this week about exoplanets', 'entdate:[NOW-7DAYS TO NOW] abs:"exoplanet"'),
    ('new papers indexed in ADS this month on dark energy', 'entdate:[NOW-1MONTH TO NOW] abs:"dark energy"'),
    ("papers entered into ADS in January 2025", "entdate:[2025-01-01 TO 2025-01-31]"),
    ('recently added articles on galaxy mergers', 'entdate:[NOW-30DAYS TO NOW] abs:"galaxy mergers" doctype:article'),
    ('papers indexed by ADS in the past year on machine learning', 'entdate:[NOW-1YEAR TO NOW] abs:"machine learning"'),
    ('newest ADS entries about fast radio bursts', 'entdate:[NOW-14DAYS TO NOW] abs:"fast radio bursts"'),
]

# --- object: ---
OBJECTS = [
    ("studies of NGC 1275", 'object:"NGC 1275" doctype:article'),
    ("observations of Sagittarius A*", 'object:"Sgr A*"'),
    ("papers about the Orion Nebula", 'object:"Orion Nebula"'),
    ("studies of 3C 273 quasar", 'object:"3C 273" doctype:article'),
    ("papers about the Large Magellanic Cloud", 'object:"LMC"'),
    ("observations of Vega", 'object:"Vega" doctype:article'),
    ("papers about NGC 4486 radio galaxy", 'object:"NGC 4486"'),
    ("studies of the Triangulum Galaxy", 'object:"M33" doctype:article'),
    ("papers about Proxima Centauri b exoplanet", 'object:"Proxima Centauri b"'),
    ("papers on M31 Andromeda galaxy", 'object:"M31"'),
    ("studies of the Crab Nebula", 'object:"Crab Nebula" doctype:article'),
    ("observations of Betelgeuse", 'object:"Betelgeuse"'),
    ("papers about the Whirlpool Galaxy", 'object:"M51" doctype:article'),
    ("studies of Cygnus X-1", 'object:"Cyg X-1"'),
]

# --- syntax (NEAR, =author:) ---
SYNTAX = [
    ("papers where dark matter and annihilation appear close together in the abstract",
     'abs:("dark matter" NEAR5 annihilation)'),
    ("articles with planet and habitability near each other in title",
     "title:(planet NEAR3 habitability)"),
    ("papers with supernova and nucleosynthesis within 5 words in abstract",
     "abs:(supernova NEAR5 nucleosynthesis)"),
    ("articles with machine learning and classification close together in full text",
     'full:("machine learning" NEAR5 classification)'),
    ("papers where accretion and jet appear near each other in the abstract",
     "abs:(accretion NEAR3 jet)"),
    ('exact match for author Smith J without synonyms',
     '=author:"Smith, J"'),
    ('find papers by exactly Wang, Y without name variants',
     '=author:"Wang, Y" doctype:article'),
    ('exact author search for Li, H on stellar physics',
     '=author:"Li, H" abs:"stellar physics"'),
    ('papers by exactly Brown, T. M. without synonym expansion',
     '=author:"Brown, T. M." doctype:article'),
    ('exact match for Kim, S in galaxy evolution papers',
     '=author:"Kim, S" abs:"galaxy evolution" doctype:article'),
]

# --- identifier (orcid:) ---
IDENTIFIERS = [
    ("papers by ORCID 0000-0002-1825-0097", "orcid:0000-0002-1825-0097"),
    ("find articles by the author with ORCID 0000-0003-1234-5678", "orcid:0000-0003-1234-5678 doctype:article"),
    ("look up publications for ORCID 0000-0002-9876-5432", "orcid:0000-0002-9876-5432"),
    ("refereed papers associated with ORCID 0000-0001-2345-6789", "orcid:0000-0001-2345-6789 property:refereed"),
]

# --- positional (pos()) ---
POSITIONAL = [
    ('papers where the first author is affiliated with MIT', 'pos(aff:"MIT", 1)'),
    ('papers where the first author is from the Astronomical Observatory of Padova', 'pos(aff:"Padova", 1)'),
    ('papers where the second author is affiliated with NASA Ames', 'pos(aff:"NASA Ames", 2)'),
]

# --- metrics (mention_count, credit_count) ---
METRICS = [
    ("papers mentioning many software packages", "mention_count:[5 TO *]"),
    ("papers that mention more than 10 data or software records", "mention_count:[10 TO *]"),
    ("software records credited by many papers", "credit_count:[20 TO *] doctype:software"),
    ("data records that have received at least 50 credits", "credit_count:[50 TO *]"),
    ("highly mentioned software packages in astronomy", "mention_count:[50 TO *] doctype:software collection:astronomy"),
    ("software credited in at least 5 papers", "credit_count:[5 TO *] doctype:software"),
    ("papers that frequently mention specific software tools", "mention_count:[20 TO *] doctype:article"),
    ('highly credited data analysis software in astrophysics', 'credit_count:[30 TO *] doctype:software abs:"data analysis"'),
]

# --- second_order operators ---
SECOND_ORDER = [
    ("papers that cite the astropy software package", "citations(bibcode:2013A&A...558A..33A)"),
    ("software packages used in exoplanet transit studies", 'doctype:software references(abs:"exoplanet transit")'),
    ("what papers does the foundational dark energy paper reference", 'references(abs:"dark energy" useful(abs:"dark energy"))'),
    ("papers referenced by galaxy formation simulations", 'references(abs:"galaxy formation simulations")'),
    ("reference list of neutron star merger research", 'references(abs:"neutron star merger")'),
    ("what sources do papers on cosmic ray propagation cite", 'references(abs:"cosmic ray propagation")'),
    ("papers referenced in exoplanet transit studies", 'references(abs:"exoplanet transit")'),
    ("bibliography of stellar mass black hole papers", 'references(abs:"stellar mass black hole")'),
    ("what references are used in CMB anisotropy studies", 'references(abs:"CMB anisotropy")'),
    ("papers cited by magnetar emission models", 'references(abs:"magnetar emission")'),
    ("reference papers used in baryon acoustic oscillation research", 'references(abs:"baryon acoustic oscillation")'),
    ("what does the literature on gravitational lensing reference", 'references(abs:"gravitational lensing")'),
]

# --- similar() operator ---
SIMILAR_OP = [
    ("papers similar to work on fast radio burst progenitors", 'similar(abs:"fast radio burst progenitors")'),
    ("find articles related to research on exoplanet atmospheres", 'similar(abs:"exoplanet atmospheres")'),
    ("papers like studies of galaxy cluster mass functions", 'similar(abs:"galaxy cluster mass function")'),
    ('related work on magnetohydrodynamic simulations of the solar corona', 'similar(abs:"magnetohydrodynamic simulations" abs:"solar corona")'),
    ("research similar to tidal disruption event light curves", 'similar(abs:"tidal disruption event" abs:"light curve")'),
    ("papers related to brown dwarf atmospheric models", 'similar(abs:"brown dwarf" abs:"atmospheric models")'),
    ("find similar papers on primordial nucleosynthesis constraints", 'similar(abs:"primordial nucleosynthesis")'),
    ('related articles on gravitational wave template banks', 'similar(abs:"gravitational wave" abs:"template bank")'),
    ("papers similar to work on the epoch of reionization", 'similar(abs:"epoch of reionization")'),
    ("find related work on Bayesian methods in cosmology", 'similar(abs:"Bayesian methods" abs:"cosmology")'),
]

# --- collection (additional) ---
COLLECTION_EXTRA = [
    ("physics papers on quantum entanglement", 'abs:"quantum entanglement" database:physics'),
    ("astronomy articles on gravitational wave detection", 'abs:"gravitational wave detection" database:astronomy doctype:article'),
    ("general science papers on climate change and astronomy", 'abs:"climate change" database:general'),
    ("physics database papers on superconductivity", 'abs:"superconductivity" database:physics'),
]

# --- doctype:book ---
DOCTYPE_EXTRA = [
    ("books about general relativity", 'abs:"general relativity" doctype:book'),
]

# --- content (ack:) ---
CONTENT_EXTRA = [
    ("papers that acknowledge the James Webb Space Telescope in their acknowledgments", 'ack:"James Webb Space Telescope"'),
]


def generate_examples() -> list[dict]:
    examples = []

    for nl, query in TEMPORAL:
        examples.append({"natural_language": nl, "ads_query": query, "category": "temporal"})
    for nl, query in OBJECTS:
        examples.append({"natural_language": nl, "ads_query": query, "category": "object"})
    for nl, query in SYNTAX:
        examples.append({"natural_language": nl, "ads_query": query, "category": "syntax"})
    for nl, query in IDENTIFIERS:
        examples.append({"natural_language": nl, "ads_query": query, "category": "identifier"})
    for nl, query in POSITIONAL:
        examples.append({"natural_language": nl, "ads_query": query, "category": "positional"})
    for nl, query in METRICS:
        examples.append({"natural_language": nl, "ads_query": query, "category": "metrics"})
    for nl, query in SECOND_ORDER:
        examples.append({"natural_language": nl, "ads_query": query, "category": "second_order"})
    for nl, query in SIMILAR_OP:
        examples.append({"natural_language": nl, "ads_query": query, "category": "operator"})
    for nl, query in COLLECTION_EXTRA:
        examples.append({"natural_language": nl, "ads_query": query, "category": "collection"})
    for nl, query in DOCTYPE_EXTRA:
        examples.append({"natural_language": nl, "ads_query": query, "category": "doctype"})
    for nl, query in CONTENT_EXTRA:
        examples.append({"natural_language": nl, "ads_query": query, "category": "content"})

    return examples


def main():
    parser = argparse.ArgumentParser(description="Generate misc field training examples")
    parser.add_argument("--output", type=Path, default=Path("data/datasets/generated/misc_field_examples.json"))
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

    cats = {}
    for e in unique:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    print(f"Generated {len(unique)} misc field examples")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
