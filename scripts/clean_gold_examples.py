#!/usr/bin/env python3
"""Clean gold_examples.json: remove bad entries, fix encoding, fix queries.

Fixes applied:
1. Remove non-academic bag-of-OR title queries
2. Rewrite academic bag-of-OR title queries to proper format
3. Fix identifier encoding (mojibake, HTML entities, URL encoding)
4. Rewrite object: queries to abs: (object: field returns 400)
5. Fix miscellaneous query issues (stray text, bad author format)
6. Add missing pubdate for NL-query year alignment
7. Standardize collection: → database: (alias normalization)
8. Flatten nested operators that cause 502 (e.g., trending(similar(...)))
9. Fix specific NL-query alignment issues (Round 2)

Usage:
    python scripts/clean_gold_examples.py              # Dry run
    python scripts/clean_gold_examples.py --apply      # Apply changes
    python scripts/clean_gold_examples.py --apply --verbose
"""

import argparse
import copy
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_FILE = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples.json"
REMOVED_FILE = PROJECT_ROOT / "data" / "reference" / "removed_examples.json"

# ---------------------------------------------------------------------------
# Non-academic keyword detector for bag-of-OR removal
# ---------------------------------------------------------------------------

# Keywords that indicate non-academic / non-astronomy content
NON_ACADEMIC_KEYWORDS = {
    # People / biography / entertainment
    "biography", "filmography", "genealogy", "biographical", "obituary",
    "actor", "actress", "singer", "dancer", "performer", "musician",
    "boxing", "prize battles", "championship",
    "mark twain", "jack london", "isadora duncan", "lola montez",
    "puss in boots", "white fang", "call of wild",
    "red hot chili peppers", "john frusciante",
    "ren and stimpy", "ren or stimpy",
    # Russian / non-English government
    "указ", "президент", "российской", "федерации", "постановление",
    "распоряжение", "губернатор", "награждении", "государственным",
    "республики", "беларусь", "министерства", "культуры",
    "единый", "голосования",
    "бабкина", "бабкiнай", "надежда",
    "видео:", "новости",
    "евгений", "горшечков",
    "хачатурян", "хачатур",
    "музыкальная", "энциклопедия",
    "кемеровская", "астраханской",
    "заседателев", "финансово",
    # Maritime / historical non-science
    "clipper ship", "clipper ships", "maritime history", "sailing directions",
    "greyhounds", "klondike", "gold fields",
    "scouting", "baden-powell",
    # Other non-academic
    "tombstone", "rogues", "glorification",
    "stolen", "marker", "vandalism",
    "teachers' choices", "boys' own book",
    "merriam webster", "baker's biographical",
    "synästhesien", "farbe licht musik",
    "synesthesia", "synesthesi",  # music synesthesia, not astro
    "waterparks", "awsten",
    "collier's weekly",
    "early engagement, long relationship",
    "directors' top 100",
    "john frusciante",
    "folk", "ushud",
    "peralta grant", "rhodesia", "bulawayo",
    "customs services western canada",
    "missouri", "radical rule",
    "san jose", "clyde arbuckle",
    "carnegie institution washington. year",
    "pekin centenary",
    "что такое текст",
    "what is text, really",
    "how many bytes",
    # Computer manuals (not scientific papers)
    "user's manual", "user manual", "user's guide",
    "programmer's manual", "programmer documentation",
    "hp 48g", "hp&nbsp;48g",
    "8086 family", "86-dos", "xlt86",
    "intel 64", "ia-32",
    "pds 8000", "verex system",
    "nasap-70",
    # Conference proceedings (non-astronomy)
    "sigir", "sigmod", "cikm", "chi '07", "vldb",
    # Misc non-academic
    "hawaii", "hawaiian", "thrum",
    "hamilton college", "annual catalogue",
    "latins", "levant", "frankish greece",
    "cours d'analyse", "polytechnique",
    "institutiones calculi integralis",
    "untold history",
    "messenger api", "gtalk",
    "nome's advent", "mining field",
    "otherworld", "kernel crashes",
    "madison grant", "eulogy",
    "robertson george morison",
    "dryden's marine",
    "thoth, portable",
    "support vector clustering (2001)",
    "die noting", "l'intégration",
}

# Keywords that indicate the example IS academic/astronomy
ACADEMIC_KEYWORDS = {
    "galaxy", "galaxies", "stellar", "star", "stars", "planet", "planets",
    "exoplanet", "nebula", "supernova", "quasar", "pulsar", "magnetar",
    "cosmolog", "gravitational", "black hole", "dark matter", "dark energy",
    "redshift", "spectroscop", "photometr", "telescope", "observatory",
    "x-ray", "gamma-ray", "infrared", "ultraviolet", "radio emission",
    "solar", "lunar", "asteroid", "comet", "meteor",
    "coronal mass ejection", "interplanetary", "magnetosphere",
    "aurora", "saturn", "jupiter", "mars", "venus", "mercury",
    "optical vortex", "coronagraph", "verification",
    "magnesium", "nanotubes", "reinforcement", "mechanical properties",
    "real-time operating system",  # Thoth is a legit CS paper
    "ieee symposium", "foundations of computer",
    "information retrieval",
}


def is_non_academic(nl: str, query: str) -> bool:
    """Classify a bag-of-OR entry as non-academic.

    Conservative: assumes ALL bag-of-OR title queries are bad unless
    clearly academic/astronomy content.
    """
    text = (nl + " " + query).lower()

    # Check academic keywords — if any match, it's academic (keep/rewrite)
    for kw in ACADEMIC_KEYWORDS:
        if kw in text:
            return False

    # Everything else is non-academic (remove)
    return True


# ---------------------------------------------------------------------------
# Fix functions
# ---------------------------------------------------------------------------

def find_bag_of_or(examples: list) -> tuple:
    """Find bag-of-OR title queries. Returns (remove_indices, rewrite_map)."""
    remove_indices = set()
    rewrite_map = {}  # index -> new_query

    for i, ex in enumerate(examples):
        q = ex.get("ads_query", "")
        nl = ex.get("natural_language", "")

        m = re.search(r'title:\(([^)]+)\)', q)
        if not m:
            continue
        inner = m.group(1)
        or_count = len(re.findall(r'\bOR\b', inner, re.IGNORECASE))
        if or_count < 2:
            continue

        if is_non_academic(nl, q):
            remove_indices.add(i)
        else:
            # Academic bag-of-OR: rewrite to title:"phrase"
            # Extract the meaningful words from the OR list
            words = [w.strip().strip("'\"[](),;.?!:") for w in re.split(r'\s+OR\s+', inner, flags=re.IGNORECASE)]
            words = [w for w in words if w and len(w) > 1 and not re.match(r'^\d+$', w)]
            phrase = " ".join(words)

            # Replace the title:(...OR...) with title:"phrase"
            # Get the rest of the query, cleaning up any trailing punctuation
            rest = q[:m.start()] + q[m.end():]
            rest = rest.strip().rstrip(";).").strip()
            new_q = f'title:"{phrase}"'
            if rest:
                new_q = f'{new_q} {rest}'
            rewrite_map[i] = new_q

    return remove_indices, rewrite_map


def fix_encoding(query: str) -> str:
    """Fix encoding issues in identifier fields."""
    fixed = query
    # Mojibake: UTF-8 bytes misread as latin1
    # \u00e2\u0080\u00a6 = mojibake for ellipsis
    fixed = fixed.replace("\u00e2\u0080\u00a6", "...")
    # \u00e2\u0080\u0093 = mojibake for en-dash
    fixed = fixed.replace("\u00e2\u0080\u0093", "-")
    # \u00e2\u0080\u0099 = mojibake for right single quote
    fixed = fixed.replace("\u00e2\u0080\u0099", "'")
    # HTML entities
    fixed = fixed.replace("&amp;", "&")
    fixed = fixed.replace("&lt;", "<")
    fixed = fixed.replace("&gt;", ">")
    fixed = fixed.replace("&nbsp;", " ")
    # URL encoding in identifiers
    fixed = fixed.replace("%26", "&")
    fixed = fixed.replace("%2F", "/")
    fixed = fixed.replace("%3A", ":")
    return fixed


def fix_object_queries(query: str) -> str:
    """Rewrite object:X to abs:"X" since object: returns 400."""
    def replace_object(m):
        val = m.group(1) or m.group(2)
        return f'abs:"{val}"'

    # object:"value" or object:value
    fixed = re.sub(r'object:"([^"]+)"', replace_object, query)
    fixed = re.sub(r'object:(\S+)', lambda m: f'abs:"{m.group(1)}"', fixed)
    return fixed


def fix_stray_text(query: str) -> str | None:
    """Fix queries with stray bare topic words outside field:value pairs.
    Returns fixed query or None if no fix needed.

    Only fixes genuine bare topic words (not years, initials, or broken syntax).
    """
    # Skip queries with complex/broken syntax we shouldn't touch
    if query.startswith("((") or query.startswith("-docs"):
        return None

    # Pattern: bare text at start followed by author:
    # e.g., "140903A author:\"^Troya\"" -> abs:"140903A" author:"^Troya"
    m = re.match(r'^([A-Za-z][\w.-]+)\s+(author:.*)', query)
    if m and ':' not in m.group(1):
        bare = m.group(1)
        # Skip single letters (likely initials) or year-like numbers
        if len(bare) > 2 and not re.match(r'^\d{4}$', bare):
            rest = m.group(2)
            return f'abs:"{bare}" {rest}'

    # Pattern: author:"..." bareword doctype:
    # Only wrap in abs: if the bare word looks like a topic (not a year or initial)
    m = re.match(r'(author:"[^"]+")\s+([A-Za-z][\w-]+)\s+(doctype:\S+)$', query)
    if m:
        author_part = m.group(1)
        bare = m.group(2)
        doctype = m.group(3)
        # Skip single chars (initials), years, or if it looks like part of author name
        if len(bare) > 2 and not re.match(r'^\d{4}$', bare) and bare[0].isupper():
            # Check it's not a surname initial like "N" after "^Katz,"
            if not re.search(r',"?\s*$', author_part.split('"')[-2] if '"' in author_part else ""):
                return f'{author_part} abs:"{bare}" {doctype}'

    # Pattern: author:"..." bareword at end (topic, not year)
    m = re.match(r'(author:"[^"]+")\s+([A-Za-z][\w-]+)$', query)
    if m:
        author_part = m.group(1)
        bare = m.group(2)
        if len(bare) > 2 and not re.match(r'^\d{4}$', bare) and bare[0].isupper():
            return f'{author_part} abs:"{bare}"'

    return None


def fix_alignment_year(nl: str, query: str) -> str | None:
    """Add missing pubdate if NL mentions a year but query doesn't.

    Conservative: skips operator queries, identifier lookups, and citation refs.
    """
    if "pubdate" in query.lower() or "year" in query.lower():
        return None

    # Skip operator queries — year in NL may refer to the paper being operated on
    if re.search(r'(citations|references|similar|trending|useful|reviews)\(', query, re.IGNORECASE):
        return None

    # Skip identifier/DOI lookups
    if "identifier:" in query.lower() or "doi:" in query.lower() or "arxiv:" in query.lower():
        return None

    # Skip queries that look like citation references (e.g., "Croton+06, MNRAS")
    if re.search(r'MNRAS|ApJ|A&A|Nature|Science|ARA&A', query):
        return None

    # Skip if query contains a DOI-like string
    if re.search(r'10\.\d{4}/', query):
        return None

    # Skip if query contains citation-style content (author names with commas/periods in abs)
    if re.search(r'abs:\([^)]*,\s+AND\s+\w+\.\s+AND', query):
        return None

    years = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', nl)
    if not years:
        return None

    # Skip if year appears in the query already (e.g., in an identifier or DOI)
    for y in years:
        if y in query:
            return None

    # Skip if NL year is embedded in a non-date context (DOI, bibcode, etc.)
    # Check that the year in NL appears as a standalone year mention
    nl_lower = nl.lower()
    for y in years:
        # Year should be preceded by space/start and followed by space/end/punctuation
        if not re.search(rf'(?:^|\s){y}(?:\s|$|[,.])', nl):
            return None

    if len(years) == 1:
        return f'{query} year:{years[0]}'
    elif len(years) == 2:
        y1, y2 = sorted(years)
        return f'{query} pubdate:[{y1} TO {y2}]'

    return None


def fix_collection_to_database(query: str) -> str:
    """Standardize collection: → database: for consistency."""
    return re.sub(r'\bcollection:', 'database:', query)


def fix_nested_operators(query: str) -> str:
    """Flatten nested operators that cause 502 errors.

    e.g., trending(similar(abs:"JWST")) → trending(abs:"JWST")
    """
    # similar() inside another operator causes 502
    fixed = re.sub(
        r'((?:trending|useful|reviews|citations|references)\()\s*similar\(([^)]+)\)\s*\)',
        r'\1\2)',
        query,
    )
    return fixed


def fix_author_format(query: str) -> str:
    """Fix common author format issues."""
    fixed = query

    # Fix trailing space inside author quotes: author:"^chabrier " -> author:"^chabrier"
    fixed = re.sub(r'(author:"[^"]*?)\s+"', r'\1"', fixed)

    # Fix lowercase first-author: author:"^leroy ak" -> author:"^Leroy, A"
    # This is too risky to do generically; we'll rely on validation to catch these
    return fixed


# ---------------------------------------------------------------------------
# Manual rewrites for specific known-bad entries
# ---------------------------------------------------------------------------

# Map of (natural_language_prefix) -> corrected ads_query
# These are entries identified during validation that need manual fixes
MANUAL_REWRITES = {
    # Academic bag-of-OR that need specific rewrites
    "38th IEEE Symposium on Foundations of Computer Science":
        'title:"Foundations of Computer Science" year:1997',
    "Saturn radio emission coronal mass ejection effects":
        'abs:"Saturn" abs:"radio emission" abs:"coronal mass ejection"',
    "Jupiter Saturn auroral response solar wind activity":
        'abs:"Jupiter" abs:"Saturn" abs:"auroral" abs:"solar wind"',
    "papers by Lee on experimental verification optical vortex coronagraph":
        'author:"^Lee" abs:"optical vortex coronagraph" doctype:article',
    "coronal mass ejections":
        'title:"coronal mass ejections"',
    "title contains coronal mass ejections":
        'title:"coronal mass ejections"',
    "coronal mass ejections in title field":
        'title:"coronal mass ejections"',
    "cosmic microwave background":
        'title:"cosmic microwave background"',
    "title contains cosmic microwave background":
        'title:"cosmic microwave background"',
    "cosmic microwave background in title field":
        'title:"cosmic microwave background"',
    "mechanical properties magnesium AZ91 carbon nanotubes SiC Al2O3 reinforcement":
        'abs:"mechanical properties" abs:"magnesium" abs:"AZ91" abs:"carbon nanotubes"',
    # Fix author-related issues
    "papers by guillermo chiape":
        'author:"Chiappe, G" doctype:article',
    "papers by leroy as first author":
        'author:"^Leroy" doctype:article',
    "papers by Simon on coagulation 2016":
        'author:"^Simon" abs:"coagulation" year:2016 doctype:article',
    "papers by Riffel on active galactic nuclei integral field spectroscopy":
        'author:"^Riffel" abs:"active galactic nuclei" abs:"integral field spectroscopy" doctype:article',
    "papers by Samovar on tidal effects":
        'author:"Samovar" abs:"tidal" doctype:article',
    "papers by Somovar on tidal effects":
        'author:"Somovar" abs:"tidal" doctype:article',
    "papers by Sazanov on tidal disruption":
        'author:"Sazonov" abs:"tidal disruption" doctype:article',
    "papers by Troya on 140903A":
        'author:"^Troja" abs:"140903A" doctype:article',
    "papers by abazajian on dark matter":
        'author:"^Abazajian" abs:"dark matter" doctype:article',
    "papers by olejak":
        'author:"Olejak" doctype:article',
    "papers by Pasham on QPOs":
        'author:"Pasham" abs:"QPO" doctype:article',
    "papers by Howell S":
        'author:"Howell, S" doctype:article',
    "papers by Jacobson and Scheeres from 2011":
        'author:"Jacobson" author:"Scheeres" year:2011 doctype:article',
    "papers by Babyk and Buote":
        'author:"Babyk" author:"Buote" doctype:article',
    "papers by Andreoni 2019 arxiv":
        'author:"Andreoni" year:2019 doctype:eprint',
    "papers by Davies on scaled sky subtraction":
        'author:"^Davies" abs:"scaled sky subtraction" doctype:article',
    "Einstein's black holes papers":
        'author:"Einstein, A" abs:"black holes"',
    "papers by Khachaturian on Armenian symphonism centennial":
        None,  # Remove: not academic/astronomy content
    "RX J1615 X-ray source observations":
        'abs:"RX J1615" abs:"X-ray" abs:"observation"',
    # Round 2 fixes
    "software mentioned in papers by Jarmak about planetary atmospheres":
        'author:"Jarmak" has:mention abs:"planetary"',
    "CSA-funded research on satellites":
        'ack:"Canadian Space Agency" abs:"satellite"',
    "NASAP-70 user manual programmer documentation":
        None,  # Remove: not academic
    "SIGIR 98 proceedings 21st annual international ACM conference research development information retri":
        None,  # Remove: CS proceedings lookup, not astronomy
    "CIKM 2009 proceedings 18th ACM conference information knowledge management":
        None,  # Remove
    "CIKM 2008 proceedings information knowledge management conference":
        None,  # Remove
    "CHI 2007 proceedings human computer interaction SIGCHI conference":
        None,  # Remove
    "SIGMOD 2007 proceedings ACM conference data management":
        None,  # Remove
    "VLDB 2003 proceedings very large data bases 30th international conference":
        None,  # Remove
}


# ---------------------------------------------------------------------------
# Main cleanup
# ---------------------------------------------------------------------------

# NL keys that should ONLY match exact NL (not prefix) to avoid
# hitting generated variants with bibstem/bibgroup/property
_EXACT_ONLY_KEYS = {
    "coronal mass ejections",
    "cosmic microwave background",
    "title contains coronal mass ejections",
    "coronal mass ejections in title field",
    "title contains cosmic microwave background",
    "cosmic microwave background in title field",
}


def clean_examples(examples: list, verbose: bool = False) -> tuple:
    """Clean all examples. Returns (cleaned, removed, stats)."""
    removed = []
    stats = {
        "bag_of_or_removed": 0,
        "bag_of_or_rewritten": 0,
        "encoding_fixed": 0,
        "object_rewritten": 0,
        "stray_text_fixed": 0,
        "alignment_fixed": 0,
        "manual_rewrite": 0,
        "manual_remove": 0,
        "author_format_fixed": 0,
    }

    # Step 1: Find bag-of-OR entries
    remove_indices, rewrite_map = find_bag_of_or(examples)

    stats["collection_to_database"] = 0
    stats["nested_operator_fixed"] = 0

    cleaned = []
    for i, ex in enumerate(examples):
        ex = copy.deepcopy(ex)
        nl = ex.get("natural_language", "")
        query = ex.get("ads_query", "")
        changes = []

        # Check manual rewrites
        manual_match = None
        for nl_key, new_query in MANUAL_REWRITES.items():
            if nl == nl_key or (nl.startswith(nl_key) and nl_key not in _EXACT_ONLY_KEYS):
                # For exact-only keys or any key: skip if query uses
                # bibstem/bibgroup/property (generated variants we shouldn't touch)
                if "bibstem:" in query or "bibgroup:" in query or "property:" in query:
                    continue
                # For keys in _EXACT_ONLY_KEYS, only match if query is
                # the bad title:(...OR...) pattern
                if nl_key in _EXACT_ONLY_KEYS:
                    if "title:(" not in query:
                        continue
                manual_match = (nl_key, new_query)
                break

        if manual_match:
            nl_key, new_query = manual_match
            if new_query is None:
                # Remove
                removed.append({"index": i, "reason": "manual_remove", **ex})
                stats["manual_remove"] += 1
                if verbose:
                    print(f"  [{i}] MANUAL REMOVE: {nl[:60]}")
                continue
            else:
                if new_query != query:
                    changes.append(f"manual_rewrite: {query} -> {new_query}")
                    ex["ads_query"] = new_query
                    query = new_query
                    stats["manual_rewrite"] += 1

        # Step 1: Bag-of-OR removal
        elif i in remove_indices:
            removed.append({"index": i, "reason": "non_academic_bag_of_or", **ex})
            stats["bag_of_or_removed"] += 1
            if verbose:
                print(f"  [{i}] REMOVE bag-of-OR: {nl[:60]}")
            continue

        # Step 1b: Bag-of-OR rewrite
        elif i in rewrite_map:
            new_q = rewrite_map[i]
            changes.append(f"bag_of_or_rewrite: {query} -> {new_q}")
            ex["ads_query"] = new_q
            query = new_q
            stats["bag_of_or_rewritten"] += 1

        # Step 2: Fix encoding
        fixed = fix_encoding(query)
        if fixed != query:
            changes.append(f"encoding_fix: {query} -> {fixed}")
            ex["ads_query"] = fixed
            query = fixed
            stats["encoding_fixed"] += 1

        # Step 3: object: queries — leave as-is
        # object: works when discipline=astrophysics (d=astrophysics param)
        # No rewriting needed; server should set discipline param at query time

        # Step 4: Fix author format
        fixed = fix_author_format(query)
        if fixed != query:
            changes.append(f"author_fix: {query} -> {fixed}")
            ex["ads_query"] = fixed
            query = fixed
            stats["author_format_fixed"] += 1

        # Step 5: Fix stray text
        fixed = fix_stray_text(query)
        if fixed:
            changes.append(f"stray_text_fix: {query} -> {fixed}")
            ex["ads_query"] = fixed
            query = fixed
            stats["stray_text_fixed"] += 1

        # Step 6: Fix alignment (year in NL but not query)
        fixed = fix_alignment_year(nl, query)
        if fixed:
            changes.append(f"alignment_fix: {query} -> {fixed}")
            ex["ads_query"] = fixed
            query = fixed
            stats["alignment_fixed"] += 1

        # Step 7: Standardize collection: → database:
        fixed = fix_collection_to_database(query)
        if fixed != query:
            changes.append(f"collection_to_database: {query} -> {fixed}")
            ex["ads_query"] = fixed
            query = fixed
            stats["collection_to_database"] += 1

        # Step 8: Flatten nested operators
        fixed = fix_nested_operators(query)
        if fixed != query:
            changes.append(f"nested_op_fix: {query} -> {fixed}")
            ex["ads_query"] = fixed
            query = fixed
            stats["nested_operator_fixed"] += 1

        if verbose and changes:
            print(f"  [{i}] {'; '.join(changes)}")

        cleaned.append(ex)

    return cleaned, removed, stats


def main():
    parser = argparse.ArgumentParser(description="Clean gold training examples")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry run)")
    parser.add_argument("--verbose", action="store_true", help="Show each change")
    parser.add_argument("--gold-file", type=str, default=str(GOLD_FILE))
    args = parser.parse_args()

    gold_path = Path(args.gold_file)
    print(f"Loading {gold_path}...")
    examples = json.loads(gold_path.read_text())
    print(f"  Loaded {len(examples)} examples")

    cleaned, removed, stats = clean_examples(examples, verbose=args.verbose)

    print(f"\n{'='*60}")
    print("CLEANUP SUMMARY")
    print(f"{'='*60}")
    print(f"  Original count:      {len(examples)}")
    print(f"  After cleanup:       {len(cleaned)}")
    print(f"  Removed:             {len(removed)}")
    print(f"  ---")
    for key, val in stats.items():
        if val > 0:
            print(f"  {key:25s} {val}")
    print(f"{'='*60}")

    if args.apply:
        print(f"\nWriting {len(cleaned)} cleaned examples to {gold_path}...")
        gold_path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n")

        removed_path = Path(str(REMOVED_FILE))
        removed_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Writing {len(removed)} removed examples to {removed_path}...")
        removed_path.write_text(json.dumps(removed, indent=2, ensure_ascii=False) + "\n")

        print("Done!")
    else:
        print("\nDRY RUN — use --apply to write changes")


if __name__ == "__main__":
    main()
