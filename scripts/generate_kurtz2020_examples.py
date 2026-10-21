#!/usr/bin/env python3
"""
Generate training examples from the Kurtz 2020 Second Order Operators paper.

Combines original NL phrasings with 3 perspective-based variations (casual,
expert, question-form) into deduplicated gold_examples.json format.

Source: "Second Order Operators in the NASA Astrophysics Data System"
        Kurtz & Chyla, BAAS Vol. 52 Issue 2, 2020
        DOI: 10.3847/25c2cfeb.8d12c399
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "datasets" / "raw"
GEN_DIR = ROOT / "data" / "datasets" / "generated"

# Load extracted queries (original NL + modernized ADS queries)
extracted = json.loads((RAW_DIR / "kurtz2020_extracted.json").read_text())

# --- Perspective 1: Casual/Conversational ---
casual = [
    {"source_index": 0, "natural_language": "show me the most useful papers on exoplanet atmospheres from 2019 to 2020"},
    {"source_index": 1, "natural_language": "find me useful exoplanet atmosphere papers from 2019-2020 but exclude anything referenced by Fortney"},
    {"source_index": 2, "natural_language": "show me useful exoplanet atmosphere papers from 2019-2020 that mention ammonia, excluding Fortney's references"},
    {"source_index": 3, "natural_language": "find papers about ammonia in Fortney's references that are useful for exoplanet atmospheres from 2019-2020"},
    {"source_index": 4, "natural_language": "which HITRAN papers does Fortney cite in his work"},
    {"source_index": 5, "natural_language": "find papers that cite both Kasting 1982 and exoplanet atmosphere work from 2019-2020"},
    {"source_index": 6, "natural_language": "show me the top 150 most cited papers by Sandage"},
    {"source_index": 7, "natural_language": "what are the most useful papers among those citing the Brown 2005 hypervelocity star discovery"},
    {"source_index": 8, "natural_language": "find all papers that cite the Brown 2005 hypervelocity star paper"},
    {"source_index": 9, "natural_language": "find non-Harvard authors whose work is useful to Harvard first-author astronomy papers from 2020, looking at 2019-2020 papers"},
    {"source_index": 10, "natural_language": "show me the most influential references cited by Thorstensen as first author from 2010-2020, published between 2005 and 2020"},
    {"source_index": 11, "natural_language": "find papers about globular clusters in M31"},
    {"source_index": 12, "natural_language": "show me papers similar to the Mazzarella 2020 NED infrared abstract"},
    {"source_index": 13, "natural_language": "find papers by Fabricant about spectrographs"},
    {"source_index": 14, "natural_language": "show me papers similar to Fabricant's spectrograph work"},
    {"source_index": 15, "natural_language": "find the top 200 papers similar to Fabricant's spectrograph work from 2000-2020, excluding MMT"},
    {"source_index": 16, "natural_language": "show me 200 papers most similar to the Johnson and Morgan 1953 spectral classification paper"},
    {"source_index": 17, "natural_language": "what are the most cited papers among those similar to the Johnson and Morgan 1953 spectral classification work"},
    {"source_index": 18, "natural_language": "find me papers related to weak lensing"},
    {"source_index": 19, "natural_language": "show me the top 200 most relevant weak lensing papers"},
    {"source_index": 20, "natural_language": "find 2020 papers that are similar to the 2019 weak lensing literature"},
    {"source_index": 21, "natural_language": "what new papers came out this week that are related to SETI research"},
    {"source_index": 22, "natural_language": "show me this week's arXiv preprints related to weak lensing"},
    {"source_index": 23, "natural_language": "what are weak lensing b-mode researchers reading lately from 2020"},
    {"source_index": 24, "natural_language": "what are weak lensing b-mode researchers reading about HST"},
    {"source_index": 25, "natural_language": "what are weak lensing b-mode researchers reading about galaxy clusters"},
    {"source_index": 26, "natural_language": "are Donahue's papers trending among the weak lensing b-mode community"},
    {"source_index": 27, "natural_language": "show me recent first-author papers by Chilingarian from 2019-2020"},
    {"source_index": 28, "natural_language": "what are people who read Chilingarian's recent papers also reading"},
    {"source_index": 29, "natural_language": "show me all references cited in Chilingarian's first-author papers from 2019-2020"},
    {"source_index": 30, "natural_language": "what's trending in Chilingarian's research community right now"},
    {"source_index": 31, "natural_language": "find trending ultra-diffuse galaxy papers among people who read Chilingarian's references"},
    {"source_index": 32, "natural_language": "what are people reading about nucleosynthesis right now"},
    {"source_index": 33, "natural_language": "show me the top 200 most relevant nucleosynthesis papers"},
    {"source_index": 34, "natural_language": "find the most recent papers citing the B2FH paper that discuss nucleosynthesis"},
    {"source_index": 35, "natural_language": "what's trending among the community that cites the B2FH paper and works on nucleosynthesis"},
    {"source_index": 36, "natural_language": "what's trending among the top weak lensing research community"},
    {"source_index": 37, "natural_language": "show me the 200 most read weak lensing papers"},
    {"source_index": 38, "natural_language": "what are the most active weak lensing readers looking at now"},
    {"source_index": 39, "natural_language": "find me review articles on weak lensing"},
    {"source_index": 40, "natural_language": "show me recent 2020 reviews on dark matter and the Higgs boson"},
    {"source_index": 41, "natural_language": "find review papers covering weak lensing from 2015 to 2020"},
    {"source_index": 42, "natural_language": "show me reviews that cover the most important recent weak lensing papers from 2015-2020"},
    {"source_index": 43, "natural_language": "what research directions have come out of Dalcanton's PHAT survey"},
    {"source_index": 44, "natural_language": "find papers by other authors that review or build on the PHAT survey, not by Dalcanton herself"},
    {"source_index": 45, "natural_language": "show me papers by other researchers that substantively discuss the PHAT survey in detail"},
    {"source_index": 46, "natural_language": "find papers with overlapping references to the Koda 2015 ultra-diffuse galaxy paper"},
    {"source_index": 47, "natural_language": "find Seager's paper on mass-radius relationships for solid exoplanets"},
    {"source_index": 48, "natural_language": "show me all papers that cite articles published in the Astrophysical Journal"},
    {"source_index": 49, "natural_language": "find all papers that are referenced by Astrophysical Journal articles"},
]

# --- Perspective 2: Expert/Professional ---
expert = [
    {"source_index": 0, "natural_language": "key references in exoplanet atmospheres research from 2019-2020"},
    {"source_index": 1, "natural_language": "key references in exoplanet atmospheres 2019-2020 excluding Fortney's bibliography"},
    {"source_index": 2, "natural_language": "key exoplanet atmospheres references 2019-2020 excluding Fortney's bibliography mentioning ammonia"},
    {"source_index": 3, "natural_language": "ammonia papers from Fortney's references that are influential in exoplanet atmospheres"},
    {"source_index": 4, "natural_language": "HITRAN papers cited by Fortney"},
    {"source_index": 5, "natural_language": "papers citing both 2019-2020 exoplanet atmosphere work and Kasting 1982 JGR paper"},
    {"source_index": 6, "natural_language": "Sandage's 150 most-cited papers"},
    {"source_index": 7, "natural_language": "co-citation analysis of Brown 2005 hypervelocity star discovery paper"},
    {"source_index": 8, "natural_language": "papers citing Brown 2005 hypervelocity star discovery"},
    {"source_index": 9, "natural_language": "external colloquium candidates frequently cited by Harvard first-author astronomy papers in 2020"},
    {"source_index": 10, "natural_language": "authors most frequently referenced by Thorstensen in cataclysmic variable work 2010-2020"},
    {"source_index": 11, "natural_language": "globular clusters in M31"},
    {"source_index": 12, "natural_language": "papers similar to Mazzarella 2020 NED infrared galaxies abstract"},
    {"source_index": 13, "natural_language": "Fabricant papers on spectrographs"},
    {"source_index": 14, "natural_language": "related work to Fabricant's spectrograph instrumentation papers"},
    {"source_index": 15, "natural_language": "top 200 spectrograph papers related to Fabricant's work excluding MMT since 2000"},
    {"source_index": 16, "natural_language": "200 papers most related to Johnson and Morgan 1953 MK spectral classification"},
    {"source_index": 17, "natural_language": "most impactful papers in the stellar classification field seeded from Johnson and Morgan 1953"},
    {"source_index": 18, "natural_language": "literature related to weak lensing"},
    {"source_index": 19, "natural_language": "top 200 most relevant weak lensing papers"},
    {"source_index": 20, "natural_language": "new 2020 papers continuing 2019 weak lensing research threads"},
    {"source_index": 21, "natural_language": "papers from this week relevant to SETI research"},
    {"source_index": 22, "natural_language": "custom weekly arXiv digest for weak lensing research"},
    {"source_index": 23, "natural_language": "trending reads in weak lensing B-mode research from 2020"},
    {"source_index": 24, "natural_language": "HST-related trending reads among the weak lensing B-mode community"},
    {"source_index": 25, "natural_language": "galaxy cluster papers trending among weak lensing B-mode readers"},
    {"source_index": 26, "natural_language": "Donahue papers popular among weak lensing B-mode readers"},
    {"source_index": 27, "natural_language": "Chilingarian first-author papers from 2019-2020"},
    {"source_index": 28, "natural_language": "what people are reading alongside Chilingarian's recent papers"},
    {"source_index": 29, "natural_language": "bibliography of Chilingarian's 2019-2020 papers"},
    {"source_index": 30, "natural_language": "hive mind reading model of Chilingarian's research community"},
    {"source_index": 31, "natural_language": "ultra-diffuse galaxy research trending in Chilingarian's citation network"},
    {"source_index": 32, "natural_language": "current reading trends in nucleosynthesis"},
    {"source_index": 33, "natural_language": "top 200 most relevant nucleosynthesis papers"},
    {"source_index": 34, "natural_language": "recent nucleosynthesis papers citing B2FH"},
    {"source_index": 35, "natural_language": "reading trends among recent nucleosynthesis papers that cite B2FH"},
    {"source_index": 36, "natural_language": "reading trends among the top weak lensing community"},
    {"source_index": 37, "natural_language": "200 most-read weak lensing papers"},
    {"source_index": 38, "natural_language": "what the most active weak lensing readers are trending toward"},
    {"source_index": 39, "natural_language": "review articles on weak lensing"},
    {"source_index": 40, "natural_language": "recent reviews covering dark matter and Higgs from 2020"},
    {"source_index": 41, "natural_language": "reviews of weak lensing literature from 2015 to 2020"},
    {"source_index": 42, "natural_language": "comprehensive reviews of the highest-impact weak lensing papers from 2015-2020"},
    {"source_index": 43, "natural_language": "review-level impact assessment of Dalcanton's PHAT survey"},
    {"source_index": 44, "natural_language": "external papers reviewing the impact of Dalcanton's PHAT program"},
    {"source_index": 45, "natural_language": "non-team papers substantively building on the PHAT survey results"},
    {"source_index": 46, "natural_language": "bibliometric coupling with Koda 2015 ultra-diffuse galaxies in Coma paper"},
    {"source_index": 47, "natural_language": "Seager mass-radius relations for solid exoplanets"},
    {"source_index": 48, "natural_language": "complete citation network of the Astrophysical Journal"},
    {"source_index": 49, "natural_language": "complete reference network of the Astrophysical Journal"},
]

# --- Perspective 3: Question-form ---
question = [
    {"source_index": 0, "natural_language": "What are the most frequently cited papers in exoplanet atmospheres research from 2019 to 2020?"},
    {"source_index": 1, "natural_language": "What are the key referenced papers in exoplanet atmospheres from 2019-2020, excluding works cited by Fortney?"},
    {"source_index": 2, "natural_language": "What are the important exoplanet atmospheres papers from 2019-2020 that mention ammonia, excluding Fortney's references?"},
    {"source_index": 3, "natural_language": "Which papers about ammonia appear in Fortney's references that are also useful for exoplanet atmospheres research from 2019-2020?"},
    {"source_index": 4, "natural_language": "Which HITRAN database papers has Fortney cited in his work?"},
    {"source_index": 5, "natural_language": "Who has cited the Kasting 1982 geophysics paper in the context of exoplanet atmosphere research from 2019-2020?"},
    {"source_index": 6, "natural_language": "What are the 150 most cited papers by Allan Sandage?"},
    {"source_index": 7, "natural_language": "What are the foundational papers in the hypervelocity star field based on who cited the Brown 2005 discovery paper?"},
    {"source_index": 8, "natural_language": "Who has cited the Brown 2005 paper on hypervelocity stars?"},
    {"source_index": 9, "natural_language": "Which non-Harvard astronomers are being frequently cited by Harvard first-author refereed astronomy papers from 2019-2020, as potential colloquium speakers?"},
    {"source_index": 10, "natural_language": "Which researchers does Thorstensen cite most in his 2010-2020 first-author papers, for identifying potential grad school advisors in cataclysmic variable research?"},
    {"source_index": 11, "natural_language": "What papers discuss globular clusters in the Andromeda galaxy?"},
    {"source_index": 12, "natural_language": "What papers are similar to the Mazzarella 2020 study on NED infrared galaxies?"},
    {"source_index": 13, "natural_language": "What papers has Daniel Fabricant published about spectrographs?"},
    {"source_index": 14, "natural_language": "What research is related to Fabricant's work on spectrographs?"},
    {"source_index": 15, "natural_language": "What are the top 200 papers related to Fabricant's spectrograph work since 2000, excluding those about MMT?"},
    {"source_index": 16, "natural_language": "What papers are most similar to the Johnson and Morgan 1953 stellar spectral classification paper?"},
    {"source_index": 17, "natural_language": "What are the most impactful papers in stellar classification that built on Johnson and Morgan 1953?"},
    {"source_index": 18, "natural_language": "What papers are related to weak gravitational lensing?"},
    {"source_index": 19, "natural_language": "What are the top 200 most relevant weak lensing papers?"},
    {"source_index": 20, "natural_language": "What 2020 papers follow up on the weak lensing research threads from 2019?"},
    {"source_index": 21, "natural_language": "What new papers related to the search for extraterrestrial intelligence were published this week?"},
    {"source_index": 22, "natural_language": "What new weak lensing preprints appeared on arXiv this week?"},
    {"source_index": 23, "natural_language": "What are weak lensing B-mode researchers reading in 2020?"},
    {"source_index": 24, "natural_language": "Which Hubble Space Telescope papers are trending among weak lensing B-mode researchers?"},
    {"source_index": 25, "natural_language": "Which galaxy cluster papers are popular among weak lensing B-mode researchers?"},
    {"source_index": 26, "natural_language": "Which of Megan Donahue's papers are popular with weak lensing B-mode researchers?"},
    {"source_index": 27, "natural_language": "What papers did Chilingarian publish as first author in 2019 and 2020?"},
    {"source_index": 28, "natural_language": "What are readers of Chilingarian's recent papers also reading?"},
    {"source_index": 29, "natural_language": "What papers does Chilingarian cite in his recent 2019-2020 first-author publications?"},
    {"source_index": 30, "natural_language": "What is currently trending in Chilingarian's broader research community?"},
    {"source_index": 31, "natural_language": "Which ultra-diffuse galaxy papers are trending among people who read Chilingarian's references?"},
    {"source_index": 32, "natural_language": "What are people reading about nucleosynthesis right now?"},
    {"source_index": 33, "natural_language": "What are the top 200 most relevant nucleosynthesis papers?"},
    {"source_index": 34, "natural_language": "What are the most recent nucleosynthesis papers that cite the Burbidge, Burbidge, Fowler, and Hoyle 1957 paper?"},
    {"source_index": 35, "natural_language": "What is trending in the nucleosynthesis community that builds on B2FH?"},
    {"source_index": 36, "natural_language": "What is trending among the weak lensing research community?"},
    {"source_index": 37, "natural_language": "What are the 200 most read weak lensing papers?"},
    {"source_index": 38, "natural_language": "What is trending among the most active weak lensing readers?"},
    {"source_index": 39, "natural_language": "What are the major review articles on weak gravitational lensing?"},
    {"source_index": 40, "natural_language": "What review papers on dark matter and the Higgs boson were published in 2020?"},
    {"source_index": 41, "natural_language": "What are the review articles covering weak lensing research from 2015 to 2020?"},
    {"source_index": 42, "natural_language": "What are the most comprehensive review articles covering recent weak lensing research?"},
    {"source_index": 43, "natural_language": "What is the broader impact of Dalcanton's PHAT survey on the field?"},
    {"source_index": 44, "natural_language": "Which papers by authors other than Dalcanton have reviewed or built upon the PHAT survey?"},
    {"source_index": 45, "natural_language": "Which papers by researchers outside the PHAT team substantively discuss the PHAT survey in their text?"},
    {"source_index": 46, "natural_language": "What papers are bibliometrically coupled with the Koda 2015 paper on ultra-diffuse galaxies?"},
    {"source_index": 47, "natural_language": "Where can I find Seager's paper on mass-radius relationships for solid exoplanets?"},
    {"source_index": 48, "natural_language": "What papers have cited articles published in the Astrophysical Journal?"},
    {"source_index": 49, "natural_language": "What papers are referenced by articles published in the Astrophysical Journal?"},
]


def normalize_nl(text: str) -> str:
    """Normalize NL for deduplication."""
    return " ".join(text.lower().strip().rstrip("?").split())


def main():
    # Collect all phrasings per source_index
    all_examples = []
    seen_nl = set()

    for i, entry in enumerate(extracted):
        query = entry["query_raw"]

        # All 4 perspectives for this query
        nls = [
            entry["natural_language"],  # original
        ]
        # Find matching casual/expert/question by source_index
        for perspective in [casual, expert, question]:
            for p in perspective:
                if p["source_index"] == i:
                    nls.append(p["natural_language"])
                    break

        # Deduplicate within this query's phrasings
        for nl in nls:
            key = normalize_nl(nl)
            if key in seen_nl:
                continue
            seen_nl.add(key)
            all_examples.append({
                "natural_language": nl,
                "ads_query": query,
                "category": "operator",
            })

    # Write output
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    output_path = GEN_DIR / "kurtz2020_examples.json"
    with open(output_path, "w") as f:
        json.dump(all_examples, f, indent=2)

    # Summary
    print(f"Total examples: {len(all_examples)}")
    print(f"Unique queries: {len(extracted)}")
    print(f"Avg phrasings per query: {len(all_examples)/len(extracted):.1f}")

    # Count by section
    section_counts = {}
    for entry in extracted:
        s = entry["section"]
        section_counts[s] = section_counts.get(s, 0) + 1
    print("\nQueries by section:")
    for s, c in sorted(section_counts.items()):
        print(f"  {s}: {c}")


if __name__ == "__main__":
    main()
