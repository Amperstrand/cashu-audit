#!/usr/bin/env python3
"""ns-main (ac1c2e0, unreleased) error-identity probes — wire-verifies
UPSTREAM-AUDIT-2026-10 §2.2-2.5 claims that were source-verified only.

Frozen predictions in PREDICTIONS.md (written pre-run). Assertions are
error-identity exact (status + detail + code), never any-4xx.

Scenarios:
  S0  control: plain mint + swap (rig health)
  S1a P2PK swap, witness ABSENT        -> 11000 "no signatures in proof."
  S1b P2PK swap, witness {"foo":"bar"} -> 11000 "witness could not be parsed."
  S2  keysets.balance forced to 0, swap VALID proofs -> 11000 balance msg
  S3  secret 2000 chars                -> 422 string_too_long (no code field)
  S4  unlocked mint-quote create       -> "pubkey" key ABSENT
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "must-gap-vectors"))
from must_gap_vectors import http, mint_proofs, fresh_output  # noqa: E402
import must_gap_vectors  # noqa: E402
from coincurve import PrivateKey  # noqa: E402

BASE = os.environ.get("MINT_URL", "http://127.0.0.1:8738")
DB = os.environ.get("NS_DB", "/tmp/opencode/ns-main-mint/data/mint/mint.sqlite3")
results = []


def record(sid, pred, status, body, ok):
    results.append({"id": sid, "prediction": pred, "status": status,
                    "body": body[:280], "verdict": "PASS" if ok else "FAIL"})
    print(f"{sid}: {status} {'PASS' if ok else 'FAIL'} :: {body[:160]}")


def p2pk_secret(pk_hex: str) -> str:
    # canonical NUT-10 tagged-array form (as wallets emit; dict form is NOT
    # parsed as a conditioned secret by the mint — discovered this run)
    return json.dumps(["P2PK", {"nonce": os.urandom(16).hex(), "data": pk_hex}],
                      separators=(",", ":"))


def split_denoms(n: int) -> list[int]:
    out = []
    for b in range(64, -1, -1):
        while n >= 2 ** b:
            out.append(2 ** b)
            n -= 2 ** b
    return out


def swap(inputs, single_output=False):
    total = sum(i["amount"] for i in inputs)
    fee = 0
    st, body = http("POST", f"{BASE}/v1/swap",
                    {"inputs": inputs, "outputs": [fresh_output(total)[0]]})
    if st == 400 and "not balanced" in body:
        import re
        m = re.search(r"fees \((\d+)\)", body)
        if m:
            fee = int(m.group(1))
    if single_output:
        return st, body
    outs = [fresh_output(a)[0] for a in split_denoms(total - fee)]
    return http("POST", f"{BASE}/v1/swap", {"inputs": inputs, "outputs": outs})


def main():
    st, body = http("GET", f"{BASE}/v1/keys")
    ks = json.loads(body)["keysets"][0]
    must_gap_vectors.keyset_id_ref[0] = ks["id"]  # fresh_output() reads this
    print("keyset:", ks["id"], "unit:", ks.get("unit"))

    # S4 — unlocked quote create: pubkey key must be ABSENT
    st, body = http("POST", f"{BASE}/v1/mint/quote/bolt11", {"amount": 64, "unit": "sat"})
    j = json.loads(body)
    record("S4", '2xx, "pubkey" key ABSENT', st, body,
           st in (200, 201) and "pubkey" not in j)

    # S0 — control: plain mint + swap (denomination-split outputs)
    proofs, err = mint_proofs(BASE, ks, {64: [os.urandom(16).hex()]})
    if err:
        record("S0", "200 swap", -1, "mint failed: " + err, False)
    else:
        st, body = swap([{"amount": p["amount"], "id": p["id"],
                          "secret": p["secret"], "C": p["C"]} for p in proofs])
        record("S0", "200 swap", st, body, st == 200)

    # S5 — DISCOVERED (unpredicated): single non-denomination output
    # (64-sat input, fee 1 -> single 63-sat output) -> opaque {"detail":"63","code":0}
    # KeyError(amount) from keyset.private_keys[output.amount] leaks at the handler.
    proofs, err = mint_proofs(BASE, ks, {64: [os.urandom(16).hex()]})
    if err:
        record("S5", "opaque code:0 detail=<amount>", -1, "mint failed: " + err, False)
    else:
        st, body = http("POST", f"{BASE}/v1/swap",
                        {"inputs": [{"amount": p["amount"], "id": p["id"],
                                     "secret": p["secret"], "C": p["C"]} for p in proofs],
                         "outputs": [fresh_output(64 - 1)[0]]})  # single non-denomination output
        try:
            j = json.loads(body)
            ok = (st == 400 and j.get("code") == 0
                  and j.get("detail") == str(64 - 1))
        except Exception:
            ok = False
        record("S5", '400 {"detail":"63","code":0} (KeyError leak)', st, body, ok)

    # S1a/S1b — P2PK proofs (mint once, two secrets)
    pk = PrivateKey().public_key.format(compressed=True).hex()
    sec_a, sec_b = p2pk_secret(pk), p2pk_secret(pk)  # distinct strings below
    sec_b = p2pk_secret(PrivateKey().public_key.format(compressed=True).hex())
    proofs, err = mint_proofs(BASE, ks, {64: [sec_a, sec_b]})
    if err:
        record("S1a", "11000 no-sigs", -1, "mint failed: " + err, False)
        record("S1b", "11000 unparsable", -1, "mint failed: " + err, False)
    else:
        pa, pb = proofs
        # S1a: witness key absent entirely
        st, body = swap([{"amount": pa["amount"], "id": pa["id"],
                          "secret": pa["secret"], "C": pa["C"]}])
        try:
            j = json.loads(body)
            ok = (st == 400 and j.get("code") == 11000
                  and j.get("detail") == "no signatures in proof.")
        except Exception:
            j, ok = {}, False
        record("S1a", '400 {"detail":"no signatures in proof.","code":11000}', st, body, ok)
        # S1b: witness present but unparsable shape
        st, body = swap([{"amount": pb["amount"], "id": pb["id"],
                          "secret": pb["secret"], "C": pb["C"],
                          "witness": '{"foo":"bar"}'}])
        try:
            j = json.loads(body)
            ok = (st == 400 and j.get("code") == 11000
                  and j.get("detail") == "witness could not be parsed.")
        except Exception:
            j, ok = {}, False
        record("S1b", '400 {"detail":"witness could not be parsed.","code":11000}', st, body, ok)

    # S2 — keyset balance forced to 0, then swap a VALID fresh proof
    proofs, err = mint_proofs(BASE, ks, {64: [os.urandom(16).hex()]})
    if err:
        record("S2", "11000 balance", -1, "mint failed: " + err, False)
    else:
        con = sqlite3.connect(DB, timeout=10)
        cur = con.execute("SELECT id, balance FROM keysets WHERE id=?", (ks["id"],))
        row = cur.fetchone()
        con.execute("UPDATE keysets SET balance=0 WHERE id=?", (ks["id"],))
        con.commit()
        print(f"S2 db: keyset row {row} -> balance 0")
        con.close()
        p = proofs[0]
        st, body = swap([{"amount": p["amount"], "id": p["id"],
                          "secret": p["secret"], "C": p["C"]}])
        try:
            j = json.loads(body)
            ok = (st == 400 and j.get("code") == 11000
                  and j.get("detail") == "keyset balance is insufficient for redemption")
        except Exception:
            j, ok = {}, False
        record("S2", '400 {"detail":"keyset balance is insufficient...","code":11000}', st, body, ok)

    # S3 — secret length 2000 (pydantic, before hash_to_curve)
    st, body = swap([{"amount": 2, "id": ks["id"], "secret": "A" * 2000,
                      "C": "02" + "00" * 32}])
    try:
        j = json.loads(body)
        d = j.get("detail")
        ok = (st == 422 and isinstance(d, list) and d
              and d[0].get("type") == "string_too_long"
              and "code" not in j
              and "secret" in str(d[0].get("loc", "")))
    except Exception:
        ok = False
    record("S3", "422 string_too_long @ inputs[0].secret, no code field", st, body, ok)

    out = os.path.join(os.path.dirname(__file__), "RESULTS.json")
    with open(out, "w") as f:
        json.dump({"target": "nutshell main ac1c2e0 (FakeWallet :8738)",
                   "predictions": "PREDICTIONS.md (frozen 2026-10-31)",
                   "results": results}, f, indent=1)
    print("wrote", out)
    return 0 if all(r["verdict"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
