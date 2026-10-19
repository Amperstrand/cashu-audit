"""Forged-proof melt probe: does testnut melt a proof that was never minted?

Fabricates {amount, secret, C: random-point, id: real keyset} and attempts
a melt. Reject = something verifies; 200 PAID = catastrophic (forged spend).
"""
import json
import os
import secrets
import time

import requests

MINT = "https://testnut.cashu.exchange"

# real active keyset id (from earlier probe run: 008e808b89acc141)
s = requests.Session()


def jpost(path, body):
    r = s.post(MINT + path, json=body, timeout=30)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text


# random VALID compressed point (y from x is unnecessary — any 02/03 + 32 bytes
# that the mint's parser accepts; a random one almost certainly isn't on-curve,
# which a signature verifier would reject on parse/verify)
keyset_id = "008e808b89acc141"
forged_secret = secrets.token_hex(32)
forged_C = "02" + secrets.token_hex(32)

# melt quote for 4 sats (self-loop invoice like the suite does)
mq = s.post(MINT + "/v1/mint/quote/bolt11", json={"amount": 4, "unit": "sat"}, timeout=30).json()
time.sleep(1)
q = s.post(MINT + "/v1/melt/quote/bolt11", json={"request": mq["request"], "unit": "sat"}, timeout=30).json()
print("melt quote:", json.dumps(q)[:200])

body = {
    "quote": q["quote"],
    "inputs": [
        {"amount": 8, "secret": forged_secret, "C": forged_C, "id": keyset_id}
    ],
    "outputs": [],
}
code, resp = jpost("/v1/melt", body)
print(f"\nFORGED MELT -> HTTP {code}")
print(json.dumps(resp, indent=2)[:800] if not isinstance(resp, str) else resp[:800])
print("\nVERDICT:", "CATASTROPHIC: forged proof melted PAID" if code == 200 and isinstance(resp, dict) and resp.get("state") == "PAID" else "rejected (some verification holds)")
