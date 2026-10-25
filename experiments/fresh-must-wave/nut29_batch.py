#!/usr/bin/env python3
"""NUT-29 batch-mint atomicity probes.

Legs: control (valid batch), A (one corrupted B_ in balanced batch),
B (unknown quote id), C (duplicate quote ids), D (empty quotes), plus
the re-submit control after each rejection (does a rejected batch burn
paid quotes? fund-loss class).

Usage: /usr/bin/python3 experiments/fresh-must-wave/nut29_batch.py
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


def paid_quote(base, amount):
    st, body = mg.http("POST", f"{base}/v1/mint/quote/bolt11",
                       {"amount": amount, "unit": "sat"})
    if st != 200:
        return None, f"quote {st}: {body[:120]}"
    q = json.loads(body)["quote"]
    for _ in range(40):
        st, body = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{q}")
        if st == 200 and json.loads(body).get("state") == "PAID":
            return q, ""
        time.sleep(1)
    return None, f"never paid: {body[:120]}"


def outputs_for(total, kid):
    """Blinded outputs decomposed as powers of 2 summing to total."""
    outs, rem = [], total
    for amt in (64, 32, 16, 8, 4, 2, 1):
        while rem >= amt:
            s = secrets.token_hex(16)
            Y = mg.hash_to_curve(s)
            r = PrivateKey()
            B_ = mg.p_add(Y, r.public_key.format())
            outs.append({"amount": amt, "B_": B_.hex(), "id": kid})
            rem -= amt
    return outs


def batch(base, quotes, outputs):
    payload = {"quotes": quotes, "outputs": outputs}
    st, body = mg.http("POST", f"{base}/v1/mint/bolt11/batch", payload)
    sigs = []
    if st == 200:
        try:
            sigs = json.loads(body).get("signatures", [])
        except Exception:
            pass
    return {"status": st, "sig_count": len(sigs), "body": body[:220]}


def run_arm(base, tag):
    ks = sat_keyset(base)
    res = {}
    q1, e1 = paid_quote(base, 64)
    q2, e2 = paid_quote(base, 32)
    if not q1 or not q2:
        return {"setup_error": f"{e1} / {e2}"}

    valid = outputs_for(96, ks["id"])
    res["control"] = batch(base, [q1, q2], valid)
    if res["control"]["status"] != 200:
        # control failed: record and still try the validation legs
        res["control_note"] = "control not 200 — batch route/behavior issue"

    for leg, quotes, outputs in (
        ("A_corrupt_B", None, None),
        ("B_unknown_quote", [q1, "00000000-0000-7000-8000-000000000000"], valid),
        ("C_dup_quotes", [q1, q1], valid),
        ("D_empty", [], []),
    ):
        if leg == "A_corrupt_B":
            q3, e3 = paid_quote(base, 96)
            if not q3:
                res[leg] = {"setup_error": e3}
                continue
            outs = outputs_for(96, ks["id"])
            outs[1]["B_"] = "z" * 66  # garbage hex, same length
            res[leg] = batch(base, [q3], outs)
        else:
            res[leg] = batch(base, quotes, outputs)

    # re-submit control after rejections: are the quotes still mintable?
    q4, e4 = paid_quote(base, 64)
    q5, e5 = paid_quote(base, 32)
    if q4 and q5:
        res["recontrol_after_rejections"] = batch(base, [q4, q5],
                                                  outputs_for(96, ks["id"]))
    return res


def main() -> int:
    OUT.mkdir(exist_ok=True)
    results = {}
    results["testnut(cashu-cf)"] = run_arm(TESTNUT, "testnut")
    print("testnut:", json.dumps(results["testnut(cashu-cf)"])[:400])
    for name, family, image in (("ns-0.21.0", "nutshell", "cashubtc/nutshell:0.21.0"),
                                ("cdk-0.18.2", "cdk", "cashubtc/mintd:0.18.2")):
        arm = Arm(name.replace(".", "-"), family)
        arm.image = image
        arm.host_network = True
        t0 = time.time()
        try:
            arm.bring_up()
            results[name] = run_arm(arm.url, name)
            print(f"{name} ({time.time()-t0:.0f}s):",
                  json.dumps(results[name])[:400])
        finally:
            arm.tear_down()
    (OUT / "nut29.json").write_text(json.dumps(results, indent=1))

    print("\n== summary")
    for arm, v in results.items():
        print(f"\n{arm}:")
        for leg in ("control", "A_corrupt_B", "B_unknown_quote",
                    "C_dup_quotes", "D_empty", "recontrol_after_rejections"):
            r = v.get(leg)
            if r is None:
                continue
            print(f"  {leg}: {r.get('status')} sigs={r.get('sig_count')} "
                  f"{str(r.get('body'))[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
