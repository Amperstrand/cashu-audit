#!/usr/bin/env python3
"""Run conformance scenarios against one or more Cashu mints.

Usage:
    python run_matrix.py --mint https://testnut.cashu.exchange
    python run_matrix.py --mint https://testnut.cashu.exchange --mint http://localhost:3338
    python run_matrix.py --mints mints.yaml
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from conformance.client import MintClient
from conformance.scenarios import all_scenarios, ScenarioResult, Result
from conformance.matrix import generate_matrix

import scenarios.nut11_p2pk_siginputs


def run_all(mint_url: str) -> list[ScenarioResult]:
    mint = MintClient(mint_url)
    results: list[ScenarioResult] = []

    scenarios = all_scenarios()
    if not scenarios:
        print(f"  No scenarios registered")
        return results

    for s in scenarios:
        t0 = time.monotonic()
        print(f"  [{len(results)+1}/{len(scenarios)}] {s.name} ...", end=" ", flush=True)
        r = s.execute(mint)
        r.duration_ms = (time.monotonic() - t0) * 1000
        print(f"{r.result.icon} {r.note[:80]}")
        results.append(r)

    return results


def main():
    parser = argparse.ArgumentParser(description="Cashu conformance matrix runner")
    parser.add_argument("--mint", action="append", dest="mints", help="Mint URL (can repeat)")
    parser.add_argument("--mints-file", help="YAML file with mint URLs")
    parser.add_argument("--output", default="reports/matrix.md", help="Output file")
    args = parser.parse_args()

    mint_urls: list[str] = []
    if args.mints:
        mint_urls.extend(args.mints)
    if args.mints_file:
        import yaml
        with open(args.mints_file) as f:
            cfg = yaml.safe_load(f)
        for m in cfg.get("mints", []):
            mint_urls.append(m["url"])

    if not mint_urls:
        parser.error("At least one --mint or --mints-file required")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    all_results: dict[str, list[ScenarioResult]] = {}

    for url in mint_urls:
        print(f"\n{'='*60}")
        print(f"Testing mint: {url}")
        print(f"{'='*60}")
        all_results[url] = run_all(url)

    matrix = generate_matrix(all_results, mint_urls)
    Path(args.output).write_text(matrix)
    print(f"\nMatrix written to {args.output}")

    total_fail = sum(1 for rs in all_results.values() for r in rs if r.result == Result.FAIL)
    if total_fail:
        print(f"\n{total_fail} failure(s) detected")
        sys.exit(1)


if __name__ == "__main__":
    main()
