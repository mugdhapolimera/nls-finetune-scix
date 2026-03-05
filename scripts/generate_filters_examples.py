#!/usr/bin/env python3
"""
Generate training data for filter-based queries.

Covers: esources, has:, grant:, ack:, keyword:, arxiv_class:, lang:,
vizier:, mention_count, credit_count, and orcid-related has: fields.

Usage:
    python scripts/generate_filters_examples.py \
        --output data/datasets/generated/filters_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

TOPICS = [
    ("galaxy clusters", "galaxy clusters"),
    ("gravitational lensing", "gravitational lensing"),
    ("stellar evolution", "stellar evolution"),
    ("dark matter", "dark matter"),
    ("gravitational waves", "gravitational waves"),
    ("exoplanet", "exoplanet"),
    ("dark energy", "dark energy"),
    ("AGN", "AGN"),
    ("stellar nucleosynthesis", "stellar nucleosynthesis"),
    ("galaxy evolution", "galaxy evolution"),
    ("neutrino oscillations", "neutrino oscillations"),
    ("cosmic ray acceleration", "cosmic ray acceleration"),
    ("quasar variability", "quasar variability"),
    ("radio galaxies", "radio galaxies"),
    ("black hole thermodynamics", "black hole thermodynamics"),
    ("interstellar dust", "interstellar dust"),
    ("AGN feedback", "AGN feedback"),
    ("Cepheid variables", "Cepheid variables"),
    ("exoplanet atmospheres", "exoplanet atmospheres"),
    ("fast radio bursts", "fast radio bursts"),
    ("pulsar timing", "pulsar timing"),
    ("supernova remnant", "supernova remnant"),
    ("magnetar", "magnetar"),
    ("spectral analysis", "spectral analysis"),
    ("interstellar medium", "interstellar medium"),
    ("spectroscopy", "spectroscopy"),
    ("black hole merger", "black hole merger"),
    ("cosmic microwave background", "cosmic microwave background"),
    ("stellar populations", "stellar populations"),
    ("active galactic nuclei", "active galactic nuclei"),
    ("solar flares", "solar flares"),
    ("neutron stars", "neutron stars"),
    ("star formation", "star formation"),
    ("planet formation", "planet formation"),
    ("solar physics", "solar physics"),
    ("stellar spectroscopy", "stellar spectroscopy"),
    ("stellar winds", "stellar winds"),
    ("galaxy survey", "galaxy survey"),
    ("cosmology", "cosmology"),
]

# --- esources ---
ESOURCES = {
    "PUB_PDF": [
        "find papers about {topic} that have a publisher PDF available",
        "{topic} papers with publisher PDF",
        "articles on {topic} with downloadable publisher PDF",
    ],
    "EPRINT_PDF": [
        "arxiv preprints on {topic} with downloadable eprint PDF",
        "{topic} eprints with PDF available",
        "preprints on {topic} available as eprint PDF",
    ],
    "ADS_SCAN": [
        "papers from the {decade}s about {topic} with scanned articles",
        "historical papers on {topic} with scanned versions",
        "{topic} papers with ADS scans",
    ],
    "PUB_HTML": [
        "papers on {topic} with HTML full text from the publisher",
        "find {topic} articles available as publisher HTML",
    ],
    "EPRINT_HTML": [
        "{topic} preprints with HTML version on arXiv",
        "papers on {topic} available as eprint HTML",
    ],
    "AUTHOR_PDF": [
        "papers with author-provided PDF on {topic}",
        "find author-submitted PDFs about {topic}",
    ],
    "AUTHOR_HTML": [
        "articles with author HTML version about {topic}",
        "find papers on {topic} with author-hosted HTML",
    ],
    "ADS_PDF": [
        "papers with ADS PDF available on {topic}",
        "find articles on {topic} available as ADS PDF",
    ],
}

# --- has: fields ---
HAS_FIELDS = {
    "body": [
        "papers with searchable full text about {topic}",
        "full-text available papers on {topic}",
    ],
    "ack": [
        "papers with acknowledgments text mentioning NASA funding",
        "papers with acknowledgment sections about {topic}",
    ],
    "grant": [
        "papers with grant information about {topic}",
        "funded research papers on {topic}",
    ],
    "orcid_pub": [
        "papers with publisher-verified ORCID IDs by first author Smith",
        "papers with publisher-verified ORCID on {topic}",
        "find papers where the first author has a verified ORCID",
    ],
    "aff": [
        "papers with affiliation information about {topic}",
    ],
    "abstract": [
        "records that have an abstract about {topic}",
    ],
    "citation": [
        "papers that have been cited at least once about {topic}",
    ],
    "mention": [
        "papers with software or data mentions about {topic}",
        "{topic} papers that mention software or data records",
    ],
    "keyword": [
        "papers with keywords about {topic}",
    ],
    "credit": [
        "papers with credited software on {topic}",
        "software records that have been credited by researchers",
        "data records credited by other papers",
    ],
    "reference": [
        "papers with reference lists about {topic}",
    ],
    "data": [
        "papers that have associated data links on {topic}",
    ],
    "doi": [
        "papers with DOI identifiers about {topic}",
    ],
    "bibgroup": [
        "articles that have bibliographic group assignments",
    ],
    "volume": [
        "papers with volume information about {topic}",
    ],
    "issue": [
        "articles that have issue numbers on {topic}",
    ],
    "institution": [
        "papers with institutional affiliations on {topic}",
    ],
    "uat": [
        "papers with unified astronomy thesaurus tags about {topic}",
    ],
    "publisher": [
        "papers with publisher information about {topic}",
    ],
    "comment": [
        "articles that have comments about {topic}",
    ],
    "orcid_other": [
        "papers with ORCID identifiers from other sources",
    ],
    "orcid_user": [
        "papers with ORCID user claims about {topic}",
        "papers with user-claimed ORCID identifiers on {topic}",
    ],
    "pub_raw": [
        "articles with raw publication info on {topic}",
    ],
    "database": [
        "papers that have database assignments in astronomy",
    ],
    "first_author": [
        "papers with first author metadata about {topic}",
    ],
    "aff_id": [
        "papers with affiliation IDs on {topic}",
    ],
    "origin": [
        "papers with origin metadata about {topic}",
    ],
    "property": [
        "papers with property flags about {topic}",
    ],
    "doctype": [
        "papers with doctype metadata in the astronomy collection",
    ],
}

# --- grant: ---
GRANT_AGENCIES = [
    ("NSF", "National Science Foundation"),
    ("NASA", "NASA"),
    ("DOE", "Department of Energy"),
    ("ESA", "European Space Agency"),
    ("ERC", "European Research Council"),
    ("STFC", "Science and Technology Facilities Council"),
    ("DFG", "Deutsche Forschungsgemeinschaft"),
    ("CSA", "Canadian Space Agency"),
]

GRANT_TEMPLATES = [
    "papers funded by {agency_short} on {topic}",
    "{agency_long}-funded research on {topic}",
    "{agency_short}-funded papers on {topic}",
    "{agency_short} grants research on {topic}",
    "papers with any grant funding on {topic}",
]

# --- ack: ---
ACK_FACILITIES = [
    "Hubble Space Telescope",
    "ALMA",
    "Keck Observatory",
    "Sloan Digital Sky Survey",
    "European Southern Observatory",
    "Gemini Observatory",
    "Chandra X-ray Center",
    "XSEDE",
    "National Radio Astronomy Observatory",
    "James Webb Space Telescope",
]

ACK_TEMPLATES = [
    "papers acknowledging {facility}",
    "articles that acknowledge {facility}",
    "research acknowledging the {facility}",
    "papers that thank the {facility} for telescope time",
]

# --- keyword: ---
KEYWORDS = [
    "gravitational lensing",
    "black hole physics",
    "stellar evolution",
    "cosmology",
    "planetary atmospheres",
    "galaxy clusters",
    "supernovae",
    "molecular clouds",
    "star formation",
    "instrumentation",
    "methods",
    "astrochemistry",
    "techniques: photometric",
    "radio continuum: galaxies",
    "large-scale structure",
    "accretion",
    "surveys",
    "active galactic nuclei",
]

KEYWORD_TEMPLATES = [
    "papers with the keyword {kw}",
    "articles tagged with keyword {kw}",
    "papers tagged with {kw} keyword",
    "papers with keyword {kw}",
]

# --- arxiv_class: ---
ARXIV_CLASSES = [
    ("astro-ph.CO", ["astrophysics cosmology preprints", "cosmology and nongalactic astrophysics eprints"]),
    ("astro-ph.HE", ["high energy astrophysics eprints", "high energy astrophysics preprints"]),
    ("astro-ph.SR", ["solar and stellar astrophysics papers on arXiv", "stellar astrophysics eprints"]),
    ("astro-ph.EP", ["earth and planetary astrophysics preprints", "planetary science arXiv papers"]),
    ("astro-ph.GA", ["arXiv papers on astrophysics of galaxies", "galaxy astrophysics preprints"]),
    ("astro-ph.IM", ["instrumentation and methods for astrophysics eprints"]),
    ("gr-qc", ["general relativity and quantum cosmology preprints"]),
    ("hep-th", ["high energy physics theory papers on arXiv"]),
    ("cond-mat", ["condensed matter preprints in ADS"]),
    ("nucl-th", ["nuclear theory preprints"]),
]

# --- esources compound ---
ESOURCES_COMPOUND = [
    {
        "nl": "open access papers on {topic} with publisher PDF or HTML",
        "query": 'abs:"{abs}" (esources:PUB_PDF OR esources:PUB_HTML) property:openaccess',
    },
    {
        "nl": "historical papers on {topic} with scanned versions",
        "query": 'abs:"{abs}" esources:ADS_SCAN pubdate:[{y1} TO {y2}]',
        "years": True,
    },
    {
        "nl": "recent refereed articles on {topic} with publisher PDF",
        "query": 'abs:"{abs}" esources:PUB_PDF property:refereed pubdate:[2020 TO 2026]',
    },
    {
        "nl": "preprints on {topic} available as eprint PDF",
        "query": 'abs:"{abs}" esources:EPRINT_PDF doctype:eprint',
    },
    {
        "nl": "papers on {topic} with any author-provided version",
        "query": 'abs:"{abs}" (esources:AUTHOR_PDF OR esources:AUTHOR_HTML)',
    },
    {
        "nl": "{topic} papers from the {decade}s with ADS scans",
        "query": 'abs:"{abs}" esources:ADS_SCAN pubdate:[{y1} TO {y2}]',
        "years": True,
    },
]


def generate_esources_examples() -> list[dict]:
    """Generate esources filter examples."""
    examples = []
    decades = [("1960", 1960, 1969), ("1970", 1970, 1979), ("1980", 1980, 1989)]

    for esource, templates in ESOURCES.items():
        for i, (topic_nl, topic_abs) in enumerate(TOPICS[:4]):
            template = templates[i % len(templates)]
            decade_str, y1, y2 = random.choice(decades)
            nl = template.format(topic=topic_nl, decade=decade_str)

            if "decade" in template or "historical" in template:
                query = f'abs:"{topic_abs}" year:{y1}-{y2} esources:{esource}'
            else:
                query = f'abs:"{topic_abs}" esources:{esource}'
                if "article" in template.lower():
                    query += " doctype:article"
                if "eprint" in template.lower() or "preprint" in template.lower():
                    query += " doctype:eprint"

            examples.append({"natural_language": nl, "ads_query": query, "category": "filters"})

    # Compound esources examples
    for spec in ESOURCES_COMPOUND:
        topic_nl, topic_abs = random.choice(TOPICS[:10])
        decade_str, y1, y2 = random.choice(decades)
        nl = spec["nl"].format(topic=topic_nl, decade=decade_str)
        query = spec["query"].format(abs=topic_abs, y1=y1, y2=y2)
        examples.append({"natural_language": nl, "ads_query": query, "category": "filters"})

    return examples


def generate_has_examples() -> list[dict]:
    """Generate has: filter examples."""
    examples = []

    for field, templates in HAS_FIELDS.items():
        for template in templates:
            topic_nl, topic_abs = random.choice(TOPICS)
            nl = template.format(topic=topic_nl)

            # Build query based on field
            if "{topic}" in template:
                query = f'has:{field} abs:"{topic_abs}"'
            elif "Smith" in template:
                query = f'has:{field} author:"^Smith"'
            elif "software records" in template:
                query = f"has:{field} doctype:software"
            elif "data records" in template:
                query = f"has:{field} -doctype:article"
            elif "astronomy" in template:
                if field == "doctype":
                    query = f"has:{field} collection:astronomy"
                else:
                    query = f"has:{field} collection:astronomy"
            elif "bibliographic" in template:
                query = f'has:{field} abs:"{topic_abs}" doctype:article'
            else:
                query = f'has:{field} abs:"{topic_abs}"'

            if "article" in template.lower() and "doctype:article" not in query:
                query += " doctype:article"

            examples.append({"natural_language": nl, "ads_query": query, "category": "filters"})

    return examples


def generate_grant_examples() -> list[dict]:
    """Generate grant: filter examples."""
    examples = []
    grant_topics = TOPICS[:10]

    for agency_short, agency_long in GRANT_AGENCIES:
        topic_nl, topic_abs = random.choice(grant_topics)
        template = random.choice(GRANT_TEMPLATES[:4])
        nl = template.format(agency_short=agency_short, agency_long=agency_long, topic=topic_nl)

        if "any grant" in nl:
            query = f'has:grant abs:"{topic_abs}"'
        else:
            query = f'grant:{agency_short} abs:"{topic_abs}"'
            if random.random() < 0.3:
                query += " doctype:article"

        examples.append({"natural_language": nl, "ads_query": query, "category": "filters"})

    # Additional: NSF with collection
    examples.append({
        "natural_language": "NSF grants research on machine learning in astronomy",
        "ads_query": 'grant:NSF abs:"machine learning" collection:astronomy',
        "category": "filters",
    })

    return examples


def generate_ack_examples() -> list[dict]:
    """Generate ack: filter examples."""
    examples = []

    for facility in ACK_FACILITIES:
        template = random.choice(ACK_TEMPLATES)
        nl = template.format(facility=facility)
        query = f'ack:"{facility}"'
        if random.random() < 0.5:
            query += " doctype:article"
        examples.append({"natural_language": nl, "ads_query": query, "category": "filters"})

    return examples


def generate_keyword_examples() -> list[dict]:
    """Generate keyword: filter examples."""
    examples = []

    for kw in KEYWORDS:
        template = random.choice(KEYWORD_TEMPLATES)
        nl = template.format(kw=kw)
        query = f'keyword:"{kw}"'
        if random.random() < 0.3:
            query += " doctype:article"
        if random.random() < 0.2:
            query += " property:refereed"
        examples.append({"natural_language": nl, "ads_query": query, "category": "filters"})

    # Multi-keyword
    examples.append({
        "natural_language": "articles with keyword cosmology and large-scale structure",
        "ads_query": 'keyword:"cosmology" keyword:"large-scale structure" doctype:article',
        "category": "filters",
    })
    examples.append({
        "natural_language": "papers with keyword molecular clouds and star formation",
        "ads_query": 'keyword:"molecular clouds" keyword:"star formation"',
        "category": "filters",
    })
    examples.append({
        "natural_language": "articles with keyword instrumentation and methods",
        "ads_query": 'keyword:"instrumentation" keyword:"methods" doctype:article',
        "category": "filters",
    })

    return examples


def generate_arxiv_class_examples() -> list[dict]:
    """Generate arxiv_class: filter examples."""
    examples = []

    for arxiv_class, nl_variants in ARXIV_CLASSES:
        nl = random.choice(nl_variants)
        query = f"arxiv_class:{arxiv_class}"
        if "eprint" in nl:
            query += " doctype:eprint"
        examples.append({"natural_language": nl, "ads_query": query, "category": "filters"})

    return examples


def generate_lang_example() -> list[dict]:
    """Generate language filter example."""
    return [
        {
            "natural_language": "astronomy papers published in French",
            "ads_query": "database:astronomy lang:fr",
            "category": "filters",
        },
    ]


def generate_vizier_example() -> list[dict]:
    """Generate vizier: example."""
    return [
        {
            "natural_language": "papers with VizieR catalog data related to infrared photometry",
            "ads_query": 'vizier:"Infrared" abs:"photometry"',
            "category": "filters",
        },
    ]


def generate_mention_filter_examples() -> list[dict]:
    """Generate mention/software filter examples."""
    return [
        {
            "natural_language": "papers that mention astropy software",
            "ads_query": 'abs:"astropy" mention_count:[1 TO *]',
            "category": "filters",
        },
        {
            "natural_language": "software packages for spectral fitting that are credited by up to 100 papers",
            "ads_query": 'credit_count:[1 TO 100] full:"spectral fitting" doctype:software',
            "category": "filters",
        },
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Generate filter-based training examples"
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/datasets/generated/filters_examples.json"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    examples = []
    examples.extend(generate_esources_examples())
    examples.extend(generate_has_examples())
    examples.extend(generate_grant_examples())
    examples.extend(generate_ack_examples())
    examples.extend(generate_keyword_examples())
    examples.extend(generate_arxiv_class_examples())
    examples.extend(generate_lang_example())
    examples.extend(generate_vizier_example())
    examples.extend(generate_mention_filter_examples())

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

    print(f"Generated {len(unique)} filter examples")


if __name__ == "__main__":
    main()
