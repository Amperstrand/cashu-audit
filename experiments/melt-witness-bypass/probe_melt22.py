"""Reproduce scenario 22 (melt_p2pk_unsigned_fails) with full captures.

Discriminates: melt-pathway witness bypass (real finding) vs self-loop
quote confound (quote already PAID before the melt attempt).
"""
import json
import sys
import time

import requests

from conformance.builder import ProofBuilder, build_p2pk_secret
from conformance.client import MintClient
from conformance.crypto import KeyPair, generate_secret

MINT = sys.argv[1] if len(sys.argv) > 1 else "https://testnut.cashu.exchange"

mint = MintClient(MINT, timeout=30)
builder = ProofBuilder(mint)
key = KeyPair.generate()

print("=== 1. mint regular proofs (scenario: _swap_for_condition) ===")
regular = builder.mint_proofs(8)
total = sum(p.amount for p in regular)
swap_amount = total - builder.calc_fee(len(regular))
print(f"minted {[p.amount for p in regular]} total={total} swap_after_fee={swap_amount}")

print("=== 2. swap to P2PK-conditioned secrets ===")
proofs = builder.swap_to_p2pk(regular, lambda: build_p2pk_secret(key.pub_hex), swap_amount)
for p in proofs:
    print(f"  proof amt={p.amount} secret={p.secret}")
print(f"  pubkey (witness key we withhold): {key.pub_hex}")

print("=== 3. melt quote via the suite's self-loop helper ===")
mq = mint.mint_quote(4)
print(f"  mint_quote(4) -> {json.dumps(mq)[:300]}")
invoice = mq.get("request", "lnbc1000n1p")
q = mint.melt_quote(invoice)
print(f"  melt_quote -> {json.dumps(q)[:500]}")
qid = q["quote"]

print("=== 4. quote state BEFORE the melt (confound check) ===")
r = requests.get(f"{MINT}/v1/melt/quote/{qid}", timeout=30)
print(f"  GET /v1/melt/quote/{qid} -> {r.status_code} {r.text[:400]}")

print("=== 5. MELT with NO witness (the assertion under test) ===")
inputs = [p.to_dict() for p in proofs]
change_total = max(0, sum(p.amount for p in proofs) - len(proofs) - 1)
change = builder.create_outputs(change_total, generate_secret) if change_total >= 1 else []
outputs = builder.outputs_to_api(change) if change else None
code, body = mint.melt(qid, inputs, outputs)
print(f"  melt -> HTTP {code}")
print(f"  body -> {json.dumps(body, indent=2)[:1200] if not isinstance(body, str) else body[:1200]}")

verdict = "BYPASS: unsigned P2PK witness melted PAID" if code == 200 and isinstance(body, dict) and body.get("state") == "PAID" else "no bypass observed"
print(f"=== VERDICT: {verdict} ===")
