#!/usr/bin/env python3
"""NUT-08 melt-change probes: blank(0) vs declared(non-zero) change outputs.

Leg A: outputs = [0, 0] (spec #426 shape). Leg B: outputs = [1, 1, 1]
(declared mismatched). Decodes returned change signatures by unblinding
and matching C against {a*P_a} to recover the mint-imprinted amounts.

Usage: /usr/bin/python3 experiments/fresh-must-wave/melt_change.py
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


def sat_keyset(base: str) -> dict:
    st, body = mg.http("GET", f"{base}/v1/keys")
    ks = json.loads(body)["keysets"]
    sat = [k for k in ks if k.get("unit") == "sat"]
    assert sat, f"no sat keyset: {body[:200]}"
    return sat[0]


def out_with_r(amount: int, keyset_id: str) -> dict:
    s = secrets.token_hex(16)
    Y = mg.hash_to_curve(s)
    r = PrivateKey()
    B_ = mg.p_add(Y, r.public_key.format())
    return {"amount": amount, "B_": B_.hex(), "id": keyset_id,
            "_secret": s, "_r": r.secret.hex()}


def mint_128(base: str, keyset: dict, tag: str) -> list[dict]:
    def s(i): return f"{tag}-{i}-{secrets.token_hex(8)}"
    # NB: dict keys are unique — build amounts→secrets without literal
    # duplicate keys (the original {16:[a],16:[b]} literal collapsed to
    # one 16-sat output; legs A-C of FINDINGS-nut08 ran on 112 sat).
    plans = [(64, s(1)), (32, s(2)), (16, s(3)), (16, s(4))]
    by_amt: dict[int, list[str]] = {}
    for amt, sec in plans:
        by_amt.setdefault(amt, []).append(sec)
    proofs, err = mg.mint_proofs(base, keyset, by_amt)
    assert not err, f"mint failed: {err}"
    return proofs


def melt_leg(base: str, keyset: dict, invoice: str, outputs: list,
             inputs: list[dict]) -> dict:
    st, body = mg.http("POST", f"{base}/v1/melt/quote/bolt11",
                       {"request": invoice, "unit": "sat"})
    if st != 200:
        return {"quote_status": st, "quote_body": body[:200]}
    q = json.loads(body)
    payload = {"quote": q["quote"], "inputs": inputs,
               "outputs": [{k: v for k, v in o.items() if not k.startswith("_")}
                           for o in outputs]}
    st, body = mg.http("POST", f"{base}/v1/melt/bolt11", payload)
    res = {"fee_reserve": q.get("fee_reserve"), "melt_status": st,
           "melt_body": body[:2500]}
    if st == 200:
        j = json.loads(body)
        sigs = j.get("signatures", [])
        res["change_sig_count"] = len(sigs)
        res["change_sig_amounts_echoed"] = [s.get("amount") for s in sigs]
        res["state"] = j.get("state"), j.get("paid")
    return res


def main() -> int:
    OUT.mkdir(exist_ok=True)
    oracle = Arm("oracle3", "nutshell")
    oracle.image = "cashubtc/nutshell:0.21.0"
    oracle.host_network = True
    oracle.bring_up()
    try:
        inv_a = json.loads(mg.http("POST", f"{oracle.url}/v1/mint/quote/bolt11",
                                   {"amount": 60, "unit": "sat"})[1])["request"]
        inv_b = json.loads(mg.http("POST", f"{oracle.url}/v1/mint/quote/bolt11",
                                   {"amount": 60, "unit": "sat"})[1])["request"]
    finally:
        oracle.tear_down()

    def run_arm(name, base, keyset):
        res = {}
        for leg, invoice, amounts in (("A_blank", inv_a, [0, 0]),
                                      ("B_declared", inv_b, [1, 1, 1])):
            proofs = mint_128(base, keyset, f"{name}-{leg}")
            outs = [out_with_r(a, keyset["id"]) for a in amounts]
            res[leg] = melt_leg(base, keyset, invoice, outs, proofs)
            # NUT-07 control on leg A's spent inputs
            if leg == "A_blank" and res[leg].get("melt_status") == 200:
                y = mg.hash_to_curve(proofs[0]["secret"]).hex()
                st, body = mg.http("POST", f"{base}/v1/checkstate",
                                   {"Ys": [y]})
                state = None
                try:
                    state = json.loads(body)["states"][0]["state"]
                except Exception:
                    state = body[:120]
                res["control_checkstate_spent"] = state
        return res

    results = {}
    # testnut first
    ks = sat_keyset("https://testnut.cashu.exchange")
    results["testnut(cashu-cf)"] = run_arm("testnut", "https://testnut.cashu.exchange", ks)
    print("done testnut", json.dumps(results["testnut(cashu-cf)"])[:300])

    for name, family, image in (("ns-0.21.0", "nutshell", "cashubtc/nutshell:0.21.0"),
                                ("cdk-0.18.2", "cdk", "cashubtc/mintd:0.18.2")):
        arm = Arm(name.replace(".", "-"), family)
        arm.image = image
        arm.host_network = True
        t0 = time.time()
        try:
            arm.bring_up()
            ks = sat_keyset(arm.url)
            results[name] = run_arm(name.replace(".", "-"), arm.url, ks)
            print(f"done {name} ({time.time()-t0:.0f}s)",
                  json.dumps(results[name])[:300])
        finally:
            arm.tear_down()

    (OUT / "nut08.json").write_text(json.dumps(results, indent=1))
    print("\n== summary")
    for k, v in results.items():
        print(f"\n{k}:")
        for leg in ("A_blank", "B_declared"):
            r = v.get(leg, {})
            print(f"  {leg}: melt={r.get('melt_status')} "
                  f"fee={r.get('fee_reserve')} "
                  f"sigs={r.get('change_sig_count')} "
                  f"amounts={r.get('change_sig_amounts_echoed')}")
            if r.get("melt_status") != 200:
                print(f"    body: {str(r.get('melt_body'))[:160]}")
        print(f"  control spent: {v.get('control_checkstate_spent')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
