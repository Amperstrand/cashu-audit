#!/usr/bin/env python3
"""SIG_ALL melt-path vectors (11.md:153-161).

Message for melt: concat(inputs: secret||C) || quote_id || concat(outputs: amount||B_)
Witness on first input per SIG_ALL. Controls included.

M1: plain (no condition) melt -> expect ACCEPT
M2: single-input SIG_ALL melt, spec message -> expect ACCEPT (map)
"""
import hashlib, json, secrets, sys, time, urllib.request, urllib.error
from coincurve import PrivateKey, PublicKey

DST = b"Secp256k1_HashToCurve_Cashu_"

def sha256(b): return hashlib.sha256(b).digest()
def p_add(p1, p2): return PublicKey(p1).combine([PublicKey(p2)]).format()
def p_neg(p): return ({b"\x02": b"\x03", b"\x03": b"\x02"}[p[:1]]) + p[1:]
def p_sub(p1, p2): return p_add(p1, p_neg(p2))
def p_mul(pt, sc): return PublicKey(pt).multiply(sc).format()
def hash_to_curve(m):
    h = sha256(DST + m.encode())
    for c in range(2**16):
        try: return PublicKey(b"\x02" + sha256(h + c.to_bytes(4, "little"))).format()
        except Exception: pass
    raise ValueError

def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r: return r.status, r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:200]

def sigall_melt_msg(proofs, outputs, quote_id):
    # spec 11.md:157: secret||C (inputs) || amount||B_ (outputs) || quote_id
    m = "".join(p["secret"] + p["C"] for p in proofs)
    m += "".join(str(o["amount"]) + o["B_"] for o in outputs)
    m += quote_id
    return m

def main():
    base = sys.argv[1]
    skA = PrivateKey()
    pkA = skA.public_key.format().hex()
    st, body = http("GET", f"{base}/v1/keys")
    ks = next(k for k in json.loads(body)["keysets"] if k.get("unit") == "sat" and "2" in k["keys"])

    def mint_proofs(secrets_by_amount):
        total = sum(a * len(s) for a, s in secrets_by_amount.items())
        st, b = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": total, "unit": "sat"})
        if st != 200: return None, f"quote {st}: {b[:120]}"
        q = json.loads(b)
        quote_id = q["quote"]
        for _ in range(20):
            st, b = http("GET", f"{base}/v1/mint/quote/bolt11/{quote_id}")
            if st == 200 and json.loads(b).get("state") == "PAID": break
            time.sleep(1)
        else: return None, "never PAID"
        outs, blind = [], []
        for amt, secs in secrets_by_amount.items():
            for s in secs:
                Y = hash_to_curve(s); r = PrivateKey()
                outs.append({"amount": amt, "B_": p_add(Y, r.public_key.format()).hex(), "id": ks["id"]})
                blind.append((amt, s, r))
        st, b = http("POST", f"{base}/v1/mint/bolt11", {"quote": quote_id, "outputs": outs})
        if st != 200: return None, f"mint {st}: {b[:150]}"
        sigs = json.loads(b)["signatures"]
        proofs = []
        for (amt, s, r), sig in zip(blind, sigs):
            C = p_sub(bytes.fromhex(sig["C_"]), p_mul(bytes.fromhex(ks["keys"][str(amt)]), r.secret))
            proofs.append({"amount": amt, "id": ks["id"], "secret": s, "C": C.hex()})
        return proofs, q.get("request", "")

    def fresh_output(amount):
        s = secrets.token_hex(16)
        Y = hash_to_curve(s); r = PrivateKey()
        return {"amount": amount, "B_": p_add(Y, r.public_key.format()).hex(), "id": ks["id"]}

    def melt(proofs, witness=None, extra_note=""):
        total = sum(p["amount"] for p in proofs)
        # get a fake invoice from a mint quote (FakeWallet), then melt-quote it
        st, b = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 1, "unit": "sat"})
        if st != 200: return {"status": -1, "body": f"inv-quote {st}: {b[:100]}"}
        invoice = json.loads(b).get("request", "")
        st, b = http("POST", f"{base}/v1/melt/quote/bolt11", {"request": invoice, "unit": "sat"})
        if st != 200: return {"status": -1, "body": f"melt-quote {st}: {b[:120]}"}
        mq = json.loads(b)
        qid, amt = mq["quote"], mq.get("amount", 1)
        out = fresh_output(total - amt) if total - amt > 0 else []
        outs = [out] if out else []
        inputs = [dict(p) for p in proofs]
        if witness is not None:
            inputs[0]["witness"] = witness
        st, b = http("POST", f"{base}/v1/melt/bolt11", {"quote": qid, "inputs": inputs, "outputs": outs})
        if st == 400 and "expected_fee" in b:
            import re as _re
            m = _re.search(r"expected_fee: (\d+)", b)
            fee = int(m.group(1))
            rem = total - amt - fee
            outs = [fresh_output(rem)] if rem > 0 else []
            if witness is not None:
                msg = sigall_melt_msg(proofs, outs, qid)
                sig = skA2.sign_schnorr(sha256(msg.encode()), None) if False else None
            st, b = http("POST", f"{base}/v1/melt/bolt11", {"quote": qid, "inputs": inputs, "outputs": outs})
        return {"status": st, "body": b[:200], "amount": amt, "note": extra_note, "sig_used": witness is not None}

    # M1: plain melt
    pr, inv = mint_proofs({8: [secrets.token_hex(16)]})
    if not pr: print("M1:", {"status": -1, "body": inv}); return
    r1 = melt(pr)
    print("M1 plain-melt:", json.dumps(r1))

    # M2: SIG_ALL single-input melt, spec message on first (only) input
    s = json.dumps(["P2PK", {"nonce": secrets.token_hex(16), "data": pkA, "tags": [["sigflag", "SIG_ALL"]]}], separators=(",", ":"))
    pr2, _ = mint_proofs({8: [s]})
    if not pr2: print("M2:", {"status": -1, "body": _}); return
    sig = skA.sign_schnorr(sha256(s.encode()), None)  # placeholder; real sig needs quote, built inside melt
    # NOTE: message depends on quote id + outputs -> we must sign INSIDE melt; do a variant:
    # build manually
    total = sum(p["amount"] for p in pr2)
    st, b = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 1, "unit": "sat"})
    invoice = json.loads(b).get("request", "")
    st, b = http("POST", f"{base}/v1/melt/quote/bolt11", {"request": invoice, "unit": "sat"})
    mq = json.loads(b); qid, amt = mq["quote"], mq.get("amount", 1)
    out = fresh_output(total - amt) if total - amt > 0 else None
    outs = [out] if out else []
    def m2_post(outs):
        msg = sigall_melt_msg(pr2, outs, qid)
        sig2 = skA.sign_schnorr(sha256(msg.encode()), None)
        pr2[0]["witness"] = json.dumps({"signatures": [sig2.hex()]})
        return http("POST", f"{base}/v1/melt/bolt11", {"quote": qid, "inputs": pr2, "outputs": outs})
    st, b = m2_post(outs)
    if st == 400 and "expected_fee" in b:
        import re as _re
        fee = int(_re.search(r"expected_fee: (\d+)", b).group(1))
        rem = total - amt - fee
        st, b = m2_post([fresh_output(rem)] if rem > 0 else [])
    print("M2 sigall-melt:", json.dumps({"status": st, "body": b[:200], "amount": amt}))

    # M3: MULTI-input SIG_ALL melt (the case that breaks swaps on nutshell)
    s1 = json.dumps(["P2PK", {"nonce": secrets.token_hex(16), "data": pkA, "tags": [["sigflag", "SIG_ALL"]]}], separators=(",", ":"))
    s2 = json.dumps(["P2PK", {"nonce": secrets.token_hex(16), "data": pkA, "tags": [["sigflag", "SIG_ALL"]]}], separators=(",", ":"))
    pr3, _e = mint_proofs({4: [s1, s2]})
    if not pr3:
        print("M3 multi-sigall-melt:", json.dumps({"status": -1, "body": _e}))
    else:
        total3 = sum(p["amount"] for p in pr3)
        st, b = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 1, "unit": "sat"})
        invoice = json.loads(b).get("request", "")
        st, b = http("POST", f"{base}/v1/melt/quote/bolt11", {"request": invoice, "unit": "sat"})
        mq = json.loads(b); qid3, amt3 = mq["quote"], mq.get("amount", 1)
        def m3_post(outs):
            msg = sigall_melt_msg(pr3, outs, qid3)
            sig3 = skA.sign_schnorr(sha256(msg.encode()), None)
            pr3[0]["witness"] = json.dumps({"signatures": [sig3.hex()]})
            return http("POST", f"{base}/v1/melt/bolt11", {"quote": qid3, "inputs": pr3, "outputs": outs})
        fee0 = mq.get("fee_reserve", 0)
        rem3 = total3 - amt3 - fee0
        st, b = m3_post([fresh_output(rem3)] if rem3 > 0 else [])
        if st == 400 and "expected_fee" in b:
            import re as _re
            fee = int(_re.search(r"expected_fee: (\d+)", b).group(1))
            rem3 = total3 - amt3 - fee
            st, b = m3_post([fresh_output(rem3)] if rem3 > 0 else [])
        print("M3 multi-sigall-melt:", json.dumps({"status": st, "body": b[:200]}))

main()
