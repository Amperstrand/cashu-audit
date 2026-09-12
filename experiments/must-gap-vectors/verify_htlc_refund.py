#!/usr/bin/env python3
"""Single-vector reproduction: HTLC refund spend with the wallet-natural
witness shape (signature-only, preimage omitted).

Self-contained: coincurve + stdlib. No repo, no battery, no framework.

Flow:
  1. mint quote (fakewallet mints settle on GET)
  2. mint a proof whose secret is an HTLC lock with a PAST locktime
     and a refund key we hold
  3. attempt the refund swap with the witness wallets actually emit:
     {"signatures":["<schnorr sig over the secret>"]}
  4. print the HTTP result

Expected:
  stock cdk 0.17.x/0.18.x/main : 400 {"code":50000,"detail":"Secret is not a HTLC secret"}
  Amperstrand/cdk htlc-refund-witness : 200
  nutshell mints >=0.19        : 200

Usage: python3 verify_htlc_refund.py <mint_url>
"""
import hashlib
import json
import secrets
import sys
import time
import urllib.error
import urllib.request

from coincurve import PrivateKey, PublicKey

DST = b"Secp256k1_HashToCurve_Cashu_"


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def p_add(p1: bytes, p2: bytes) -> bytes:
    return PublicKey(p1).combine([PublicKey(p2)]).format()


def p_neg(p: bytes) -> bytes:
    return ({b"\x02": b"\x03", b"\x03": b"\x02"}[p[:1]]) + p[1:]


def p_sub(p1: bytes, p2: bytes) -> bytes:
    return p_add(p1, p_neg(p2))


def p_mul(point: bytes, scalar: bytes) -> bytes:
    return PublicKey(point).multiply(scalar).format()


def hash_to_curve(msg: str) -> bytes:
    h = sha256(DST + msg.encode())
    for ctr in range(2**16):
        try:
            return PublicKey(b"\x02" + sha256(h + ctr.to_bytes(4, "little"))).format()
        except Exception:
            continue
    raise ValueError


def http(method: str, url: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main() -> int:
    base = sys.argv[1].rstrip("/")

    st, body = http("GET", f"{base}/v1/info")
    if st != 200:
        print(f"mint unreachable: {st} {body[:100]}")
        return 2
    print(f"mint: {json.loads(body).get('version', '?')}")

    st, body = http("GET", f"{base}/v1/keys")
    ks = next(k for k in json.loads(body)["keysets"]
              if k.get("unit") == "sat" and "2" in k.get("keys", {}))

    # refund keypair (ours)
    sk_r = PrivateKey()
    pk_r = sk_r.public_key.format().hex()

    # HTLC secret: hash-lock to a dummy hash, PAST locktime, refund key = ours
    lock_hash = secrets.token_bytes(32).hex()
    t_past = int(time.time()) - 1000
    secret = json.dumps(["HTLC", {
        "nonce": secrets.token_hex(16),
        "data": lock_hash,
        "tags": [["locktime", str(t_past)], ["refund", pk_r]],
    }], separators=(",", ":"))

    # mint a 2-sat proof with that secret
    st, body = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 2, "unit": "sat"})
    if st != 200:
        print(f"quote failed: {st} {body[:120]}")
        return 2
    quote_id = json.loads(body)["quote"]
    for _ in range(20):
        st, body = http("GET", f"{base}/v1/mint/quote/bolt11/{quote_id}")
        if st == 200 and json.loads(body).get("state") == "PAID":
            break
        time.sleep(1)
    else:
        print("quote never PAID (non-fakewallet mint? this repro needs a fakewallet mint)")
        return 2

    Y = hash_to_curve(secret)
    r = PrivateKey()
    B_ = p_add(Y, r.public_key.format())
    st, body = http("POST", f"{base}/v1/mint/bolt11",
                    {"quote": quote_id, "outputs": [{"amount": 2, "B_": B_.hex(), "id": ks["id"]}]})
    if st != 200:
        print(f"blind mint failed: {st} {body[:150]}")
        return 2
    C_ = bytes.fromhex(json.loads(body)["signatures"][0]["C_"])
    C = p_sub(C_, p_mul(bytes.fromhex(ks["keys"]["2"]), r.secret))
    proof = {"amount": 2, "id": ks["id"], "secret": secret, "C": C.hex()}

    # the wallet-natural refund witness: signature only, preimage omitted
    sig = sk_r.sign_schnorr(sha256(secret.encode()), None)
    proof["witness"] = json.dumps({"signatures": [sig.hex()]})

    # fresh output; handle per-proof fees if the mint charges them
    out_secret = secrets.token_hex(16)
    Yo = hash_to_curve(out_secret)
    ro = PrivateKey()
    Bo = p_add(Yo, ro.public_key.format())

    def swap(outputs):
        return http("POST", f"{base}/v1/swap", {"inputs": [proof], "outputs": outputs})

    st, body = swap([{"amount": 2, "B_": Bo.hex(), "id": ks["id"]}])
    if st == 400 and "fees" in body:
        import re
        m = re.search(r"required \((\d+)\)", body) or re.search(r"fees \((\d+)\)", body)
        if m and 2 - int(m.group(1)) > 0:
            st, body = swap([{"amount": 2 - int(m.group(1)), "B_": Bo.hex(), "id": ks["id"]}])

    print(f"\nwitness sent: {proof['witness'][:90]}...")
    print(f"refund swap:  {st} {body[:160]}")
    print("\nVERDICT:", "ACCEPTED (fix present / tolerant mint)" if st == 200
          else f"REJECTED (stock cdk behavior)" if st == 400 else "UNEXPECTED")
    return 0 if st == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
