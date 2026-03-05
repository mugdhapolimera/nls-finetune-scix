"""ADS/SciX search field definitions.

Reference: https://ui.adsabs.harvard.edu/help/search/search-syntax
"""

# All searchable ADS fields
ADS_FIELDS = {
    # Core metadata
    "abs": "Abstract, title, and keywords (virtual field)",
    "abstract": "Abstract only",
    "title": "Title only",
    "keyword": "Publisher or author-supplied keywords",
    "full": "Fulltext, acknowledgements, abstract, title, keywords",
    "body": "Full text only (minus acknowledgements)",
    "ack": "Acknowledgements section",
    # Authors
    "author": "Author name (Last, First or Last, F)",
    "^author": "First author only (prefix with ^)",
    "author_count": "Number of authors",
    "orcid": "ORCID identifier",
    "orcid_pub": "ORCID from publishers",
    "orcid_user": "ORCID claimed by ADS users",
    # Affiliations
    "aff": "Raw affiliation string",
    "aff_id": "Canonical affiliation ID",
    "inst": "Curated institution abbreviation",
    # Publication info
    "bibcode": "ADS bibcode identifier",
    "bibstem": "Journal abbreviation (e.g., ApJ, MNRAS)",
    "bibgroup": "Bibliographic group (e.g., HST)",
    "pub": "Publication name",
    "pubdate": "Publication date (YYYY-MM or range)",
    "year": "Publication year",
    "volume": "Volume number",
    "issue": "Issue number",
    "page": "Page number",
    "doctype": "Document type (article, eprint, etc.)",
    # Identifiers
    "doi": "Digital Object Identifier",
    "arXiv": "arXiv identifier",
    "arxiv_class": "arXiv classification",
    "identifier": "Any identifier (bibcode, doi, arXiv)",
    "alternate_bibcode": "Alternate bibcode",
    # Citations and metrics
    "citation_count": "Number of citations",
    "read_count": "Number of reads",
    "cite_read_boost": "Citation/read boost factor",
    "classic_factor": "Classic popularity factor",
    # Data and links
    "data": "Data source links",
    "property": "Record properties (e.g., refereed, openaccess)",
    "esources": "Electronic source types",
    # Astronomy-specific
    "object": "Astronomical object name or coordinates",
    # Affiliations (virtual)
    "affil": "Virtual field searching aff, aff_abbrev, aff_canonical, aff_id, institution",
    # Software/data mentions and credits
    "mention": "Bibcodes of software/data records mentioned in this paper",
    "mention_count": "Number of software/data mentions in this paper",
    "credit": "Bibcodes of papers that credit this software/data record",
    "credit_count": "Number of credits this software/data record has received",
    # has: field (metadata presence filter)
    "has": "Filter by presence of metadata fields (e.g., has:body, has:ack)",
    # Other
    "database": "Database/collection (astronomy, physics, general, earthscience)",
    "collection": "Collection filter - alias for database (astronomy, physics, general, earthscience)",
    "lang": "Language of the paper",
    "copyright": "Copyright information",
    "grant": "Grant information",
    "entdate": "Entry date in ADS",
    "editor": "Editor name (for books)",
    "book_author": "Book author",
    "caption": "Figure/table captions",
    "comment": "Comments field",
    "alternate_title": "Alternate title (translations)",
}

# Fields organized by category for training data generation
FIELD_CATEGORIES = {
    "author": ["author", "^author", "author_count", "orcid"],
    "content": ["abs", "abstract", "title", "keyword", "full", "body"],
    "publication": ["bibstem", "pubdate", "year", "volume", "issue", "page", "pub", "doctype"],
    "identifiers": ["bibcode", "doi", "arXiv", "identifier"],
    "metrics": ["citation_count", "read_count", "mention_count", "credit_count"],
    "affiliation": ["aff", "aff_id", "inst", "affil"],
    "astronomy": ["object", "arxiv_class"],
    "properties": ["property", "database", "data", "has"],
    "software": ["mention", "credit", "mention_count", "credit_count"],
}

# Common bibstems for synthetic data generation
COMMON_BIBSTEMS = [
    # Core astronomy journals
    "ApJ",  # Astrophysical Journal
    "MNRAS",  # Monthly Notices of the Royal Astronomical Society
    "A&A",  # Astronomy & Astrophysics
    "AJ",  # Astronomical Journal
    "ApJL",  # Astrophysical Journal Letters
    "ApJS",  # Astrophysical Journal Supplement Series
    "ARA&A",  # Annual Review of Astronomy and Astrophysics
    "PASP",  # Publications of the Astronomical Society of the Pacific
    "PASJ",  # Publications of the Astronomical Society of Japan
    "PASA",  # Publications of the Astronomical Society of Australia
    # General science
    "Nature",  # Nature
    "Science",  # Science
    "NatAs",  # Nature Astronomy
    # Physics
    "PhRvL",  # Physical Review Letters
    "PhRvD",  # Physical Review D
    "PhRvC",  # Physical Review C
    "PhRvA",  # Physical Review A
    "PhRvE",  # Physical Review E
    "NuPhB",  # Nuclear Physics B
    "EPJC",  # European Physical Journal C
    "CQGra",  # Classical and Quantum Gravity
    "JHEP",  # Journal of High Energy Physics
    "JCAP",  # Journal of Cosmology and Astroparticle Physics
    "LRR",  # Living Reviews in Relativity
    # Solar/heliophysics
    "SoPh",  # Solar Physics
    "JGRA",  # Journal of Geophysical Research: Space Physics
    "SpWea",  # Space Weather
    # Planetary science
    "Icar",  # Icarus
    "P&SS",  # Planetary and Space Science
    "JGRE",  # Journal of Geophysical Research: Planets
    "PSJ",  # Planetary Science Journal
    # Earth science / geophysics
    "GeoRL",  # Geophysical Research Letters
    "JGRB",  # Journal of Geophysical Research: Solid Earth
    # Instrumentation & methods
    "ExA",  # Experimental Astronomy
    "NewA",  # New Astronomy
    "NewAR",  # New Astronomy Reviews
    "A&AS",  # Astronomy & Astrophysics Supplement Series
    # Space science reviews
    "SSRv",  # Space Science Reviews
    "AsBio",  # Astrobiology
    # Additional high-impact
    "AREPS",  # Annual Review of Earth and Planetary Sciences
    "PhR",  # Physics Reports
    "RvMP",  # Reviews of Modern Physics
    "PrPNP",  # Progress in Particle and Nuclear Physics
    "AdSpR",  # Advances in Space Research
    "Ap&SS",  # Astrophysics and Space Science
    "AN",  # Astronomische Nachrichten
    "AcA",  # Acta Astronomica
    "BASI",  # Bulletin of the Astronomical Society of India
    "JApA",  # Journal of Astrophysics and Astronomy
    "RAA",  # Research in Astronomy and Astrophysics
]

# Common astronomical objects for synthetic data
COMMON_OBJECTS = [
    "M31",  # Andromeda Galaxy
    "M87",  # Virgo A
    "Sgr A*",  # Sagittarius A*
    "Crab Nebula",
    "Orion Nebula",
    "LMC",  # Large Magellanic Cloud
    "SMC",  # Small Magellanic Cloud
    "NGC 1234",  # Example NGC object
    "HD 209458",  # Famous exoplanet host
    "TRAPPIST-1",
    "Proxima Centauri",
    "Alpha Centauri",
    "Betelgeuse",
    "Vega",
]

# Document types
DOC_TYPES = [
    "article",
    "eprint",
    "inproceedings",
    "book",
    "bookreview",
    "catalog",
    "circular",
    "editorial",
    "erratum",
    "inbook",
    "mastersthesis",
    "misc",
    "newsletter",
    "obituary",
    "phdthesis",
    "pressrelease",
    "proceedings",
    "proposal",
    "software",
    "talk",
    "techreport",
]

# Properties for filtering
PROPERTIES = [
    "refereed",
    "notrefereed",
    "article",
    "openaccess",
    "eprint",
    "data",
    "software",
    "citation",
    "reference",
    "toc",  # Table of contents
    "catalog",
    "associated",
]
