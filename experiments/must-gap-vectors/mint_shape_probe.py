"""Isolate why cdk 0.17.0 rejects the wallet's mint: one fresh quote per shape."""
import json, secrets, sys, urllib.request, urllib.error, hashlib
from coincurve import PrivateKey, PublicKey
DST = b"Secp256k1_HashToCurve_Cashu_"
def sha256(b): return hashlib.sha256(b).digest()
def p_add(p1, p2): return PublicKey(p1).combine([PublicKey(p2)]).format()
def hash_to_curve(m):
    h = sha256(DST + m.encode())
    for c in range(2**16):
        try: return PublicKey(b"\x02" + sha256(h + c.to_bytes(4, "little"))).format()
        except Exception: pass

def http(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r: return r.status, r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:150]

base = sys.argv[1]
_, kb = http("GET", f"{base}/v1/keys")
ks = next(k for k in json.loads(kb)["keysets"] if k.get("unit") == "sat" and "1" in k["keys"])

def mint_shape(total, amounts, poll=True):
    st, b = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": total, "unit": "sat"})
    q = json.loads(b)["quote"]
    import time
    if poll:
        for _ in range(15):
            st, qb = http("GET", f"{base}/v1/mint/quote/bolt11/{q}")
            if json.loads(qb).get("state") == "PAID": break
            time.sleep(1)
    else:
        time.sleep(3)  # like the wallet: no poll
    outs = [{"amount": a, "id": ks["id"], "B_": p_add(hash_to_curve(secrets.token_hex(16)), PrivateKey().public_key.format()).hex()} for a in amounts]
    return http("POST", f"{base}/v1/mint/bolt11", {"quote": q, "outputs": outs})

for name, total, amounts in [
    ("1x2-poll", 2, [2]),
    ("8x1-nopoll", 8, [1]*8),
    ("1x2-nopoll", 2, [2]),
]:
    st, b = mint_shape(total, amounts, poll=("nopoll" not in name))
    print(f"{name}: {st} {b[:130]}")

# ---- NUT-20 probe: quote WITH pubkey + properly signed mint request ----
def nut20_msg(quote_id, outputs):
    from hashlib import sha256 as _sh
    def itmb(v): return b"" if v == 0 else v.to_bytes((v.bit_length()+7)//8, "big")
    msg = b"Cashu_MintQuoteSig_v1"
    qb = quote_id.encode()
    msg += len(qb).to_bytes(4, "big") + qb
    for o in outputs:
        ab = itmb(o["amount"]); bb = bytes.fromhex(o["B_"])
        msg += len(ab).to_bytes(4, "big") + ab
        msg += len(bb).to_bytes(4, "big") + bb
    return _sh(msg).digest()

sk = PrivateKey(); pk = sk.public_key.format().hex()
st, b = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 2, "unit": "sat", "pubkey": pk})
q = json.loads(b)["quote"]
import time
for _ in range(15):
    st, qb = http("GET", f"{base}/v1/mint/quote/bolt11/{q}")
    if json.loads(qb).get("state") == "PAID": break
    time.sleep(1)
outs = [{"amount": 2, "id": ks["id"], "B_": p_add(hash_to_curve(secrets.token_hex(16)), PrivateKey().public_key.format()).hex()} for _ in range(1)]
sig = sk.sign_schnorr(nut20_msg(q, outs), None).hex()
st, b = http("POST", f"{base}/v1/mint/bolt11", {"quote": q, "outputs": outs, "signature": sig})
print(f"nut20-pubkey-quote+validsig: {st} {b[:130]}")

# fresh quote, valid sig but quote created WITHOUT pubkey
st, b = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 2, "unit": "sat"})
q2 = json.loads(b)["quote"]
for _ in range(15):
    st, qb = http("GET", f"{base}/v1/mint/quote/bolt11/{q2}")
    if json.loads(qb).get("state") == "PAID": break
    time.sleep(1)
outs2 = [{"amount": 2, "id": ks["id"], "B_": p_add(hash_to_curve(secrets.token_hex(16)), PrivateKey().public_key.format()).hex()}]
sig2 = sk.sign_schnorr(nut20_msg(q2, outs2), None).hex()
st, b = http("POST", f"{base}/v1/mint/bolt11", {"quote": q2, "outputs": outs2, "signature": sig2})
print(f"nut20-nopubkey-quote+validsig: {st} {b[:130]}")

# legacy scheme (construct_message_legacy) on cdk
st, b = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 2, "unit": "sat", "pubkey": pk})
q3 = json.loads(b)["quote"]
for _ in range(15):
    st, qb = http("GET", f"{base}/v1/mint/quote/bolt11/{q3}")
    if json.loads(qb).get("state") == "PAID": break
    time.sleep(1)
outs3 = [{"amount": 2, "id": ks["id"], "B_": p_add(hash_to_curve(secrets.token_hex(16)), PrivateKey().public_key.format()).hex()}]
import hashlib as _h2
legacy = _h2.sha256(q3.encode() + b"".join(o["B_"].encode() for o in outs3)).digest()
sig3 = sk.sign_schnorr(legacy, None).hex()
st, b = http("POST", f"{base}/v1/mint/bolt11", {"quote": q3, "outputs": outs3, "signature": sig3})
print(f"nut20-LEGACY-scheme: {st} {b[:130]}")
