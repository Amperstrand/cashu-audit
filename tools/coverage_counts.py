#!/usr/bin/env python3
"""Re-count per-NUT research-doc and suite-scenario coverage for NUT-TRACKER.md.

Research docs: every .md under research/, divergences/, issues/, experiments/
(excluding SPEC-HISTORY and generated run artifacts) — a doc counts toward
every NUT-NN mentioned in its filename + first heading block.

Suite scenarios: parsed from conformance/README.md's coverage table.

Usage: python3 tools/coverage_counts.py
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def research_counts() -> dict[str, list[str]]:
    cov: dict[str, list[str]] = defaultdict(list)
    for base in ("research", "divergences", "issues", "experiments"):
        for f in (REPO / base).rglob("*.md"):
            rel = str(f.relative_to(REPO))
            if "SPEC-HISTORY" in rel or "/study-out/" in rel or "/artifacts/" in rel:
                continue
            text = f.read_text(errors="replace")[:1500]
            for n in sorted(set(re.findall(r"NUT-(\d{2})", f.name + " " + text))):
                cov[n].append(rel)
    return cov


def suite_counts() -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    readme = (REPO / "conformance" / "README.md").read_text()
    for m in re.finditer(r"^\|\s*(NUT-[\d/]+)\s*\|\s*(\d+)\+?\s*\|", readme, re.M):
        count = int(m.group(2))
        for part in re.findall(r"\d{2}", m.group(1)):
            out[part] += count
    return out


def main() -> int:
    cov, suite = research_counts(), suite_counts()
    print("| NUT | research-docs | suite-scenarios |")
    print("|---|---|---|")
    for i in range(31):
        n = f"{i:02d}"
        print(f"| {n} | {len(cov.get(n, []))} | {suite.get(n, 0)} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
