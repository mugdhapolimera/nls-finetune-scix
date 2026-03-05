#!/usr/bin/env python3
"""
Generate training data from patterns found in ADS/SciX blog posts.

Covers gap patterns not in other generation scripts:
- Nested second-order operators (trending(useful(...)), reviews(useful(...)), etc.)
- similar() with entdate: temporal filters
- property:(...) multi-value syntax
- bibstem: wildcards and multi-bibstem OR
- docs(library/...) patterns
- full: field for instrument/identifier searches
- Additional data-linking patterns (property:data, citations(doctype:software))
- Earth science cross-domain patterns with collection:earthscience

Source: Blog posts from adsabs.github.io/_includes/_blogcontent/
Reference: data/reference/blog_query_examples.md

Usage:
    python scripts/generate_blog_examples.py \
        --output data/datasets/generated/blog_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Nested second-order operators
# ---------------------------------------------------------------------------
NESTED_OPERATORS = [
    # trending(useful(...))
    ("trending useful papers on exoplanet atmospheres",
     'trending(useful(abs:"exoplanet atmospheres"))'),
    ("what are the trending seminal papers in stellar spectroscopy",
     'trending(useful(abs:"stellar spectroscopy"))'),
    ("trending key papers on galaxy evolution",
     'trending(useful(abs:"galaxy evolution"))'),
    ("trending important papers on dark matter detection",
     'trending(useful(abs:"dark matter detection"))'),
    ("currently popular foundational papers on gravitational lensing",
     'trending(useful(abs:"gravitational lensing"))'),
    # trending(useful(author:...))
    ("what trending papers cite the key works by Riess",
     'trending(useful(author:"^Riess"))'),
    ("trending useful papers by first author Blanco-Cuaresma",
     'trending(useful(author:"^Blanco-Cuaresma, Sergi" collection:astronomy))'),
    # reviews(useful(...))
    ("review papers that cite the most useful cosmology literature",
     'reviews(useful(abs:"cosmology"))'),
    ("reviews citing key papers on black hole mergers",
     'reviews(useful(abs:"black hole mergers"))'),
    ("review articles based on important neutron star research",
     'reviews(useful(abs:"neutron star"))'),
    ("reviews of the most useful gravitational wave papers",
     'reviews(useful(abs:"gravitational waves"))'),
    ("reviews citing seminal papers by first author Hawking",
     'reviews(useful(author:"^Hawking"))'),
    # citations(topn(...))
    ("papers citing the top 100 dark energy papers by citation count",
     'citations(topn(100, abs:"dark energy", "citation_count desc"))'),
    ("papers that cite the 50 most-cited exoplanet papers",
     'citations(topn(50, abs:"exoplanet", "citation_count desc"))'),
    ("papers citing the top 200 galaxy cluster papers",
     'citations(topn(200, abs:"galaxy cluster", "citation_count desc"))'),
    ("who cites the most-read stellar evolution papers",
     'citations(topn(100, abs:"stellar evolution", "read_count desc"))'),
    # similar(citations(...))
    ("papers similar to what cites the gravitational wave detection paper",
     'similar(citations(bibcode:2016PhRvL.116f1102A)) collection:astronomy'),
    # trending(topn(...))
    ("trending papers among the top 200 stellar spectroscopy papers by read count",
     'trending(topn(200, abs:"stellar spectroscopy", "read_count desc"))'),
    ("trending from the most-read chemical abundances papers in astronomy",
     'trending(topn(200, abs:"chemical abundances" collection:astronomy, "read_count desc"))'),
]

# ---------------------------------------------------------------------------
# similar() with entdate: temporal filters
# ---------------------------------------------------------------------------
SIMILAR_TEMPORAL = [
    ("new papers this week related to fast radio bursts",
     'similar(abs:"fast radio bursts") entdate:[NOW-7DAYS TO *]'),
    ("recent papers similar to exoplanet atmosphere research",
     'similar(abs:"exoplanet atmospheres") entdate:[NOW-7DAYS TO *]'),
    ("papers added this month similar to dark energy research",
     'similar(abs:"dark energy") entdate:[NOW-1MONTH TO *]'),
    ("new papers this week like galaxy merger simulations",
     'similar(abs:"galaxy merger simulations") entdate:[NOW-7DAYS TO *]'),
    ("recently indexed papers related to gravitational wave detection",
     'similar(abs:"gravitational wave detection") entdate:[NOW-14DAYS TO *]'),
    ("this week's papers similar to magnetar emission models",
     'similar(abs:"magnetar emission") entdate:[NOW-7DAYS TO *]'),
    ("new preprints related to cosmic microwave background",
     'similar(abs:"cosmic microwave background") entdate:[NOW-7DAYS TO *] bibstem:"arXiv"'),
    ("recent papers similar to AGN feedback simulations",
     'similar(abs:"AGN feedback") entdate:[NOW-1MONTH TO *]'),
    ("newly added papers like brown dwarf atmospheric models",
     'similar(abs:"brown dwarf atmosphere") entdate:[NOW-14DAYS TO *]'),
    ("this month's papers related to primordial nucleosynthesis",
     'similar(abs:"primordial nucleosynthesis") entdate:[NOW-1MONTH TO *]'),
]

# ---------------------------------------------------------------------------
# property:(...) multi-value syntax
# ---------------------------------------------------------------------------
PROPERTY_MULTI = [
    ("refereed open access papers on gravitational waves",
     'property:(refereed openaccess) abs:"gravitational waves"'),
    ("peer-reviewed open access papers on exoplanets",
     'property:(refereed openaccess) abs:"exoplanet"'),
    ("refereed papers with data links on galaxy clusters",
     'property:(refereed data) abs:"galaxy clusters"'),
    ("open access refereed papers with data links on stellar evolution",
     'property:(refereed openaccess data) abs:"stellar evolution"'),
    ("refereed open access papers with data from 2020 to 2024",
     'property:(refereed openaccess data) pubdate:[2020 TO 2024]'),
    ("refereed papers with open access and data links on dark matter",
     'property:(refereed openaccess data) abs:"dark matter"'),
    ("open access non-article records about supernovae",
     'property:(openaccess nonarticle) abs:"supernova"'),
    ("refereed papers with electronic resources about CMB",
     'property:(refereed openaccess) abs:"cosmic microwave background"'),
    ("open access earth science papers with data links",
     'property:(openaccess data) collection:earthscience'),
    ("refereed papers with open access full text on black holes",
     'property:(refereed openaccess) abs:"black hole"'),
]

# ---------------------------------------------------------------------------
# bibstem: wildcards and multi-bibstem OR
# ---------------------------------------------------------------------------
BIBSTEM_PATTERNS = [
    ("papers published in any JGR journal",
     "bibstem:jgr*"),
    ("geophysics papers in JGR journals on magnetotellurics",
     'bibstem:jgr* abs:"magnetotelluric"'),
    ("papers in JGR journals about sea ice",
     'bibstem:jgr* abs:"sea ice"'),
    ("Hubble Space Telescope proposals",
     'bibstem:"hst..prop"'),
    ("papers published in ApJ, ApJL, or ApJS",
     "bibstem:(ApJ OR ApJL OR ApJS)"),
    ("papers on supernovae in any of the ApJ journals",
     'bibstem:(ApJ OR ApJL OR ApJS) abs:"supernova"'),
    ("papers in Physical Review journals about neutrinos",
     'bibstem:(PhRvD OR PhRvL OR PhRvC) abs:"neutrino"'),
    ("papers in either MNRAS or A&A on AGN feedback",
     'bibstem:(MNRAS OR A&A) abs:"AGN feedback"'),
    ("papers in Nature or Science about gravitational waves",
     'bibstem:(Nature OR Sci) abs:"gravitational waves"'),
    ("VizieR catalog entries",
     "bibstem:yCat"),
    ("VizieR catalogs about stellar photometry",
     'bibstem:yCat abs:"stellar photometry"'),
]

# ---------------------------------------------------------------------------
# full: field for instrument/identifier searches
# ---------------------------------------------------------------------------
FULL_TEXT = [
    ("papers mentioning MUSE and VLT in the full text",
     'full:"MUSE" full:"VLT"'),
    ("full-text search for machine learning in astronomy papers",
     'full:"machine learning" collection:astronomy'),
    ("papers that mention the Hubble Space Telescope in their full text",
     'full:"Hubble Space Telescope"'),
    ("papers with JWST mentioned in the full text since 2022",
     'full:"JWST" pubdate:[2022 TO 2026]'),
    ("full text search for neural networks in astrophysics",
     'full:"neural network" collection:astronomy'),
    ("papers mentioning specific DOI 10.5281 in their text",
     'full:"10.5281"'),
    ("papers referencing PDS URNs in their text",
     'full:"urn:nasa:pds"'),
    ("papers with ALMA mentioned in the full text about protoplanetary disks",
     'full:"ALMA" abs:"protoplanetary disk"'),
]

# ---------------------------------------------------------------------------
# Data linking patterns (property:data, citations(doctype:software))
# ---------------------------------------------------------------------------
DATA_LINKING = [
    ("papers with linked data products",
     "property:data"),
    ("refereed papers with data products on exoplanets",
     'property:data property:refereed abs:"exoplanet"'),
    ("papers that cite software records in gravitational wave research",
     'abs:"gravitational waves" citations(doctype:software)'),
    ("refereed open access papers with data from 2020 to 2024 in earth science",
     "property:(refereed openaccess data) pubdate:[2020 TO 2024] collection:earthscience"),
    ("papers citing software used in galaxy simulations",
     'citations(doctype:software) abs:"galaxy simulation"'),
    ("NICMOS papers that are refereed and open access with data links",
     'abs:"NICMOS" property:(data refereed openaccess)'),
    ("papers citing software in the earth science collection",
     "citations(doctype:software) collection:earthscience"),
    ("software packages referenced by exoplanet transit studies",
     'doctype:software references(abs:"exoplanet transit")'),
    ("software records about LISA gravitational wave detector",
     'doctype:software collection:astronomy abs:"LISA"'),
    ("catalog records in the astronomy database",
     "doctype:catalog collection:astronomy"),
]

# ---------------------------------------------------------------------------
# Earth science / cross-domain data linking
# ---------------------------------------------------------------------------
EARTH_SCIENCE = [
    ("earth science papers about sea level rise",
     'collection:earthscience abs:"sea level rise"'),
    ("refereed earth science papers on Antarctic ice sheets",
     'collection:earthscience abs:"Antarctic ice sheet" property:refereed'),
    ("earth science papers about seismology since 2020",
     'collection:earthscience abs:"seismology" pubdate:[2020 TO 2026]'),
    ("earth science papers with data links about ocean circulation",
     'collection:earthscience property:data abs:"ocean circulation"'),
    ("open access earth science papers about climate modeling",
     'collection:earthscience property:openaccess abs:"climate model"'),
    ("earth science papers citing software about atmospheric chemistry",
     'collection:earthscience citations(doctype:software) abs:"atmospheric chemistry"'),
    ("refereed open access earth science papers with data since 2020",
     "collection:earthscience property:(refereed openaccess data) pubdate:[2020 TO 2026]"),
    ("earth science papers about magnetotellurics",
     'collection:earthscience abs:"magnetotelluric"'),
    ("papers about geodesy in the earth science collection",
     'collection:earthscience abs:"geodesy" doctype:article'),
    ("earth science papers on volcanic eruptions",
     'collection:earthscience abs:"volcanic eruption" doctype:article'),
]

# ---------------------------------------------------------------------------
# Object search patterns from blog (Boolean within object:)
# ---------------------------------------------------------------------------
OBJECT_BLOG = [
    ("papers about both the LMC and SMC",
     'object:((LMC) AND (SMC))'),
    ("papers about the LMC or SMC and M31",
     'object:((SMC OR LMC) AND M31)'),
    ("refereed papers about the star Aldebaran",
     'object:Aldebaran property:refereed'),
    ("papers about M67 that are refereed",
     'object:M67 property:refereed'),
]

# ---------------------------------------------------------------------------
# abs: with Boolean AND (from Earth science blog)
# ---------------------------------------------------------------------------
ABS_BOOLEAN = [
    ("papers about Antarctica and snowfall and sea ice",
     'abs:("Antarctica" AND "snowfall" AND "sea ice")'),
    ("papers about climate change and Arctic and permafrost",
     'abs:("climate change" AND "Arctic" AND "permafrost")'),
    ("papers about earthquake and tsunami and subduction",
     'abs:("earthquake" AND "tsunami" AND "subduction")'),
    ("papers about solar wind and magnetosphere and reconnection",
     'abs:("solar wind" AND "magnetosphere" AND "reconnection")'),
    ("papers on ocean acidification and coral reefs and biodiversity",
     'abs:("ocean acidification" AND "coral reef" AND "biodiversity")'),
]

# ---------------------------------------------------------------------------
# Exact match modifier (= disabling synonyms)
# ---------------------------------------------------------------------------
EXACT_MATCH = [
    ("exact search for keyword accretion without synonyms",
     '=keyword:"accretion"'),
    ("search for keyword sun without synonym expansion",
     '=keyword:"sun"'),
    ("find exact matches for the term supernova without related terms",
     '=abs:"supernova"'),
    ("exact keyword search for galaxies without synonyms",
     '=keyword:"galaxies"'),
]


def generate_examples() -> list[dict]:
    examples = []

    categories = [
        (NESTED_OPERATORS, "operator"),
        (SIMILAR_TEMPORAL, "operator"),
        (PROPERTY_MULTI, "filters"),
        (BIBSTEM_PATTERNS, "publication"),
        (FULL_TEXT, "content"),
        (DATA_LINKING, "compound"),
        (EARTH_SCIENCE, "collection"),
        (OBJECT_BLOG, "object"),
        (ABS_BOOLEAN, "content"),
        (EXACT_MATCH, "syntax"),
    ]

    for pairs, category in categories:
        for nl, query in pairs:
            examples.append({
                "natural_language": nl,
                "ads_query": query,
                "category": category,
            })

    return examples


def main():
    parser = argparse.ArgumentParser(description="Generate blog-sourced training examples")
    parser.add_argument("--output", type=Path, default=Path("data/datasets/generated/blog_examples.json"))
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

    cats: dict[str, int] = {}
    for e in unique:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    print(f"Generated {len(unique)} blog-sourced examples")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
