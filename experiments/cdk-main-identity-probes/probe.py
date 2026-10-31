#!/usr/bin/env python3
"""cdk-main (3523c8a9, unreleased) probes — wire-verifies UPSTREAM-AUDIT
§1.2 (sig-only HTLC refund, cd8c84d9), §1.3 (restore-empty-200, 0b225c9b),
§1.4/§1.7 (info advertisement, captured at boot). Frozen predictions in
PREDICTIONS.md. Error-identity exact where frozen.

cdk keyset input_fee_ppk=0 → single-output swaps are fine (per-amount keys
derived on demand — no denomination KeyError class, cf. ns-main S5).
"""
import hashlib
import json
import os
import secrets
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "must-gap-vectors"))
from must_gap_vectors import http, mint_proofs, try_swap  # noqa: E402
import must_gap_vectors  # noqa: E402
from coincurve import PrivateKey  # noqa: E402

BASE = os.environ.get("MINT_URL", "http://127.0.0.1:8739")
results = []


def record(cid, pred, status, body, ok):
    results.append({"id": cid, "prediction": pred, "status": status,
                    "body": body[:280], "verdict": "PASS" if ok else "FAIL"})
    print(f"{cid}: {status} {'PASS' if ok else 'FAIL'} :: {body[:170]}")


def htlc(data, tags):
    payload = {"nonce": secrets.token_hex(16), "data": data}
    if tags:
        payload["tags"] = [[k, v] for k, v in tags]
    return json.dumps(["HTLC", payload], separators=(",", ":"))


def schnorr(sk, msg):
    return sk.sign_schnorr(hashlib.sha256(msg.encode()).digest(), None)


def main():
    st, body = http("GET", f"{BASE}/v1/keys")
    keysets = json.loads(body).get("keysets", [])
    ks = next((k for k in keysets if k.get("unit") == "sat"), keysets[0])
    must_gap_vectors.keyset_id_ref[0] = ks["id"]  # try_swap/fresh_output read this
    print("keyset:", ks["id"][:16], "unit:", ks.get("unit"))

    # C5 — unlocked bolt11 quote create: shape capture
    st, body = http("POST", f"{BASE}/v1/mint/quote/bolt11", {"amount": 2, "unit": "sat"})
    j = json.loads(body)
    record("C5", "2xx, method=bolt11, pubkey key ABSENT", st, body,
           st in (200, 201) and j.get("method") == "bolt11" and "pubkey" not in j
           and j.get("state") == "UNPAID")

    # C0 — control: plain mint + swap
    proofs, err = mint_proofs(BASE, ks, {2: [secrets.token_hex(16)]})
    if err:
        record("C0", "200 swap", -1, "mint failed: " + err, False)
        return finish()
    r = try_swap(BASE, [{"amount": p["amount"], "id": p["id"],
                         "secret": p["secret"], "C": p["C"]} for p in proofs], 2)
    record("C0", "200 swap", r["status"], r["body"], r["status"] == 200)

    # C1 — restore with empty outputs
    st, body = http("POST", f"{BASE}/v1/restore", {"outputs": []})
    try:
        j = json.loads(body)
        ok = st == 200 and j.get("outputs") == [] and j.get("signatures") == []
    except Exception:
        ok = False
    record("C1", '200 {"outputs":[],"signatures":[]}', st, body, ok)

    # C2 — HTLC refund, sig-only witness, PAST locktime (the cd8c84d9 fix)
    skR = PrivateKey()
    pkR = skR.public_key.format().hex()
    preimage = secrets.token_bytes(32).hex()
    h = hashlib.sha256(bytes.fromhex(preimage)).hexdigest()
    s_past = htlc(h, [("locktime", "1700000000"), ("refund", pkR)])
    proofs, err = mint_proofs(BASE, ks, {2: [s_past]})
    if err:
        record("C2", "200 ACCEPT", -1, "mint failed: " + err, False)
    else:
        p = proofs[0]
        p["witness"] = json.dumps({"signatures": [schnorr(skR, p["secret"]).hex()]})
        r = try_swap(BASE, [p], 2)
        record("C2", "200 ACCEPT (was 20008 on 0.18.x)", r["status"], r["body"],
               r["status"] == 200)

    # C2b — control: FUTURE locktime, same sig-only witness -> reject
    s_fut = htlc(h, [("locktime", str(int(time.time()) + 3600)), ("refund", pkR)])
    proofs, err = mint_proofs(BASE, ks, {2: [s_fut]})
    if err:
        record("C2b", "400 reject", -1, "mint failed: " + err, False)
    else:
        p = proofs[0]
        p["witness"] = json.dumps({"signatures": [schnorr(skR, p["secret"]).hex()]})
        r = try_swap(BASE, [p], 2)
        record("C2b", "400 reject (identity recorded)", r["status"], r["body"],
               r["status"] == 400)

    return finish()


def finish():
    out = os.path.join(os.path.dirname(__file__), "RESULTS.json")
    with open(out, "w") as f:
        json.dump({"target": "cdk main 3523c8a9 (mintd+FakeWallet :8739)",
                   "predictions": "PREDICTIONS.md (frozen 2026-10-31)",
                   "results": results}, f, indent=1)
    print("wrote", out)
    return 0 if all(r["verdict"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
