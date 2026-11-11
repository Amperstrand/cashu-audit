#!/usr/bin/env /usr/bin/python3
"""Signut certifier — extensive baseline for signut.cashu.exchange (2026-11-11).

Cashu-cf / CLNrest backend / sat-only / pre-#118 deploy. Legs match
PREDICTIONS-2026-11-11-signut.md (frozen before this ran). Funding:
primary = CLN rail (ssh inr2 -> lightning-cli pay, same as
must_gap_vectors MUST_GAP_AUTO_PAY); fallback = lnbits creds from the
cashu-cf checkout (never printed).

Usage:
  /usr/bin/python3 certify_signut.py \
    [--base https://signut.cashu.exchange] \
    [--creds /root/src/cashu-cf/test/live/lightning/credentials.json]
"""
import json, os, subprocess, sys, secrets, time, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "must-gap-vectors"))
import must_gap_vectors as mg
from coincurve import PrivateKey

os.environ.setdefault("MUST_GAP_AUTO_PAY", "1")


def out(amount, kid, malformed=False):
    s = secrets.token_hex(16)
    Y = mg.hash_to_curve(s)
    r = PrivateKey()
    B_ = mg.p_add(Y, r.public_key.format()).hex()
    if malformed:
        B_ = "zz" + B_[2:]
    return {"amount": amount, "B_": B_, "id": kid}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://signut.cashu.exchange")
    ap.add_argument("--creds", default="/root/src/cashu-cf/test/live/lightning/credentials.json")
    args = ap.parse_args()
    base = args.base
    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    def pay(bolt11):
        """Pay a signet invoice: CLN rail first, lnbits fallback."""
        if bolt11.startswith("lntb"):
            r = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                 "inr2.cashu.exchange",
                 "docker exec cln-swap-signet lightning-cli --network=signet pay " + bolt11],
                capture_output=True, timeout=90)
            if r.returncode == 0:
                return True, "cln rail"
        try:
            import requests
            creds = json.loads(Path(args.creds).read_text())["lnbits"]
            rr = requests.post(
                creds["endpoint"].rstrip("/") + "/api/v1/payments",
                headers={"X-Api-Key": creds["apiKey"], "Content-Type": "application/json"},
                json={"out": True, "bolt11": bolt11}, timeout=30)
            return rr.status_code in (200, 201), f"lnbits {rr.status_code}"
        except Exception as e:  # noqa: BLE001
            return False, f"both rails failed ({e.__class__.__name__})"

    ks = json.loads(mg.http("GET", f"{base}/v1/keys")[1])["keysets"]
    ks = [k for k in ks if k.get("unit") == "sat" and k.get("active")][0]
    kid = ks["id"]

    # S5: NUT-15 ad absent
    st, b = mg.http("GET", f"{base}/v1/info")
    nuts = json.loads(b).get("nuts", {})
    check("S5 no NUT-15 ad", "15" not in nuts, f"nut15={'present' if '15' in nuts else 'absent'}")

    # S4: restore-empty identity
    st, b = mg.http("POST", f"{base}/v1/restore", {"outputs": []})
    ok = st == 200 and json.loads(b) == {"outputs": [], "signatures": []}
    check("S4 restore-empty -> 200 empty", ok, f"{st} {b[:90]}")

    # S6: batch-fetch cap
    ids = [str(secrets.token_hex(16)) for _ in range(51)]
    st, b = mg.http("POST", f"{base}/v1/mint/quotes", {"ids": ids})
    check("S6 mint/quotes 51 ids -> 400/11014", st == 400 and "11014" in b, f"{st} {b[:90]}")

    # S1: check-path NUT-04 fields on an UNPAID quote (funding-free)
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 21, "unit": "sat"})
    q1 = json.loads(b)["quote"] if st == 200 else ""
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11/check", {"quotes": [q1]})
    ent = json.loads(b)[0] if st == 200 and b.startswith("[") else {}
    fields_unpaid = all(k in ent for k in ("amount_paid", "amount_issued", "updated_at"))
    check("S1 #118 check fields present (UNPAID)", fields_unpaid,
          f"{st} ap={ent.get('amount_paid')!r} ai={ent.get('amount_issued')!r} ua={ent.get('updated_at')!r} state={ent.get('state')!r}")

    # S7: malformed-B_ mint on the UNPAID quote (ordering identity)
    st, b = mg.http("POST", f"{base}/v1/mint/bolt11", {"quote": q1, "outputs": [out(21, kid, True)]})
    check("S7 malformed-B_ on UNPAID quote -> recorded (ordering identity)",
          st == 400, f"{st} {b[:110]}")

    # S11 + S2: fund a fresh quote, then re-check fields (PAID)
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 21, "unit": "sat"})
    q2 = json.loads(b)["quote"]
    inv = json.loads(b)["request"]
    pok, pdet = pay(inv)
    check("S11 payment rail pays 21-sat signut invoice", pok, pdet)
    paid = False
    for _ in range(45):
        st, b = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{q2}")
        if st == 200 and json.loads(b).get("state") == "PAID":
            paid = True
            break
        time.sleep(2)
    check("S11b quote reaches PAID", paid, f"state={json.loads(b).get('state') if st == 200 else st}")
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11/check", {"quotes": [q2]})
    ent = json.loads(b)[0] if st == 200 and b.startswith("[") else {}
    fields_paid = all(k in ent for k in ("amount_paid", "amount_issued", "updated_at"))
    check("S2 #118 check fields present (PAID)", fields_paid,
          f"{st} ap={ent.get('amount_paid')!r} ai={ent.get('amount_issued')!r} ua={ent.get('updated_at')!r} state={ent.get('state')!r}")

    # Full mint + S3/S10: GET accounting staleness + updated_at monotonicity
    ua_before = ent.get("updated_at")
    st, b = mg.http("POST", f"{base}/v1/mint/bolt11", {"quote": q2, "outputs": [out(21, kid)]})
    mint_ok = st == 200
    st, b = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{q2}")
    g = json.loads(b) if st == 200 else {}
    check("S3 GET accounting after full mint (fresh, not stale)",
          mint_ok and g.get("amount_issued") == 21 and isinstance(g.get("updated_at"), int)
          and (ua_before is None or g.get("updated_at") > ua_before),
          f"mint={mint_ok} ap={g.get('amount_paid')!r} ai={g.get('amount_issued')!r} ua={g.get('updated_at')!r} state={g.get('state')!r}")
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11/check", {"quotes": [q2]})
    ent2 = json.loads(b)[0] if st == 200 and b.startswith("[") else {}
    check("S10 updated_at bumps on issuance (check path)",
          ent2.get("updated_at") is not None and ua_before is not None
          and ent2.get("updated_at") > ua_before,
          f"before={ua_before!r} after={ent2.get('updated_at')!r} ai={ent2.get('amount_issued')!r}")

    # S8: swap legs via mg.mint_proofs (CLN rail funds its internal quote)
    p, e = mg.mint_proofs(base, ks, {64: [f"sgn-{secrets.token_hex(4)}"]})
    check("S8 mint_proofs (funded rail)", not e, e[:80] if e else "64 sat minted")
    if not e:
        payload = {"inputs": p, "outputs": [out(a, kid) for a in (32, 16, 8, 4, 2, 1)]}
        st, b = mg.http("POST", f"{base}/v1/swap", payload)
        check("S8a balanced swap 200", st == 200, f"{st} {b[:70] if st != 200 else 'ok'}")
        if st == 200:
            st2, b2 = mg.http("POST", f"{base}/v1/swap", payload)
            check("S8b swap replay cached 200 (byte-identical)", st2 == 200 and b2 == b,
                  f"{st2} identical={b2 == b}")

    # S9: self-payment detection (melt quote for the mint's own invoice)
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 21, "unit": "sat"})
    own_inv = json.loads(b)["request"] if st == 200 else ""
    st, b = mg.http("POST", f"{base}/v1/melt/quote/bolt11", {"request": own_inv, "unit": "sat"})
    fr = json.loads(b).get("fee_reserve") if st == 200 else None
    check("S9 self-payment fee_reserve == 1", st == 200 and fr == 1, f"{st} fee_reserve={fr!r}")

    fails = [r for r in results if not r[1]]
    print(f"\n{'=' * 60}\nSIGNUT BASELINE: {len(results) - len(fails)}/{len(results)} PASS"
          + (f" — RED legs: {', '.join(n for n, _, _ in fails)}" if fails else " — CLEAN"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
