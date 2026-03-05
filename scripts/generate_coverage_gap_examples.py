#!/usr/bin/env python3
"""Generate training examples to fill coverage gaps in gold_examples.json.

Adds ~210 examples across 17 categories that were identified as under-covered
by the training data coverage audit (2026-03-04):

    P0 (critical):  esources (16), data archives (24), NOT/negation (25)
    P1 (sparse):    has (20), grant (11), ack (10), keyword (15), arxiv_class (10),
                    orcid (8), entry_date (8), object (10)
    P2 (use cases): proximity (5), exact author (5), cross-domain (8),
                    mentions (5), verbose NL (10)
    P3 (balance):   similar() (10), references() (10)

Usage:
    python scripts/generate_coverage_gap_examples.py

WARNING: This script appends to gold_examples.json. Running it multiple times
will create duplicates. Check the file before re-running.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_FILE = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples.json"

# Load existing examples
with open(GOLD_FILE) as f:
    existing = json.load(f)

new_examples = []

# =============================================================================
# P0: ESOURCES (missing: PUB_HTML, EPRINT_HTML, AUTHOR_PDF, AUTHOR_HTML, ADS_PDF)
# =============================================================================
esources_examples = [
    # PUB_HTML
    {"natural_language": "papers on stellar nucleosynthesis with HTML full text from the publisher",
     "ads_query": "abs:\"stellar nucleosynthesis\" esources:PUB_HTML", "category": "filters"},
    {"natural_language": "find galaxy evolution articles available as publisher HTML",
     "ads_query": "abs:\"galaxy evolution\" esources:PUB_HTML doctype:article", "category": "filters"},
    # EPRINT_HTML
    {"natural_language": "dark energy preprints with HTML version on arXiv",
     "ads_query": "abs:\"dark energy\" esources:EPRINT_HTML doctype:eprint", "category": "filters"},
    {"natural_language": "papers on neutrino oscillations available as eprint HTML",
     "ads_query": "abs:\"neutrino oscillations\" esources:EPRINT_HTML", "category": "filters"},
    # AUTHOR_PDF
    {"natural_language": "papers with author-provided PDF on cosmic ray acceleration",
     "ads_query": "abs:\"cosmic ray acceleration\" esources:AUTHOR_PDF", "category": "filters"},
    {"natural_language": "find author-submitted PDFs about gravitational lensing",
     "ads_query": "abs:\"gravitational lensing\" esources:AUTHOR_PDF doctype:article", "category": "filters"},
    # AUTHOR_HTML
    {"natural_language": "articles with author HTML version about quasar variability",
     "ads_query": "abs:\"quasar variability\" esources:AUTHOR_HTML", "category": "filters"},
    {"natural_language": "find papers on radio galaxies with author-hosted HTML",
     "ads_query": "abs:\"radio galaxies\" esources:AUTHOR_HTML", "category": "filters"},
    # ADS_PDF
    {"natural_language": "papers with ADS PDF available on black hole thermodynamics",
     "ads_query": "abs:\"black hole thermodynamics\" esources:ADS_PDF", "category": "filters"},
    {"natural_language": "find articles on interstellar dust available as ADS PDF",
     "ads_query": "abs:\"interstellar dust\" esources:ADS_PDF doctype:article", "category": "filters"},
    # Mixed / compound esources
    {"natural_language": "open access papers on AGN feedback with publisher PDF or HTML",
     "ads_query": "abs:\"AGN feedback\" (esources:PUB_PDF OR esources:PUB_HTML) property:openaccess", "category": "filters"},
    {"natural_language": "historical papers on Cepheid variables with scanned versions",
     "ads_query": "abs:\"Cepheid variables\" esources:ADS_SCAN pubdate:[1900 TO 1970]", "category": "filters"},
    {"natural_language": "recent refereed articles on exoplanet atmospheres with publisher PDF",
     "ads_query": "abs:\"exoplanet atmospheres\" esources:PUB_PDF property:refereed pubdate:[2020 TO 2026]", "category": "filters"},
    {"natural_language": "preprints on fast radio bursts available as eprint PDF",
     "ads_query": "abs:\"fast radio bursts\" esources:EPRINT_PDF doctype:eprint", "category": "filters"},
    {"natural_language": "papers on pulsar timing with any author-provided version",
     "ads_query": "abs:\"pulsar timing\" (esources:AUTHOR_PDF OR esources:AUTHOR_HTML)", "category": "filters"},
    {"natural_language": "supernova remnant papers from the 1980s with ADS scans",
     "ads_query": "abs:\"supernova remnant\" esources:ADS_SCAN pubdate:[1980 TO 1989]", "category": "filters"},
]
new_examples.extend(esources_examples)

# =============================================================================
# P0: DATA FIELD (missing many archive values)
# =============================================================================
data_examples = [
    # NED
    {"natural_language": "galaxy cluster papers with NED data links",
     "ads_query": "abs:\"galaxy cluster\" data:NED doctype:article", "category": "data"},
    {"natural_language": "extragalactic distance papers linked to NED",
     "ads_query": "abs:\"extragalactic distance\" data:NED", "category": "data"},
    # VizieR
    {"natural_language": "papers with VizieR catalog data on stellar photometry",
     "ads_query": "abs:\"stellar photometry\" data:VizieR", "category": "data"},
    {"natural_language": "articles linked to VizieR catalogs about variable stars",
     "ads_query": "abs:\"variable stars\" data:VizieR doctype:article", "category": "data"},
    # IRSA
    {"natural_language": "infrared survey papers with IRSA data",
     "ads_query": "abs:\"infrared survey\" data:IRSA", "category": "data"},
    {"natural_language": "papers using IRSA archive data on dust emission",
     "ads_query": "abs:\"dust emission\" data:IRSA doctype:article", "category": "data"},
    # HEASARC
    {"natural_language": "X-ray binary papers linked to HEASARC",
     "ads_query": "abs:\"X-ray binary\" data:HEASARC", "category": "data"},
    {"natural_language": "gamma-ray burst articles with HEASARC data",
     "ads_query": "abs:\"gamma-ray burst\" data:HEASARC doctype:article", "category": "data"},
    # MAST
    {"natural_language": "Hubble papers with MAST archive data",
     "ads_query": "abs:\"Hubble\" data:MAST doctype:article", "category": "data"},
    {"natural_language": "papers using MAST data on planetary nebulae",
     "ads_query": "abs:\"planetary nebulae\" data:MAST", "category": "data"},
    # PDS
    {"natural_language": "Mars surface papers with Planetary Data System links",
     "ads_query": "abs:\"Mars surface\" data:PDS", "category": "data"},
    {"natural_language": "asteroid spectroscopy papers linked to PDS",
     "ads_query": "abs:\"asteroid spectroscopy\" data:PDS doctype:article", "category": "data"},
    # NExScI
    {"natural_language": "exoplanet characterization papers with NExScI data",
     "ads_query": "abs:\"exoplanet characterization\" data:NExScI", "category": "data"},
    {"natural_language": "transit photometry articles linked to NExScI",
     "ads_query": "abs:\"transit photometry\" data:NExScI doctype:article", "category": "data"},
    # SIMBAD
    {"natural_language": "papers on globular clusters with SIMBAD links",
     "ads_query": "abs:\"globular clusters\" data:SIMBAD", "category": "data"},
    {"natural_language": "stellar classification articles linked to SIMBAD",
     "ads_query": "abs:\"stellar classification\" data:SIMBAD doctype:article", "category": "data"},
    # ESO
    {"natural_language": "VLT spectroscopy papers with ESO archive data",
     "ads_query": "abs:\"VLT spectroscopy\" data:ESO", "category": "data"},
    {"natural_language": "articles using ESO data on galaxy morphology",
     "ads_query": "abs:\"galaxy morphology\" data:ESO doctype:article", "category": "data"},
    # XMM
    {"natural_language": "active galactic nuclei papers with XMM data",
     "ads_query": "abs:\"active galactic nuclei\" data:XMM", "category": "data"},
    # KOA
    {"natural_language": "Keck observations of brown dwarfs with KOA archive data",
     "ads_query": "abs:\"brown dwarfs\" data:KOA", "category": "data"},
    # CXO
    {"natural_language": "Chandra X-ray observations with CXO data links",
     "ads_query": "abs:\"Chandra X-ray\" data:CXO", "category": "data"},
    # Herschel
    {"natural_language": "far-infrared papers linked to Herschel archive",
     "ads_query": "abs:\"far-infrared\" data:Herschel", "category": "data"},
    # ESA
    {"natural_language": "Gaia astrometry papers with ESA data links",
     "ads_query": "abs:\"Gaia astrometry\" data:ESA", "category": "data"},
    # TNS
    {"natural_language": "transient discovery papers linked to TNS",
     "ads_query": "abs:\"transient\" data:TNS doctype:article", "category": "data"},
]
new_examples.extend(data_examples)

# =============================================================================
# P0: NOT/NEGATION (expand exclusion patterns)
# =============================================================================
not_examples = [
    {"natural_language": "dark matter papers not about WIMPs",
     "ads_query": "abs:\"dark matter\" NOT abs:\"WIMP\" doctype:article", "category": "compound"},
    {"natural_language": "supernova papers excluding Type Ia",
     "ads_query": "abs:\"supernova\" NOT abs:\"Type Ia\"", "category": "compound"},
    {"natural_language": "stellar evolution articles but not about red giants",
     "ads_query": "abs:\"stellar evolution\" -abs:\"red giant\" doctype:article", "category": "compound"},
    {"natural_language": "galaxy surveys not in the physics collection",
     "ads_query": "abs:\"galaxy survey\" NOT collection:physics", "category": "compound"},
    {"natural_language": "magnetar papers not by Kaspi",
     "ads_query": "abs:\"magnetar\" -author:\"Kaspi\" doctype:article", "category": "compound"},
    {"natural_language": "exoplanet detection papers excluding radial velocity method",
     "ads_query": "abs:\"exoplanet detection\" -abs:\"radial velocity\"", "category": "compound"},
    {"natural_language": "black hole papers not published in ApJ",
     "ads_query": "abs:\"black hole\" -bibstem:\"ApJ\" doctype:article", "category": "compound"},
    {"natural_language": "gravitational wave articles excluding LIGO bibgroup",
     "ads_query": "abs:\"gravitational wave\" NOT bibgroup:LIGO doctype:article", "category": "compound"},
    {"natural_language": "solar flare papers that are not conference proceedings",
     "ads_query": "abs:\"solar flare\" NOT doctype:inproceedings", "category": "compound"},
    {"natural_language": "cosmology papers excluding preprints",
     "ads_query": "abs:\"cosmology\" -property:eprint property:refereed", "category": "compound"},
    {"natural_language": "neutron star papers not about pulsars",
     "ads_query": "abs:\"neutron star\" -abs:\"pulsar\"", "category": "compound"},
    {"natural_language": "star formation articles but not in molecular clouds",
     "ads_query": "abs:\"star formation\" NOT abs:\"molecular cloud\" doctype:article", "category": "compound"},
    {"natural_language": "AGN variability papers not from the Kepler mission",
     "ads_query": "abs:\"AGN variability\" NOT bibgroup:Kepler", "category": "compound"},
    {"natural_language": "interstellar medium studies excluding HII regions",
     "ads_query": "abs:\"interstellar medium\" -abs:\"HII region\"", "category": "compound"},
    {"natural_language": "planetary science papers not about Mars",
     "ads_query": "abs:\"planetary science\" NOT abs:\"Mars\"", "category": "compound"},
    {"natural_language": "refereed galaxy papers excluding reviews",
     "ads_query": "abs:\"galaxy\" property:refereed -property:nonarticle", "category": "compound"},
    {"natural_language": "white dwarf papers not involving binary systems",
     "ads_query": "abs:\"white dwarf\" -abs:\"binary\" doctype:article", "category": "compound"},
    {"natural_language": "infrared astronomy papers not from Spitzer",
     "ads_query": "abs:\"infrared\" -bibgroup:Spitzer doctype:article", "category": "compound"},
    {"natural_language": "quasar absorption lines excluding Lyman alpha forest",
     "ads_query": "abs:\"quasar absorption\" -abs:\"Lyman alpha forest\"", "category": "compound"},
    {"natural_language": "high-redshift galaxy papers excluding photometric redshifts",
     "ads_query": "abs:\"high-redshift galaxy\" NOT abs:\"photometric redshift\"", "category": "compound"},
    {"natural_language": "stellar spectroscopy papers not about M dwarfs",
     "ads_query": "abs:\"stellar spectroscopy\" -abs:\"M dwarf\"", "category": "compound"},
    {"natural_language": "papers on tidal disruption events but not in X-ray",
     "ads_query": "abs:\"tidal disruption\" -abs:\"X-ray\"", "category": "compound"},
    {"natural_language": "Milky Way structure papers not about the bulge",
     "ads_query": "abs:\"Milky Way\" abs:\"structure\" NOT abs:\"bulge\"", "category": "compound"},
    {"natural_language": "extrasolar planet papers excluding hot Jupiters and mini-Neptunes",
     "ads_query": "abs:\"extrasolar planet\" -abs:\"hot Jupiter\" -abs:\"mini-Neptune\"", "category": "compound"},
    {"natural_language": "refereed articles on gamma-ray astronomy not by Fermi collaboration",
     "ads_query": "abs:\"gamma-ray\" -bibgroup:Fermi property:refereed doctype:article", "category": "compound"},
]
new_examples.extend(not_examples)

# =============================================================================
# P1: HAS field expansion (missing values from HAS_VALUES)
# =============================================================================
has_examples = [
    {"natural_language": "papers with DOI identifiers about stellar winds",
     "ads_query": "has:doi abs:\"stellar winds\"", "category": "filters"},
    {"natural_language": "articles that have bibliographic group assignments",
     "ads_query": "has:bibgroup abs:\"galaxy survey\" doctype:article", "category": "filters"},
    {"natural_language": "papers with volume information about cosmology",
     "ads_query": "has:volume abs:\"cosmology\" doctype:article", "category": "filters"},
    {"natural_language": "articles that have issue numbers on gravitational lensing",
     "ads_query": "has:issue abs:\"gravitational lensing\" doctype:article", "category": "filters"},
    {"natural_language": "papers with institutional affiliations on dark energy",
     "ads_query": "has:institution abs:\"dark energy\"", "category": "filters"},
    {"natural_language": "papers with unified astronomy thesaurus tags about star formation",
     "ads_query": "has:uat abs:\"star formation\"", "category": "filters"},
    {"natural_language": "papers with publisher information about neutron stars",
     "ads_query": "has:publisher abs:\"neutron stars\"", "category": "filters"},
    {"natural_language": "articles that have comments about supernova remnants",
     "ads_query": "has:comment abs:\"supernova remnants\" doctype:article", "category": "filters"},
    {"natural_language": "papers with ORCID identifiers from other sources",
     "ads_query": "has:orcid_other abs:\"exoplanet\"", "category": "filters"},
    {"natural_language": "papers with ORCID user claims about quasars",
     "ads_query": "has:orcid_user abs:\"quasars\"", "category": "filters"},
    {"natural_language": "papers with credited software on spectroscopy",
     "ads_query": "has:credit abs:\"spectroscopy\"", "category": "filters"},
    {"natural_language": "papers with reference lists about black hole mergers",
     "ads_query": "has:reference abs:\"black hole merger\"", "category": "filters"},
    {"natural_language": "papers that have associated data links on galaxy clusters",
     "ads_query": "has:data abs:\"galaxy clusters\" doctype:article", "category": "filters"},
    {"natural_language": "articles with raw publication info on cosmic microwave background",
     "ads_query": "has:pub_raw abs:\"cosmic microwave background\" doctype:article", "category": "filters"},
    {"natural_language": "papers that have database assignments in astronomy",
     "ads_query": "has:database abs:\"stellar populations\" doctype:article", "category": "filters"},
    {"natural_language": "papers with first author metadata about AGN",
     "ads_query": "has:first_author abs:\"active galactic nuclei\"", "category": "filters"},
    {"natural_language": "papers with affiliation IDs on gravitational waves",
     "ads_query": "has:aff_id abs:\"gravitational waves\"", "category": "filters"},
    {"natural_language": "papers with origin metadata about solar physics",
     "ads_query": "has:origin abs:\"solar physics\"", "category": "filters"},
    {"natural_language": "papers with property flags about planet formation",
     "ads_query": "has:property abs:\"planet formation\"", "category": "filters"},
    {"natural_language": "papers with doctype metadata in the astronomy collection",
     "ads_query": "has:doctype collection:astronomy", "category": "filters"},
]
new_examples.extend(has_examples)

# =============================================================================
# P1: GRANT field
# =============================================================================
grant_examples = [
    {"natural_language": "papers funded by NSF on galaxy evolution",
     "ads_query": "grant:NSF abs:\"galaxy evolution\" doctype:article", "category": "filters"},
    {"natural_language": "NASA-funded research on exoplanet detection",
     "ads_query": "grant:NASA abs:\"exoplanet detection\"", "category": "filters"},
    {"natural_language": "DOE-funded papers on dark energy surveys",
     "ads_query": "grant:DOE abs:\"dark energy survey\"", "category": "filters"},
    {"natural_language": "ESA-funded articles on space missions",
     "ads_query": "grant:ESA abs:\"space mission\" doctype:article", "category": "filters"},
    {"natural_language": "papers funded by the European Research Council on stellar astrophysics",
     "ads_query": "grant:ERC abs:\"stellar astrophysics\"", "category": "filters"},
    {"natural_language": "STFC-funded research on radio astronomy",
     "ads_query": "grant:STFC abs:\"radio astronomy\"", "category": "filters"},
    {"natural_language": "NASA-funded refereed papers on black holes since 2020",
     "ads_query": "grant:NASA abs:\"black hole\" property:refereed pubdate:[2020 TO 2026]", "category": "compound"},
    {"natural_language": "NSF grants research on machine learning in astronomy",
     "ads_query": "grant:NSF abs:\"machine learning\" collection:astronomy", "category": "filters"},
    {"natural_language": "papers with any grant funding on gravitational wave detection",
     "ads_query": "has:grant abs:\"gravitational wave detection\"", "category": "filters"},
    {"natural_language": "DFG-funded papers on interstellar medium",
     "ads_query": "grant:DFG abs:\"interstellar medium\"", "category": "filters"},
    {"natural_language": "CSA-funded research on space debris",
     "ads_query": "grant:CSA abs:\"space debris\"", "category": "filters"},
]
new_examples.extend(grant_examples)

# =============================================================================
# P1: ACK field
# =============================================================================
ack_examples = [
    {"natural_language": "papers acknowledging Hubble Space Telescope time",
     "ads_query": "ack:\"Hubble Space Telescope\" doctype:article", "category": "filters"},
    {"natural_language": "articles that acknowledge ALMA observations",
     "ads_query": "ack:\"ALMA\" doctype:article", "category": "filters"},
    {"natural_language": "papers acknowledging Keck Observatory",
     "ads_query": "ack:\"Keck Observatory\"", "category": "filters"},
    {"natural_language": "research acknowledging the Sloan Digital Sky Survey",
     "ads_query": "ack:\"Sloan Digital Sky Survey\" doctype:article", "category": "filters"},
    {"natural_language": "papers that thank the European Southern Observatory for telescope time",
     "ads_query": "ack:\"European Southern Observatory\"", "category": "filters"},
    {"natural_language": "articles acknowledging Gemini Observatory",
     "ads_query": "ack:\"Gemini Observatory\" doctype:article", "category": "filters"},
    {"natural_language": "papers acknowledging NSF funding for computational resources",
     "ads_query": "ack:\"NSF\" abs:\"computational\"", "category": "compound"},
    {"natural_language": "articles acknowledging the Chandra X-ray Center",
     "ads_query": "ack:\"Chandra X-ray Center\" doctype:article", "category": "filters"},
    {"natural_language": "papers that acknowledge XSEDE computing resources",
     "ads_query": "ack:\"XSEDE\"", "category": "filters"},
    {"natural_language": "papers acknowledging the National Radio Astronomy Observatory",
     "ads_query": "ack:\"National Radio Astronomy Observatory\" doctype:article", "category": "filters"},
]
new_examples.extend(ack_examples)

# =============================================================================
# P1: KEYWORD field
# =============================================================================
keyword_examples = [
    {"natural_language": "papers with the keyword gravitational lensing",
     "ads_query": "keyword:\"gravitational lensing\"", "category": "filters"},
    {"natural_language": "articles tagged with keyword black hole physics",
     "ads_query": "keyword:\"black hole physics\" doctype:article", "category": "filters"},
    {"natural_language": "papers with keyword stellar evolution",
     "ads_query": "keyword:\"stellar evolution\"", "category": "filters"},
    {"natural_language": "articles with keyword cosmology and large-scale structure",
     "ads_query": "keyword:\"cosmology\" keyword:\"large-scale structure\" doctype:article", "category": "filters"},
    {"natural_language": "papers tagged with planetary atmospheres keyword",
     "ads_query": "keyword:\"planetary atmospheres\"", "category": "filters"},
    {"natural_language": "articles with keyword accretion disks published since 2015",
     "ads_query": "keyword:\"accretion\" pubdate:[2015 TO 2026] doctype:article", "category": "compound"},
    {"natural_language": "papers with keyword galaxy clusters in the astronomy database",
     "ads_query": "keyword:\"galaxy clusters\" collection:astronomy", "category": "filters"},
    {"natural_language": "refereed articles tagged with keyword supernovae",
     "ads_query": "keyword:\"supernovae\" property:refereed doctype:article", "category": "filters"},
    {"natural_language": "papers with keyword molecular clouds and star formation",
     "ads_query": "keyword:\"molecular clouds\" keyword:\"star formation\"", "category": "filters"},
    {"natural_language": "papers tagged with keyword active galactic nuclei by Smith",
     "ads_query": "keyword:\"active galactic nuclei\" author:\"Smith\" doctype:article", "category": "compound"},
    {"natural_language": "articles with keyword instrumentation and methods",
     "ads_query": "keyword:\"instrumentation\" keyword:\"methods\" doctype:article", "category": "filters"},
    {"natural_language": "papers with keyword astrochemistry",
     "ads_query": "keyword:\"astrochemistry\"", "category": "filters"},
    {"natural_language": "papers with keyword techniques: photometric",
     "ads_query": "keyword:\"techniques: photometric\"", "category": "filters"},
    {"natural_language": "papers tagged with keyword radio continuum: galaxies",
     "ads_query": "keyword:\"radio continuum: galaxies\"", "category": "filters"},
    {"natural_language": "articles with keyword surveys published in MNRAS",
     "ads_query": "keyword:\"surveys\" bibstem:\"MNRAS\" doctype:article", "category": "compound"},
]
new_examples.extend(keyword_examples)

# =============================================================================
# P1: ARXIV_CLASS
# =============================================================================
arxiv_examples = [
    {"natural_language": "astrophysics cosmology preprints",
     "ads_query": "arxiv_class:astro-ph.CO", "category": "filters"},
    {"natural_language": "high energy astrophysics eprints",
     "ads_query": "arxiv_class:astro-ph.HE doctype:eprint", "category": "filters"},
    {"natural_language": "solar and stellar astrophysics papers on arXiv",
     "ads_query": "arxiv_class:astro-ph.SR", "category": "filters"},
    {"natural_language": "earth and planetary astrophysics preprints",
     "ads_query": "arxiv_class:astro-ph.EP", "category": "filters"},
    {"natural_language": "arXiv papers on astrophysics of galaxies",
     "ads_query": "arxiv_class:astro-ph.GA", "category": "filters"},
    {"natural_language": "instrumentation and methods for astrophysics eprints",
     "ads_query": "arxiv_class:astro-ph.IM", "category": "filters"},
    {"natural_language": "general relativity and quantum cosmology preprints",
     "ads_query": "arxiv_class:gr-qc", "category": "filters"},
    {"natural_language": "high energy physics theory papers on arXiv",
     "ads_query": "arxiv_class:hep-th", "category": "filters"},
    {"natural_language": "nuclear theory preprints about neutron stars",
     "ads_query": "arxiv_class:nucl-th abs:\"neutron star\"", "category": "compound"},
    {"natural_language": "condensed matter preprints in ADS",
     "ads_query": "arxiv_class:cond-mat", "category": "filters"},
]
new_examples.extend(arxiv_examples)

# =============================================================================
# P1: ORCID fields
# =============================================================================
orcid_examples = [
    {"natural_language": "papers by ORCID 0000-0002-1825-0097",
     "ads_query": "orcid:0000-0002-1825-0097", "category": "identifier"},
    {"natural_language": "find articles by the author with ORCID 0000-0003-1234-5678",
     "ads_query": "orcid:0000-0003-1234-5678 doctype:article", "category": "identifier"},
    {"natural_language": "papers with publisher-verified ORCID on dark matter",
     "ads_query": "has:orcid_pub abs:\"dark matter\"", "category": "filters"},
    {"natural_language": "find papers where the first author has a verified ORCID",
     "ads_query": "has:orcid_pub author:\"^Smith\" doctype:article", "category": "filters"},
    {"natural_language": "papers with user-claimed ORCID identifiers on exoplanets",
     "ads_query": "has:orcid_user abs:\"exoplanet\"", "category": "filters"},
    {"natural_language": "papers by ORCID 0000-0001-5000-0007 on stellar evolution",
     "ads_query": "orcid:0000-0001-5000-0007 abs:\"stellar evolution\"", "category": "compound"},
    {"natural_language": "look up publications for ORCID 0000-0002-9876-5432",
     "ads_query": "orcid:0000-0002-9876-5432", "category": "identifier"},
    {"natural_language": "refereed papers associated with ORCID 0000-0001-2345-6789",
     "ads_query": "orcid:0000-0001-2345-6789 property:refereed", "category": "identifier"},
]
new_examples.extend(orcid_examples)

# =============================================================================
# P1: ENTRY_DATE
# =============================================================================
entry_date_examples = [
    {"natural_language": "papers added to ADS in the last month",
     "ads_query": "entdate:[NOW-1MONTH TO NOW]", "category": "temporal"},
    {"natural_language": "recently indexed papers on gravitational waves",
     "ads_query": "entdate:[NOW-7DAYS TO NOW] abs:\"gravitational waves\"", "category": "temporal"},
    {"natural_language": "papers added to ADS this week about exoplanets",
     "ads_query": "entdate:[NOW-7DAYS TO NOW] abs:\"exoplanet\"", "category": "temporal"},
    {"natural_language": "new papers indexed in ADS this month on dark energy",
     "ads_query": "entdate:[NOW-1MONTH TO NOW] abs:\"dark energy\"", "category": "temporal"},
    {"natural_language": "papers entered into ADS in January 2025",
     "ads_query": "entdate:[2025-01-01 TO 2025-01-31]", "category": "temporal"},
    {"natural_language": "recently added articles on galaxy mergers",
     "ads_query": "entdate:[NOW-30DAYS TO NOW] abs:\"galaxy mergers\" doctype:article", "category": "temporal"},
    {"natural_language": "papers indexed by ADS in the past year on machine learning",
     "ads_query": "entdate:[NOW-1YEAR TO NOW] abs:\"machine learning\"", "category": "temporal"},
    {"natural_language": "newest ADS entries about fast radio bursts",
     "ads_query": "entdate:[NOW-14DAYS TO NOW] abs:\"fast radio bursts\"", "category": "temporal"},
]
new_examples.extend(entry_date_examples)

# =============================================================================
# P1: OBJECT field expansion
# =============================================================================
object_examples = [
    {"natural_language": "papers about the Crab Nebula",
     "ads_query": "object:\"Crab Nebula\"", "category": "object"},
    {"natural_language": "studies of NGC 1275",
     "ads_query": "object:\"NGC 1275\" doctype:article", "category": "object"},
    {"natural_language": "observations of Sagittarius A*",
     "ads_query": "object:\"Sgr A*\"", "category": "object"},
    {"natural_language": "papers about the Orion Nebula",
     "ads_query": "object:\"Orion Nebula\"", "category": "object"},
    {"natural_language": "studies of 3C 273 quasar",
     "ads_query": "object:\"3C 273\" doctype:article", "category": "object"},
    {"natural_language": "papers about the Large Magellanic Cloud",
     "ads_query": "object:\"LMC\"", "category": "object"},
    {"natural_language": "observations of Vega",
     "ads_query": "object:\"Vega\" doctype:article", "category": "object"},
    {"natural_language": "papers about NGC 4486 radio galaxy",
     "ads_query": "object:\"NGC 4486\"", "category": "object"},
    {"natural_language": "studies of the Triangulum Galaxy",
     "ads_query": "object:\"M33\" doctype:article", "category": "object"},
    {"natural_language": "papers about Proxima Centauri b exoplanet",
     "ads_query": "object:\"Proxima Centauri b\"", "category": "object"},
]
new_examples.extend(object_examples)

# =============================================================================
# P2: PROXIMITY SEARCH (add a few more varied patterns)
# =============================================================================
proximity_examples = [
    {"natural_language": "papers where dark matter and annihilation appear close together in the abstract",
     "ads_query": "abs:(\"dark matter\" NEAR5 annihilation)", "category": "syntax"},
    {"natural_language": "articles with planet and habitability near each other in title",
     "ads_query": "title:(planet NEAR3 habitability)", "category": "syntax"},
    {"natural_language": "papers with supernova and nucleosynthesis within 5 words in abstract",
     "ads_query": "abs:(supernova NEAR5 nucleosynthesis)", "category": "syntax"},
    {"natural_language": "articles with machine learning and classification close together in full text",
     "ads_query": "full:(\"machine learning\" NEAR5 classification)", "category": "syntax"},
    {"natural_language": "papers where accretion and jet appear near each other in the abstract",
     "ads_query": "abs:(accretion NEAR3 jet)", "category": "syntax"},
]
new_examples.extend(proximity_examples)

# =============================================================================
# P2: EXACT AUTHOR MATCHING
# =============================================================================
exact_author_examples = [
    {"natural_language": "exact match for author Smith J without synonyms",
     "ads_query": "=author:\"Smith, J\"", "category": "syntax"},
    {"natural_language": "find papers by exactly Wang, Y without name variants",
     "ads_query": "=author:\"Wang, Y\" doctype:article", "category": "syntax"},
    {"natural_language": "exact author search for Li, H on stellar physics",
     "ads_query": "=author:\"Li, H\" abs:\"stellar physics\"", "category": "syntax"},
    {"natural_language": "papers by exactly Brown, T. M. without synonym expansion",
     "ads_query": "=author:\"Brown, T. M.\" doctype:article", "category": "syntax"},
    {"natural_language": "exact match for Kim, S in galaxy evolution papers",
     "ads_query": "=author:\"Kim, S\" abs:\"galaxy evolution\" doctype:article", "category": "syntax"},
]
new_examples.extend(exact_author_examples)

# =============================================================================
# P2: CROSS-DOMAIN / database: filters
# =============================================================================
cross_domain_examples = [
    {"natural_language": "physics papers on quantum entanglement",
     "ads_query": "abs:\"quantum entanglement\" database:physics", "category": "collection"},
    {"natural_language": "astronomy articles on gravitational wave detection",
     "ads_query": "abs:\"gravitational wave detection\" database:astronomy doctype:article", "category": "collection"},
    {"natural_language": "general science papers on climate change and astronomy",
     "ads_query": "abs:\"climate change\" database:general", "category": "collection"},
    {"natural_language": "physics database papers on superconductivity",
     "ads_query": "abs:\"superconductivity\" database:physics", "category": "collection"},
    {"natural_language": "refereed astronomy papers on galaxy dynamics",
     "ads_query": "abs:\"galaxy dynamics\" database:astronomy property:refereed doctype:article", "category": "collection"},
    {"natural_language": "earth science papers on meteorite composition",
     "ads_query": "abs:\"meteorite composition\" database:earthscience", "category": "collection"},
    {"natural_language": "physics articles about neutrino mass",
     "ads_query": "abs:\"neutrino mass\" database:physics doctype:article", "category": "collection"},
    {"natural_language": "papers in the astronomy collection about machine learning applications",
     "ads_query": "abs:\"machine learning\" database:astronomy doctype:article", "category": "collection"},
]
new_examples.extend(cross_domain_examples)

# =============================================================================
# P2: SOFTWARE/DATA MENTIONS
# =============================================================================
mention_examples = [
    {"natural_language": "papers that mention astropy software",
     "ads_query": "abs:\"astropy\" mention_count:[1 TO *]", "category": "filters"},
    {"natural_language": "highly mentioned software packages in astronomy",
     "ads_query": "mention_count:[50 TO *] doctype:software collection:astronomy", "category": "metrics"},
    {"natural_language": "software credited in at least 5 papers",
     "ads_query": "credit_count:[5 TO *] doctype:software", "category": "metrics"},
    {"natural_language": "papers that frequently mention specific software tools",
     "ads_query": "mention_count:[20 TO *] doctype:article", "category": "metrics"},
    {"natural_language": "highly credited data analysis software in astrophysics",
     "ads_query": "credit_count:[30 TO *] doctype:software abs:\"data analysis\"", "category": "metrics"},
]
new_examples.extend(mention_examples)

# =============================================================================
# P2: VERBOSE NL DISTILLATION
# =============================================================================
verbose_examples = [
    {"natural_language": "I'm looking for recent research papers that discuss the relationship between galaxy mergers and the triggering of active galactic nuclei in the local universe",
     "ads_query": "abs:\"galaxy mergers\" abs:\"active galactic nuclei\" pubdate:[2018 TO 2026] doctype:article", "category": "compound"},
    {"natural_language": "Can you find me studies about how the cosmic microwave background radiation can be used to constrain models of inflation in the early universe",
     "ads_query": "abs:\"cosmic microwave background\" abs:\"inflation\" doctype:article", "category": "compound"},
    {"natural_language": "I need to find all the published work on using gravitational microlensing surveys to detect free-floating planets in our galaxy",
     "ads_query": "abs:\"gravitational microlensing\" abs:\"free-floating planet\" doctype:article", "category": "compound"},
    {"natural_language": "What papers exist about the chemical enrichment history of dwarf galaxies in the Local Group and what it tells us about early star formation",
     "ads_query": "abs:\"chemical enrichment\" abs:\"dwarf galaxies\" abs:\"Local Group\"", "category": "compound"},
    {"natural_language": "Show me the literature on how machine learning and deep learning techniques have been applied to the problem of galaxy morphological classification",
     "ads_query": "abs:\"machine learning\" abs:\"galaxy morphology\" abs:\"classification\" doctype:article", "category": "compound"},
    {"natural_language": "I want to understand what has been written about the formation and evolution of supermassive black holes at the centers of galaxies and how they co-evolve with their host galaxies",
     "ads_query": "abs:\"supermassive black hole\" abs:\"co-evolution\" abs:\"host galaxy\"", "category": "compound"},
    {"natural_language": "Find me papers about how astronomers are using the James Webb Space Telescope to study the atmospheres of rocky exoplanets in the habitable zone",
     "ads_query": "abs:\"JWST\" abs:\"rocky exoplanet\" abs:\"atmosphere\" abs:\"habitable zone\" doctype:article", "category": "compound"},
    {"natural_language": "I'm interested in the current state of research on whether the expansion of the universe is really accelerating and the evidence for or against dark energy",
     "ads_query": "abs:\"accelerating expansion\" abs:\"dark energy\" doctype:article", "category": "compound"},
    {"natural_language": "Are there papers discussing the use of radio interferometry techniques like VLBI for studying jets from supermassive black holes in active galaxies",
     "ads_query": "abs:\"VLBI\" abs:\"jet\" abs:\"supermassive black hole\" doctype:article", "category": "compound"},
    {"natural_language": "Help me find published research on the effects of stellar feedback including supernovae and stellar winds on the interstellar medium in nearby galaxies",
     "ads_query": "abs:\"stellar feedback\" abs:\"interstellar medium\" abs:\"nearby galaxies\" doctype:article", "category": "compound"},
]
new_examples.extend(verbose_examples)

# =============================================================================
# P3: SIMILAR() expansion
# =============================================================================
similar_examples = [
    {"natural_language": "papers similar to work on fast radio burst progenitors",
     "ads_query": "similar(abs:\"fast radio burst progenitors\")", "category": "operator"},
    {"natural_language": "find articles related to research on exoplanet atmospheres",
     "ads_query": "similar(abs:\"exoplanet atmospheres\")", "category": "operator"},
    {"natural_language": "papers like studies of galaxy cluster mass functions",
     "ads_query": "similar(abs:\"galaxy cluster mass function\")", "category": "operator"},
    {"natural_language": "related work on magnetohydrodynamic simulations of the solar corona",
     "ads_query": "similar(abs:\"magnetohydrodynamic simulations\" abs:\"solar corona\")", "category": "operator"},
    {"natural_language": "research similar to tidal disruption event light curves",
     "ads_query": "similar(abs:\"tidal disruption event\" abs:\"light curve\")", "category": "operator"},
    {"natural_language": "papers related to brown dwarf atmospheric models",
     "ads_query": "similar(abs:\"brown dwarf\" abs:\"atmospheric models\")", "category": "operator"},
    {"natural_language": "find similar papers on primordial nucleosynthesis constraints",
     "ads_query": "similar(abs:\"primordial nucleosynthesis\")", "category": "operator"},
    {"natural_language": "related articles on gravitational wave template banks",
     "ads_query": "similar(abs:\"gravitational wave\" abs:\"template bank\")", "category": "operator"},
    {"natural_language": "papers similar to work on the epoch of reionization",
     "ads_query": "similar(abs:\"epoch of reionization\")", "category": "operator"},
    {"natural_language": "find related work on Bayesian methods in cosmology",
     "ads_query": "similar(abs:\"Bayesian methods\" abs:\"cosmology\")", "category": "operator"},
]
new_examples.extend(similar_examples)

# =============================================================================
# P3: REFERENCES() balance
# =============================================================================
references_examples = [
    {"natural_language": "what papers does the foundational dark energy paper reference",
     "ads_query": "references(abs:\"dark energy\" useful(abs:\"dark energy\"))", "category": "second_order"},
    {"natural_language": "papers referenced by galaxy formation simulations",
     "ads_query": "references(abs:\"galaxy formation simulations\")", "category": "second_order"},
    {"natural_language": "reference list of neutron star merger research",
     "ads_query": "references(abs:\"neutron star merger\")", "category": "second_order"},
    {"natural_language": "what sources do papers on cosmic ray propagation cite",
     "ads_query": "references(abs:\"cosmic ray propagation\")", "category": "second_order"},
    {"natural_language": "papers referenced in exoplanet transit studies",
     "ads_query": "references(abs:\"exoplanet transit\")", "category": "second_order"},
    {"natural_language": "bibliography of stellar mass black hole papers",
     "ads_query": "references(abs:\"stellar mass black hole\")", "category": "second_order"},
    {"natural_language": "what references are used in CMB anisotropy studies",
     "ads_query": "references(abs:\"CMB anisotropy\")", "category": "second_order"},
    {"natural_language": "papers cited by magnetar emission models",
     "ads_query": "references(abs:\"magnetar emission\")", "category": "second_order"},
    {"natural_language": "reference papers used in baryon acoustic oscillation research",
     "ads_query": "references(abs:\"baryon acoustic oscillation\")", "category": "second_order"},
    {"natural_language": "what does the literature on gravitational lensing reference",
     "ads_query": "references(abs:\"gravitational lensing\")", "category": "second_order"},
]
new_examples.extend(references_examples)

# Append to existing
existing.extend(new_examples)

# Write back
with open(GOLD_FILE, "w") as f:
    json.dump(existing, f, indent=2)

print(f"Added {len(new_examples)} new examples")
print(f"Total examples: {len(existing)}")

# Category breakdown of new examples
from collections import Counter
cats = Counter(ex["category"] for ex in new_examples)
for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")
