#!/usr/bin/env python3
"""Multi-config benchmark comparison runner.

Runs the evaluator across multiple backend configurations and produces a
comparison table showing improvement trajectory.

Assumes servers are already running on different ports. Takes a config spec
either as JSON string or JSON file path.

Usage:
    # Using JSON file
    python scripts/benchmark_comparison.py \
        --configs configs.json \
        --benchmark data/datasets/benchmark/benchmark_queries_v2.json

    # Using inline JSON
    python scripts/benchmark_comparison.py \
        --configs '[
            {"name": "NER-only", "backend": "ner"},
            {"name": "NER+augmentation", "backend": "ner", "with_augmentation": true},
            {"name": "Hybrid", "url": "http://localhost:8001"}
        ]' \
        --benchmark data/datasets/benchmark/benchmark_queries_v2.json

    # NER-only quick comparison (no server needed)
    python scripts/benchmark_comparison.py \
        --benchmark data/datasets/benchmark/benchmark_queries_v2.json

Output:
    1. JSON: Full per-config stats by category
    2. Markdown comparison table to console
    3. Diff report: Tests that change status between configs
    4. Latency report (server backends only)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/finetune/src"))

from evaluate_benchmark import (
    Backend,
    EvaluationReport,
    NERBackend,
    ServerBackend,
    evaluate_benchmark,
    flatten_tests,
    load_benchmark,
    serialize_report,
)


@dataclass
class ConfigResult:
    """Result for a single configuration run."""
    name: str
    report: EvaluationReport
    elapsed_s: float


def build_backend(config: dict) -> Backend:
    """Build a Backend from a config dict."""
    if config.get("url"):
        return ServerBackend(config["url"])
    elif config.get("backend") == "server":
        url = config.get("url", "http://localhost:8001")
        return ServerBackend(url)
    else:
        return NERBackend(with_augmentation=config.get("with_augmentation", False))


def run_comparison(
    configs: list[dict],
    benchmark_path: Path,
    verbose: bool = False,
) -> list[ConfigResult]:
    """Run benchmark evaluation for each config sequentially."""
    results: list[ConfigResult] = []

    for i, config in enumerate(configs):
        name = config.get("name", f"config-{i}")
        print(f"\n{'='*60}")
        print(f"Running config: {name}")
        print(f"{'='*60}")

        backend = build_backend(config)
        backend.warmup()

        t0 = time.monotonic()
        report = evaluate_benchmark(
            benchmark_path, backend, verbose=verbose,
        )
        elapsed = time.monotonic() - t0

        results.append(ConfigResult(name=name, report=report, elapsed_s=elapsed))

        # Quick summary
        stats = report.overall_stats
        print(f"\n  Pass: {stats['pass_rate']}% | Exact: {stats['exact_match_rate']}% | "
              f"Time: {elapsed:.1f}s")

    return results


def print_comparison_table(results: list[ConfigResult]) -> None:
    """Print markdown comparison table to console."""
    if not results:
        return

    print("\n")
    print("=" * 80)
    print("COMPARISON TABLE")
    print("=" * 80)
    print()

    names = [r.name for r in results]
    col_width = max(12, max(len(n) for n in names) + 2)

    # Header
    header = f"| {'Metric':<20} |"
    separator = f"|{'-'*22}|"
    for name in names:
        header += f" {name:>{col_width}} |"
        separator += f"{'-'*(col_width+2)}|"

    print(header)
    print(separator)

    # Rows
    metrics = [
        ("Pass rate", lambda r: f"{r.report.overall_stats['pass_rate']}%"),
        ("Exact match", lambda r: f"{r.report.overall_stats['exact_match_rate']}%"),
        ("Syntax valid", lambda r: f"{r.report.overall_stats['syntax_valid_rate']}%"),
        ("Constraint valid", lambda r: f"{r.report.overall_stats['constraint_valid_rate']}%"),
    ]

    # Add pattern match if any config has it
    if any("pattern_match_rate" in r.report.overall_stats for r in results):
        metrics.append((
            "Pattern match",
            lambda r: f"{r.report.overall_stats.get('pattern_match_rate', '--')}%"
            if "pattern_match_rate" in r.report.overall_stats else "--",
        ))

    # Add field F1 if any config has it
    if any("avg_field_f1" in r.report.overall_stats for r in results):
        metrics.append((
            "Avg field F1",
            lambda r: f"{r.report.overall_stats.get('avg_field_f1', '--')}%"
            if "avg_field_f1" in r.report.overall_stats else "--",
        ))

    # Version breakdown
    for ver in ("v1", "v2"):
        key = f"{ver}_pass_rate"
        if any(key in r.report.overall_stats for r in results):
            metrics.append((
                f"{ver} tests pass",
                lambda r, k=key: f"{r.report.overall_stats.get(k, '--')}%"
                if k in r.report.overall_stats else "--",
            ))

    # Eval time
    metrics.append(("Eval time", lambda r: f"{r.elapsed_s:.1f}s"))

    for metric_name, getter in metrics:
        row = f"| {metric_name:<20} |"
        for r in results:
            val = getter(r)
            row += f" {val:>{col_width}} |"
        print(row)

    print()

    # Category breakdown table
    all_categories = set()
    for r in results:
        all_categories.update(r.report.category_stats.keys())

    if all_categories:
        print("BY CATEGORY (pass rate)")
        print("-" * 80)
        header = f"| {'Category':<25} |"
        separator = f"|{'-'*27}|"
        for name in names:
            header += f" {name:>{col_width}} |"
            separator += f"{'-'*(col_width+2)}|"
        print(header)
        print(separator)

        for cat in sorted(all_categories):
            row = f"| {cat:<25} |"
            for r in results:
                cat_stats = r.report.category_stats.get(cat, {})
                if cat_stats:
                    rate = cat_stats.get("pass_rate", 0)
                    total = cat_stats.get("total", 0)
                    val = f"{rate}% ({total})"
                else:
                    val = "--"
                row += f" {val:>{col_width}} |"
            print(row)
        print()


def print_diff_report(results: list[ConfigResult]) -> None:
    """Print tests that change status between configs."""
    if len(results) < 2:
        return

    print("DIFF REPORT (status changes between configs)")
    print("-" * 70)

    for i in range(1, len(results)):
        prev = results[i - 1]
        curr = results[i]
        print(f"\n{prev.name} -> {curr.name}:")

        # Build test_id -> passed maps
        prev_map = {r.test_id: r.passed for r in prev.report.all_results}
        curr_map = {r.test_id: r.passed for r in curr.report.all_results}

        improvements = []
        regressions = []

        for r in curr.report.all_results:
            prev_passed = prev_map.get(r.test_id)
            if prev_passed is not None:
                if not prev_passed and r.passed:
                    improvements.append(r)
                elif prev_passed and not r.passed:
                    regressions.append(r)

        if improvements:
            print(f"  Improvements ({len(improvements)}):")
            for r in improvements[:10]:
                print(f"    + [{r.test_id}] {r.natural_language[:50]}")
            if len(improvements) > 10:
                print(f"    ... and {len(improvements) - 10} more")

        if regressions:
            print(f"  Regressions ({len(regressions)}):")
            for r in regressions[:10]:
                print(f"    - [{r.test_id}] {r.natural_language[:50]}")
            if len(regressions) > 10:
                print(f"    ... and {len(regressions) - 10} more")

        if not improvements and not regressions:
            print("  No changes")

    print()


def print_latency_report(results: list[ConfigResult]) -> None:
    """Print latency report for server backends."""
    server_results = [
        r for r in results
        if any(
            br.backend_result and br.backend_result.timing
            for br in r.report.all_results
        )
    ]

    if not server_results:
        return

    print("LATENCY REPORT (server backends)")
    print("-" * 50)

    for r in server_results:
        timings = [
            br.backend_result.timing["total_s"]
            for br in r.report.all_results
            if br.backend_result and br.backend_result.timing and "total_s" in br.backend_result.timing
        ]

        if not timings:
            continue

        timings.sort()
        n = len(timings)
        p50 = timings[int(n * 0.50)]
        p95 = timings[int(n * 0.95)]
        p99 = timings[min(int(n * 0.99), n - 1)]
        avg = sum(timings) / n

        print(f"\n  {r.name}:")
        print(f"    p50: {p50*1000:.0f}ms  p95: {p95*1000:.0f}ms  p99: {p99*1000:.0f}ms  avg: {avg*1000:.0f}ms")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Run benchmark across multiple configurations and compare"
    )
    parser.add_argument(
        "--configs", type=str, default=None,
        help="JSON string or path to JSON file with config list. "
             "Each config: {name, backend, url, with_augmentation}. "
             "Defaults to NER-only + NER+augmentation.",
    )
    parser.add_argument(
        "--benchmark", "-b", type=str,
        default="data/datasets/benchmark/benchmark_queries_v2.json",
        help="Path to benchmark file",
    )
    parser.add_argument(
        "--output", "-o", type=str,
        default="data/datasets/evaluations/comparison_v2.json",
        help="Output path for JSON comparison results",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print progress during evaluation",
    )
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark)
    if not benchmark_path.exists():
        print(f"Error: Benchmark file not found: {benchmark_path}", file=sys.stderr)
        sys.exit(1)

    # Parse configs
    if args.configs is None:
        # Default: NER-only and NER+augmentation
        configs = [
            {"name": "NER-only", "backend": "ner"},
            {"name": "NER+augmentation", "backend": "ner", "with_augmentation": True},
        ]
    elif Path(args.configs).exists():
        with open(args.configs) as f:
            configs = json.load(f)
    else:
        configs = json.loads(args.configs)

    print(f"Benchmark: {benchmark_path}")
    print(f"Configs: {len(configs)}")
    for c in configs:
        print(f"  - {c.get('name', 'unnamed')}: {c}")

    # Run comparison
    results = run_comparison(configs, benchmark_path, verbose=args.verbose)

    # Print reports
    print_comparison_table(results)
    print_diff_report(results)
    print_latency_report(results)

    # Save JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    comparison_data = {
        "benchmark_file": str(benchmark_path),
        "configs": configs,
        "results": [],
    }
    for r in results:
        comparison_data["results"].append({
            "name": r.name,
            "elapsed_s": round(r.elapsed_s, 2),
            **serialize_report(r.report),
        })

    with open(output_path, "w") as f:
        json.dump(comparison_data, f, indent=2)

    print(f"Comparison saved to: {output_path}")


if __name__ == "__main__":
    main()
