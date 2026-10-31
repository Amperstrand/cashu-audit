#!/usr/bin/env /usr/bin/python3
"""Post-deploy certification for testnut (2026-10-31).

Verifies the wire identities of everything landed on cashu-cf main
through 6befce4 (A1 malformed-B_ 400s, A2 request bounds, B2
restore-empty mirror, B3 NUT-15 no-false-ad). Run BEFORE deploy: the
three changed legs FAIL (script self-test). Run AFTER deploy: all PASS.

Usage: /usr/bin/python3 certify_testnut.py [--base https://testnut.cashu.exchange]
"""
import json, sys, secrets, time, uuid, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "must-gap-vectors"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "conformance"))
import must_gap_vectors as mg
from coincurve import PrivateKey

def out(amount, kid, malformed=False):
    s = secrets.token_hex(16); Y = mg.hash_to_curve(s); r = PrivateKey()
    B_ = mg.p_add(Y, r.public_key.format()).hex()
    if malformed: B_ = "zz" + B_[2:]
    return {"amount": amount, "B_": B_, "id": kid}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://testnut.cashu.exchange")
    base = ap.parse_args().base
    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    ks = json.loads(mg.http("GET", f"{base}/v1/keys")[1])["keysets"]
    ks = [k for k in ks if k.get("unit") == "sat"][0]; kid = ks["id"]

    # A1: malformed B_ (single + batch) with a PAID quote -> 400, not 500
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 4, "unit": "sat"})
    q = json.loads(b)["quote"]
    for _ in range(30):
        st, b = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{q}")
        if st == 200 and json.loads(b).get("state") == "PAID": break
        time.sleep(1)
    st, b = mg.http("POST", f"{base}/v1/mint/bolt11", {"quote": q, "outputs": [out(4, kid, True)]})
    check("A1 single malformed-B_ -> 400", st == 400, f"{st} {b[:90]}")
    st, b = mg.http("POST", f"{base}/v1/mint/bolt11/batch", {"quotes": [q], "outputs": [out(4, kid, True)]})
    check("A1 batch malformed-B_ -> 400", st == 400, f"{st} {b[:90]}")

    # A2: batch-fetch loops capped at 50 (11014)
    ids = [str(uuid.uuid4()) for _ in range(51)]
    st, b = mg.http("POST", f"{base}/v1/mint/quotes", {"ids": ids})
    check("A2 mint/quotes 51 ids -> 400/11014", st == 400 and "11014" in b, f"{st} {b[:90]}")

    # B2: restore-empty -> 200 with empty arrays
    st, b = mg.http("POST", f"{base}/v1/restore", {"outputs": []})
    ok = st == 200 and json.loads(b) == {"outputs": [], "signatures": []}
    check("B2 restore-empty -> 200 empty", ok, f"{st} {b[:90]}")

    # B3: fakewallet backend must NOT advertise NUT-15
    st, b = mg.http("GET", f"{base}/v1/info")
    info = json.loads(b)
    nuts = info.get("nuts", {})
    check("B3 no false NUT-15 ad (fakewallet)", "15" not in nuts, f"nut15={'present' if '15' in nuts else 'absent'}")

    # Regression guards: unchanged identities
    p, e = mg.mint_proofs(base, ks, {64: [f"cert-{secrets.token_hex(4)}"]})
    check("regression: mint sanity", not e, e[:80] if e else "64 sat minted")
    if not e:
        # fee-correct shape: testnut fee is 1 sat -> outputs sum 63 (keyed amounts)
        payload = {"inputs": p, "outputs": [out(a, kid) for a in (32, 16, 8, 4, 2, 1)]}
        st, b = mg.http("POST", f"{base}/v1/swap", payload)
        check("regression: swap 200", st == 200, f"{st} {b[:60] if st != 200 else 'ok'}")
        if st == 200:
            st2, b2 = mg.http("POST", f"{base}/v1/swap", payload)
            check("regression: swap replay cached 200", st2 == 200 and b2 == b, f"{st2} identical={b2 == b}")
    p2, e2 = mg.mint_proofs(base, ks, {64: [f"certk-{secrets.token_hex(4)}"]})
    if not e2:
        st, b = mg.http("POST", f"{base}/v1/swap", {"inputs": p2, "outputs": [out(63, kid), out(1, kid)]})
        check("regression: keyless still rejected", st != 200, f"{st} {b[:70]}")

    fails = [r for r in results if not r[1]]
    print(f"\n{'=' * 60}\nCERTIFICATION: {len(results) - len(fails)}/{len(results)} PASS" +
          (" — DEPLOY NOT LIVE YET (expected pre-deploy)" if fails else " — CLEAN"))
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
