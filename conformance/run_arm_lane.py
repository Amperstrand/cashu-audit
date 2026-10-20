"""Deterministic conformance lane on local docker arms (#33 rebuild).

Boots a target mint (and an invoice-oracle scratch mint — the target's
FakeWallet auto-settles its own invoices, so melt-success scenarios need
an external invoice), runs the scenario registry with per-scenario
timeouts, and writes an artifact-only report (deterministic per #34's
closed design: no live-mint flakiness, no baseline drift).

Usage:
    python3 run_arm_lane.py --target ns=nutshell:cashubtc/nutshell:0.20.3 \
        [--host-network] [--family melt] [--out reports]

Exit code: 1 when any scenario FAILs (SKIPs are environmental and
recorded, never silent) — the workflow surfaces red without filing
anything; the report is the artifact.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pkgutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import scenarios as _pkg  # noqa: E402  (registry import side effects)

for _f, _n, _p in pkgutil.iter_modules(_pkg.__path__):
    importlib.import_module(f"scenarios.{_n}")

from conformance.client import MintClient  # noqa: E402
from conformance.scenarios import all_scenarios  # noqa: E402
from version_matrix import Arm, parse_arm_spec  # noqa: E402

# Deterministic-hang skips observed against FakeWallet arms (kept from
# run_filtered.py; revisit per release).
SKIP = {"melt_p2pk_sigall_transaction_signature_succeeds"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, metavar="NAME=family:image",
                    help="target mint arm, e.g. ns=nutshell:cashubtc/nutshell:0.20.3")
    ap.add_argument("--host-network", action="store_true",
                    help="boot with --network host (broken-bridge hosts)")
    ap.add_argument("--family", help="run only scenarios whose module filename starts with this")
    ap.add_argument("--out", default="reports", help="report output directory")
    ap.add_argument("--timeout", type=int, default=45, help="per-scenario timeout (s)")
    ap.add_argument("--expected-fail", metavar="JSON",
                    help="map of scenario name -> justification; counted as "
                         "EXPECTED_FAIL (documented divergences/artifacts), "
                         "not gating FAILs (seed: conformance/expected-fail-nutshell-0.20.3.json)")
    args = ap.parse_args()

    expected_fail: dict[str, str] = {}
    if args.expected_fail:
        expected_fail = json.loads(Path(args.expected_fail).read_text())

    target = parse_arm_spec(args.target, "docker")
    target.host_network = args.host_network

    # Oracle: same-family scratch mint, exists only to issue invoices the
    # target mint has never seen (see nut11_melt._create_melt_quote).
    oracle = Arm(f"{target.name}-oracle", target.family)
    oracle.image = target.image
    oracle.host_network = args.host_network

    import concurrent.futures as cf

    results: dict[str, dict] = {}
    started = time.time()
    try:
        target.bring_up()
        oracle.bring_up()
        print(f"target: {target.name} @ {target.url} ({target.identity})")
        print(f"oracle: {oracle.name} @ {oracle.url} ({oracle.identity})", flush=True)

        mint = MintClient(target.url, timeout=30)
        mint.invoice_oracle = MintClient(oracle.url, timeout=30)

        scen = [s for s in all_scenarios() if not args.family or _module_of(s).startswith(args.family)]
        for s in scen:
            if s.name in SKIP:
                results[s.name] = {"result": "SKIP", "note": "known hang (run_filtered set)"}
                print(f"⏭️  [SKIP] {s.name} (known hang)")
                continue
            t0 = time.time()
            with cf.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(s.execute, mint)
                try:
                    r = fut.result(timeout=args.timeout)
                    verdict = r.result.value
                    note = r.note
                    if verdict == "FAIL" and s.name in expected_fail:
                        verdict = "EXPECTED_FAIL"
                        note = f"[documented] {expected_fail[s.name]} | {r.note}"
                    results[s.name] = {"result": verdict, "note": note,
                                       "module": _module_of(s), "duration_s": round(time.time() - t0, 1)}
                    print(f"{r.result.icon} [{verdict}] {s.name} ({results[s.name]['duration_s']}s) — {results[s.name]['note'][:110]}")
                except cf.TimeoutError:
                    results[s.name] = {"result": "TIMEOUT", "note": f">{args.timeout}s", "module": _module_of(s)}
                    print(f"⏱️  [TIMEOUT] {s.name}")
                except Exception as e:
                    results[s.name] = {"result": "ERROR", "note": str(e)[:160], "module": _module_of(s)}
                    print(f"❓ [ERROR] {s.name}: {str(e)[:100]}")
    finally:
        target.tear_down()
        oracle.tear_down()
        print("arms torn down", flush=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    counts: dict[str, int] = {}
    for v in results.values():
        counts[v["result"]] = counts.get(v["result"], 0) + 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "ts": ts,
        "target": {"name": target.name, "identity": target.identity, "image": target.image},
        "oracle": {"name": oracle.name, "image": oracle.image},
        "totals": counts,
        "elapsed_s": round(time.time() - started, 1),
        "results": results,
    }
    (out / f"conformance-v2-{ts}.json").write_text(json.dumps(report, indent=1))
    lines = [f"# conformance-v2 {ts}", "",
             f"target: **{target.name}** ({target.identity})  ", f"totals: **{counts}**", ""]
    for name, v in results.items():
        lines.append(f"| {v['result']} | `{name}` | {v.get('note', '')[:100]} |")
    (out / f"conformance-v2-{ts}.md").write_text("\n".join(lines) + "\n")
    print(f"\ntotals {counts} -> {out}/conformance-v2-{ts}.{{json,md}}")
    return 1 if counts.get("FAIL", 0) else 0


def _module_of(s) -> str:
    return getattr(s, "module", "") or s.run.__module__.split(".")[-1]


if __name__ == "__main__":
    sys.exit(main())
