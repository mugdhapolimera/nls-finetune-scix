#!/usr/bin/env python3
"""Evaluate the NL-to-ADS pipeline against the benchmark evaluation set.

Supports multiple backends (NER pipeline, server-based hybrid/RAG) and
both v1 and v2 benchmark formats. Calculates:
- Pass rate (syntax valid + constraint valid + no forbidden patterns)
- Exact match rate
- Field assignment accuracy (precision, recall, F1)
- Pattern match (expected_patterns / forbidden_patterns)
- Optional semantic overlap via ADS API (--semantic)

Results are broken down by category and output to JSON.

Usage:
    # NER-only on v1 (backward compatible)
    python scripts/evaluate_benchmark.py

    # NER-only on v2
    python scripts/evaluate_benchmark.py --benchmark data/datasets/benchmark/benchmark_queries_v2.json

    # NER + runtime augmentation on v2
    python scripts/evaluate_benchmark.py --benchmark data/datasets/benchmark/benchmark_queries_v2.json --with-augmentation

    # Server backend (hybrid/RAG)
    python scripts/evaluate_benchmark.py --backend server --server-url http://localhost:8001 --benchmark data/datasets/benchmark/benchmark_queries_v2.json

    # With semantic overlap
    python scripts/evaluate_benchmark.py --semantic --benchmark data/datasets/benchmark/benchmark_queries_v2.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add the finetune package to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/finetune/src"))

from finetune.domains.scix.pipeline import process_query
from finetune.domains.scix.validate import lint_query, validate_field_constraints


# ---------------------------------------------------------------------------
# Backend abstraction
# ---------------------------------------------------------------------------

@dataclass
class BackendResult:
    """Result from running a query through a backend."""
    query: str
    source: str = "ner_only"
    intents: dict | None = None
    timing: dict | None = None
    rag_context: dict | None = None


class Backend(ABC):
    @abstractmethod
    def run(self, nl_query: str) -> BackendResult:
        ...

    @abstractmethod
    def warmup(self) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class NERBackend(Backend):
    """Runs the NER pipeline directly."""

    def __init__(self, with_augmentation: bool = False):
        self._with_augmentation = with_augmentation
        self._augmentation_loaded = False

    @property
    def name(self) -> str:
        return "ner+augmentation" if self._with_augmentation else "ner"

    def _load_augmentation(self):
        if self._augmentation_loaded:
            return
        if self._with_augmentation:
            try:
                from finetune.domains.scix.uat_lookup import rewrite_abs_to_abs_or_uat
                from finetune.domains.scix.planetary_feature_lookup import (
                    rewrite_abs_to_abs_or_planetary_feature,
                )
                from finetune.domains.scix.institution_lookup import rewrite_aff_to_inst_or_aff
                from finetune.domains.scix.bibstem_lookup import rewrite_bibstem_values
                from finetune.domains.scix.assembler import rewrite_complex_author_wildcards

                self._rewrite_uat = rewrite_abs_to_abs_or_uat
                self._rewrite_pf = rewrite_abs_to_abs_or_planetary_feature
                self._rewrite_inst = rewrite_aff_to_inst_or_aff
                self._rewrite_bibstem = rewrite_bibstem_values
                self._rewrite_author = rewrite_complex_author_wildcards
            except ImportError as e:
                print(f"Warning: Could not load augmentation modules: {e}")
                self._with_augmentation = False
        self._augmentation_loaded = True

    def warmup(self) -> None:
        try:
            process_query("test query")
        except Exception as e:
            print(f"Warning: Pipeline warmup failed: {e}")
        self._load_augmentation()

    def run(self, nl_query: str) -> BackendResult:
        try:
            result = process_query(nl_query)
            query = result.final_query
        except Exception as e:
            return BackendResult(query=f"ERROR: {e}", source="error")

        if self._with_augmentation:
            try:
                query = self._rewrite_inst(query)
                query = self._rewrite_bibstem(query)
                query = self._rewrite_author(query)
                query = self._rewrite_uat(query)
                query = self._rewrite_pf(query)
            except Exception:
                pass  # Fall through with un-augmented query

        return BackendResult(query=query, source=self.name)


class ServerBackend(Backend):
    """Calls a running server's /debug/hybrid endpoint."""

    def __init__(self, server_url: str = "http://localhost:8001"):
        self._url = server_url.rstrip("/")

    @property
    def name(self) -> str:
        return f"server({self._url})"

    def warmup(self) -> None:
        try:
            import httpx
            resp = httpx.get(f"{self._url}/debug/hybrid", params={"q": "test"}, timeout=10)
            if resp.status_code != 200:
                print(f"Warning: Server warmup returned {resp.status_code}")
        except Exception as e:
            print(f"Warning: Server warmup failed: {e}")

    def run(self, nl_query: str) -> BackendResult:
        import httpx
        try:
            t0 = time.monotonic()
            resp = httpx.get(
                f"{self._url}/debug/hybrid",
                params={"q": nl_query},
                timeout=15,
            )
            elapsed = time.monotonic() - t0
            if resp.status_code != 200:
                return BackendResult(
                    query=f"ERROR: HTTP {resp.status_code}",
                    source="error",
                )
            data = resp.json()
            return BackendResult(
                query=data.get("final_query", data.get("query", "")),
                source=data.get("source", "server"),
                intents={
                    "ner": data.get("ner_intent"),
                    "llm": data.get("llm_intent"),
                    "merged": data.get("merged_intent"),
                },
                timing={"total_s": elapsed, **data.get("timing", {})},
                rag_context=data.get("rag_context"),
            )
        except Exception as e:
            return BackendResult(query=f"ERROR: {e}", source="error")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    """Result for a single benchmark test case."""
    test_id: str
    natural_language: str
    expected_query: str | None
    expected_behavior: str | None
    expected_patterns: list[str]
    forbidden_patterns: list[str]
    actual_query: str
    exact_match: bool
    syntax_valid: bool
    syntax_errors: list[str]
    constraint_valid: bool
    constraint_errors: list[str]
    forbidden_matched: list[str]
    pattern_match: bool  # all expected_patterns present
    patterns_missing: list[str]
    field_precision: float
    field_recall: float
    field_f1: float
    passed: bool
    category: str
    subcategory: str
    difficulty: str
    added_in: str = "v1"
    backend_result: BackendResult | None = None


@dataclass
class CategoryStats:
    """Statistics for a category of tests."""
    total: int = 0
    passed: int = 0
    exact_match: int = 0
    syntax_valid: int = 0
    constraint_valid: int = 0
    no_forbidden: int = 0
    pattern_match: int = 0
    field_precision_sum: float = 0.0
    field_recall_sum: float = 0.0
    field_f1_sum: float = 0.0
    field_counted: int = 0

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0.0

    @property
    def exact_match_rate(self) -> float:
        return (self.exact_match / self.total * 100) if self.total > 0 else 0.0

    @property
    def syntax_valid_rate(self) -> float:
        return (self.syntax_valid / self.total * 100) if self.total > 0 else 0.0

    @property
    def avg_field_f1(self) -> float:
        return (self.field_f1_sum / self.field_counted * 100) if self.field_counted > 0 else 0.0


@dataclass
class EvaluationReport:
    """Full evaluation report."""
    timestamp: str
    benchmark_file: str
    backend_name: str
    total_tests: int
    passed_tests: int
    overall_stats: dict
    category_stats: dict[str, dict]
    difficulty_stats: dict[str, dict]
    failed_tests: list[dict]
    all_results: list[TestResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def normalize_query(query: str) -> str:
    """Normalize query for comparison (lowercase, consistent whitespace)."""
    normalized = query.lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    return normalized


def extract_fields(query: str) -> set[str]:
    """Extract field names used in a query."""
    pattern = r"(\^?[a-z_]+):"
    fields = set(re.findall(pattern, query.lower()))
    return fields


def extract_operators(query: str) -> set[str]:
    """Extract operator names used in a query."""
    operators = set()
    operator_pattern = r"\b(citations|references|trending|similar|useful|reviews|topn)\s*\("
    for match in re.finditer(operator_pattern, query.lower()):
        operators.add(match.group(1))
    return operators


def check_forbidden_patterns(query: str, forbidden: list[str]) -> list[str]:
    """Check if query contains any forbidden patterns."""
    matched = []
    for pattern in forbidden:
        if pattern.lower() in query.lower():
            matched.append(pattern)
    return matched


def check_expected_patterns(query: str, expected: list[str]) -> list[str]:
    """Check which expected patterns are missing from query.

    Returns list of missing patterns.
    """
    missing = []
    for pattern in expected:
        if pattern.lower() not in query.lower():
            missing.append(pattern)
    return missing


def compute_field_accuracy(
    actual_query: str, fields_expected: list[str] | None
) -> tuple[float, float, float]:
    """Compute field precision, recall, F1 for a test case.

    Returns (precision, recall, f1). Returns (0, 0, 0) if no fields_expected.
    """
    if not fields_expected:
        return 0.0, 0.0, 0.0

    expected_set = set(f.lower().lstrip("^") for f in fields_expected)
    actual_set = extract_fields(actual_query)
    # Normalize: remove ^ prefix
    actual_set = {f.lstrip("^") for f in actual_set}

    if not expected_set and not actual_set:
        return 1.0, 1.0, 1.0

    intersection = expected_set & actual_set
    precision = len(intersection) / len(actual_set) if actual_set else 0.0
    recall = len(intersection) / len(expected_set) if expected_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return precision, recall, f1


# ---------------------------------------------------------------------------
# Semantic evaluation (optional)
# ---------------------------------------------------------------------------

_semantic_cache: dict[str, list[str]] = {}
_semantic_cache_path: Path | None = None


def _load_semantic_cache(path: Path) -> dict[str, list[str]]:
    global _semantic_cache, _semantic_cache_path
    _semantic_cache_path = path
    if path.exists():
        with open(path) as f:
            _semantic_cache = json.load(f)
    return _semantic_cache


def _save_semantic_cache():
    if _semantic_cache_path:
        _semantic_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(_semantic_cache_path, "w") as f:
            json.dump(_semantic_cache, f, indent=2)


def fetch_bibcodes_cached(query: str, n: int = 50) -> list[str]:
    """Fetch bibcodes with caching."""
    if query in _semantic_cache:
        return _semantic_cache[query]

    api_key = os.environ.get("ADS_API_KEY")
    if not api_key:
        return []

    try:
        import httpx
        response = httpx.get(
            "https://api.adsabs.harvard.edu/v1/search/query",
            params={"q": query, "rows": n, "fl": "bibcode", "sort": "score desc"},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
        )
        if response.status_code == 200:
            data = response.json()
            docs = data.get("response", {}).get("docs", [])
            bibcodes = [doc["bibcode"] for doc in docs if "bibcode" in doc]
            _semantic_cache[query] = bibcodes
            return bibcodes
    except Exception:
        pass
    return []


def compute_semantic_overlap(
    expected_query: str, actual_query: str, n: int = 50
) -> dict:
    """Compute semantic overlap via ADS API bibcode comparison."""
    expected_bibs = set(fetch_bibcodes_cached(expected_query, n))
    actual_bibs = set(fetch_bibcodes_cached(actual_query, n))

    if not expected_bibs and not actual_bibs:
        return {"jaccard": 1.0, "precision": 1.0, "recall": 1.0}
    if not expected_bibs or not actual_bibs:
        return {"jaccard": 0.0, "precision": 0.0, "recall": 0.0}

    intersection = expected_bibs & actual_bibs
    union = expected_bibs | actual_bibs

    return {
        "jaccard": len(intersection) / len(union),
        "precision": len(intersection) / len(actual_bibs),
        "recall": len(intersection) / len(expected_bibs),
    }


# ---------------------------------------------------------------------------
# Test evaluation
# ---------------------------------------------------------------------------

def evaluate_test(
    test: dict,
    category: str,
    subcategory: str,
    backend: Backend,
    strict: bool = False,
    semantic: bool = False,
) -> TestResult:
    """Evaluate a single test case."""
    nl = test.get("natural_language", "")
    expected_query = test.get("expected_query")
    expected_behavior = test.get("expected_behavior")
    expected_patterns = test.get("expected_patterns", [])
    forbidden = test.get("forbidden_patterns", [])
    fields_expected = test.get("fields_expected")
    test_id = test.get("id", "unknown")
    difficulty = test.get("difficulty", "simple")
    added_in = test.get("added_in", "v1")

    # Run backend
    backend_result = backend.run(nl)
    actual_query = backend_result.query

    # Check syntax validity
    syntax_valid = True
    syntax_errors: list[str] = []
    if not actual_query.startswith("ERROR:"):
        lint_result = lint_query(actual_query)
        syntax_valid = lint_result.valid
        syntax_errors = lint_result.errors if not syntax_valid else []
    else:
        syntax_valid = False
        syntax_errors = [actual_query]

    # Check constraint validity
    constraint_valid = True
    constraint_errors: list[str] = []
    if syntax_valid:
        constraint_result = validate_field_constraints(actual_query)
        constraint_valid = constraint_result.valid
        constraint_errors = constraint_result.error_messages if not constraint_valid else []

    # Check forbidden patterns
    forbidden_matched = check_forbidden_patterns(actual_query, forbidden)

    # Check expected patterns
    patterns_missing = check_expected_patterns(actual_query, expected_patterns)
    pattern_match = len(patterns_missing) == 0 if expected_patterns else True

    # Check exact match
    exact_match = False
    if expected_query:
        exact_match = normalize_query(expected_query) == normalize_query(actual_query)

    # Compute field accuracy
    field_precision, field_recall, field_f1 = compute_field_accuracy(
        actual_query, fields_expected
    )

    # Determine pass/fail
    passed = False

    if expected_patterns and forbidden:
        # Pattern + forbidden test: must match all patterns, no forbidden
        passed = pattern_match and len(forbidden_matched) == 0 and syntax_valid
    elif expected_patterns:
        # Pattern-only test: must match all expected patterns
        passed = pattern_match and syntax_valid
    elif forbidden:
        # Regression test: no forbidden patterns matched
        passed = len(forbidden_matched) == 0 and syntax_valid
    elif expected_behavior:
        # Behavior test
        if expected_behavior == "no_operator":
            passed = not bool(extract_operators(actual_query)) and syntax_valid
        elif expected_behavior == "single_operator":
            passed = len(extract_operators(actual_query)) <= 1 and syntax_valid
        elif expected_behavior == "valid_response":
            passed = syntax_valid or not actual_query.startswith("ERROR")
        elif expected_behavior == "passthrough":
            passed = syntax_valid
        elif expected_behavior == "balanced_parens":
            balanced = actual_query.count("(") == actual_query.count(")")
            passed = balanced and syntax_valid
        elif expected_behavior == "ambiguous":
            passed = syntax_valid
        elif expected_behavior in ("valid_database_only", "valid_property_only"):
            passed = constraint_valid and syntax_valid
        else:
            passed = syntax_valid
    elif expected_query:
        # Standard test: valid syntax + constraints + no forbidden
        if strict:
            # Strict: also require field overlap or exact match
            passed = (
                syntax_valid
                and constraint_valid
                and len(forbidden_matched) == 0
                and (exact_match or field_f1 > 0.5)
            )
        else:
            passed = syntax_valid and constraint_valid and len(forbidden_matched) == 0

    return TestResult(
        test_id=test_id,
        natural_language=nl,
        expected_query=expected_query,
        expected_behavior=expected_behavior,
        expected_patterns=expected_patterns,
        forbidden_patterns=forbidden,
        actual_query=actual_query,
        exact_match=exact_match,
        syntax_valid=syntax_valid,
        syntax_errors=syntax_errors,
        constraint_valid=constraint_valid,
        constraint_errors=constraint_errors,
        forbidden_matched=forbidden_matched,
        pattern_match=pattern_match,
        patterns_missing=patterns_missing,
        field_precision=field_precision,
        field_recall=field_recall,
        field_f1=field_f1,
        passed=passed,
        category=category,
        subcategory=subcategory,
        difficulty=difficulty,
        added_in=added_in,
        backend_result=backend_result,
    )


# ---------------------------------------------------------------------------
# Benchmark loading and flattening
# ---------------------------------------------------------------------------

def load_benchmark(path: Path) -> dict:
    """Load benchmark file."""
    with open(path) as f:
        return json.load(f)


def flatten_tests(benchmark: dict) -> list[tuple[dict, str, str]]:
    """Flatten benchmark structure into list of (test, category, subcategory)."""
    tests = []

    # Dict-of-lists categories (field_types, operators, enum_fields,
    # runtime_augmentation, new_fields)
    dict_categories = [
        "field_types",
        "operators",
        "enum_fields",
        "runtime_augmentation",
        "new_fields",
    ]
    for cat_name in dict_categories:
        if cat_name in benchmark:
            cat_data = benchmark[cat_name]
            if isinstance(cat_data, dict):
                for subcat, subcat_tests in cat_data.items():
                    if isinstance(subcat_tests, list):
                        for test in subcat_tests:
                            tests.append((test, cat_name, subcat))

    # Flat list categories
    flat_categories = {
        "edge_cases": "edge",
        "regression_tests": "regression",
        "compound_queries": "compound",
        "reference_parsing": "reference",
    }
    for cat_name, default_subcat in flat_categories.items():
        if cat_name in benchmark:
            cat_data = benchmark[cat_name]
            if isinstance(cat_data, list):
                for test in cat_data:
                    tests.append((test, cat_name, default_subcat))

    return tests


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def evaluate_benchmark(
    benchmark_path: Path,
    backend: Backend,
    verbose: bool = False,
    strict: bool = False,
    semantic: bool = False,
) -> EvaluationReport:
    """Run full benchmark evaluation."""
    benchmark = load_benchmark(benchmark_path)
    tests = flatten_tests(benchmark)

    if verbose:
        print(f"Loaded {len(tests)} test cases from {benchmark_path.name}")
        print(f"Backend: {backend.name}")
        print()

    results: list[TestResult] = []
    category_stats: dict[str, CategoryStats] = defaultdict(CategoryStats)
    subcategory_stats: dict[str, dict[str, CategoryStats]] = defaultdict(
        lambda: defaultdict(CategoryStats)
    )
    difficulty_stats: dict[str, CategoryStats] = defaultdict(CategoryStats)
    version_stats: dict[str, CategoryStats] = defaultdict(CategoryStats)

    for i, (test, category, subcategory) in enumerate(tests):
        result = evaluate_test(test, category, subcategory, backend, strict, semantic)
        results.append(result)

        # Update category stats
        for stats in [
            category_stats[category],
            subcategory_stats[category][subcategory],
            difficulty_stats[result.difficulty],
            version_stats[result.added_in],
        ]:
            stats.total += 1
            stats.syntax_valid += int(result.syntax_valid)
            stats.constraint_valid += int(result.constraint_valid)
            stats.exact_match += int(result.exact_match)
            stats.no_forbidden += int(len(result.forbidden_matched) == 0)
            stats.passed += int(result.passed)
            stats.pattern_match += int(result.pattern_match)
            if test.get("fields_expected"):
                stats.field_precision_sum += result.field_precision
                stats.field_recall_sum += result.field_recall
                stats.field_f1_sum += result.field_f1
                stats.field_counted += 1

        if verbose and (i + 1) % 50 == 0:
            print(f"  Evaluated {i + 1}/{len(tests)} tests...")

    # Collect failed tests
    failed_tests = []
    for result in results:
        if not result.passed:
            entry: dict[str, Any] = {
                "test_id": result.test_id,
                "category": result.category,
                "subcategory": result.subcategory,
                "natural_language": result.natural_language,
                "expected_query": result.expected_query,
                "expected_behavior": result.expected_behavior,
                "expected_patterns": result.expected_patterns,
                "actual_query": result.actual_query,
                "exact_match": result.exact_match,
                "syntax_valid": result.syntax_valid,
                "syntax_errors": result.syntax_errors,
                "constraint_errors": result.constraint_errors,
                "forbidden_matched": result.forbidden_matched,
                "patterns_missing": result.patterns_missing,
                "field_f1": round(result.field_f1, 3),
                "added_in": result.added_in,
            }
            failed_tests.append(entry)

    # Overall stats
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.passed)
    exact_matches = sum(1 for r in results if r.exact_match)
    syntax_valid_count = sum(1 for r in results if r.syntax_valid)
    constraint_valid_count = sum(1 for r in results if r.constraint_valid)
    pattern_tests = [r for r in results if r.expected_patterns]
    pattern_match_count = sum(1 for r in pattern_tests if r.pattern_match)
    field_tests = [r for r in results if r.field_f1 > 0 or (
        # Include tests with fields_expected even if f1=0
        any(t.get("fields_expected") for t, _, _ in tests if t.get("id") == r.test_id)
    )]

    overall_stats: dict[str, Any] = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "pass_rate": round((passed_tests / total_tests * 100) if total_tests else 0.0, 1),
        "exact_match_count": exact_matches,
        "exact_match_rate": round((exact_matches / total_tests * 100) if total_tests else 0.0, 1),
        "syntax_valid_count": syntax_valid_count,
        "syntax_valid_rate": round(
            (syntax_valid_count / total_tests * 100) if total_tests else 0.0, 1
        ),
        "constraint_valid_count": constraint_valid_count,
        "constraint_valid_rate": round(
            (constraint_valid_count / total_tests * 100) if total_tests else 0.0, 1
        ),
    }

    if pattern_tests:
        overall_stats["pattern_tests"] = len(pattern_tests)
        overall_stats["pattern_match_count"] = pattern_match_count
        overall_stats["pattern_match_rate"] = round(
            (pattern_match_count / len(pattern_tests) * 100) if pattern_tests else 0.0, 1
        )

    # Field F1 stats
    tests_with_fields = sum(1 for s in [category_stats] for cs in s.values() if cs.field_counted > 0)
    total_field_counted = sum(cs.field_counted for cs in category_stats.values())
    total_field_f1_sum = sum(cs.field_f1_sum for cs in category_stats.values())
    if total_field_counted > 0:
        overall_stats["avg_field_f1"] = round(
            total_field_f1_sum / total_field_counted * 100, 1
        )

    # Version breakdown
    for ver, stats in version_stats.items():
        overall_stats[f"{ver}_tests"] = stats.total
        overall_stats[f"{ver}_passed"] = stats.passed
        overall_stats[f"{ver}_pass_rate"] = round(stats.pass_rate, 1)

    # Convert category stats to dicts
    category_stats_dict = {}
    for cat, stats in category_stats.items():
        cat_dict: dict[str, Any] = {
            "total": stats.total,
            "passed": stats.passed,
            "pass_rate": round(stats.pass_rate, 1),
            "exact_match": stats.exact_match,
            "exact_match_rate": round(stats.exact_match_rate, 1),
            "syntax_valid": stats.syntax_valid,
            "syntax_valid_rate": round(stats.syntax_valid_rate, 1),
            "subcategories": {},
        }
        if stats.field_counted > 0:
            cat_dict["avg_field_f1"] = round(stats.avg_field_f1, 1)
        if stats.pattern_match > 0:
            cat_dict["pattern_match"] = stats.pattern_match

        for subcat, substats in subcategory_stats[cat].items():
            sub_dict: dict[str, Any] = {
                "total": substats.total,
                "passed": substats.passed,
                "pass_rate": round(substats.pass_rate, 1),
                "exact_match": substats.exact_match,
                "syntax_valid": substats.syntax_valid,
            }
            if substats.field_counted > 0:
                sub_dict["avg_field_f1"] = round(substats.avg_field_f1, 1)
            cat_dict["subcategories"][subcat] = sub_dict

        category_stats_dict[cat] = cat_dict

    difficulty_stats_dict = {}
    for diff, stats in difficulty_stats.items():
        difficulty_stats_dict[diff] = {
            "total": stats.total,
            "passed": stats.passed,
            "pass_rate": round(stats.pass_rate, 1),
            "syntax_valid": stats.syntax_valid,
        }

    return EvaluationReport(
        timestamp=datetime.now().isoformat(),
        benchmark_file=str(benchmark_path),
        backend_name=backend.name,
        total_tests=total_tests,
        passed_tests=passed_tests,
        overall_stats=overall_stats,
        category_stats=category_stats_dict,
        difficulty_stats=difficulty_stats_dict,
        failed_tests=failed_tests,
        all_results=results,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(report: EvaluationReport) -> None:
    """Print human-readable evaluation report."""
    print("=" * 70)
    print("BENCHMARK EVALUATION REPORT")
    print("=" * 70)
    print()
    print(f"Timestamp: {report.timestamp}")
    print(f"Benchmark: {report.benchmark_file}")
    print(f"Backend:   {report.backend_name}")
    print()

    # Overall stats
    stats = report.overall_stats
    print("OVERALL RESULTS")
    print("-" * 40)
    print(f"Total tests:        {stats['total_tests']}")
    print(f"Passed tests:       {stats['passed_tests']} ({stats['pass_rate']}%)")
    print(f"Exact matches:      {stats['exact_match_count']} ({stats['exact_match_rate']}%)")
    print(f"Syntax valid:       {stats['syntax_valid_count']} ({stats['syntax_valid_rate']}%)")
    print(f"Constraint valid:   {stats['constraint_valid_count']} ({stats['constraint_valid_rate']}%)")
    if "pattern_match_rate" in stats:
        print(
            f"Pattern match:      {stats['pattern_match_count']}/{stats['pattern_tests']} "
            f"({stats['pattern_match_rate']}%)"
        )
    if "avg_field_f1" in stats:
        print(f"Avg field F1:       {stats['avg_field_f1']}%")

    # Version breakdown
    for ver in ("v1", "v2"):
        key = f"{ver}_tests"
        if key in stats:
            print(
                f"  {ver} tests:       {stats[f'{ver}_passed']}/{stats[key]} "
                f"({stats[f'{ver}_pass_rate']}%)"
            )
    print()

    # Category breakdown
    print("BY CATEGORY")
    print("-" * 60)
    header = f"{'Category':<25} {'Passed':<12} {'Rate':<8} {'Exact':<8} {'F1':<8}"
    print(header)
    for cat, cat_stats in sorted(report.category_stats.items()):
        f1_str = f"{cat_stats['avg_field_f1']}%" if "avg_field_f1" in cat_stats else "--"
        print(
            f"{cat:<25} {cat_stats['passed']}/{cat_stats['total']:<8} "
            f"{cat_stats['pass_rate']:>5.1f}%  {cat_stats['exact_match']:<8} {f1_str:<8}"
        )
    print()

    # Subcategory breakdown
    print("BY SUBCATEGORY")
    print("-" * 60)
    for cat, cat_stats in sorted(report.category_stats.items()):
        subcats = cat_stats.get("subcategories", {})
        if subcats:
            print(f"\n{cat}:")
            for subcat, substats in sorted(subcats.items()):
                f1_str = f" F1={substats['avg_field_f1']}%" if "avg_field_f1" in substats else ""
                print(
                    f"  {subcat:<22} {substats['passed']}/{substats['total']:<4} "
                    f"({substats['pass_rate']:>5.1f}%){f1_str}"
                )
    print()

    # Difficulty breakdown
    print("BY DIFFICULTY")
    print("-" * 40)
    print(f"{'Difficulty':<15} {'Passed':<10} {'Rate':<10}")
    for diff, diff_stats in sorted(report.difficulty_stats.items()):
        print(
            f"{diff:<15} {diff_stats['passed']}/{diff_stats['total']:<6} "
            f"{diff_stats['pass_rate']:>6.1f}%"
        )
    print()

    # Failed tests summary
    if report.failed_tests:
        print(f"FAILED TESTS (first 15 of {len(report.failed_tests)})")
        print("-" * 60)
        for i, test in enumerate(report.failed_tests[:15]):
            print(f"\n{i + 1}. [{test['test_id']}] ({test['category']}/{test['subcategory']}) [{test.get('added_in', 'v1')}]")
            nl_display = test["natural_language"][:70]
            print(f"   NL: {nl_display}{'...' if len(test['natural_language']) > 70 else ''}")
            if test.get("expected_query"):
                eq = test["expected_query"][:60]
                print(f"   Expected: {eq}{'...' if len(test.get('expected_query', '')) > 60 else ''}")
            if test.get("expected_patterns"):
                print(f"   Expected patterns: {test['expected_patterns']}")
            aq = test["actual_query"][:60]
            print(f"   Actual:   {aq}{'...' if len(test['actual_query']) > 60 else ''}")
            if test.get("syntax_errors"):
                print(f"   Syntax errors: {', '.join(test['syntax_errors'][:3])}")
            if test.get("constraint_errors"):
                print(f"   Constraint errors: {', '.join(test['constraint_errors'][:3])}")
            if test.get("forbidden_matched"):
                print(f"   Forbidden matched: {', '.join(test['forbidden_matched'])}")
            if test.get("patterns_missing"):
                print(f"   Patterns missing: {', '.join(test['patterns_missing'])}")

        remaining = len(report.failed_tests) - 15
        if remaining > 0:
            print(f"\n... and {remaining} more failures")
    print()


def write_csv(report: EvaluationReport, csv_path: Path) -> None:
    """Write per-test CSV for diffing."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "test_id", "category", "subcategory", "added_in", "difficulty",
            "passed", "exact_match", "syntax_valid", "constraint_valid",
            "pattern_match", "field_f1", "natural_language", "expected_query",
            "actual_query",
        ])
        for r in report.all_results:
            writer.writerow([
                r.test_id, r.category, r.subcategory, r.added_in, r.difficulty,
                r.passed, r.exact_match, r.syntax_valid, r.constraint_valid,
                r.pattern_match, round(r.field_f1, 3),
                r.natural_language[:100], (r.expected_query or "")[:100],
                r.actual_query[:100],
            ])
    print(f"CSV written to: {csv_path}")


def serialize_report(report: EvaluationReport) -> dict:
    """Serialize report to JSON-compatible dict (excludes all_results)."""
    return {
        "timestamp": report.timestamp,
        "benchmark_file": report.benchmark_file,
        "backend": report.backend_name,
        "total_tests": report.total_tests,
        "passed_tests": report.passed_tests,
        "overall_stats": report.overall_stats,
        "category_stats": report.category_stats,
        "difficulty_stats": report.difficulty_stats,
        "failed_tests": report.failed_tests,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate the NL-to-ADS pipeline against benchmark tests"
    )
    parser.add_argument(
        "--benchmark", "-b", type=str,
        default="data/datasets/benchmark/benchmark_queries.json",
        help="Path to benchmark file (default: v1 for backward compat)",
    )
    parser.add_argument(
        "--output", "-o", type=str,
        default="data/datasets/evaluations/benchmark_results.json",
        help="Output path for JSON results",
    )
    parser.add_argument(
        "--backend", type=str, default="ner", choices=["ner", "server"],
        help="Backend to use: 'ner' (local pipeline) or 'server' (HTTP)",
    )
    parser.add_argument(
        "--server-url", type=str, default="http://localhost:8001",
        help="Server URL for 'server' backend",
    )
    parser.add_argument(
        "--with-augmentation", action="store_true",
        help="Apply runtime rewrites (UAT, inst, bibstem, author wildcarding) in NER backend",
    )
    parser.add_argument(
        "--semantic", action="store_true",
        help="Run ADS API bibcode overlap (requires ADS_API_KEY env var)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Stricter pass: require field overlap or pattern match in addition to syntax",
    )
    parser.add_argument(
        "--csv", type=str, default=None,
        help="Output per-test CSV for diffing",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print progress and details",
    )
    parser.add_argument(
        "--ci", action="store_true",
        help="CI mode: exit 1 if pass rate < 80%%",
    )
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark)
    output_path = Path(args.output)

    if not benchmark_path.exists():
        print(f"Error: Benchmark file not found: {benchmark_path}", file=sys.stderr)
        sys.exit(1)

    # Create backend
    if args.backend == "server":
        backend: Backend = ServerBackend(args.server_url)
    else:
        backend = NERBackend(with_augmentation=args.with_augmentation)

    # Warm up
    if args.verbose:
        print(f"Warming up {backend.name} backend...")
    backend.warmup()

    # Load semantic cache
    if args.semantic:
        cache_path = Path("data/datasets/evaluations/semantic_cache.json")
        _load_semantic_cache(cache_path)

    # Run evaluation
    if args.verbose:
        print("Running benchmark evaluation...")
        print()

    report = evaluate_benchmark(
        benchmark_path, backend,
        verbose=args.verbose, strict=args.strict, semantic=args.semantic,
    )

    # Print report
    print_report(report)

    # Save JSON results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(serialize_report(report), f, indent=2)
    print(f"Results saved to: {output_path}")

    # Save semantic cache
    if args.semantic:
        _save_semantic_cache()

    # Save CSV
    if args.csv:
        write_csv(report, Path(args.csv))

    # CI check
    if args.ci:
        pass_rate = report.overall_stats["pass_rate"]
        if pass_rate < 80.0:
            print(f"\nCI CHECK FAILED: Pass rate {pass_rate}% < 80%")
            sys.exit(1)
        else:
            print(f"\nCI CHECK PASSED: Pass rate {pass_rate}% >= 80%")
            sys.exit(0)


if __name__ == "__main__":
    main()
