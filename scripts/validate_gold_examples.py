#!/usr/bin/env python3
"""Batch validation of gold training examples for NL-to-query translation.

Validates all examples in gold_examples.json through:
1. Static syntax checks (brackets, quotes, parens, field names, enum values)
2. NL quality checks (no ADS syntax leaking into NL, length, etc.)
3. NL-query alignment heuristics (first-author caret, refereed, date mentions)
4. API result checks (query returns > 0 results)

Supports --resume to continue from where a previous run left off.

Usage:
    python scripts/validate_gold_examples.py
    python scripts/validate_gold_examples.py --resume
    python scripts/validate_gold_examples.py --skip-api
    python scripts/validate_gold_examples.py --start 100 --end 200
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote
from urllib.error import HTTPError, URLError

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_FILE = PROJECT_ROOT / "data" / "datasets" / "raw" / "gold_examples.json"
RESULTS_FILE = PROJECT_ROOT / "data" / "reference" / "validation_results.json"
REPORT_FILE = PROJECT_ROOT / "data" / "reference" / "validation_report.md"
ENV_FILE = PROJECT_ROOT / ".env"


# ---------------------------------------------------------------------------
# Inline field/enum definitions (avoids importing project modules that need httpx)
# ---------------------------------------------------------------------------

ADS_FIELD_NAMES = {
    "abs", "abstract", "title", "keyword", "full", "body", "ack",
    "author", "author_count", "orcid", "orcid_pub", "orcid_user", "orcid_other",
    "aff", "aff_id", "inst", "affil",
    "bibcode", "bibstem", "bibgroup", "pub", "pubdate", "year", "volume", "issue", "page", "doctype",
    "doi", "arxiv", "arxiv_class", "identifier", "alternate_bibcode",
    "citation_count", "read_count", "cite_read_boost", "classic_factor",
    "data", "property", "esources",
    "object", "database", "collection",
    "lang", "copyright", "grant", "entdate", "entry_date", "editor", "book_author",
    "caption", "comment", "alternate_title",
    "mention", "mention_count", "credit", "credit_count",
    "has", "pos", "simbad_object_facet_hier",
    "vizier", "simbad", "ned_object_facet_hier",
    "first_author", "first_author_norm", "orcid_pub", "orcid_user", "orcid_other",
}

DOCTYPES = frozenset({
    "abstract", "article", "book", "bookreview", "catalog", "circular",
    "editorial", "eprint", "erratum", "inbook", "inproceedings",
    "mastersthesis", "misc", "newsletter", "obituary", "phdthesis",
    "pressrelease", "proceedings", "proposal", "software", "talk", "techreport",
})

PROPERTIES = frozenset({
    "ads_openaccess", "author_openaccess", "eprint_openaccess", "pub_openaccess",
    "openaccess", "article", "nonarticle", "refereed", "notrefereed",
    "eprint", "inproceedings", "software", "catalog",
    "associated", "data", "esource", "inspire", "library_catalog",
    "presentation", "toc", "ocr_abstract",
})

COLLECTIONS = frozenset({"astronomy", "physics", "general", "earthscience"})

BIBGROUPS = frozenset({
    "HST", "JWST", "Spitzer", "Chandra", "XMM", "GALEX", "Kepler", "K2",
    "TESS", "FUSE", "IUE", "EUVE", "Copernicus", "IRAS", "WISE", "NEOWISE",
    "Fermi", "Swift", "RXTE", "NuSTAR", "SOHO", "STEREO", "SDO",
    "ESO/Telescopes", "CFHT", "Gemini", "Keck", "VLT", "Subaru", "NOAO",
    "NOIRLab", "CTIO", "KPNO", "Pan-STARRS", "SDSS", "2MASS", "UKIRT",
    "ALMA", "JCMT", "APEX", "ARECIBO", "VLA", "VLBA", "GBT", "LOFAR",
    "MeerKAT", "SKA", "Gaia", "Hipparcos", "CfA", "NASA PubSpace", "LISA",
    "LIGO", "SETI", "ESO",
})

ESOURCES = frozenset({
    "PUB_PDF", "PUB_HTML", "EPRINT_PDF", "EPRINT_HTML",
    "AUTHOR_PDF", "AUTHOR_HTML", "ADS_PDF", "ADS_SCAN",
})

DATA_SOURCES = frozenset({
    "ARI", "BICEP2", "Chandra", "CXO", "ESA", "ESO", "GCPD", "GTC",
    "HEASARC", "Herschel", "INES", "IRSA", "ISO", "KOA", "MAST",
    "NED", "NExScI", "NOAO", "PDS", "SIMBAD", "Spitzer", "TNS", "VizieR", "XMM",
})

HAS_VALUES = frozenset({
    "abstract", "ack", "aff", "aff_id", "author", "bibgroup", "body",
    "citation", "comment", "credit", "data", "database", "doctype", "doi",
    "first_author", "grant", "identifier", "institution", "issue", "keyword",
    "mention", "orcid_other", "orcid_pub", "orcid_user", "origin", "property",
    "pub", "pub_raw", "publisher", "reference", "title", "uat", "volume",
})

FIELD_ENUMS = {
    "doctype": DOCTYPES,
    "collection": COLLECTIONS,
    "database": COLLECTIONS,
    "property": PROPERTIES,
    "bibgroup": BIBGROUPS,
    "esources": ESOURCES,
    "data": DATA_SOURCES,
    "has": HAS_VALUES,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_api_key() -> str | None:
    """Load ADS_API_KEY from .env file or environment."""
    key = os.environ.get("ADS_API_KEY")
    if key:
        return key.strip()
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "ADS_API_KEY":
                val = v.strip().strip("'").strip('"')
                os.environ["ADS_API_KEY"] = val
                return val
    return None


def suggest_correction(field_name: str, invalid_value: str) -> list[str]:
    """Suggest corrections for invalid enum values."""
    valid_values = FIELD_ENUMS.get(field_name)
    if not valid_values:
        return []
    invalid_lower = invalid_value.lower()
    suggestions = []
    for valid in valid_values:
        vl = valid.lower()
        if vl.startswith(invalid_lower) or invalid_lower.startswith(vl):
            suggestions.append((0, valid))
        elif invalid_lower in vl or vl in invalid_lower:
            suggestions.append((1, valid))
    suggestions.sort(key=lambda x: x[0])
    return [s[1] for s in suggestions[:3]]


# ---------------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------------

@dataclass
class ExampleResult:
    """Result for a single training example."""
    index: int
    natural_language: str
    ads_query: str
    category: str
    # Syntax
    syntax_pass: bool = True
    syntax_errors: list = field(default_factory=list)
    syntax_warnings: list = field(default_factory=list)
    # Constraint (enum) validation
    constraint_pass: bool = True
    constraint_errors: list = field(default_factory=list)
    # NL quality
    nl_pass: bool = True
    nl_issues: list = field(default_factory=list)
    # NL-query alignment
    alignment_pass: bool = True
    alignment_warnings: list = field(default_factory=list)
    # API test
    api_tested: bool = False
    api_pass: object = None  # bool or None
    api_num_results: object = None
    api_error: object = None
    # Overall
    overall_pass: bool = True

    def compute_overall(self):
        self.overall_pass = (
            self.syntax_pass
            and self.constraint_pass
            and self.nl_pass
            and (self.api_pass is not False)
        )


def check_syntax(query: str) -> tuple:
    """Run static syntax checks. Returns (pass, errors, warnings)."""
    errors = []
    warnings = []

    if not query or not query.strip():
        return False, ["Empty query"], []

    query = query.strip()

    # Unbalanced quotes
    quote_count = query.count('"')
    if quote_count % 2 != 0:
        errors.append("Unbalanced quotes")

    # Unbalanced parens
    paren_depth = 0
    for ch in query:
        if ch == '(':
            paren_depth += 1
        elif ch == ')':
            paren_depth -= 1
        if paren_depth < 0:
            errors.append("Unbalanced parentheses (extra closing)")
            break
    if paren_depth > 0:
        errors.append("Unbalanced parentheses (unclosed)")

    # Unbalanced brackets
    bracket_count = query.count("[") - query.count("]")
    if bracket_count != 0:
        errors.append("Unbalanced brackets")

    # Check field prefixes -- pattern that avoids false positives from coords
    # Strip quoted strings first to avoid matching colons inside quotes
    # (e.g., full:"urn:nasa:pds" would falsely flag urn: and nasa:)
    field_pattern = r"(?<![.\d\w])(\^?[a-zA-Z_]{2,}):"
    query_no_quotes = re.sub(r'"[^"]*"', '""', query)
    fields_used = re.findall(field_pattern, query_no_quotes)
    for fld in fields_used:
        fld_lower = fld.lower()
        if fld_lower.startswith("^"):
            base = fld_lower[1:]
            if base not in ADS_FIELD_NAMES and base != "author":
                errors.append(f"Unknown field: {fld}")
        elif fld_lower not in ADS_FIELD_NAMES:
            # Exclude known false positives (e.g., "http", "https", "ftp")
            if fld_lower not in {"http", "https", "ftp", "mailto"}:
                errors.append(f"Unknown field: {fld}")

    # Caret outside quotes
    if re.search(r'\^author:', query):
        errors.append("Caret outside quotes: use author:\"^Last\" not ^author:\"Last\"")

    # pubdate range syntax
    for m in re.finditer(r"pubdate:\s*\[([^\]]+)\]", query, re.IGNORECASE):
        range_str = m.group(1)
        if " TO " not in range_str.upper():
            errors.append(f"Invalid pubdate range: [{range_str}] (missing TO)")

    # Leading/trailing boolean operators
    if re.match(r"^\s*(AND|OR)\s+", query, re.IGNORECASE):
        errors.append("Query starts with AND/OR")
    if re.search(r"\s+(AND|OR|NOT)\s*$", query, re.IGNORECASE):
        errors.append("Query ends with boolean operator")

    # Double boolean operators
    if re.search(r"\b(AND|OR|NOT)\s+(AND|OR|NOT)\b", query, re.IGNORECASE):
        errors.append("Consecutive boolean operators")

    # Unquoted bibstem warning
    for m in re.finditer(r'bibstem:([^\s()"]+)', query, re.IGNORECASE):
        val = m.group(1)
        warnings.append(f"Unquoted bibstem: bibstem:{val}")

    return len(errors) == 0, errors, warnings


def check_constraints(query: str) -> tuple:
    """Validate enum field constraints. Returns (pass, errors)."""
    errors = []
    constrained_fields = ["doctype", "database", "collection", "property", "bibgroup", "esources", "data", "has"]

    for field_name in constrained_fields:
        valid_values = FIELD_ENUMS.get(field_name)
        if not valid_values:
            continue
        valid_lower = {v.lower() for v in valid_values}

        # Match field:value, field:"value", field:(v1 OR v2)
        pattern = rf'\b{field_name}:\s*(?:"([^"]+)"|(\([^)]+\))|([^\s()]+))'
        for match in re.finditer(pattern, query, re.IGNORECASE):
            if match.group(1):  # Quoted
                value = match.group(1)
                if value.lower() not in valid_lower:
                    sugg = suggest_correction(field_name, value)
                    msg = f"Invalid {field_name}:\"{value}\""
                    if sugg:
                        msg += f" (did you mean: {', '.join(sugg)}?)"
                    errors.append(msg)
            elif match.group(2):  # Parenthesized
                inner = match.group(2)[1:-1]
                values = [v.strip().strip('"') for v in re.split(r"\s+OR\s+|\s+", inner, flags=re.IGNORECASE)]
                for v in values:
                    if v and v.lower() not in valid_lower:
                        sugg = suggest_correction(field_name, v)
                        msg = f"Invalid {field_name}:{v}"
                        if sugg:
                            msg += f" (did you mean: {', '.join(sugg)}?)"
                        errors.append(msg)
            else:  # Bare
                value = match.group(3).rstrip(",;")
                if value.lower() not in valid_lower:
                    sugg = suggest_correction(field_name, value)
                    msg = f"Invalid {field_name}:{value}"
                    if sugg:
                        msg += f" (did you mean: {', '.join(sugg)}?)"
                    errors.append(msg)

    return len(errors) == 0, errors


def check_nl_quality(nl: str, category: str = "") -> tuple:
    """Check NL string for quality issues. Returns (pass, issues)."""
    issues = []

    # Skip syntax-leak checks for categories where NL is intentionally raw syntax
    syntax_demo_categories = {"syntax", "object"}
    skip_syntax_leak = category in syntax_demo_categories

    syntax_patterns = [
        (r"\bauthor:", "contains 'author:'"),
        (r"\babs:", "contains 'abs:'"),
        (r"\babstract:", "contains 'abstract:'"),
        (r"\btitle:", "contains 'title:'"),
        (r"\bpubdate:", "contains 'pubdate:'"),
        (r"\bbibstem:", "contains 'bibstem:'"),
        (r"\bobject:", "contains 'object:'"),
        (r"\bkeyword:", "contains 'keyword:'"),
        (r"\bdoi:(?!\s*10\.)", "contains 'doi:'"),
        (r"\barXiv:(?!\s*\d)", "contains 'arXiv:'"),
        (r"\borcid:", "contains 'orcid:'"),
        (r"\baff:", "contains 'aff:'"),
        (r"\binst:", "contains 'inst:'"),
        (r"\bcitation_count:", "contains 'citation_count:'"),
        (r"\bproperty:", "contains 'property:'"),
        (r"\b(?:database|collection):", "contains 'collection/database:'"),
        (r"\bdoctype:", "contains 'doctype:'"),
        (r"\bfull:", "contains 'full:'"),
        (r"\bbody:", "contains 'body:'"),
    ]

    if not skip_syntax_leak:
        for pattern, message in syntax_patterns:
            if re.search(pattern, nl, re.IGNORECASE):
                issues.append(message)

    # Range syntax
    if re.search(r"\[[^\]]+\s+TO\s+[^\]]+\]", nl, re.IGNORECASE):
        issues.append("contains range syntax [X TO Y]")

    # ^ prefix
    if re.search(r"\^[a-z]", nl, re.IGNORECASE):
        issues.append("contains ^ prefix (first author syntax)")

    # Basic quality
    if len(nl) < 5:
        issues.append("too short (< 5 chars)")
    if len(nl) > 300:
        issues.append("too long (> 300 chars)")
    if nl.count('"') > 6:
        issues.append("too many quotes")

    return len(issues) == 0, issues


def check_alignment(nl: str, query: str, category: str) -> tuple:
    """Check NL-to-query alignment. Returns (pass, warnings)."""
    warnings = []
    nl_lower = nl.lower()
    query_lower = query.lower()

    # First author checks
    if 'author:"^' in query_lower or "author:(\"^" in query_lower:
        if "first author" not in nl_lower and "first-author" not in nl_lower and "led by" not in nl_lower:
            if category != "first_author":
                warnings.append("Query uses first-author (^) but NL doesn't mention 'first author'")
    if ("first author" in nl_lower or "first-author" in nl_lower) and "^" not in query:
        warnings.append("NL mentions 'first author' but query lacks ^ operator")

    # Refereed
    if any(w in nl_lower for w in ["refereed", "peer-reviewed", "peer reviewed"]):
        if "property:refereed" not in query_lower:
            warnings.append("NL mentions refereed/peer-reviewed but query lacks property:refereed")

    # Date mentions
    date_words = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', nl)
    if date_words and "pubdate" not in query_lower and "year" not in query_lower:
        warnings.append(f"NL mentions year(s) {date_words} but query has no date constraint")

    # Citation/reference confusion
    if "citations(" in query_lower:
        if "cited by" in nl_lower or "references of" in nl_lower:
            warnings.append("Possible citations/references confusion")
    if "references(" in query_lower:
        if "citing" in nl_lower or "that cite" in nl_lower:
            warnings.append("Possible citations/references confusion")

    # Category sanity
    if category == "first_author" and "^" not in query:
        warnings.append("Category='first_author' but query has no ^ operator")
    if category == "author" and "author" not in query_lower and "orcid" not in query_lower:
        warnings.append("Category='author' but query has no author/orcid field")

    return len(warnings) == 0, warnings


# ---------------------------------------------------------------------------
# API testing (stdlib only -- no httpx dependency)
# ---------------------------------------------------------------------------

EXPENSIVE_OPS = re.compile(r'(similar|useful|trending|reviews)\(', re.IGNORECASE)
DISCIPLINE_FIELDS = re.compile(r'\b(object|uat):', re.IGNORECASE)


def _is_expensive_query(query: str) -> bool:
    """Check if a query uses operators that need longer timeouts."""
    if EXPENSIVE_OPS.search(query):
        return True
    # Nested operators (operator inside operator)
    depth = 0
    for ch in query:
        if ch == '(':
            depth += 1
            if depth >= 2:
                return True
        elif ch == ')':
            depth -= 1
    return False


def _needs_discipline_param(query: str) -> bool:
    """Check if query uses fields that require d=astrophysics."""
    return bool(DISCIPLINE_FIELDS.search(query))


def test_query_api(query: str, api_key: str) -> tuple:
    """Test a query against ADS API using urllib. Returns (pass, num_results, error)."""
    params = {"q": query, "rows": 1, "fl": "bibcode"}
    if _needs_discipline_param(query):
        params["d"] = "astrophysics"

    url = "https://api.adsabs.harvard.edu/v1/search/query?" + urlencode(params)
    req = Request(url, headers={"Authorization": f"Bearer {api_key}"})

    timeout = 45 if _is_expensive_query(query) else 15

    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            num_found = data.get("response", {}).get("numFound", 0)
            return (num_found > 0), num_found, None
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:300]
        except Exception:
            pass
        if e.code == 429:
            return None, None, "Rate limited (429)"
        elif e.code == 400:
            try:
                err_data = json.loads(body)
                msg = err_data.get("error", {}).get("msg", body[:200])
            except Exception:
                msg = body[:200]
            return False, 0, f"HTTP 400: {msg}"
        else:
            return False, 0, f"HTTP {e.code}: {body[:200]}"
    except URLError as e:
        reason = str(e.reason)
        if "timed out" in reason.lower():
            return None, None, f"Timeout ({timeout}s): {reason}"
        return None, None, f"URL error: {reason}"
    except TimeoutError:
        return None, None, f"Timeout ({timeout}s)"
    except Exception as e:
        return None, None, f"Error: {e}"


# ---------------------------------------------------------------------------
# Main validation loop
# ---------------------------------------------------------------------------

def validate_all(
    examples: list,
    existing_results: dict | None = None,
    skip_api: bool = False,
    api_key: str | None = None,
    start: int = 0,
    end: int | None = None,
    rate_limit: float = 1.0,
) -> list:
    if existing_results is None:
        existing_results = {}
    if end is None:
        end = len(examples)

    results = []
    api_tested_count = 0
    last_api_time = 0.0

    try:
        for i in range(start, min(end, len(examples))):
            ex = examples[i]
            nl = ex.get("natural_language", "")
            query = ex.get("ads_query", "")
            cat = ex.get("category", "")

            # Resume: reuse cached result
            if i in existing_results:
                prev = existing_results[i]
                if prev.get("api_tested", False) or skip_api:
                    r = ExampleResult(index=i, natural_language=nl, ads_query=query, category=cat)
                    for k, v in prev.items():
                        if hasattr(r, k):
                            setattr(r, k, v)
                    results.append(r)
                    if (i - start) % 500 == 0:
                        print(f"  [{i}/{end}] Reusing cached result")
                    continue

            r = ExampleResult(index=i, natural_language=nl, ads_query=query, category=cat)

            # 1. Syntax
            r.syntax_pass, r.syntax_errors, r.syntax_warnings = check_syntax(query)

            # 2. Constraints
            r.constraint_pass, r.constraint_errors = check_constraints(query)

            # 3. NL quality
            r.nl_pass, r.nl_issues = check_nl_quality(nl, cat)

            # 4. Alignment
            r.alignment_pass, r.alignment_warnings = check_alignment(nl, query, cat)

            # 5. API test
            if not skip_api and api_key and r.syntax_pass:
                now = time.time()
                elapsed = now - last_api_time
                if elapsed < rate_limit:
                    time.sleep(rate_limit - elapsed)

                api_pass, num_results, api_err = test_query_api(query, api_key)
                last_api_time = time.time()
                r.api_tested = True
                r.api_pass = api_pass
                r.api_num_results = num_results
                r.api_error = api_err
                api_tested_count += 1

                # Rate limit backoff
                if api_err and "429" in str(api_err):
                    print(f"  [{i}] Rate limited! Sleeping 60s...")
                    time.sleep(60)
                    api_pass, num_results, api_err = test_query_api(query, api_key)
                    last_api_time = time.time()
                    r.api_pass = api_pass
                    r.api_num_results = num_results
                    r.api_error = api_err

            r.compute_overall()
            results.append(r)

            if (i - start) % 100 == 0:
                sf = sum(1 for x in results if not x.syntax_pass)
                af = sum(1 for x in results if x.api_pass is False)
                print(f"  [{i}/{end}] processed={len(results)}, syntax_fail={sf}, api_fail={af}, api_tested={api_tested_count}", flush=True)

            # Checkpoint every 500
            if len(results) % 500 == 0 and len(results) > 0:
                save_results(results, RESULTS_FILE)
                print(f"  Checkpoint saved at {len(results)} results", flush=True)

    except KeyboardInterrupt:
        print(f"\nInterrupted. Saving {len(results)} results...")
    finally:
        pass

    return results


def save_results(results: list, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(r) for r in results]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_existing_results(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {r["index"]: r for r in data}


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(results: list, report_path: Path):
    total = len(results)
    if total == 0:
        report_path.write_text("# Validation Report\n\nNo results.\n")
        return

    syntax_pass = sum(1 for r in results if r.syntax_pass)
    constraint_pass = sum(1 for r in results if r.constraint_pass)
    nl_pass = sum(1 for r in results if r.nl_pass)
    alignment_pass = sum(1 for r in results if r.alignment_pass)
    api_tested = sum(1 for r in results if r.api_tested)
    api_pass = sum(1 for r in results if r.api_pass is True)
    api_fail = sum(1 for r in results if r.api_pass is False)
    overall_pass = sum(1 for r in results if r.overall_pass)

    # Category breakdown
    categories = {}
    for r in results:
        cat = r.category or "(empty)"
        if cat not in categories:
            categories[cat] = {"total": 0, "pass": 0, "syntax_fail": 0, "api_fail": 0, "nl_fail": 0}
        categories[cat]["total"] += 1
        if r.overall_pass:
            categories[cat]["pass"] += 1
        if not r.syntax_pass:
            categories[cat]["syntax_fail"] += 1
        if r.api_pass is False:
            categories[cat]["api_fail"] += 1
        if not r.nl_pass:
            categories[cat]["nl_fail"] += 1

    # Error tallies
    def tally(attr):
        counts = {}
        for r in results:
            for item in getattr(r, attr, []):
                # Normalize year lists etc.
                key = re.sub(r"\[.*?\]", "[...]", str(item))
                counts[key] = counts.get(key, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])

    syntax_err_tally = tally("syntax_errors")
    constraint_err_tally = tally("constraint_errors")
    nl_issue_tally = tally("nl_issues")
    alignment_warn_tally = tally("alignment_warnings")

    api_error_counts = {}
    for r in results:
        if r.api_error:
            key = str(r.api_error)[:100]
            api_error_counts[key] = api_error_counts.get(key, 0) + 1
    api_error_tally = sorted(api_error_counts.items(), key=lambda x: -x[1])

    L = []
    L.append("# Gold Examples Validation Report\n")
    L.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"**Total examples:** {total}\n")
    L.append("## Summary\n")
    L.append("| Check | Pass | Fail/Warn | Rate |")
    L.append("|-------|------|-----------|------|")
    L.append(f"| Syntax | {syntax_pass} | {total - syntax_pass} | {syntax_pass/total*100:.1f}% |")
    L.append(f"| Enum constraints | {constraint_pass} | {total - constraint_pass} | {constraint_pass/total*100:.1f}% |")
    L.append(f"| NL quality | {nl_pass} | {total - nl_pass} | {nl_pass/total*100:.1f}% |")
    L.append(f"| NL-query alignment | {alignment_pass} | {total - alignment_pass} | {alignment_pass/total*100:.1f}% |")
    if api_tested > 0:
        L.append(f"| API (>0 results) | {api_pass} | {api_fail} | {api_pass/api_tested*100:.1f}% of {api_tested} tested |")
    else:
        L.append("| API | -- | -- | Not tested |")
    L.append(f"| **Overall** | **{overall_pass}** | **{total - overall_pass}** | **{overall_pass/total*100:.1f}%** |")
    L.append("")

    L.append("## By Category\n")
    L.append("| Category | Total | Pass | Syntax Fail | API Fail | NL Fail |")
    L.append("|----------|-------|------|-------------|----------|---------|")
    for cat in sorted(categories.keys()):
        c = categories[cat]
        L.append(f"| {cat} | {c['total']} | {c['pass']} | {c['syntax_fail']} | {c['api_fail']} | {c['nl_fail']} |")
    L.append("")

    def append_tally_section(title, tally_list, limit=20):
        if not tally_list:
            return
        L.append(f"## {title}\n")
        for item, count in tally_list[:limit]:
            L.append(f"- **{count}x** {item}")
        L.append("")

    append_tally_section("Common Syntax Errors", syntax_err_tally)
    append_tally_section("Common Constraint Errors", constraint_err_tally)
    append_tally_section("Common NL Issues", nl_issue_tally)
    append_tally_section("Common Alignment Warnings", alignment_warn_tally)
    append_tally_section("API Errors", api_error_tally)

    # Sample failures
    failures = [r for r in results if not r.overall_pass]
    if failures:
        L.append(f"## Sample Failures (first 50 of {len(failures)})\n")
        for r in failures[:50]:
            L.append(f"### Example {r.index}: \"{r.natural_language[:80]}\"")
            L.append(f"- **Query:** `{r.ads_query}`")
            L.append(f"- **Category:** {r.category}")
            if r.syntax_errors:
                L.append(f"- **Syntax errors:** {'; '.join(r.syntax_errors)}")
            if r.constraint_errors:
                L.append(f"- **Constraint errors:** {'; '.join(r.constraint_errors)}")
            if r.nl_issues:
                L.append(f"- **NL issues:** {'; '.join(r.nl_issues)}")
            if r.alignment_warnings:
                L.append(f"- **Alignment:** {'; '.join(r.alignment_warnings)}")
            if r.api_error:
                L.append(f"- **API error:** {r.api_error}")
            elif r.api_pass is False:
                L.append(f"- **API:** 0 results")
            L.append("")

    # Zero-result queries
    zero_results = [r for r in results if r.api_tested and r.api_num_results == 0 and r.api_error is None]
    if zero_results:
        L.append(f"## Zero-Result Queries ({len(zero_results)} total)\n")
        for r in zero_results[:100]:
            L.append(f"- [{r.index}] `{r.ads_query}` -- \"{r.natural_language[:60]}\"")
        L.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(L))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Validate gold training examples")
    parser.add_argument("--resume", action="store_true", help="Resume from previous results")
    parser.add_argument("--skip-api", action="store_true", help="Skip API testing")
    parser.add_argument("--start", type=int, default=0, help="Start index")
    parser.add_argument("--end", type=int, default=None, help="End index")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Seconds between API calls")
    parser.add_argument("--gold-file", type=str, default=str(GOLD_FILE))
    parser.add_argument("--results-file", type=str, default=str(RESULTS_FILE))
    parser.add_argument("--report-file", type=str, default=str(REPORT_FILE))
    args = parser.parse_args()

    results_path = Path(args.results_file)
    report_path = Path(args.report_file)

    print(f"Loading examples from {args.gold_file}...")
    examples = json.loads(Path(args.gold_file).read_text())
    print(f"  Loaded {len(examples)} examples")

    api_key = None
    if not args.skip_api:
        api_key = load_api_key()
        if api_key:
            print(f"  ADS API key loaded ({len(api_key)} chars)")
        else:
            print("  WARNING: No ADS_API_KEY found. Skipping API tests.")
            args.skip_api = True

    existing = {}
    if args.resume:
        existing = load_existing_results(results_path)
        print(f"  Loaded {len(existing)} existing results for resume")

    print(f"\nValidating {args.start} to {args.end or len(examples)}...")
    print(f"  API testing: {'ON' if not args.skip_api else 'OFF'}")
    print(f"  Rate limit: {args.rate_limit}s\n")

    results = validate_all(
        examples=examples,
        existing_results=existing if args.resume else None,
        skip_api=args.skip_api,
        api_key=api_key,
        start=args.start,
        end=args.end,
        rate_limit=args.rate_limit,
    )

    print(f"\nSaving {len(results)} results to {results_path}...")
    save_results(results, results_path)

    print(f"Generating report to {report_path}...")
    generate_report(results, report_path)

    total = len(results)
    sf = sum(1 for r in results if not r.syntax_pass)
    cf = sum(1 for r in results if not r.constraint_pass)
    nf = sum(1 for r in results if not r.nl_pass)
    af = sum(1 for r in results if r.api_pass is False)
    op = sum(1 for r in results if r.overall_pass)

    print(f"\n{'='*60}")
    print(f"VALIDATION COMPLETE: {total} examples")
    print(f"  Syntax failures:     {sf}")
    print(f"  Constraint failures: {cf}")
    print(f"  NL quality failures: {nf}")
    print(f"  API failures:        {af}")
    print(f"  Overall pass:        {op}/{total} ({op/total*100:.1f}%)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
