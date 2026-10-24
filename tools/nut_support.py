#!/usr/bin/env python3
"""Capture and compare the NUT-support declarations of mint implementations.

Wire evidence only (house method): each arm's `/v1/info` `nuts` array is the
NUT-06 declaration surface. Nothing is inferred from source code.

Arms (pinned to the conformance-v2 lane versions + our production mints):
    docker: ns-0.20.3, ns-0.21.0 (cashubtc/nutshell), cdk-0.18.1, cdk-0.18.2
            (cashubtc/mintd)
    url:    testnut, rugs (Amperstrand cashu-cf production)

Usage:
    python3 tools/nut_support.py [--host-network] [--keep-containers]

Output:
    research/MINT-NUT-SUPPORT.md      — generated comparison matrix
    research/mint-nut-support.json    — raw /v1/info per arm (regenerated
                                        wholesale each run; diff for drift)

Reuses conformance/version_matrix.Arm for bring-up so the boot recipe is
identical to the weekly conformance-v2 lane.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "conformance"))

import requests  # noqa: E402
from version_matrix import Arm  # noqa: E402

DOCKER_ARMS = [
    ("ns-0.20.3", "nutshell", "cashubtc/nutshell:0.20.3"),
    ("ns-0.21.0", "nutshell", "cashubtc/nutshell:0.21.0"),
    ("cdk-0.18.1", "cdk", "cashubtc/mintd:0.18.1"),
    ("cdk-0.18.2", "cdk", "cashubtc/mintd:0.18.2"),
]
URL_ARMS = [
    ("testnut(cashu-cf)", "https://testnut.cashu.exchange"),
    ("rugs(cashu-cf)", "https://rugs.cashu.exchange"),
]


def fetch_info(url: str, timeout: int = 20) -> dict:
    r = requests.get(f"{url}/v1/info", timeout=timeout)
    r.raise_for_status()
    return r.json()


def normalize_nuts(nuts_raw) -> dict:
    """`nuts` array -> {"NUT-XX": payload-dict}; tolerates dict or list forms."""
    out: dict = {}

    def norm_key(k: str) -> str:
        k = k.strip().upper()
        m = re.fullmatch(r"(?:NUT-)?(\d+)", k)
        return f"NUT-{int(m.group(1)):02d}" if m else k

    if isinstance(nuts_raw, dict):
        it = ((norm_key(k), v) for k, v in nuts_raw.items())
    else:
        it = ((norm_key(str(e[0])), e[1] if len(e) > 1 else {}) for e in nuts_raw)
    for k, v in it:
        out[k] = v
    return out


def payload_summary(v) -> str:
    if not isinstance(v, dict):
        return str(v)[:40]
    bits = []
    for key in ("methods", "params", "supported"):
        if key not in v:
            continue
        val = v[key]
        if key == "methods" and isinstance(val, list):
            pairs = [f"{m.get('method','?')}:{m.get('unit','?')}"
                     if isinstance(m, dict) else str(m) for m in val]
            bits.append("methods=" + "+".join(pairs))
        elif key == "supported" and isinstance(val, list) and val and isinstance(val[0], dict):
            cmds = sorted({c for s in val if isinstance(s, dict)
                           for c in (s.get("commands") or
                                     ([s["command"]] if "command" in s else []))})
            units = sorted({s.get("unit", "?") for s in val if isinstance(s, dict)})
            bits.append(f"commands={len(cmds)} units={','.join(units)}")
        else:
            bits.append(f"{key}={json.dumps(val, separators=(',', ':'))[:60]}")
    return " ".join(bits) if bits else "{}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host-network", action="store_true",
                    help="boot docker arms with --network host (ai-legion)")
    ap.add_argument("--keep-containers", action="store_true")
    ap.add_argument("--from-json", action="store_true",
                    help="re-render the matrix from the existing "
                         "research/mint-nut-support.json (no probing)")
    args = ap.parse_args()

    raw: dict = {}
    arms: list[Arm] = []
    stamp = ""
    json_path = REPO / "research/mint-nut-support.json"
    if args.from_json:
        raw = json.loads(json_path.read_text())["arms"]
        stamp = json.loads(json_path.read_text())["generated"] + " (re-rendered)"
        print(f"loaded {len(raw)} arms from {json_path} (no probe)")
    else:
        for name, url in URL_ARMS:
            info = fetch_info(url)
            raw[name] = {"kind": "url", "url": url, "fetched": info}
            print(f"ok url arm {name}: version={info.get('version')}")

        for name, family, image in DOCKER_ARMS:
            arm = Arm(name, family)
            arm.image = image
            arm.host_network = args.host_network
            t0 = time.time()
            try:
                arm.bring_up()
                info = fetch_info(arm.url)
                raw[name] = {
                    "kind": "docker", "image": image, "url": arm.url,
                    "identity_version": arm.identity, "fetched": info,
                }
                print(f"ok docker arm {name} ({time.time()-t0:.0f}s): "
                      f"version={info.get('version')} nuts={len(info.get('nuts', []))}")
            finally:
                if not args.keep_containers:
                    arm.tear_down()
            arms.append(arm)

    if not args.from_json:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    norm = {n: {"version": d["fetched"].get("version"),
                "nuts": normalize_nuts(d["fetched"].get("nuts", []))}
            for n, d in raw.items()}
    (REPO / "research/mint-nut-support.json").write_text(
        json.dumps({"generated": stamp, "arms": raw}, indent=1))

    keys = {k for v in norm.values() for k in v["nuts"]}
    odd = sorted(k for k in keys if not re.fullmatch(r"NUT-\d+", k))
    if odd:
        print(f"note: non-NUT keys in some /v1/info nuts arrays: {odd}")
    all_nuts = sorted((k for k in keys if re.fullmatch(r"NUT-\d+", k)),
                      key=lambda k: int(k.split("-")[1])) + odd
    cols = list(norm)
    md = [
        "# MINT NUT-SUPPORT MATRIX — `/v1/info` declarations (wire evidence)",
        "",
        f"Generated {stamp} by `tools/nut_support.py`. Raw JSON: "
        "`research/mint-nut-support.json` (regenerated wholesale; diff = drift).",
        "Docker arms reuse the conformance-v2 boot recipe (FakeWallet).",
        "",
        "| NUT | " + " | ".join(cols) + " |",
        "|---|" + "|".join("---" for _ in cols) + "|",
    ]
    for nut in all_nuts:
        cells = []
        for c in cols:
            v = norm[c]["nuts"].get(nut)
            cells.append("✔ " + payload_summary(v) if v is not None else "—")
        md.append(f"| {nut} | " + " | ".join(cells) + " |")
    md += [
        "",
        "## Arm versions as declared on the wire",
        "",
        "| Arm | version |",
        "|---|---|",
    ]
    for c in cols:
        md.append(f"| {c} | {norm[c]['version']} |")

    (REPO / "research/MINT-NUT-SUPPORT.md").write_text("\n".join(md) + "\n")
    print(f"wrote research/MINT-NUT-SUPPORT.md ({len(all_nuts)} NUT rows, "
          f"{len(cols)} arms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
