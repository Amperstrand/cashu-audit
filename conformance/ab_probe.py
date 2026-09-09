#!/usr/bin/env python3
"""Frozen-hypothesis A/B probe: redemption rules across nutshell/cdk versions.

Derivations tested per arm (amount 64, canonical secret = 64-char hex):
  canonical : B_ = H_modern(utf8(secret))            + rG   [NUT-00 spec]
  algolegacy: B_ = H_deprecated(utf8(secret))         + rG   [pre-0.15.1 algorithm]
  entraptrap : B_ = H_modern(hex_decode(secret))      + rG   [entropy-hashing trap]

FROZEN PREDICTIONS (written before running; from source archaeology):
  ns015  (0.15.0, deprecated-primary verify + modern fallback): ACCEPT algolegacy(primary), ACCEPT canonical(fallback), REJECT trap
  ns0182 (0.18.2, modern-primary + deprecated fallback):        ACCEPT canonical(primary), ACCEPT algolegacy(fallback), REJECT trap
  cdk0176 / cdk0180 (modern only):                              ACCEPT canonical, REJECT algolegacy, REJECT trap
"""
import hashlib, json, os, sys, time, urllib.request

from coincurve import PrivateKey, PublicKey
sys.path.insert(0, "/tmp")
from cf_crypto import pubkey_add, pubkey_mul, pubkey_neg, hash_to_curve as h_modern_c, step3_alice

DOMSEP = b"Secp256k1_HashToCurve_Cashu_"

def h_modern(msg: bytes) -> PublicKey:
    h = hashlib.sha256(DOMSEP + msg).digest()
    for counter in range(2**16):
        try:
            return PublicKey(b"\x02" + hashlib.sha256(h + counter.to_bytes(4, "little")).digest())
        except ValueError:
            continue
    raise RuntimeError("no point")

def h_deprecated(msg: bytes) -> PublicKey:
    m = msg
    while True:
        h = hashlib.sha256(m).digest()
        try:
            return PublicKey(b"\x02" + h)
        except ValueError:
            m = h

def api(base, path, body=None):
    req = urllib.request.Request(base + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"},
        method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read().decode())
        except Exception: body = None
        return e.code, body

def get_active_keyset(base):
    st, d = api(base, "/v1/keys")
    cands = [ks for ks in d["keysets"] if ks.get("unit") == "sat" and ks.get("active", True)]
    if not cands:
        cands = [ks for ks in d["keysets"] if ks.get("unit") == "sat"]
    ks = cands[0]
    st2, d2 = api(base, "/v1/keysets")
    fee_ppk = 0
    for k in d2["keysets"]:
        if k["id"] == ks["id"]:
            fee_ppk = k.get("input_fee_ppk") or 0
    return ks["id"], ks["keys"], fee_ppk

def probe(base, derivation):
    ks_id, keys, fee_ppk = get_active_keyset(base)
    A = PublicKey(bytes.fromhex(keys["64"]))
    secret_bytes = os.urandom(32)
    secret = secret_bytes.hex()
    msg = {"canonical": lambda: h_modern(secret.encode()),
           "algolegacy": lambda: h_deprecated(secret.encode()),
           "trap": lambda: h_modern(secret_bytes)}[derivation]()
    r = PrivateKey()
    B_ = pubkey_add(msg, r.public_key)
    q = api(base, "/v1/mint/quote/bolt11", {"amount": 64, "unit": "sat"})[1]
    sigs = None
    for _ in range(40):
        st, d = api(base, "/v1/mint/bolt11", {"quote": q["quote"], "outputs": [{"amount": 64, "id": ks_id, "B_": B_.format().hex()}]})
        if st == 200:
            sigs = d["signatures"]; break
        time.sleep(1)
    if sigs is None:
        return "MINT_FAILED"
    C_ = PublicKey(bytes.fromhex(sigs[0]["C_"]))
    C = step3_alice(C_, r, A)
    # swap with canonical outputs (powers-of-2 decomposition of amount minus fee)
    total = 64 - (fee_ppk + 999) // 1000
    outs = []
    rem = total
    p = 1
    while rem > 0:
        if rem & 1:
            Yn = h_modern(os.urandom(32).hex().encode())
            rn = PrivateKey()
            outs.append({"amount": p, "id": ks_id, "B_": pubkey_add(Yn, rn.public_key).format().hex()})
        rem >>= 1
        p <<= 1
    st, d = api(base, "/v1/swap", {"inputs": [{"amount": 64, "secret": secret, "C": C.format().hex(), "id": ks_id}],
                                    "outputs": outs})
    return "ACCEPT" if st == 200 else f"REJECT({st})"

ARMS = {"ns015": "http://127.0.0.1:3338", "ns0182": "http://127.0.0.1:3339",
        "cdk0176": "http://127.0.0.1:8086", "cdk0180": "http://127.0.0.1:8087"}
results = {}
for name, base in ARMS.items():
    st, info = api(base, "/v1/info")
    ident = info.get("version", "?")
    results[name] = {"identity": ident}
    for deriv in ["canonical", "algolegacy", "trap"]:
        results[name][deriv] = probe(base, deriv)
        print(f"{name} ({ident}) {deriv}: {results[name][deriv]}", flush=True)
json.dump(results, open("/tmp/ab-results.json", "w"), indent=1)
print("\nFROZEN PREDICTION CHECK:")
PRED = {"ns015": {"canonical": "ACCEPT", "algolegacy": "ACCEPT", "trap": "REJECT"},
        "ns0182": {"canonical": "ACCEPT", "algolegacy": "ACCEPT", "trap": "REJECT"},
        "cdk0176": {"canonical": "ACCEPT", "algolegacy": "REJECT", "trap": "REJECT"},
        "cdk0180": {"canonical": "ACCEPT", "algolegacy": "REJECT", "trap": "REJECT"}}
ok = True
for arm, preds in PRED.items():
    for d, want in preds.items():
        got = results[arm][d]
        match = got.startswith(want[:6])
        if not match: ok = False
        print(f"  {arm}/{d}: predicted {want}, got {got} {'OK' if match else 'MISMATCH'}")
print("HYPOTHESIS:", "CONFIRMED" if ok else "PARTIAL/REFUTED — analyze")
