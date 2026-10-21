"""Divergence gate for conformance-v2 reports (nightly_diff pattern).

Compares this run's per-scenario verdicts against the committed baseline
(conformance/v2-baseline/<arm>.json). Gates (exit 1) on NEW divergences:
- a scenario that FAILs/TIMEOUTs and was not baseline-FAIL/EXPECTED_FAIL
- a verdict that moved PASS -> FAIL/TIMEOUT

Reports (non-gating, informational):
- EXPECTED_FAIL -> PASS: divergence RESOLVED upstream — update the seed
  AND the registry entry
- new scenarios absent from the baseline (first run of a new scenario)
  are recorded as NEW and gate only if they FAIL

Usage: v2_diff.py --report <conformance-v2-*.json> --baseline <arm.json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BAD = {"FAIL", "TIMEOUT", "ERROR"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--baseline", required=True)
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text())
    baseline = json.loads(Path(args.baseline).read_text())
    base = baseline.get("verdicts", {})
    cur = {k: v["result"] for k, v in report["results"].items()}

    gating: list[str] = []
    info: list[str] = []
    for name, verdict in sorted(cur.items()):
        prev = base.get(name)
        if prev is None:
            (gating if verdict in BAD else info).append(f"NEW {verdict:14s} {name}")
        elif verdict in BAD and prev not in BAD and prev != "EXPECTED_FAIL":
            gating.append(f"FLIP {prev}->{verdict} {name}")
        elif verdict == "PASS" and prev == "EXPECTED_FAIL":
            info.append(f"RESOLVED {prev}->PASS {name} — update seed + registry entry")
        elif verdict != prev and not (verdict == "EXPECTED_FAIL" and prev == "EXPECTED_FAIL"):
            info.append(f"moved {prev}->{verdict} {name}")

    for line in info:
        print(f"  [info] {line}")
    if gating:
        print(f"\nDIVERGENCE GATE: {len(gating)} new/changed divergence(s) vs baseline:")
        for line in gating:
            print(f"  [GATE] {line}")
        return 1
    print("\nDIVERGENCE GATE: clean (no new divergences vs baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
