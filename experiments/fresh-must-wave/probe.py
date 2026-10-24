#!/usr/bin/env python3
"""Fresh-MUST wave probes: NUT-06/19/05/03 tightening-wave measurements.

Reads PREDICTIONS.md (frozen BEFORE this ran). Arms: ns-0.20.3,
ns-0.21.0, cdk-0.18.1, cdk-0.18.2 (docker) + testnut (url). Melt quotes
use an invoice-oracle arm (scratch nutshell FakeWallet) so target arms
never auto-settle the invoice (conformance-v2 pattern).

Usage: /usr/bin/python3 experiments/fresh-must-wave/probe.py [--host-network]
Output: experiments/fresh-must-wave/out/results.json (+ per-run stdout table)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "conformance"))

import requests  # noqa: E402
from version_matrix import Arm  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
DOCKER_ARMS = [
    ("ns-0.20.3", "nutshell", "cashubtc/nutshell:0.20.3"),
    ("ns-0.21.0", "nutshell", "cashubtc/nutshell:0.21.0"),
    ("cdk-0.18.1", "cdk", "cashubtc/mintd:0.18.1"),
    ("cdk-0.18.2", "cdk", "cashubtc/mintd:0.18.2"),
]
TESTNUT = "https://testnut.cashu.exchange"


def req(method: str, url: str, **kw) -> dict:
    """One request -> {status, body, headers-of-interest}; never raises."""
    try:
        r = requests.request(method, url, timeout=25, **kw)
        body = r.text[:400]
        try:
            j = r.json()
            body = json.dumps(j)[:400]
        except Exception:
            pass
        return {"status": r.status_code,
                "etag": r.headers.get("ETag"),
                "cache_control": r.headers.get("Cache-Control"),
                "body": body}
    except Exception as e:
        return {"status": None, "error": f"{type(e).__name__}: {e}"[:200]}


def ys_body(n: int, shape: str) -> dict:
    def y(i): return f"02{i:064x}"
    if shape == "Ys":
        return {"Ys": [y(i) for i in range(n)]}
    return {"outputs": [{"id": y(i), "amount": 1} for i in range(n)]}


def probe_arm(base: str, invoice: str) -> dict:
    res: dict = {}

    # P1 — NUT-06: checkstate shapes + array limit
    p1 = {}
    for shape in ("Ys", "outputs"):
        p1[f"shape_{shape}_60"] = req("POST", f"{base}/v1/checkstate",
                                      json=ys_body(60, shape))
    # pick the accepted shape for the limit probe
    ok_shape = "Ys"
    if p1["shape_outputs_60"]["status"] == 200:
        ok_shape = "outputs"
    p1["accepted_shape"] = ok_shape
    p1["limit_1001"] = req("POST", f"{base}/v1/checkstate",
                           json=ys_body(1001, ok_shape))
    res["P1_nut06_max_array"] = p1

    # P2 — NUT-19: caching headers + conditional GET
    g1 = req("GET", f"{base}/v1/info")
    g2 = req("GET", f"{base}/v1/info")
    cond = {"status": None, "error": "no etag"}
    if g1.get("etag"):
        r = requests.get(f"{base}/v1/info", timeout=25,
                         headers={"If-None-Match": g1["etag"]})
        cond = {"status": r.status_code}
    res["P2_nut19_cache"] = {
        "get1": {k: g1[k] for k in ("etag", "cache_control")},
        "etag_stable_across_gets": g1.get("etag") == g2.get("etag"),
        "if_none_match": cond,
    }

    # P3 — NUT-05: prefer_async on melt quote (oracle invoice)
    r = requests.post(f"{base}/v1/melt/quote/bolt11", timeout=25, json={
        "request": invoice, "unit": "sat", "prefer_async": True})
    try:
        body = json.dumps(r.json())
    except Exception:
        body = r.text[:300]
    res["P3_nut05_prefer_async"] = {"status": r.status_code, "body": body[:400]}

    # P4 — NUT-03: unit consistency on mint quotes
    p4 = {}
    for unit in ("usd", "eur"):
        r = requests.post(f"{base}/v1/mint/quote/bolt11", timeout=25,
                          json={"amount": 100, "unit": unit})
        try:
            body = json.dumps(r.json())
        except Exception:
            body = r.text[:300]
        p4[f"unit_{unit}"] = {"status": r.status_code, "body": body[:300]}
    res["P4_nut03_unit"] = p4

    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host-network", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    # invoice oracle first
    oracle = Arm("oracle", "nutshell")
    oracle.image = "cashubtc/nutshell:0.21.0"
    oracle.host_network = args.host_network
    oracle.bring_up()
    try:
        q = requests.post(f"{oracle.url}/v1/mint/quote/bolt11", timeout=25,
                          json={"amount": 1000, "unit": "sat"})
        invoice = q.json()["request"]
        print(f"oracle invoice ok ({invoice[:30]}...)")
    finally:
        oracle.tear_down()

    results: dict = {"generated": datetime.now(timezone.utc).isoformat(),
                     "oracle_invoice": invoice[:40] + "...",
                     "arms": {}}

    # testnut (url arm)
    info = req("GET", f"{TESTNUT}/v1/info")
    results["arms"]["testnut(cashu-cf)"] = {
        "identity": info["body"][:120], **probe_arm(TESTNUT, invoice)}
    print("done testnut")

    for name, family, image in DOCKER_ARMS:
        arm = Arm(name, family)
        arm.image = image
        arm.host_network = args.host_network
        t0 = time.time()
        try:
            arm.bring_up()
            info = req("GET", f"{arm.url}/v1/info")
            results["arms"][name] = {
                "identity": arm.identity, "image": image,
                **probe_arm(arm.url, invoice)}
            print(f"done {name} ({time.time()-t0:.0f}s)")
        finally:
            arm.tear_down()

    (OUT / "results.json").write_text(json.dumps(results, indent=1))

    # compact table
    for aname, a in results["arms"].items():
        p1 = a["P1_nut06_max_array"]
        p4 = a["P4_nut03_unit"]
        p2 = a["P2_nut19_cache"]
        print(f"\n== {aname} ({a.get('identity', '')[:30]})")
        print(f"  P1 shape(Ys/outputs): {p1['shape_Ys_60']['status']}/"
              f"{p1['shape_outputs_60']['status']} accepted={p1['accepted_shape']}")
        lim = p1["limit_1001"]
        print(f"  P1 1001-array: {lim['status']} {str(lim.get('body'))[:90]}")
        print(f"  P2 etag={p2['get1']['etag'] is not None} "
              f"cc={p2['get1']['cache_control']} cond={p2['if_none_match']}")
        p3 = a["P3_nut05_prefer_async"]
        print(f"  P3 prefer_async melt-quote: {p3['status']} {p3['body'][:90]}")
        for u in ("usd", "eur"):
            print(f"  P4 unit={u}: {p4[f'unit_{u}']['status']} "
                  f"{p4[f'unit_{u}']['body'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
