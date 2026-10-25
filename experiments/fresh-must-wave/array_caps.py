#!/usr/bin/env python3
"""Mint/swap array-cap probes (fund-path endpoints).

Leg 1: mint 128 one-sat outputs (mint-endpoint output cap datum).
Leg 2: swap all minted inputs at once (swap-input cap datum).
Leg 3: swap 16x64-sat inputs into ~1001 one-sat outputs (swap-output
cap datum; adaptive: if balance-check fires before length, retry with
the exact sum).

Usage: /usr/bin/python3 experiments/fresh-must-wave/array_caps.py
"""
from __future__ import annotations

import json
import re
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


def many_outputs(total_ones: int, kid: str):
    outs = []
    for _ in range(total_ones):
        s = secrets.token_hex(16)
        Y = mg.hash_to_curve(s)
        r = PrivateKey()
        outs.append({"amount": 1, "B_": mg.p_add(Y, r.public_key.format()).hex(),
                     "id": kid})
    return outs


def run_arm(base):
    ks = sat_keyset(base)
    kid = ks["id"]
    res = {}

    # Leg 1: mint 128 x 1-sat (mint-output cap)
    outs128 = many_outputs(128, kid)
    proofs, err = mg.mint_proofs(base, ks, {1: [f"cap-{secrets.token_hex(6)}-{i}"
                                                for i in range(128)]})
    res["L1_mint_128_outputs"] = "ok" if not err else f"FAIL: {err[:120]}"

    # Leg 2: swap all inputs at once -> 1 output (swap-input cap)
    if not err:
        total = sum(p["amount"] for p in proofs)
        s = secrets.token_hex(16)
        Y = mg.hash_to_curve(s)
        r = PrivateKey()
        one = {"amount": total, "B_": mg.p_add(Y, r.public_key.format()).hex(), "id": kid}
        st, body = mg.http("POST", f"{base}/v1/swap",
                           {"inputs": proofs, "outputs": [one]})
        res["L2_swap_128_inputs"] = {"status": st, "body": body[:160]}

    # Leg 3: 16x64 in -> ~1001 one-sat out (swap-output cap)
    proofs16, err2 = mg.mint_proofs(base, ks,
                                    {64: [f"b-{secrets.token_hex(6)}-{i}" for i in range(16)]})
    if not err2:
        total = 1024
        # first attempt: 1001 outputs summing 1001 (balance mismatch expected
        # unless length fires first — check-order datum either way)
        outs = many_outputs(1001, kid)
        st, body = mg.http("POST", f"{base}/v1/swap",
                           {"inputs": proofs16, "outputs": outs})
        res["L3_swap_1001_out_mismatch"] = {"status": st, "body": body[:160]}
        # parse fee if balance error, retry with exact sum
        if st == 400:
            m = re.search(r"(\d+)", body)
            fee = None
            for pat in (r"fees \((\d+)\)", r"required \((\d+)\)", r"fee.*?(\d+)"):
                mm = re.search(pat, body)
                if mm:
                    fee = int(mm.group(1))
                    break
            if fee is not None and total - fee > 1000:
                n_out = total - fee - (total - fee - 1000)  # all 1s
                outs2 = many_outputs(n_out, kid)
                st2, body2 = mg.http("POST", f"{base}/v1/swap",
                                     {"inputs": proofs16, "outputs": outs2})
                res["L3_retry_exact_sum"] = {"n_outputs": n_out, "status": st2,
                                              "body": body2[:160]}
            else:
                # fall back: mint fresh inputs sized for 1001 outputs + fee
                proofs17, err3 = mg.mint_proofs(
                    base, ks, {64: [f"c-{secrets.token_hex(6)}-{i}" for i in range(16)]})
                if not err3:
                    outs3 = many_outputs(1001, kid)
                    st3, body3 = mg.http("POST", f"{base}/v1/swap",
                                         {"inputs": proofs17, "outputs": outs3})
                    res["L3_retry_fresh_1024"] = {"status": st3, "body": body3[:160]}
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
    (OUT / "array_caps.json").write_text(json.dumps(results, indent=1))
    print("\n== summary")
    for arm, v in results.items():
        print(f"\n{arm}:")
        for k, r in v.items():
            print(f"  {k}: {json.dumps(r)[:180]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
