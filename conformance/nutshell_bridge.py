#!/usr/bin/env python3
"""Bridge to nutshell's real crypto functions for the interop fuzz lab.

Reads JSON-RPC requests (one per line) on stdin, writes JSON responses on stdout.
Runs nutshell from source (PYTHONPATH=/tmp/nutshell-src) using the cashu-audit venv.

Protocol: {"id": N, "method": "...", "params": {...}} → {"id": N, "result": ...}
"""
import json
import sys
import os

from cashu.core.crypto.b_dhke import step1_alice, step2_bob, step3_alice
from cashu.core.crypto.secp import PrivateKey, PublicKey

# Nutshell uses coincurve; serialize points as compressed hex for the wire
def priv_to_hex(priv):
    return priv.secret.hex() if hasattr(priv, 'secret') else bytes(priv).hex()

def pub_to_hex(pub):
    return pub.format(compressed=True).hex()

def hex_to_pub(hex_str):
    return PublicKey(bytes.fromhex(hex_str))

def hex_to_priv(hex_str):
    return PrivateKey(bytes.fromhex(hex_str))


def handle(req):
    method = req["method"]
    p = req.get("params", {})
    rid = req["id"]

    if method == "ping":
        return {"id": rid, "result": "pong"}

    if method == "bdhke_roundtrip":
        # Full round-trip: secret → blind → sign → unblind → verify
        # Inputs: secret_msg (utf8 string), a_hex (mint private key scalar)
        secret_msg = p["secret_msg"]
        a = PrivateKey(bytes.fromhex(p["a_hex"]))

        B_, r = step1_alice(secret_msg)
        C_, e, s = step2_bob(B_, a)
        C = step3_alice(C_, r, a.public_key)

        return {"id": rid, "result": {
            "B_": pub_to_hex(B_),
            "r": priv_to_hex(r),
            "C_": pub_to_hex(C_),
            "C": pub_to_hex(C),
            "A": pub_to_hex(a.public_key),
            "e": priv_to_hex(e) if e else None,
            "s": priv_to_hex(s) if s else None,
        }}

    if method == "bdhke_with_inputs":
        # Deterministic: given secret_msg + r_hex + a_hex, produce all intermediate values
        from cashu.core.crypto.b_dhke import hash_to_curve
        secret_msg = p["secret_msg"]
        r = PrivateKey(bytes.fromhex(p["r_hex"]))
        a = PrivateKey(bytes.fromhex(p["a_hex"]))

        Y = hash_to_curve(secret_msg.encode("utf-8"))
        B_ = Y + r.public_key
        C_ = B_ * a
        C = C_ - a.public_key * r

        return {"id": rid, "result": {
            "Y": pub_to_hex(Y),
            "B_": pub_to_hex(B_),
            "C_": pub_to_hex(C_),
            "C": pub_to_hex(C),
        }}

    if method == "hash_to_curve":
        from cashu.core.crypto.b_dhke import hash_to_curve
        msg = p["message"]
        Y = hash_to_curve(msg.encode("utf-8"))
        return {"id": rid, "result": {"Y": pub_to_hex(Y)}}

    if method == "amount_split":
        from cashu.core.split import amount_split
        amount = p["amount"]
        result = amount_split(amount)
        return {"id": rid, "result": {"amounts": result}}

    if method == "verify":
        from cashu.core.crypto.b_dhke import verify
        a = PrivateKey(bytes.fromhex(p["a_hex"]))
        C = PublicKey(bytes.fromhex(p["C_hex"]))
        secret_msg = p["secret_msg"]
        valid = verify(a, C, secret_msg)
        return {"id": rid, "result": {"valid": valid}}

    if method == "parse_secret":
        from cashu.core.secret import Secret
        secret_str = p["secret"]
        try:
            s = Secret.deserialize(secret_str)
            kind = s.kind.value if s.kind else None
            tags = s.tags.root if s.tags else []
            return {"id": rid, "result": {
                "kind": kind,
                "tags": tags,
                "data": s.data if hasattr(s, 'data') else None,
            }}
        except Exception as e:
            return {"id": rid, "result": {"parse_error": str(e)}}

    if method == "hash_e":
        from cashu.core.crypto.b_dhke import hash_e
        pubkeys = [PublicKey(bytes.fromhex(h)) for h in p["pubkeys_hex"]]
        e = hash_e(*pubkeys)
        return {"id": rid, "result": {"e": e.hex()}}

    if method == "dleq_components":
        from cashu.core.crypto.b_dhke import hash_to_curve, hash_e
        from cashu.core.crypto.b_dhke import derive_dleq_nonce
        secret_msg = p["secret_msg"]
        r_hex = p["r_hex"]
        a_hex = p["a_hex"]

        r = PrivateKey(bytes.fromhex(r_hex))
        a = PrivateKey(bytes.fromhex(a_hex))

        Y = hash_to_curve(secret_msg.encode("utf-8"))
        B_ = Y + r.public_key
        C_ = B_ * a
        A = a.public_key

        # DLEQ nonce (deterministic per NUT-12)
        p_nonce = derive_dleq_nonce(a, A, B_, C_)

        R1 = p_nonce.public_key
        R2 = B_ * p_nonce
        e = hash_e(R1, R2, A, C_)
        s = p_nonce.add(bytes.fromhex(a.multiply(bytes(e)).to_hex()))

        return {"id": rid, "result": {
            "B_": pub_to_hex(B_),
            "C_": pub_to_hex(C_),
            "A": pub_to_hex(A),
            "R1": pub_to_hex(R1),
            "R2": pub_to_hex(R2),
            "e": e.hex(),
            "s": s.to_hex() if hasattr(s, 'to_hex') else priv_to_hex(s),
            "nonce": priv_to_hex(p_nonce),
        }}

    return {"id": rid, "error": f"unknown method: {method}"}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle(req)
        except Exception as e:
            resp = {"id": req.get("id", -1), "error": str(e)}
        print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
