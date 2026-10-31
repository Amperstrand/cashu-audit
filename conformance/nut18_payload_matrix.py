#!/usr/bin/env python3
"""NUT-18 payload-spelling matrix (#63) — repeatable lane cell.

Promotes the 2026-10-31 NUT-18 payload probe (findings:
research/FINDINGS-2026-10-31-nut18-payload-spelling.md) into a
deterministic battery: payload variants x consumer parsers, exact
error-identity assertions (no family regex), plus the live settlement
and captured-wire cells.

Consumers (both must be provided; rebuild recipes at the bottom):
  --cdk-probe  cargo example binary `nut18_payload_probe`
               (crates/cashu/examples/, upstream-cache/cdk @ v0.18.2)
  --ts-dir     cashu-ts v5.0.0-rc.9 checkout with node_modules
               (NOT 4.11.0 — PaymentRequest.decodePayload is
               rc.9-API; on 4.11.0 the tests fail with
               `decodePayload is not a function`, a probe-env
               mismatch, not a divergence)

Inputs:
  --payloads   dir with payload_*.json + capture-0[12].json
               (default: the private mirror's nut18-live/out — the
               captures are wire evidence and must not be recrafted)
  --arm        live nutshell arm URL for the settlement leg
               (default http://127.0.0.1:28086; docker `nut18-arm`
               recipe in the mirror v4-pool/harness/REBUILD.md)

Emission watch pins (cell 4, re-verify on drift):
  nutshell emission path unchanged @ ac1c2e0; cdk payload struct
  unchanged @ 8006cc30 — flips here mean re-capture before re-running.

Exit 0 = every row matches its frozen expectation; 1 = any drift.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VARIANTS = ["full66", "short16", "v1era16", "overlong18", "mixed", "nullfields"]
CAPTURES = ["capture-01", "capture-02"]

# Frozen expectations (2026-10-31 probe, reproduced 2026-11-01).
CDK_EXPECT = {
    "full66": ("PASS", None),
    "short16": ("FAIL", "NUT02: ID length invalid, expected 8 bytes (short/v1) or 33 bytes (v2)"),
    "v1era16": ("PASS", None),
    "overlong18": ("FAIL", "NUT02: ID length invalid, expected 8 bytes (short/v1) or 33 bytes (v2)"),
    "mixed": ("FAIL", "NUT02: ID length invalid, expected 8 bytes (short/v1) or 33 bytes (v2)"),
    "nullfields": ("PASS", None),  # id:null/memo:null parse — the cashu-ts mirror divergence
    "capture-01": ("FAIL", "NUT02: ID length invalid, expected 8 bytes (short/v1) or 33 bytes (v2)"),
    "capture-02": ("PASS", None),  # cdk emission: full ids + dleq + nulls
}
TS_DECODE_EXPECT = {  # decodePayload is shape-only: string ids all pass; null optionals are NOT
    **{v: "PASS" for v in VARIANTS if v != "nullfields"},
    "nullfields": "FAIL",  # 'invalid payment payload: id must be a string' — cdk PASSes nulls (the divergence)
    "capture-01": "PASS",
    "capture-02": "FAIL",  # memo:null → 'invalid payment payload: memo must be a string' family
}

PROBE_TS = """import {{ describe, it, expect }} from 'vitest';
import {{ readFileSync }} from 'fs';
import {{ PaymentRequest }} from '../../src';
const D = {d!r};
const load = (f: string) => readFileSync(`${{D}}/${{f}}`, 'utf8');
describe('nut18 cell', () => {{
  it('decodes the battery', () => {{
    for (const f of {files!r}) {{
      let verdict = 'PASS', detail = '';
      try {{ PaymentRequest.decodePayload(load(f)); }}
      catch (e: any) {{ verdict = 'FAIL'; detail = String(e?.message || e).slice(0, 120); }}
      console.log(`TS\t${{f}}\t${{verdict}}\t${{detail}}`);
    }}
  }});
}});
"""


def fname(n: str) -> str:
    """Crafted variants are payload_<v>.json; captures are capture-0X.json."""
    return f"payload_{n}.json" if n in VARIANTS else f"{n}.json"


def run_cdk(probe: Path, payloads: Path, names: list[str]) -> dict[str, tuple[str, str]]:
    files = [str(payloads / fname(n)) for n in names]
    out = subprocess.run([str(probe), *files], capture_output=True, text=True, timeout=120)
    rows: dict[str, tuple[str, str]] = {}
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].endswith(".json"):
            stem = Path(parts[0]).stem
            name = stem[len("payload_"):] if stem.startswith("payload_") else stem
            rows[name] = (parts[1], "\t".join(parts[2:])[:160])
    return rows


def run_ts(ts_dir: Path, payloads: Path, names: list[str]) -> dict[str, tuple[str, str]]:
    with tempfile.TemporaryDirectory() as td:
        harness = Path(td) / "nut18-cell.node.test.ts"
        harness.write_text(PROBE_TS.format(d=str(payloads), files=[fname(n) for n in names]))
        (ts_dir / "test" / "live").mkdir(parents=True, exist_ok=True)
        dst = ts_dir / "test" / "live" / "nut18-cell.node.test.ts"
        dst.write_text(harness.read_text())
        out = subprocess.run(
            ["npx", "vitest", "run", "test/live/nut18-cell.node.test.ts"],
            cwd=ts_dir, capture_output=True, text=True, timeout=300,
        )
        rows: dict[str, tuple[str, str]] = {}
        for m in re.finditer(r"^\s*TS\t(\S+)\t(PASS|FAIL)\t(.*)$", out.stdout, re.M):
            stem = m.group(1).removesuffix(".json")
            name = stem[len("payload_"):] if stem.startswith("payload_") else stem
            rows[name] = (m.group(2), m.group(3)[:160])
        dst.unlink(missing_ok=True)
    return rows


def run_settlement(ts_harness: Path, ts_dir: Path, arm: str) -> list[dict]:
    """Live settlement leg — the successor's 10/10 harness (P7/P8 etc)."""
    src = Path(ts_harness)
    dst = ts_dir / "test" / "live" / src.name
    dst.write_text(src.read_text().replace("http://127.0.0.1:28086", arm))
    out = subprocess.run(
        ["npx", "vitest", "run", f"test/live/{src.name}"],
        cwd=ts_dir, capture_output=True, text=True, timeout=300,
    )
    dst.unlink(missing_ok=True)
    m = re.search(r"Tests\s+(\d+) passed(?:[^,]*,\s+(\d+) failed)?", out.stdout)
    passed = int(m.group(1)) if m else 0
    failed = int(m.group(2) or 0) if m else -1
    return [{"lane": "nut18", "vector": f"settlement-harness/{arm}", "result":
             "PASS" if failed == 0 and passed == 10 else "FAIL",
             "expected": "10/10 (P5-P8, captures, emission)",
             "actual": f"{passed} passed / {failed} failed",
             "detail": ""}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdk-probe", required=True)
    ap.add_argument("--ts-dir", required=True, type=Path)
    ap.add_argument("--payloads", default="/root/src/cashu-audit-private/private/nut18-live/out", type=Path)
    ap.add_argument("--ts-harness", default="/root/src/cashu-audit-private/private/nut18-live/harness/nut18-payload-live.node.test.ts", type=Path)
    ap.add_argument("--arm", default="http://127.0.0.1:28086")
    ap.add_argument("--skip-settlement", action="store_true")
    ap.add_argument("--report-out", default="")
    args = ap.parse_args()

    names = VARIANTS + CAPTURES
    cdk = run_cdk(Path(args.cdk_probe), args.payloads, names)
    ts = run_ts(args.ts_dir, args.payloads, names)

    rows = []
    for n in names:
        for fam, got, want in (
            ("cdk", cdk.get(n), CDK_EXPECT[n]),
            ("cashu-ts", ts.get(n), (TS_DECODE_EXPECT[n], None)),
        ):
            if got is None:
                rows.append({"lane": "nut18", "vector": f"parser/{n}/{fam}", "result": "ERROR",
                             "expected": str(want), "actual": "no row", "detail": "consumer produced no verdict"})
                continue
            ok = got[0] == want[0] and (want[1] is None or want[1] in got[1])
            rows.append({"lane": "nut18", "vector": f"parser/{n}/{fam}",
                         "result": "PASS" if ok else "FAIL",
                         "expected": f"{want[0]}" + (f" containing '{want[1][:40]}…'" if want[1] else ""),
                         "actual": f"{got[0]}" + (f" '{got[1][:80]}'" if got[1] else ""),
                         "detail": ""})
    if not args.skip_settlement:
        rows += run_settlement(args.ts_harness, args.ts_dir, args.arm)

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
    for r in rows:
        print(f"[{r['result']}] {r['vector']}: expected {r['expected']} | actual {r['actual']}")
    print(f"nut18 matrix: {len(rows)} rows — " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    if args.report_out:
        Path(args.report_out).write_text(json.dumps(
            {"ts": datetime.now(timezone.utc).isoformat(), "counts": counts, "rows": rows}, indent=1))
        print(f"report: {args.report_out}")
    return 1 if counts.get("FAIL") or counts.get("ERROR") else 0


# Rebuild recipes (machinery is disposable; verdicts are not):
#   cdk probe:  cd /root/src/upstream-cache/cdk && nice -n 10 cargo build -p cashu \
#                 --example nut18_payload_probe -j 2 --target-dir /tmp/opencode/cdk-0182-target-dbg
#               → /tmp/opencode/cdk-0182-target-dbg/debug/examples/nut18_payload_probe
#   ts dir:     git clone --depth 1 --branch v5.0.0-rc.9 https://github.com/cashubtc/cashu-ts \
#                 /root/src/upstream-cache/cashu-ts-rc9 && npm install
#   arm:        docker run -d --name nut18-arm --network host -e MINT_BACKEND_BOLT11_SAT=FakeWallet \
#                 -e MINT_LISTEN_HOST=127.0.0.1 -e MINT_LISTEN_PORT=28086 -e MINT_RATE_LIMIT=FALSE \
#                 -e MINT_PRIVATE_KEY=5d1a09c7... cashubtc/nutshell:0.21.0 poetry run mint
if __name__ == "__main__":
    sys.exit(main())
