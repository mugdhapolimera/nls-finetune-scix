#!/usr/bin/env python3
"""
Generate training data for compound multi-field queries.

Covers combinations of: property + operator, property + data, property + bibstem,
property + institution, citation_count, negation (NOT/-), grant + topic,
keyword + filters, arxiv_class + topic, orcid + topic, and more verbose NL.

Usage:
    python scripts/generate_compound_examples.py \
        --output data/datasets/generated/compound_examples.json
"""

import argparse
import json
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Seed data for compound queries
# ---------------------------------------------------------------------------

# property + data archive
PROP_DATA = [
    ("refereed papers with Chandra data on AGN", 'property:refereed data:Chandra abs:"AGN"'),
    ("peer-reviewed papers with MAST archive data on stellar winds", 'property:refereed data:MAST abs:"stellar winds"'),
    ("refereed publications using SIMBAD data on binary stars", 'property:refereed data:SIMBAD abs:"binary stars"'),
    ("refereed papers with NED data on galaxy clusters", 'property:refereed data:NED abs:"galaxy clusters"'),
    ("peer-reviewed articles with IRSA data on dust emission", 'property:refereed data:IRSA abs:"dust emission"'),
]

# property + operator
PROP_OP = [
    ("trending open access papers on exoplanets", 'trending(abs:"exoplanet") property:openaccess'),
    ("useful refereed papers about dark energy", 'useful(abs:"dark energy") property:refereed'),
    ("reviews of peer-reviewed cosmology literature", 'reviews(abs:"cosmology") property:refereed'),
    ("trending non-refereed papers on machine learning in astronomy", 'trending(abs:"machine learning") property:notrefereed'),
]

# property + citation_count
PROP_CITE = [
    ("highly cited peer-reviewed cosmology papers", 'abs:"cosmology" property:refereed citation_count:[100 TO *]'),
    ("well-cited open access papers on galaxy evolution", 'abs:"galaxy evolution" property:openaccess citation_count:[50 TO *]'),
    ("refereed papers on quasars with more than 200 citations", 'abs:"quasars" property:refereed citation_count:[200 TO *]'),
]

# property negation
PROP_NEG = [
    ("refereed dark energy papers excluding preprints", 'abs:"dark energy" property:refereed -property:eprint'),
    ("non-article records about supernovae that are refereed", 'abs:"supernova" property:nonarticle property:refereed'),
    ("open access papers on stellar evolution that are not preprints", 'abs:"stellar evolution" property:openaccess -property:eprint'),
]

# property + bibstem
PROP_BIBSTEM = [
    ("open access ApJ papers on stellar nucleosynthesis", 'property:openaccess bibstem:"ApJ" abs:"stellar nucleosynthesis"'),
    ("refereed MNRAS papers about galaxy clusters", 'property:refereed bibstem:"MNRAS" abs:"galaxy clusters"'),
    ("open access A&A papers on protoplanetary disks", 'property:openaccess bibstem:"A&A" abs:"protoplanetary disks"'),
    ("highly cited Nature papers on cosmic microwave background", 'bibstem:"Nature" abs:"cosmic microwave background" citation_count:[50 TO *]'),
    ("refereed ApJ papers by Perlmutter on supernovae since 1998", 'bibstem:"ApJ" author:"Perlmutter" abs:"supernova" property:refereed pubdate:[1998 TO *]'),
    ("recent MNRAS papers on machine learning for galaxy classification", 'bibstem:"MNRAS" abs:"machine learning" abs:"galaxy classification" pubdate:[2020 TO 2026]'),
]

# property + software
PROP_SOFTWARE = [
    ("software packages cited in gravitational wave research", 'property:software citations(abs:"gravitational waves")'),
    ("refereed software papers about data reduction pipelines", 'property:refereed doctype:software abs:"data reduction"'),
    ("software records with associated data products", "property:software property:data"),
    ("refereed papers with associated software records", "property:software property:refereed"),
]

# property + institution
PROP_INST = [
    ("open access papers from NASA about Mars exploration", 'property:openaccess (inst:"JPL" OR inst:"GSFC" OR inst:"NASA Ames" OR inst:"MSFC" OR aff:"NASA") abs:"Mars"'),
    ("refereed papers from ESO on adaptive optics", 'property:refereed (inst:"ESO" OR aff:"ESO") abs:"adaptive optics"'),
    ("refereed papers from the Goddard Space Flight Center on X-ray astronomy", 'inst:"GSFC" abs:"X-ray" property:refereed'),
    ('highly cited papers from the Max Planck Institute on galaxy formation', '(inst:"MPA" OR inst:"MPE" OR inst:"MPIA" OR aff:"Max Planck") abs:"galaxy formation" citation_count:[100 TO *]'),
    ("first-author papers from IPAC on infrared surveys", 'inst:"IPAC" abs:"infrared survey" property:refereed'),
    ('open access papers from the University of Hawaii on telescopes', '(inst:"U Hawaii" OR aff:"University of Hawaii") abs:"telescope" property:openaccess'),
    ('recent papers from the Kavli Institute on gravitational waves since 2020', '(inst:"KIPAC" OR inst:"KITP" OR aff:"Kavli") abs:"gravitational waves" pubdate:[2020 TO 2026]'),
    ('papers from CERN published in Physical Review Letters', '(inst:"CERN" OR aff:"CERN") bibstem:"PhRvL"'),
]

# property + time
PROP_TIME = [
    ("refereed open access papers on neutron stars from the last 5 years", 'abs:"neutron stars" property:refereed property:openaccess pubdate:[2021 TO 2026]'),
    ("peer-reviewed exoplanet papers published in 2023 with data links", 'abs:"exoplanet" property:refereed property:data year:2023'),
]

# property + bibgroup
PROP_BIBGROUP = [
    ("refereed JWST papers on early universe galaxies", 'property:refereed bibgroup:JWST abs:"early universe" abs:"galaxies"'),
    ("open access HST papers on planetary nebulae", 'property:openaccess bibgroup:HST abs:"planetary nebulae"'),
]

# property + esources
PROP_ESOURCES = [
    ("refereed papers with publisher PDFs about magnetars", 'property:refereed esources:PUB_PDF abs:"magnetar"'),
    ("open access papers with scanned articles on historical astronomy", 'property:openaccess esources:ADS_SCAN abs:"historical astronomy"'),
]

# property + author
PROP_AUTHOR = [
    ("refereed papers by Hawking on black hole thermodynamics", 'author:"Hawking, S" abs:"black hole thermodynamics" property:refereed'),
    ("open access first-author papers by Riess on supernovae", 'author:"^Riess" abs:"supernova" property:openaccess'),
]

# property + misc
PROP_MISC = [
    ("refereed catalog records in the astronomy database", "property:refereed property:catalog database:astronomy"),
    ("conference proceedings with associated open access resources on cosmological simulations", 'property:inproceedings property:openaccess abs:"cosmological simulations"'),
    ("refereed papers with linked data sources on exoplanets", 'has:data abs:"exoplanets" property:refereed'),
    ("software mentioned in papers by Jarmak about planetary atmospheres", 'author:"Jarmak, Stephanie" has:mention abs:"planetary atmospheres"'),
]

# credit/mention compound
CREDIT_MENTION = [
    ("popular software packages for radio astronomy", 'credit_count:[10 TO *] doctype:software abs:"radio astronomy"'),
    ("widely-used data reduction software", 'credit_count:[50 TO *] doctype:software abs:"data reduction"'),
    ("software tools with at least 20 credits used in cosmological simulations", 'credit_count:[20 TO *] doctype:software abs:"cosmological simulations"'),
    ("most credited software in the astronomy database", "credit_count:[100 TO *] doctype:software collection:astronomy"),
    ("papers that reference multiple software packages about photometry", 'mention_count:[3 TO *] abs:"photometry"'),
    ("papers citing many data sources on galaxy redshift surveys", 'mention_count:[5 TO *] abs:"galaxy redshift survey"'),
    ("refereed papers mentioning at least 10 software or data records", "mention_count:[10 TO *] property:refereed"),
    ("NASA-funded papers that mention software packages", "grant:NASA has:mention doctype:article"),
    ('papers acknowledging NSF funding with software mentions', 'ack:"NSF" has:mention'),
    ("refereed papers with grant info that mention data records", "has:grant has:mention property:refereed"),
    ("software packages credited by at least one paper", "credit_count:[1 TO *] doctype:software"),
    ('recent papers by Smith that mention software packages', 'author:"Smith" has:mention pubdate:[2020 TO 2026]'),
    ('ApJ papers with software mentions on machine learning', 'bibstem:"ApJ" has:mention abs:"machine learning"'),
    ("papers with data mentions in the Chandra bibgroup", "has:mention bibgroup:Chandra"),
    ("highly cited papers that mention software", "has:mention citation_count:[100 TO *]"),
]

# grant compound
GRANT_COMPOUND = [
    ("research papers funded by NASA grants on dark matter", 'abs:"dark matter" (grant:NASA OR ack:"NASA") doctype:article'),
    ("NASA proposals related to exoplanets", 'doctype:proposal grant:NASA abs:"exoplanet"'),
    ("NSF-funded proposals on computational astrophysics", 'doctype:proposal grant:NSF abs:"computational astrophysics"'),
    ("NASA-funded refereed papers on black holes since 2020", 'grant:NASA abs:"black hole" property:refereed pubdate:[2020 TO 2026]'),
    ('papers acknowledging NSF funding for computational resources', 'ack:"NSF" abs:"computational"'),
]

# Negation (NOT / -)
NEGATION = [
    ("dark matter papers not about WIMPs", 'abs:"dark matter" NOT abs:"WIMP" doctype:article'),
    ("supernova papers excluding Type Ia", 'abs:"supernova" NOT abs:"Type Ia"'),
    ("stellar evolution articles but not about red giants", 'abs:"stellar evolution" -abs:"red giant" doctype:article'),
    ("galaxy surveys not in the physics collection", 'abs:"galaxy survey" NOT collection:physics'),
    ("magnetar papers not by Kaspi", 'abs:"magnetar" -author:"Kaspi" doctype:article'),
    ("exoplanet detection papers excluding radial velocity method", 'abs:"exoplanet detection" -abs:"radial velocity"'),
    ("black hole papers not published in ApJ", 'abs:"black hole" -bibstem:"ApJ" doctype:article'),
    ("gravitational wave articles excluding LIGO bibgroup", 'abs:"gravitational wave" NOT bibgroup:LIGO doctype:article'),
    ("solar flare papers that are not conference proceedings", 'abs:"solar flare" NOT doctype:inproceedings'),
    ("cosmology papers excluding preprints", 'abs:"cosmology" -property:eprint property:refereed'),
    ("neutron star papers not about pulsars", 'abs:"neutron star" -abs:"pulsar"'),
    ("star formation articles but not in molecular clouds", 'abs:"star formation" NOT abs:"molecular cloud" doctype:article'),
    ("AGN variability papers not from the Kepler mission", 'abs:"AGN variability" NOT bibgroup:Kepler'),
    ("interstellar medium studies excluding HII regions", 'abs:"interstellar medium" -abs:"HII region"'),
    ("planetary science papers not about Mars", 'abs:"planetary science" NOT abs:"Mars"'),
    ("refereed galaxy papers excluding reviews", 'abs:"galaxy" property:refereed -property:nonarticle'),
    ("white dwarf papers not involving binary systems", 'abs:"white dwarf" -abs:"binary" doctype:article'),
    ("infrared astronomy papers not from Spitzer", 'abs:"infrared" -bibgroup:Spitzer doctype:article'),
    ("quasar absorption lines excluding Lyman alpha forest", 'abs:"quasar absorption" -abs:"Lyman alpha forest"'),
    ("high-redshift galaxy papers excluding photometric redshifts", 'abs:"high-redshift galaxy" NOT abs:"photometric redshift"'),
    ("stellar spectroscopy papers not about M dwarfs", 'abs:"stellar spectroscopy" -abs:"M dwarf"'),
    ("papers on tidal disruption events but not in X-ray", 'abs:"tidal disruption" -abs:"X-ray"'),
    ('Milky Way structure papers not about the bulge', 'abs:"Milky Way" abs:"structure" NOT abs:"bulge"'),
    ("extrasolar planet papers excluding hot Jupiters and mini-Neptunes", 'abs:"extrasolar planet" -abs:"hot Jupiter" -abs:"mini-Neptune"'),
    ("refereed articles on gamma-ray astronomy not by Fermi collaboration", 'abs:"gamma-ray" -bibgroup:Fermi property:refereed doctype:article'),
]

# keyword compound
KEYWORD_COMPOUND = [
    ('articles with keyword accretion disks published since 2015', 'keyword:"accretion" pubdate:[2015 TO 2026] doctype:article'),
    ('papers tagged with keyword active galactic nuclei by Smith', 'keyword:"active galactic nuclei" author:"Smith" doctype:article'),
    ('articles with keyword surveys published in MNRAS', 'keyword:"surveys" bibstem:"MNRAS" doctype:article'),
]

# arxiv_class + topic
ARXIV_COMPOUND = [
    ("nuclear theory preprints about neutron stars", 'arxiv_class:nucl-th abs:"neutron star"'),
]

# orcid + topic
ORCID_COMPOUND = [
    ("papers by ORCID 0000-0001-5000-0007 on stellar evolution", 'orcid:0000-0001-5000-0007 abs:"stellar evolution"'),
]

# Verbose NL compound (already partly in verbose_nl script, these are the additional ones)
VERBOSE_COMPOUND = [
    ("I'm looking for recent research papers that discuss the relationship between galaxy mergers and the triggering of active galactic nuclei in the local universe",
     'abs:"galaxy mergers" abs:"active galactic nuclei" pubdate:[2018 TO 2026] doctype:article'),
    ("Can you find me studies about how the cosmic microwave background radiation can be used to constrain models of inflation in the early universe",
     'abs:"cosmic microwave background" abs:"inflation" doctype:article'),
    ("I need to find all the published work on using gravitational microlensing surveys to detect free-floating planets in our galaxy",
     'abs:"gravitational microlensing" abs:"free-floating planet" doctype:article'),
    ("What papers exist about the chemical enrichment history of dwarf galaxies in the Local Group and what it tells us about early star formation",
     'abs:"chemical enrichment" abs:"dwarf galaxies" abs:"Local Group"'),
    ("I want to understand what has been written about the formation and evolution of supermassive black holes at the centers of galaxies and how they co-evolve with their host galaxies",
     'abs:"supermassive black hole" abs:"co-evolution" abs:"host galaxy"'),
    ("Find me papers about how astronomers are using the James Webb Space Telescope to study the atmospheres of rocky exoplanets in the habitable zone",
     'abs:"JWST" abs:"rocky exoplanet" abs:"atmosphere" abs:"habitable zone" doctype:article'),
    ("I'm interested in the current state of research on whether the expansion of the universe is really accelerating and the evidence for or against dark energy",
     'abs:"accelerating expansion" abs:"dark energy" doctype:article'),
    ("Are there papers discussing the use of radio interferometry techniques like VLBI for studying jets from supermassive black holes in active galaxies",
     'abs:"VLBI" abs:"jet" abs:"supermassive black hole" doctype:article'),
    ("Help me find published research on the effects of stellar feedback including supernovae and stellar winds on the interstellar medium in nearby galaxies",
     'abs:"stellar feedback" abs:"interstellar medium" abs:"nearby galaxies" doctype:article'),
]


def generate_examples() -> list[dict]:
    examples = []

    all_pairs = (
        PROP_DATA + PROP_OP + PROP_CITE + PROP_NEG + PROP_BIBSTEM +
        PROP_SOFTWARE + PROP_INST + PROP_TIME + PROP_BIBGROUP +
        PROP_ESOURCES + PROP_AUTHOR + PROP_MISC +
        CREDIT_MENTION + GRANT_COMPOUND + NEGATION +
        KEYWORD_COMPOUND + ARXIV_COMPOUND + ORCID_COMPOUND +
        VERBOSE_COMPOUND
    )

    for nl, query in all_pairs:
        examples.append({
            "natural_language": nl,
            "ads_query": query,
            "category": "compound",
        })

    return examples


def main():
    parser = argparse.ArgumentParser(description="Generate compound multi-field training examples")
    parser.add_argument("--output", type=Path, default=Path("data/datasets/generated/compound_examples.json"))
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
    print(f"Generated {len(unique)} compound examples")


if __name__ == "__main__":
    main()
