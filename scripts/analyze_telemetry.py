#!/usr/bin/env python3
"""Analyze NLS telemetry logs.

Reads structured JSON log lines from stdin or a file and produces
a summary of query sources, failure rates, and latency distribution.

Usage:
    python scripts/analyze_telemetry.py < telemetry.log
    python scripts/analyze_telemetry.py telemetry.log
"""

import json
import sys
from collections import Counter
from pathlib import Path


def analyze(lines):
    """Analyze telemetry log lines."""
    entries = []
    parse_errors = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            entries.append(entry)
        except json.JSONDecodeError:
            parse_errors += 1

    if not entries:
        print("No telemetry entries found.")
        return

    total = len(entries)
    print(f"Total queries: {total}")
    if parse_errors:
        print(f"Parse errors: {parse_errors}")
    print()

    # Source distribution
    sources = Counter(e.get("source", "unknown") for e in entries)
    print("Query sources:")
    for source, count in sources.most_common():
        pct = count / total * 100
        print(f"  {source:20s} {count:5d} ({pct:5.1f}%)")
    print()

    # Error rate
    errors = [e for e in entries if e.get("error")]
    print(f"Error rate: {len(errors)}/{total} ({len(errors)/total*100:.1f}%)")
    if errors:
        error_types = Counter(e["error"] for e in errors)
        for err, count in error_types.most_common(5):
            print(f"  {err[:60]:60s} {count}")
    print()

    # Empty query rate
    empty = [e for e in entries if not e.get("final_query")]
    print(f"Empty query rate: {len(empty)}/{total} ({len(empty)/total*100:.1f}%)")
    print()

    # Fallback rate
    fallbacks = [e for e in entries if e.get("source") == "fallback"]
    print(f"Fallback rate: {len(fallbacks)}/{total} ({len(fallbacks)/total*100:.1f}%)")
    print()

    # Latency distribution
    latencies = [e.get("latency_ms", 0) for e in entries if e.get("latency_ms")]
    if latencies:
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        print(f"Latency: p50={p50:.0f}ms  p95={p95:.0f}ms  p99={p99:.0f}ms  max={max(latencies):.0f}ms")
    print()

    # Fields injected by NER
    field_counts = Counter()
    for e in entries:
        for f in e.get("fields_injected", []):
            field_counts[f] += 1
    if field_counts:
        print("NER fields injected:")
        for field, count in field_counts.most_common():
            print(f"  {field:20s} {count:5d}")
    print()

    # Repairs applied
    repair_counts = Counter()
    for e in entries:
        for r in e.get("repairs_applied", []):
            repair_counts[r] += 1
    if repair_counts:
        print("Query repairs applied:")
        for repair, count in repair_counts.most_common():
            print(f"  {repair:40s} {count:5d}")
    print()

    # RAG usage
    rag_entries = [e for e in entries if e.get("rag_enabled")]
    if rag_entries:
        avg_shots = sum(e.get("rag_few_shot_count", 0) for e in rag_entries) / len(rag_entries)
        print(f"RAG enabled: {len(rag_entries)}/{total} ({len(rag_entries)/total*100:.1f}%)")
        print(f"Avg few-shot examples: {avg_shots:.1f}")


def main():
    if len(sys.argv) > 1:
        filepath = Path(sys.argv[1])
        if not filepath.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)
        with open(filepath) as f:
            analyze(f)
    else:
        analyze(sys.stdin)


if __name__ == "__main__":
    main()
