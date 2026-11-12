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

# Auto-import all scenario modules to register them
import importlib
import pkgutil
import scenarios as _scenarios_pkg
for _finder, _name, _ispkg in pkgutil.iter_modules(_scenarios_pkg.__path__):
    importlib.import_module(f"scenarios.{_name}")


def capture_mint_identity(url: str) -> str:
    """#40: mint identity at run start — /v1/info name+version per URL.

    Reports must be attributable after the fact: a bare URL (especially a
    container-internal port) cannot reconstruct which implementation and
    version served the run.
    """
    try:
        mint = MintClient(url)
        info = mint.get_mint_info()
        name = info.get("name") or "unnamed"
        version = info.get("version") or "unknown-version"
        return f"{name} / {version}"
    except Exception as e:
        return f"identity-unavailable ({str(e)[:60]})"


class ClnSignetOracle:
    """Invoice oracle backed by the inr2 cln-swap-signet node (2026-11-12).

    Real signet invoices a real-LN target (signut's CLNrest backend) can
    actually PAY — unlike invoices created on the target itself (a real
    backend cannot pay its own; wire identity: 20004 'Destination said it
    doesn't know invoice'). Amounts in SAT (invoice takes msat).
    """

    def __init__(self) -> None:
        import itertools
        self._counter = itertools.count(1)

    def mint_quote(self, amount: int) -> dict:
        import json as _json
        import subprocess
        import time as _time
        label = f"clnoracle-{int(_time.time())}-{next(self._counter)}"
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
             "inr2.cashu.exchange",
             f"docker exec cln-swap-signet lightning-cli --network=signet invoice {amount * 1000} {label} oracle"],
            capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"cln oracle invoice failed: {(r.stderr or r.stdout)[:100]}")
        return {"request": _json.loads(r.stdout)["bolt11"]}


def run_all(mint_url: str, family: str | None = None, cln_oracle: bool = False) -> list[ScenarioResult]:
    mint = MintClient(mint_url)
    if cln_oracle:
        mint.invoice_oracle = ClnSignetOracle()  # type: ignore[attr-defined]
    results: list[ScenarioResult] = []

    scenarios = all_scenarios()
    if family:
        def _module_of(s) -> str:
            return getattr(s, "module", "") or s.run.__module__.split(".")[-1]
        scenarios = [s for s in scenarios if _module_of(s).startswith(family)]
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
    parser.add_argument("--family", help="run only scenarios whose module starts with this (e.g. melt)")
    parser.add_argument("--cln-oracle", action="store_true", help="attach the inr2 cln-swap-signet invoice oracle (real-LN targets: signut)")
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
    identities: dict[str, str] = {}

    for url in mint_urls:
        identities[url] = capture_mint_identity(url)
        print(f"\n{'='*60}")
        print(f"Testing mint: {url}  [{identities[url]}]")
        print(f"{'='*60}")
        all_results[url] = run_all(url, family=args.family, cln_oracle=args.cln_oracle)

    matrix = generate_matrix(all_results, mint_urls, identities=identities)
    Path(args.output).write_text(matrix)
    print(f"\nMatrix written to {args.output}")

    total_fail = sum(1 for rs in all_results.values() for r in rs if r.result == Result.FAIL)
    if total_fail:
        print(f"\n{total_fail} failure(s) detected")
        sys.exit(1)


if __name__ == "__main__":
    main()
