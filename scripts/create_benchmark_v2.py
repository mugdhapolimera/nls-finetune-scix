#!/usr/bin/env python3
"""Create benchmark v2 test cases.

Includes all 301 v1 tests (tagged "v1") plus ~120 new tests (tagged "v2")
covering runtime augmentation, new fields, compound queries, reference parsing,
edge cases, and regression tests.

Output: data/datasets/benchmark/benchmark_queries_v2.json

Usage:
    python scripts/create_benchmark_v2.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
V1_PATH = ROOT / "data/datasets/benchmark/benchmark_queries.json"
V2_PATH = ROOT / "data/datasets/benchmark/benchmark_queries_v2.json"


def tag_v1_tests(benchmark: dict) -> dict:
    """Add 'added_in': 'v1' to all existing tests."""
    for key, value in benchmark.items():
        if key == "metadata":
            continue
        if isinstance(value, list):
            for test in value:
                test["added_in"] = "v1"
        elif isinstance(value, dict):
            for subkey, tests in value.items():
                for test in tests:
                    test["added_in"] = "v1"
    return benchmark


# ---------------------------------------------------------------------------
# New v2 test definitions
# ---------------------------------------------------------------------------

RUNTIME_AUGMENTATION = {
    "uat": [
        {
            "id": "uat-001",
            "natural_language": "papers about dark matter",
            "expected_patterns": ["uat:\"Dark matter\"", "abs:\"dark matter\""],
            "forbidden_patterns": [],
            "description": "UAT augmentation for known thesaurus term",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "uat-002",
            "natural_language": "stellar evolution research",
            "expected_patterns": ["uat:\"Stellar evolution\"", "abs:\"stellar evolution\""],
            "forbidden_patterns": [],
            "description": "UAT augmentation for stellar evolution",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "uat-003",
            "natural_language": "papers on exoplanet atmospheres",
            "expected_patterns": ["abs:\"exoplanet atmospheres\""],
            "forbidden_patterns": [],
            "description": "UAT augmentation for exoplanet atmospheres",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "uat-004",
            "natural_language": "galaxy clusters and gravitational lensing",
            "expected_patterns": ["abs:"],
            "forbidden_patterns": [],
            "description": "UAT augmentation for multi-topic query — at minimum should have abs field",
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "uat-005",
            "natural_language": "white dwarf cooling sequences",
            "expected_patterns": ["abs:"],
            "forbidden_patterns": [],
            "description": "UAT augmentation for white dwarf cooling",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "uat-006",
            "natural_language": "interstellar dust models",
            "expected_patterns": ["abs:"],
            "forbidden_patterns": [],
            "description": "UAT augmentation for interstellar dust",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "uat-007",
            "natural_language": "supernova remnant spectra",
            "expected_patterns": ["abs:"],
            "forbidden_patterns": [],
            "description": "UAT augmentation for supernova remnants",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "uat-008",
            "natural_language": "binary star systems and mass transfer",
            "expected_patterns": ["abs:"],
            "forbidden_patterns": [],
            "description": "UAT augmentation for binary stars",
            "difficulty": "medium",
            "added_in": "v2",
        },
    ],
    "planetary_feature": [
        {
            "id": "pf-001",
            "natural_language": "papers about Olympus Mons",
            "expected_patterns": ["planetary_feature:\"Olympus Mons\""],
            "forbidden_patterns": [],
            "description": "Planetary feature augmentation for known feature",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "pf-002",
            "natural_language": "Valles Marineris geology",
            "expected_patterns": ["planetary_feature:\"Valles Marineris\""],
            "forbidden_patterns": [],
            "description": "Planetary feature augmentation for Valles Marineris",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "pf-003",
            "natural_language": "crater morphology on the Moon",
            "expected_patterns": ["abs:"],
            "forbidden_patterns": [],
            "description": "Planetary feature for crater type — at minimum should have abs field",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "pf-004",
            "natural_language": "Gale Crater on Mars",
            "expected_patterns": ["abs:"],
            "forbidden_patterns": [],
            "description": "Planetary feature for Gale Crater — augmentation adds planetary_feature:",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "pf-005",
            "natural_language": "Jezero Crater landing site",
            "expected_patterns": ["abs:"],
            "forbidden_patterns": [],
            "description": "Planetary feature for Jezero Crater — augmentation adds planetary_feature:",
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
    "institution_expansion": [
        {
            "id": "inst-exp-001",
            "natural_language": "papers from MIT on exoplanets",
            "expected_patterns": ["inst:\"MIT\""],
            "forbidden_patterns": [],
            "description": "Institution expansion for MIT",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "inst-exp-002",
            "natural_language": "papers from the Space Telescope Science Institute",
            "expected_patterns": ["inst:\"STScI\""],
            "forbidden_patterns": [],
            "description": "Institution expansion for STScI",
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "inst-exp-003",
            "natural_language": "Caltech authors on gravitational waves",
            "expected_patterns": ["inst:\"Caltech\""],
            "forbidden_patterns": [],
            "description": "Institution expansion for Caltech",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "inst-exp-004",
            "natural_language": "papers from the European Southern Observatory",
            "expected_patterns": ["inst:\"ESO\""],
            "forbidden_patterns": [],
            "description": "Institution expansion for ESO",
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "inst-exp-005",
            "natural_language": "Goddard Space Flight Center publications on solar wind",
            "expected_patterns": ["inst:\"GSFC\""],
            "forbidden_patterns": [],
            "description": "Institution expansion for GSFC",
            "difficulty": "medium",
            "added_in": "v2",
        },
    ],
    "bibstem_normalization": [
        {
            "id": "bibstem-norm-001",
            "natural_language": "papers in the Astrophysical Journal on quasars",
            "expected_patterns": ["bibstem:\"ApJ\""],
            "forbidden_patterns": [],
            "description": "Bibstem normalization for Astrophysical Journal",
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "bibstem-norm-002",
            "natural_language": "articles in Monthly Notices of the Royal Astronomical Society",
            "expected_patterns": ["bibstem:\"MNRAS\""],
            "forbidden_patterns": [],
            "description": "Bibstem normalization for MNRAS",
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "bibstem-norm-003",
            "natural_language": "papers published in Astronomy and Astrophysics",
            "expected_patterns": ["bibstem:\"A&A\""],
            "forbidden_patterns": [],
            "description": "Bibstem normalization for A&A",
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "bibstem-norm-004",
            "natural_language": "Nature papers on black holes",
            "expected_patterns": ["bibstem:\"Natur\""],
            "forbidden_patterns": [],
            "description": "Bibstem normalization for Nature",
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
    "author_wildcarding": [
        {
            "id": "author-wc-001",
            "natural_language": "papers by El-Badry on binary stars",
            "expected_patterns": ["author:\"El*Badry*\""],
            "forbidden_patterns": [],
            "description": "Complex author wildcarding for hyphenated name",
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "author-wc-002",
            "natural_language": "papers by Garcia-Perez",
            "expected_patterns": ["author:\"Garcia*Perez*\""],
            "forbidden_patterns": [],
            "description": "Complex author wildcarding for hyphenated name",
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "author-wc-003",
            "natural_language": "papers by de Groot-Hedlin on seismology",
            "expected_patterns": ["author:\"de*Groot*Hedlin*\""],
            "forbidden_patterns": [],
            "description": "Complex author wildcarding with prefix and hyphen",
            "difficulty": "hard",
            "added_in": "v2",
        },
    ],
}

NEW_FIELDS = {
    "object": [
        {
            "id": "newf-obj-001",
            "natural_language": "papers about M31",
            "expected_query": "object:M31",
            "fields_expected": ["object"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-obj-002",
            "natural_language": "papers studying NGC 1275",
            "expected_query": "object:\"NGC 1275\"",
            "fields_expected": ["object"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-obj-003",
            "natural_language": "observations of the Crab Nebula",
            "expected_query": "object:\"Crab Nebula\"",
            "fields_expected": ["object"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-obj-004",
            "natural_language": "Sgr A* accretion studies",
            "expected_query": "object:\"Sgr A*\" abs:\"accretion\"",
            "fields_expected": ["object", "abs"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-obj-005",
            "natural_language": "LMC star formation rate",
            "expected_query": "object:LMC abs:\"star formation rate\"",
            "fields_expected": ["object", "abs"],
            "difficulty": "medium",
            "added_in": "v2",
        },
    ],
    "has": [
        {
            "id": "newf-has-001",
            "natural_language": "papers with full text available about exoplanets",
            "expected_query": "abs:\"exoplanets\" has:body",
            "fields_expected": ["abs", "has"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-has-002",
            "natural_language": "papers with associated data about galaxy clusters",
            "expected_query": "abs:\"galaxy clusters\" has:data",
            "fields_expected": ["abs", "has"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-has-003",
            "natural_language": "papers with ORCID verified authors on dark energy",
            "expected_query": "abs:\"dark energy\" has:orcid_pub",
            "fields_expected": ["abs", "has"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-has-004",
            "natural_language": "articles with acknowledgment sections mentioning grants",
            "expected_query": "has:ack has:grant",
            "fields_expected": ["has"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-has-005",
            "natural_language": "papers that have abstracts on gravitational waves",
            "expected_query": "abs:\"gravitational waves\" has:abstract",
            "fields_expected": ["abs", "has"],
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
    "data_archives": [
        {
            "id": "newf-data-001",
            "natural_language": "papers with MAST data on Hubble observations",
            "expected_query": "data:MAST abs:\"Hubble\"",
            "fields_expected": ["data", "abs"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-data-002",
            "natural_language": "papers linked to NED about galaxy redshifts",
            "expected_query": "data:NED abs:\"galaxy redshifts\"",
            "fields_expected": ["data", "abs"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-data-003",
            "natural_language": "papers with SIMBAD data on variable stars",
            "expected_query": "data:SIMBAD abs:\"variable stars\"",
            "fields_expected": ["data", "abs"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-data-004",
            "natural_language": "papers with VizieR catalog data",
            "expected_query": "data:VizieR",
            "fields_expected": ["data"],
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
    "esources": [
        {
            "id": "newf-esrc-001",
            "natural_language": "papers with publisher PDF available about supernovae",
            "expected_query": "abs:\"supernovae\" esources:PUB_PDF",
            "fields_expected": ["abs", "esources"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-esrc-002",
            "natural_language": "papers with arXiv preprint PDF on cosmology",
            "expected_query": "abs:\"cosmology\" esources:EPRINT_PDF",
            "fields_expected": ["abs", "esources"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-esrc-003",
            "natural_language": "papers with ADS scanned pages",
            "expected_query": "esources:ADS_SCAN",
            "fields_expected": ["esources"],
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
    "grant_ack": [
        {
            "id": "newf-grant-001",
            "natural_language": "papers funded by NSF grant AST-1234567",
            "expected_query": "grant:\"AST-1234567\"",
            "fields_expected": ["grant"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-grant-002",
            "natural_language": "papers acknowledging Hubble Space Telescope time",
            "expected_query": "ack:\"Hubble Space Telescope\"",
            "fields_expected": ["ack"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-grant-003",
            "natural_language": "papers acknowledging ALMA observations",
            "expected_query": "ack:\"ALMA\"",
            "fields_expected": ["ack"],
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
    "arxiv_class": [
        {
            "id": "newf-arxiv-001",
            "natural_language": "papers in the astro-ph.HE category",
            "expected_query": "arxiv_class:astro-ph.HE",
            "fields_expected": ["arxiv_class"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-arxiv-002",
            "natural_language": "cosmology papers on arXiv astro-ph.CO",
            "expected_query": "abs:\"cosmology\" arxiv_class:astro-ph.CO",
            "fields_expected": ["abs", "arxiv_class"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-arxiv-003",
            "natural_language": "instrumentation papers from astro-ph.IM",
            "expected_query": "arxiv_class:astro-ph.IM",
            "fields_expected": ["arxiv_class"],
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
    "orcid": [
        {
            "id": "newf-orcid-001",
            "natural_language": "papers by ORCID 0000-0002-1825-0097",
            "expected_query": "orcid:0000-0002-1825-0097",
            "fields_expected": ["orcid"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-orcid-002",
            "natural_language": "publications with ORCID 0000-0001-5000-0007",
            "expected_query": "orcid:0000-0001-5000-0007",
            "fields_expected": ["orcid"],
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
    "mention_credit": [
        {
            "id": "newf-mc-001",
            "natural_language": "papers mentioning astropy software",
            "expected_query": "abs:\"astropy\" mention_count:[1 TO *]",
            "fields_expected": ["abs", "mention_count"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-mc-002",
            "natural_language": "papers that credit numpy at least 5 times",
            "expected_query": "abs:\"numpy\" credit_count:[5 TO *]",
            "fields_expected": ["abs", "credit_count"],
            "difficulty": "medium",
            "added_in": "v2",
        },
        {
            "id": "newf-mc-003",
            "natural_language": "papers with high mention counts about JWST",
            "expected_query": "abs:\"JWST\" mention_count:[10 TO *]",
            "fields_expected": ["abs", "mention_count"],
            "difficulty": "medium",
            "added_in": "v2",
        },
    ],
    "caption": [
        {
            "id": "newf-cap-001",
            "natural_language": "papers with figure captions about H-R diagrams",
            "expected_query": "caption:\"H-R diagram\"",
            "fields_expected": ["caption"],
            "difficulty": "simple",
            "added_in": "v2",
        },
        {
            "id": "newf-cap-002",
            "natural_language": "papers with table captions about abundance ratios",
            "expected_query": "caption:\"abundance ratios\"",
            "fields_expected": ["caption"],
            "difficulty": "simple",
            "added_in": "v2",
        },
    ],
}

COMPOUND_QUERIES = [
    {
        "id": "compound-v2-001",
        "natural_language": "refereed papers by Riess on dark energy since 2010",
        "expected_query": "author:\"Riess\" abs:\"dark energy\" pubdate:[2010 TO *] property:refereed",
        "fields_expected": ["author", "abs", "pubdate", "property"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-002",
        "natural_language": "papers about exoplanets NOT hot Jupiters",
        "expected_query": "abs:\"exoplanets\" -abs:\"hot Jupiters\"",
        "fields_expected": ["abs"],
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-003",
        "natural_language": "papers on galaxy morphology or galaxy structure",
        "expected_query": "abs:\"galaxy morphology\" OR abs:\"galaxy structure\"",
        "fields_expected": ["abs"],
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-004",
        "natural_language": "citations of papers about LIGO from 2016",
        "expected_query": "citations(abs:\"LIGO\" pubdate:2016)",
        "fields_expected": ["abs", "pubdate"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-005",
        "natural_language": "trending papers on machine learning in astronomy",
        "expected_query": "trending(abs:\"machine learning\")",
        "fields_expected": ["abs"],
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-006",
        "natural_language": "PhD theses on quasars from 2020 to 2024",
        "expected_query": "abs:\"quasars\" doctype:phdthesis pubdate:[2020 TO 2024]",
        "fields_expected": ["abs", "doctype", "pubdate"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-007",
        "natural_language": "open access papers on stellar nucleosynthesis",
        "expected_query": "abs:\"stellar nucleosynthesis\" property:openaccess",
        "fields_expected": ["abs", "property"],
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-008",
        "natural_language": "papers by Hawking or Penrose on cosmology",
        "expected_query": "(author:\"Hawking\" OR author:\"Penrose\") abs:\"cosmology\"",
        "fields_expected": ["author", "abs"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-009",
        "natural_language": "JWST papers in Nature or Science from 2023",
        "expected_query": "abs:\"JWST\" (bibstem:\"Natur\" OR bibstem:\"Sci\") pubdate:2023",
        "fields_expected": ["abs", "bibstem", "pubdate"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-010",
        "natural_language": "software papers about SExtractor",
        "expected_query": "abs:\"SExtractor\" doctype:software",
        "fields_expected": ["abs", "doctype"],
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-011",
        "natural_language": "papers from last 5 years on fast radio bursts",
        "expected_query": "abs:\"fast radio bursts\" pubdate:[2021 TO *]",
        "fields_expected": ["abs", "pubdate"],
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-012",
        "natural_language": "refereed papers not preprints on AGN feedback",
        "expected_query": "abs:\"AGN feedback\" property:refereed -doctype:eprint",
        "fields_expected": ["abs", "property", "doctype"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-013",
        "natural_language": "top 10 most cited papers on dark matter",
        "expected_query": "topn(10, abs:\"dark matter\", \"citation_count desc\")",
        "fields_expected": ["abs"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-014",
        "natural_language": "similar papers to those about black hole mergers",
        "expected_query": "similar(abs:\"black hole mergers\")",
        "fields_expected": ["abs"],
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-015",
        "natural_language": "papers with more than 200 citations on the CMB",
        "expected_query": "abs:\"CMB\" citation_count:[200 TO *]",
        "fields_expected": ["abs", "citation_count"],
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-016",
        "natural_language": "Chandra X-ray papers about galaxy clusters with data",
        "expected_query": "bibgroup:Chandra abs:\"galaxy clusters\" has:data",
        "fields_expected": ["bibgroup", "abs", "has"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-017",
        "natural_language": "conference proceedings on radio interferometry since 2015",
        "expected_query": "abs:\"radio interferometry\" doctype:inproceedings pubdate:[2015 TO *]",
        "fields_expected": ["abs", "doctype", "pubdate"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-018",
        "natural_language": "astronomy database papers about supernova not from physics",
        "expected_query": "abs:\"supernova\" database:astronomy -database:physics",
        "fields_expected": ["abs", "database"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-019",
        "natural_language": "first author papers by Smith on spectroscopy before 2000",
        "expected_query": "author:\"^Smith\" abs:\"spectroscopy\" pubdate:[* TO 2000]",
        "fields_expected": ["author", "abs", "pubdate"],
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "compound-v2-020",
        "natural_language": "reviews of useful papers on magnetars",
        "expected_query": "reviews(abs:\"magnetars\")",
        "fields_expected": ["abs"],
        "difficulty": "medium",
        "added_in": "v2",
    },
]

REFERENCE_PARSING = [
    {
        "id": "refparse-001",
        "natural_language": "2016PhRvL.116f1102A",
        "expected_query": "bibcode:2016PhRvL.116f1102A",
        "fields_expected": ["bibcode"],
        "difficulty": "simple",
        "added_in": "v2",
    },
    {
        "id": "refparse-002",
        "natural_language": "10.1038/nature12373",
        "expected_query": "doi:\"10.1038/nature12373\"",
        "fields_expected": ["doi"],
        "difficulty": "simple",
        "added_in": "v2",
    },
    {
        "id": "refparse-003",
        "natural_language": "arXiv:2301.12345",
        "expected_query": "arxiv:2301.12345",
        "fields_expected": ["arxiv"],
        "difficulty": "simple",
        "added_in": "v2",
    },
    {
        "id": "refparse-004",
        "natural_language": "1998AJ....116.3040G",
        "expected_query": "bibcode:1998AJ....116.3040G",
        "fields_expected": ["bibcode"],
        "difficulty": "simple",
        "added_in": "v2",
    },
    {
        "id": "refparse-005",
        "natural_language": "doi:10.1086/300499",
        "expected_query": "doi:\"10.1086/300499\"",
        "fields_expected": ["doi"],
        "difficulty": "simple",
        "added_in": "v2",
    },
    {
        "id": "refparse-006",
        "natural_language": "arXiv:1502.01589",
        "expected_query": "arxiv:1502.01589",
        "fields_expected": ["arxiv"],
        "difficulty": "simple",
        "added_in": "v2",
    },
    {
        "id": "refparse-007",
        "natural_language": "Riess et al. 1998, AJ, 116, 1009",
        "expected_patterns": ["author:\"Riess\""],
        "forbidden_patterns": [],
        "description": "Formatted citation should extract author at minimum",
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "refparse-008",
        "natural_language": "Perlmutter et al. 1999 ApJ 517 565",
        "expected_patterns": ["author:\"Perlmutter\""],
        "forbidden_patterns": [],
        "description": "Formatted citation should extract author at minimum",
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "refparse-009",
        "natural_language": "2023MNRAS.521.4024L",
        "expected_query": "bibcode:2023MNRAS.521.4024L",
        "fields_expected": ["bibcode"],
        "difficulty": "simple",
        "added_in": "v2",
    },
    {
        "id": "refparse-010",
        "natural_language": "10.3847/1538-4357/ac5965",
        "expected_query": "doi:\"10.3847/1538-4357/ac5965\"",
        "fields_expected": ["doi"],
        "difficulty": "simple",
        "added_in": "v2",
    },
]

# Additional edge cases for v2
EDGE_CASES_V2 = [
    {
        "id": "edge-v2-001",
        "natural_language": "papers about the Hubble constant tension between early and late universe measurements using CMB and supernovae as distance ladders",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Verbose NL distillation — should produce valid query with abs field",
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-002",
        "natural_language": "papers on protein folding",
        "expected_patterns": ["abs:\"protein folding\""],
        "forbidden_patterns": [],
        "description": "Cross-domain query - biochemistry topic",
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-003",
        "natural_language": "superconductivity in high temperature materials",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Cross-domain query - physics/materials science",
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-004",
        "natural_language": "what are the best papers on JWST?",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Conversational query — should extract topic into abs field",
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-005",
        "natural_language": "can you find me recent work on dark energy by Riess?",
        "expected_patterns": ["abs:", "author:"],
        "forbidden_patterns": [],
        "description": "Conversational query — should extract author and topic",
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-006",
        "natural_language": "I'm looking for that paper about the first image of a black hole",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Conversational / vague reference query",
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-007",
        "natural_language": "^author:\"Smith\" abs:\"dark matter\"",
        "expected_behavior": "passthrough",
        "description": "Query repair: caret fix — requires server passthrough",
        "difficulty": "edge",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-008",
        "natural_language": "papers on dark energy from 2025 to 2020",
        "expected_patterns": ["abs:\"dark energy\""],
        "forbidden_patterns": [],
        "description": "Backwards year range in NL — should produce valid query",
        "difficulty": "edge",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-009",
        "natural_language": "preprint papers on cosmology",
        "expected_patterns": ["abs:\"cosmology\""],
        "forbidden_patterns": [],
        "description": "Preprint intent should produce valid query with doctype:eprint or similar",
        "difficulty": "edge",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-010",
        "natural_language": "peer-reviewed papers on AGN",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Peer-reviewed intent — should produce valid query",
        "difficulty": "edge",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-011",
        "natural_language": "I want to understand the current state of research on the formation and evolution of massive galaxies at high redshift, particularly focusing on the role of active galactic nuclei feedback mechanisms",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Verbose NL distillation - long research description",
        "difficulty": "hard",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-012",
        "natural_language": "Planck 2018 results",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Short specific reference — should make reasonable query with abs field",
        "difficulty": "medium",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-013",
        "natural_language": "",
        "expected_behavior": "valid_response",
        "description": "Empty input should not crash",
        "difficulty": "edge",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-014",
        "natural_language": "astrophysics database papers on dark matter",
        "expected_patterns": ["abs:\"dark matter\""],
        "forbidden_patterns": [],
        "description": "Database intent — should produce valid query",
        "difficulty": "edge",
        "added_in": "v2",
    },
    {
        "id": "edge-v2-015",
        "natural_language": "citations(abs:dark matter)",
        "expected_behavior": "passthrough",
        "description": "Query repair: unquoted operator values — requires server passthrough",
        "difficulty": "edge",
        "added_in": "v2",
    },
]

# Regression tests for v2
REGRESSION_TESTS_V2 = [
    {
        "id": "regression-v2-001",
        "natural_language": "JWST bibliography papers on exoplanets",
        "forbidden_patterns": ["bibgroup:\"JWST\""],
        "expected_patterns": ["bibgroup:JWST"],
        "description": "Bibgroup values should NOT be quoted",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-002",
        "natural_language": "papers from MIT about stellar physics",
        "forbidden_patterns": ["abs:\"MIT\"", "abs:\"Massachusetts\""],
        "description": "Institution should not leak into abs field",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-003",
        "natural_language": "papers about brown dwarfs",
        "forbidden_patterns": ["abs:\"brown dwarfs\" OR abs:\"L dwarfs\" OR abs:\"T dwarfs\""],
        "description": "LLM should NOT expand synonyms - single abs term only",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-004",
        "natural_language": "papers about supernovae",
        "forbidden_patterns": ["abs:\"supernovae\" OR abs:\"SN Ia\"", "abs:\"supernova\" OR abs:\"SN\""],
        "description": "LLM should NOT expand synonyms",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-005",
        "natural_language": "papers about galaxies",
        "forbidden_patterns": ["doctype:article"],
        "description": "Generic 'papers' should NOT add doctype:article",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-006",
        "natural_language": "papers by Hawking on black holes",
        "forbidden_patterns": ["abs:\"Stephen Hawking\"", "abs:\"Hawking\""],
        "description": "Author should go in author field, not abs field",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-007",
        "natural_language": "papers from NASA on Mars exploration",
        "forbidden_patterns": ["abs:\"NASA\""],
        "description": "NASA should go in aff/inst field, not abs field",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-008",
        "natural_language": "papers in the Astrophysical Journal on quasars",
        "forbidden_patterns": ["abs:\"Astrophysical Journal\""],
        "description": "Journal name should go in bibstem field, not abs field",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-009",
        "natural_language": "aff:Berkeley abs:\"dark matter\"",
        "expected_behavior": "passthrough",
        "description": "aff: passthrough — requires server for inst expansion",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-010",
        "natural_language": "papers from the Jet Propulsion Laboratory on Mars",
        "expected_patterns": ["inst:\"JPL\""],
        "forbidden_patterns": [],
        "description": "Long institution name should be normalized to abbreviation",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-011",
        "natural_language": "refereed papers on star formation",
        "forbidden_patterns": ["property:\"refereed\""],
        "description": "Property values should NOT be quoted",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-012",
        "natural_language": "article type papers on cosmology",
        "forbidden_patterns": ["doctype:\"article\""],
        "description": "Doctype values should NOT be quoted",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-013",
        "natural_language": "abs:\"dark matter\" property:refereed",
        "expected_behavior": "passthrough",
        "description": "ADS syntax passthrough — requires server",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-014",
        "natural_language": "author:\"Hawking\" abs:\"black holes\" pubdate:[2000 TO 2020]",
        "expected_behavior": "passthrough",
        "description": "Multi-field ADS syntax passthrough — requires server",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-015",
        "natural_language": "papers about neutron stars",
        "forbidden_patterns": ["abs:\"neutron stars\" OR abs:", "abs:\"neutron star\" OR abs:\"pulsar\""],
        "description": "LLM should NOT add synonym OR-lists for neutron stars",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-016",
        "natural_language": "similar(abs:\"dark matter\") entdate:[NOW-7DAYS TO *]",
        "expected_behavior": "passthrough",
        "description": "similar() with entdate passthrough — requires server",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-017",
        "natural_language": "trending(useful(abs:\"cosmology\"))",
        "expected_behavior": "passthrough",
        "description": "Nested operator passthrough — requires server",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-018",
        "natural_language": "papers on magnetohydrodynamics published this year",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Relative date 'this year' should produce valid query with abs field",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-019",
        "natural_language": "Earth science papers on atmospheric CO2",
        "expected_patterns": ["abs:"],
        "forbidden_patterns": [],
        "description": "Earth science query should produce valid output",
        "difficulty": "regression",
        "added_in": "v2",
    },
    {
        "id": "regression-v2-020",
        "natural_language": "papers about protoplanetary disk evolution by Williams and Cieza",
        "expected_patterns": ["author:"],
        "forbidden_patterns": [],
        "description": "Multi-author extraction should work",
        "difficulty": "regression",
        "added_in": "v2",
    },
]


def build_v2_benchmark():
    """Build the v2 benchmark file."""
    # Load v1
    with open(V1_PATH) as f:
        v1 = json.load(f)

    # Tag all v1 tests
    v1 = tag_v1_tests(v1)

    # Start with v1 structure
    v2 = dict(v1)

    # Add new top-level categories
    v2["runtime_augmentation"] = RUNTIME_AUGMENTATION
    v2["new_fields"] = NEW_FIELDS
    v2["compound_queries"] = COMPOUND_QUERIES
    v2["reference_parsing"] = REFERENCE_PARSING

    # Append v2 edge cases and regression tests to existing lists
    v2["edge_cases"] = v1.get("edge_cases", []) + EDGE_CASES_V2
    v2["regression_tests"] = v1.get("regression_tests", []) + REGRESSION_TESTS_V2

    # Count tests
    total = 0
    v1_count = 0
    v2_count = 0
    for key, value in v2.items():
        if key == "metadata":
            continue
        if isinstance(value, list):
            total += len(value)
            v1_count += sum(1 for t in value if t.get("added_in") == "v1")
            v2_count += sum(1 for t in value if t.get("added_in") == "v2")
        elif isinstance(value, dict):
            for subkey, tests in value.items():
                if isinstance(tests, list):
                    total += len(tests)
                    v1_count += sum(1 for t in tests if t.get("added_in") == "v1")
                    v2_count += sum(1 for t in tests if t.get("added_in") == "v2")

    # Update metadata
    v2["metadata"] = {
        "version": "2.0.0",
        "description": "Comprehensive benchmark v2 for NL-to-ADS query translation",
        "created": "2026-01-22",
        "updated": "2026-03-18",
        "v1_count": v1_count,
        "v2_count": v2_count,
        "actual_count": total,
        "categories": {
            "field_types": ["content", "author", "identifier", "metric", "date"],
            "operators": [
                "citations",
                "references",
                "trending",
                "similar",
                "useful",
                "reviews",
                "topn",
            ],
            "enum_fields": ["property", "doctype", "bibgroup", "database"],
            "runtime_augmentation": [
                "uat",
                "planetary_feature",
                "institution_expansion",
                "bibstem_normalization",
                "author_wildcarding",
            ],
            "new_fields": [
                "object",
                "has",
                "data_archives",
                "esources",
                "grant_ack",
                "arxiv_class",
                "orcid",
                "mention_credit",
                "caption",
            ],
            "compound_queries": True,
            "reference_parsing": True,
            "edge_cases": True,
            "regression_tests": True,
        },
    }

    # Write output
    V2_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(V2_PATH, "w") as f:
        json.dump(v2, f, indent=2)

    print(f"Benchmark v2 written to {V2_PATH}")
    print(f"  v1 tests: {v1_count}")
    print(f"  v2 tests: {v2_count}")
    print(f"  Total: {total}")

    # Breakdown by category
    print("\nBreakdown:")
    for key, value in v2.items():
        if key == "metadata":
            continue
        if isinstance(value, list):
            v2_in_cat = sum(1 for t in value if t.get("added_in") == "v2")
            print(f"  {key}: {len(value)} ({v2_in_cat} new)")
        elif isinstance(value, dict):
            subtotal = sum(len(tests) for tests in value.values() if isinstance(tests, list))
            v2_in_cat = sum(
                1
                for tests in value.values()
                if isinstance(tests, list)
                for t in tests
                if t.get("added_in") == "v2"
            )
            print(f"  {key}: {subtotal} ({v2_in_cat} new)")


if __name__ == "__main__":
    build_v2_benchmark()
