"""Static field reference cards for RAG-augmented LLM prompting.

Compact cards (~10 lines each) listing valid enum values and syntax
for specific ADS fields. Injected into the LLM prompt to reduce
enum hallucination (e.g., doctype:"journal" instead of doctype:article).
"""

import re

# Field reference cards — compact, within 1.7B model attention span
CARDS: dict[str, str] = {
    "doctype": (
        "Valid doctypes: article, eprint, phdthesis, mastersthesis, inproceedings, "
        "inbook, book, proceedings, abstract, software, proposal, techreport, catalog, "
        "circular, editorial, erratum, newsletter, obituary, pressrelease, talk, misc, bookreview."
    ),
    "property": (
        "Valid properties: refereed, openaccess, eprint, nonarticle, article, notrefereed, "
        "ads_openaccess, author_openaccess, eprint_openaccess, pub_openaccess, "
        "associated, data, esource, inspire, software, catalog, inproceedings, "
        "library_catalog, presentation, toc, ocr_abstract."
    ),
    "operators": (
        "Operators: citations(), references(), trending(), useful(), similar(), reviews(). "
        "All field values inside operators MUST be quoted. "
        "Can nest: trending(useful(abs:\"X\")), citations(topn(100, abs:\"X\", \"citation_count desc\")). "
        "similar() with entdate: finds new related papers: similar(abs:\"X\") entdate:[NOW-7DAYS TO *]."
    ),
    "negation": (
        "Negation: prefix with NOT. Examples: NOT abs:\"term\", NOT property:refereed, "
        "NOT doctype:eprint, NOT author:\"Name\". "
        "Negation applies to the immediately following clause."
    ),
    "data": (
        "Data archives (data: field): MAST, NED, SIMBAD, VizieR, IRSA, Chandra, "
        "CXO, ESA, HEASARC, INES, PDS, CADC, GCPD, Author, CDS, ESO, "
        "GTC, NOAO, BICEP2, ARI, ISO, KOA, Keck, ALMA, XMM."
    ),
    "has": (
        "has: field checks metadata presence. Values include: body, ack, data, grant, "
        "orcid_pub, orcid_user, orcid_other, mention, abstract, citation, reference, "
        "read_count, download_count, table, figure, toc."
    ),
    "metrics": (
        "Metric ranges: citation_count:[100 TO *], read_count:[50 TO *], "
        "mention_count:[1 TO *], credit_count:[20 TO *]. "
        "Use [N TO *] for minimum, [* TO N] for maximum, [N TO M] for range."
    ),
    "dates": (
        "Date syntax: pubdate:[2020 TO 2023], pubdate:[2020 TO *], pubdate:2020. "
        "Entry date: entdate:[NOW-7DAYS TO *], entdate:[NOW-1MONTH TO *]. "
        "Year integers only for pubdate, NOW- syntax for entdate."
    ),
    "esources": (
        "Electronic sources (esources: field): PUB_PDF, EPRINT_PDF, ADS_PDF, "
        "PUB_HTML, EPRINT_HTML, ADS_SCAN, AUTHOR_PDF, AUTHOR_HTML."
    ),
    "collection": (
        "Database/collection filters: astronomy, physics, general, earthscience."
    ),
    "bibgroup": (
        "Bibgroups (telescope/mission bibliographies): HST, JWST, Spitzer, Chandra, "
        "XMM, GALEX, Kepler, K2, TESS, ALMA, SDSS, Gaia, LIGO, Fermi, WMAP, Planck, "
        "HERSCHEL, WISE, IRAS, ROSAT, NuSTAR, Swift, SUZAKU, CfA, ESO, NOAO, NOIRLab."
    ),
}

# Keyword patterns that trigger each card
_CARD_TRIGGERS: dict[str, list[str]] = {
    "doctype": [
        "article", "preprint", "eprint", "thesis", "phd", "masters",
        "proceeding", "conference", "software", "review", "book",
        "proposal", "technical report", "catalog", "editorial",
    ],
    "property": [
        "refereed", "peer review", "open access", "openaccess",
        "non-article", "nonarticle",
    ],
    "operators": [
        "citing", "cited by", "references", "referenced", "trending",
        "popular", "useful", "similar", "reviews of", "review articles",
        "papers that cite", "papers citing",
    ],
    "negation": [
        "not including", "not by", "not from", "not in", "not about",
        "excluding", "exclude", "without", "except for",
        "no papers", "no preprints", "no eprints",
        "neither",
    ],
    "data": [
        "data from", "data archive", "archive data",
        "mast", "ned", "simbad", "vizier",
        "irsa", "chandra data", "heasarc", "pds data",
        "linked data", "data product",
    ],
    "has": [
        "has body", "has data", "has grant", "has orcid",
        "has acknowledgment", "has citation", "has reference",
        "has abstract", "has mention", "has table", "has figure",
        "papers with body", "papers with data", "papers with grant",
        "articles with data", "articles with body",
        "containing full text", "body text",
        "full text available",
    ],
    "metrics": [
        "highly cited", "citation count", "read count",
        "mention count", "most cited", "well cited", "at least",
        "more than", "minimum",
    ],
    "dates": [
        "recent", "last year", "this year", "since", "before",
        "between", "from 1", "from 2", "published in", "entry date",
        "last week", "last month", "this week", "this month",
    ],
    "esources": [
        "pdf", "full text", "scan", "electronic", "html",
        "publisher version",
    ],
    "collection": [
        "astronomy", "physics", "earth science", "planetary",
        "general science", "database",
    ],
    "bibgroup": [
        "hubble", "jwst", "james webb", "spitzer", "chandra",
        "kepler", "tess", "alma", "sdss", "gaia", "ligo",
        "fermi", "herschel", "telescope", "mission", "survey",
    ],
}

# Triggers that need word-boundary matching (short words that are common English)
_WORD_BOUNDARY_TRIGGERS = frozenset([
    "ned", "alma", "tess", "book", "scan",
])


def select_cards(nl_text: str, max_cards: int = 2) -> list[str]:
    """Select relevant field reference cards based on NL keywords.

    Args:
        nl_text: Natural language query text.
        max_cards: Maximum number of cards to return.

    Returns:
        List of card text strings, most relevant first.
    """
    text_lower = nl_text.lower()

    if not text_lower.strip():
        return []

    # Score each card by number of trigger keyword matches
    scores: dict[str, int] = {}
    for card_name, triggers in _CARD_TRIGGERS.items():
        score = 0
        for trigger in triggers:
            if trigger in _WORD_BOUNDARY_TRIGGERS:
                # Use word boundary for short common-word triggers
                if re.search(rf'\b{re.escape(trigger)}\b', text_lower):
                    score += 1
            else:
                if trigger in text_lower:
                    score += 1
        if score > 0:
            scores[card_name] = score

    # Sort by score descending, take top max_cards
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return [CARDS[name] for name, _ in ranked[:max_cards]]
