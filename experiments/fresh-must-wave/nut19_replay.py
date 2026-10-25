#!/usr/bin/env python3
"""NUT-19 replay probes on fund paths: byte-identical swap and melt
re-POSTs after success. Cached (200 identical) vs rejected (400).

Usage: /usr/bin/python3 experiments/fresh-must-wave/nut19_replay.py
"""
from __future__ import annotations

import json
import secrets
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "must-gap-vectors"))
sys.path.insert(0, str(HERE.parent.parent / "conformance"))

import must_gap_vectors as mg  # noqa: E402
from coincurve import PrivateKey  # noqa: E402
from version_matrix import Arm  # noqa: E402

OUT = HERE / "out"
TESTNUT = "https://testnut.cashu.exchange"


def sat_keyset(base):
    ks = json.loads(mg.http("GET", f"{base}/v1/keys")[1])["keysets"]
    return [k for k in ks if k.get("unit") == "sat"][0]


def fresh_out(amount, kid):
    s = secrets.token_hex(16)
    Y = mg.hash_to_curve(s)
    r = PrivateKey()
    return {"amount": amount, "B_": mg.p_add(Y, r.public_key.format()).hex(), "id": kid}


def oracle_invoice():
    o = Arm(f"orc-{secrets.token_hex(3)}", "nutshell")
    o.image = "cashubtc/nutshell:0.21.0"
    o.host_network = True
    o.bring_up()
    try:
        return json.loads(mg.http("POST", f"{o.url}/v1/mint/quote/bolt11",
                                  {"amount": 32, "unit": "sat"})[1])["request"]
    finally:
        o.tear_down()


def run_arm(base):
    ks = sat_keyset(base)
    kid = ks["id"]
    res = {}

    # ---- swap replay ----
    proofs, err = mg.mint_proofs(base, ks,
                                 {64: [f"r-{secrets.token_hex(6)}-{i}"] for i in range(1)})
    if err:
        return {"setup": f"mint: {err[:120]}"}
    total = 64
    out = fresh_out(total, kid)
    payload = {"inputs": proofs, "outputs": [out]}
    st1, b1 = mg.http("POST", f"{base}/v1/swap", payload)
    res["swap_first"] = {"status": st1, "body": b1[:100]}
    if st1 == 200:
        st2, b2 = mg.http("POST", f"{base}/v1/swap", payload)
        res["swap_replay"] = {
            "status": st2,
            "identical_body": b2 == b1,
            "body": b2[:160],
        }

    # ---- melt replay ----
    proofs2, err2 = mg.mint_proofs(base, ks,
                                   {64: [f"m-{secrets.token_hex(6)}-{i}"] for i in range(1)})
    if err2:
        res["melt_setup"] = f"mint: {err2[:120]}"
        return res
    inv = oracle_invoice()
    st, body = mg.http("POST", f"{base}/v1/melt/quote/bolt11",
                       {"request": inv, "unit": "sat"})
    if st != 200:
        res["melt_quote"] = f"{st}: {body[:120]}"
        return res
    q = json.loads(body)["quote"]
    mpayload = {"quote": q, "inputs": proofs2, "outputs": [fresh_out(32, kid)]}
    st1, b1 = mg.http("POST", f"{base}/v1/melt/bolt11", mpayload)
    res["melt_first"] = {"status": st1, "body": b1[:100]}
    if st1 == 200:
        st2, b2 = mg.http("POST", f"{base}/v1/melt/bolt11", mpayload)
        res["melt_replay"] = {
            "status": st2,
            "identical_body": b2 == b1,
            "body": b2[:160],
        }
    return res


def main() -> int:
    OUT.mkdir(exist_ok=True)
    results = {"testnut(cashu-cf)": run_arm(TESTNUT)}
    print("testnut:", json.dumps(results["testnut(cashu-cf)"])[:400])
    for name, family, image in (("ns-0.21.0", "nutshell", "cashubtc/nutshell:0.21.0"),
                                ("cdk-0.18.2", "cdk", "cashubtc/mintd:0.18.2")):
        arm = Arm(name.replace(".", "-"), family)
        arm.image = image
        arm.host_network = True
        t0 = time.time()
        try:
            arm.bring_up()
            results[name] = run_arm(arm.url)
            print(f"{name} ({time.time()-t0:.0f}s):", json.dumps(results[name])[:400])
        finally:
            arm.tear_down()
    (OUT / "nut19_replay.json").write_text(json.dumps(results, indent=1))
    print("\n== summary")
    for arm, v in results.items():
        print(f"\n{arm}:")
        for k, r in v.items():
            print(f"  {k}: {json.dumps(r)[:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
