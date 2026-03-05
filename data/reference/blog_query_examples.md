# Query Examples from ADS/SciX Blog Posts

Extracted from HIGH-priority blog posts for training data reference.

---

## The New myADS (2020-08-10)

- `citations(bibcode:(2019MNRAS.486.2075B OR 2014A&A...569A.111B))` — citations to two specific papers by bibcode
- `citations(docs(library/L1iIrVsLTtiA8jp984C6eA))` — citations to papers saved in a library
- `similar(citations(bibcode:(2019MNRAS.486.2075B OR 2014A&A...569A.111B))) collection:astronomy` — similar astronomy articles to recent citations of two specific papers
- `similar(title:"Gaia-ESO") collection:astronomy` — similar astronomy papers to top 200 papers with "Gaia-ESO" in their title
- `trending(topn(200, abs:(stellar spectroscopy chemical abundances) collection:astronomy year:2000-, "read_count desc"))` — trending papers among the top 200 most-read papers on stellar spectroscopy published after 2000
- `trending(useful(author:"^Blanco-Cuaresma, Sergi" collection:astronomy))` — trending papers among the most frequently referenced articles by a given first author
- `reviews(useful(author:"^Blanco-Cuaresma, Sergi" collection:astronomy))` — review-like papers that cite the most frequently referenced articles by a given first author
- `object:M67 property:refereed` — refereed papers about the open cluster M67
- `doctype:software AND spectra` — software records matching the keyword "spectra"
- `full:"machine learning" collection:astronomy` — astronomy articles containing "machine learning" in full text (sorted by read counts)
- `arxiv_class:(astro-ph.EP OR astro-ph.IM OR astro-ph.SR) (stellar spectroscopy OR chemical abundances OR atmospheric parameters)` — articles in specific arXiv categories containing certain keywords
- `entdate:[NOW-7DAYS TO NOW]` — restrict to papers ingested in the last week (appended to any query)

---

## Data Linking II (2024-07-01)

- `property:data` — find records that have linked data associated with them
- `data:MAST` — find records with data products hosted at MAST
- `Lunar carbonaceous chondrites` — unfielded search for a topic
- `Lunar carbonaceous chondrites property:data` — topic search filtered to records with data links
- `full:"urn:nasa:pds:ast-lightcurve-database"` — full-text search for a specific data product URN
- `NICMOS property:(data refereed openaccess)` — refereed open-access publications with data links mentioning NICMOS
- `data:NOAA property:(refereed openaccess) year:2020-2024` — refereed open-access publications from 2020-2024 with NOAA data links
- `"exoplanet atmosphere" property:(refereed data openaccess) year:2020-2024` — refereed open-access papers on exoplanet atmospheres with data links from 2020-2024
- `property:(refereed openaccess data) year:2010-2023 citations(doctype:software) collection:earthscience` — open-access refereed Earth Science papers from 2010-2023 with data links that cite software

---

## Data Linking III (2024-08-01)

- `doctype:dataset` — find all data product records
- `doi:"10.26033/*"` — find all records for a data repository by DOI prefix
- `doi:"10.26033/*" has:citation_count` — find records for a DOI prefix that have citations
- `bibstem:yCat` — find all data products with VizieR bibstem
- `doctype:dataset -property:data` — find data records that do not have a link to data
- `data:PDS` — find all records with a link to the PDS data archive
- `similar(bibcode:2015ivs..data....1N)` — find records similar to a specific data product
- `similar(bibcode:2015ivs..data....1N) doctype:(dataset OR software)` — find similar data or software records to a specific data product
- `topn(5000, bibstem:yCat, date desc)` — top 5000 most recent VizieR data catalogs
- `citations(topn(5000, bibstem:yCat, date desc))` — publications citing the 5000 most recent VizieR catalogs
- `citations(topn(5000, bibstem:yCat, date desc)) property:(openaccess data)` — open-access publications with data links that cite recent VizieR catalogs
- `doctype:proposal` — find all proposal records
- `doctype:software` — find all software records
- `property:data` — find all records with data links

---

## What I Wish I Knew About ADS/SciX During My PhD (2025-03-25)

- `collection:astronomy` — limit search results to the astronomy collection
- `similar("Globular Cluster" -entdate:[NOW-7DAYS TO *]) entdate:[NOW-7DAYS TO *] bibstem:"arXiv"` — find recent arXiv preprints similar to older papers about globular clusters
- `similar("input text string", input)` — use the similar operator with arbitrary text input
- `useful(docs(library/bcynVbTNTK6I__4hHDhAAA))` — most frequently referenced papers from a library
- `doctype:software collection:astronomy abs:"LISA"` — astronomy software mentioning the LISA mission in the abstract
- `data:Zenodo year:2024 title:"Black Hole"` — Zenodo data products with "black hole" in the title from 2024
- `ack:"My Cat" collection:astronomy` — astronomy papers acknowledging "My Cat"

---

## ADS Object Search (2022-09-06)

- `Aldebaran collection:astronomy` — unfielded search for Aldebaran in the astronomy collection
- `Aldebaran NOT collection:astronomy` — find Aldebaran mentions outside the astronomy collection
- `Aldebaran NOT =Aldebaran collection:astronomy` — find records matched via synonyms only (= disables synonym expansion)
- `(Aldebaran OR "Alpha Tauri" OR "alf Tau") collection:astronomy` — search for an object using multiple known names
- `object:Aldebaran collection:astronomy` — object search using SIMBAD/NED correspondences
- `object:((SMC OR LMC) AND M31)` — Boolean object search for multiple astronomical objects
- `body:Aldebaran collection:astronomy` — search for Aldebaran in the body text of articles
- `full:Aldebaran` — search for Aldebaran in full text (title, abstract, body, acknowledgements, keywords)
- `="2003 EL61" NOT Haumea` — find early references to the dwarf planet Haumea by its MPC designation (= disables synonyms)

---

## SciX Earth Science Literature Review (2025-02-27)

- `abs:("Antarctica" AND "snowfall" AND "sea ice")` — search keywords in title, abstract, and keywords fields
- `full:"keyword"` — search keywords in full text of literature
- `useful(Wagner and Eisenman, 2015)` — find papers cited by publications relevant to a specific paper (foundational literature)
- `reviews(Wagner and Eisenman, 2015)` — find papers that cite publications relevant to a specific paper (follow-up literature)
- `trending(Wagner and Eisenman, 2015)` — find papers read by users who also read a specific paper's topic
- `similar(Wagner and Eisenman, 2015)` — find papers with similar content to a specific paper

---

## ADS Updates (2019-02-13)

- `similar(2016PhRvL.116f1102A)` — find articles similar to the GW150914 discovery paper
- `similar(2016PhRvL.116f1102A) bibstem:arXiv entdate:[2019-02-06 TO 2019-02-13]` — similar papers to GW150914 published on arXiv in the past week
- `similar(author:"Name")` — find papers by researchers doing similar work to a given author
- `similar(abs:"exoplanet atmospheres")` — find papers related to a keyword query via semantic similarity
- `aff:STScI OR aff:"Space Telescope Science Institute"` — search affiliations by raw string

---

## NASA Open Access (2020-04-06)

- `year:2018 property:refereed collection:(astronomy OR physics)` — refereed papers from 2018 in astronomy or physics
- `year:2018 property:refereed collection:(astronomy OR physics) -property:openaccess` — non-open-access refereed papers from 2018
- `year:2018 property:refereed collection:(astronomy OR physics) -property:eprint_openaccess property:openaccess` — gold open-access (non-arXiv) refereed papers from 2018
- `year:2018 property:refereed collection:(astronomy OR physics) property:eprint_openaccess property:openaccess` — arXiv open-access refereed papers from 2018
- `(aff:NASA OR ack:NASA) year:2018 property:refereed collection:(astronomy OR physics)` — NASA-affiliated or NASA-acknowledging refereed papers from 2018
- `year:2018 bibstem:(apj OR apjl OR apjs OR aj)` — AAS journal articles from 2018
- `(aff:NASA OR ack:NASA) year:2018 bibstem:(apj OR apjl OR apjs OR aj)` — NASA papers in AAS journals from 2018
- `year:2018 bibstem:(jgr* OR georl)` — AGU journal articles from 2018
- `year:2018 bibstem:(mnras)` — MNRAS articles from 2018
- `year:2018 bibstem:(a&a)` — A&A articles from 2018
- `year:2018 bibstem:(icar)` — Icarus articles from 2018
- `year:2018 bibstem:(jgre)` — JGR Planets articles from 2018
- `year:2018 bibstem:(jgra)` — JGR Space Physics articles from 2018
- `year:2018 bibstem:(soph)` — Solar Physics articles from 2018
- `year:2018 bibstem:(apj) =keyword:sun` — ApJ heliophysics articles from 2018 (exact keyword match for "sun")
- `year:2018 bibstem:(jgrb or jgrc or jgrd or jgrf)` — JGR Earth Science articles from 2018
- `year:2018 bibstem:(jastp or gecoa or adspr or p&ss or e&psl or ssrv or lssr)` — Elsevier planetary/space science journals from 2018

---

## Citations and Journals (2018-08-20)

- `bibstem:PhRvD year:2010 citations(bibstem:(ApJ OR ApJL OR ApJS OR AJ OR MNRAS OR A&A OR JCAP OR Icar OR E&PSL OR SoPh))` — Phys Rev D papers from 2010 that cite major astronomy journals (defines "astronomy-relevant" papers)

---

## SciX Data Collections (2025-08-25)

- `data:Zenodo` — find records with Zenodo data links
- `data:ORNL.DAAC` — find records in the ORNL DAAC data collection
- `collection:earthscience` — filter to Earth Science collection

---

## Things We Wish We'd Known (2018-08-06)

- `full:"MUSE" full:"VLT"` — full-text search for papers mentioning the MUSE instrument on VLT
- `bibstem:"HST" M31` — search for accepted HST proposals about the Andromeda Galaxy
- `bibstem:"*prop*"` — find bibstems containing "prop" (telescope proposals)

---

## Affiliations Feature (2020-01-15)

- `aff:Harvard` — raw affiliation string search for "Harvard"
- `aff:"Harvard University"` — raw affiliation search for exact phrase "Harvard University"
- `aff_id:A00211` — search by curated affiliation identifier for Harvard University
- `inst:"Harvard U"` — search by institution abbreviation (includes children)
- `affil:"UCB"` — combined affiliation search across raw strings, canonical strings, IDs, and abbreviations
- `aff:"SRON"` — search for a specific string in affiliation data

---

## Affiliations Update (2021-04-15)

- `"gravitational waves" year:2020` — unfielded search with year filter
- `inst:"CfA"` — search for Center for Astrophysics (equivalent forms: inst:"Harvard U/CfA", inst:"SI/CfA", aff_id:"CfA")
- `aff_id:"SI"` — search for Smithsonian Institution parent only
- `inst:"SI"` — search for Smithsonian Institution plus all children (CfA, MNH, Air and Space Museum)
- `inst:"UNAM/Inst Phy"` — search for a specific department within a university (National Autonomous University of Mexico)
- `inst:"NTU/Inst Phy"` — search for National Taiwan University's Institute of Physics
- `inst:"U Amsterdam/Inst Phy"` — search for University of Amsterdam's Institute of Physics

---

## UAT Integration (2022-12-29)

- `full:"super Earth" property:refereed` — refereed papers with "super Earth" in full text
- `full:"super Earth" property:refereed uat:"high contrast techniques"` — same search filtered by UAT concept
