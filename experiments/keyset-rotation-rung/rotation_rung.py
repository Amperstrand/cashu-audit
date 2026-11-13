"""cashu-cf keyset-rotation rung (tollgate #818 scenario; NUT-TRACKER queue #1).

Mint under keyset A -> admin-rotate (sat, input_fee_ppk=40) -> verify:
old-proof spendability (swap + melt), issuance gating under the retired
keyset, keyset listing states, checkstate, and error identities.

Run (against a local boot with ENVIRONMENT=signut + admin overrides):
  PYTHONPATH=../../conformance python3 rotation_rung.py http://127.0.0.1:PORT <ADMIN_KEY>
"""
import json
import sys

import requests

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret

MINT = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8796"
ADMIN_KEY = sys.argv[2] if len(sys.argv) > 2 else "rot-rung-admin"
ADMIN_HDR = {"Authorization": f"Bearer {ADMIN_KEY}"}

mint = MintClient(MINT, timeout=30)
builder = ProofBuilder(mint)
out = {"target": MINT}

def record(step, **kv):
    out[step] = kv
    print(f"[{step}] " + json.dumps(kv)[:400])

# --- P1: pre-rotation state + mint under A ---
keysets_before = requests.get(f"{MINT}/v1/keysets", timeout=30).json()
active_before = [k["id"] for k in keysets_before["keysets"] if k.get("active")]
A = active_before[0]
proofs_A_swap = builder.mint_proofs(8)
proofs_A_melt = builder.mint_proofs(8)
record("P1_pre", active=A, minted_swap=8, minted_melt=8,
       keyset_of_proofs=proofs_A_swap[0].id,
       on_default_keyset=(proofs_A_swap[0].id == A))

# --- P2: admin rotate (sat, input_fee_ppk=40) ---
r = requests.post(f"{MINT}/v1/admin/keysets/rotate", headers=ADMIN_HDR,
                  json={"unit": "sat", "input_fee_ppk": 40}, timeout=30)
try:
    rot = r.json()
except Exception:
    rot = {"raw": r.text[:300]}
record("P2_rotate", http=r.status_code, body=rot)
B = rot.get("id")

# --- P3: keyset listing states ---
keysets_after = requests.get(f"{MINT}/v1/keysets", timeout=30).json()
states = {k["id"]: (k.get("active"), k.get("unit"), k.get("input_fee_ppk")) for k in keysets_after["keysets"]}
record("P3_keysets", states=states, A_listed=A in states, B_listed=(B in states) if B else None,
       A_active=states.get(A, (None,))[0], B_active=states.get(B, (None,))[0] if B else None)

# --- P4: SWAP old-era (A) proofs -> plain outputs ---
total_A = sum(p.amount for p in proofs_A_swap)
fee_A = builder.calc_fee(len(proofs_A_swap))
swap_amount = total_A - fee_A
try:
    swapped = builder.swap_to_p2pk(proofs_A_swap, generate_secret, swap_amount)
    record("P4_swap_A", verdict="200-redeemed", inputs=total_A, outputs=sum(p.amount for p in swapped),
           new_keyset=swapped[0].id, outputs_on_B=(swapped[0].id == B) if B else None)
except Exception as e:
    record("P4_swap_A", verdict="REJECTED", error=str(e)[:300])

# --- P6: mint explicitly under retired keyset A ---
mq = mint.mint_quote(4)
try:
    code, body = mint.mint_with_keyset(mq["quote"], 4, A) if hasattr(mint, "mint_with_keyset") else (None, None)
except Exception as e:
    code, body = None, {"exception": str(e)[:200]}
if code is None:
    # manual fallback: POST /v1/mint/bolt11 with explicit keyset_id
    outputs = builder.create_outputs(4, generate_secret)
    api_outputs = builder.outputs_to_api(outputs)
    resp = requests.post(f"{MINT}/v1/mint/bolt11", timeout=30,
                         json={"quote": mq["quote"], "outputs": api_outputs, "keyset_id": A})
    code, body = resp.status_code, (resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:300])
record("P6_mint_under_A", http=code, body=body if not isinstance(body, dict) else {k: body[k] for k in list(body)[:5]})

# --- P7: default mint lands on B ---
try:
    proofs_B = builder.mint_proofs(4)
    record("P7_mint_default", keyset=proofs_B[0].id, on_B=(proofs_B[0].id == B) if B else None)
except Exception as e:
    record("P7_mint_default", verdict="REJECTED", error=str(e)[:300])

# --- P5: MELT old-era (A) proofs ---
dest = mint.mint_quote(4)["request"]
q = mint.melt_quote(dest)
inputs = [p.to_dict() for p in proofs_A_melt]
code, body = mint.melt(q["quote"], inputs, None)
state = body.get("state") if isinstance(body, dict) else None
record("P5_melt_A", http=code, state=state, error=(body.get("error") if isinstance(body, dict) else str(body)[:200]))

# --- P8: checkstate of A-proofs ---
try:
    st = mint.checkstate([p.y_value() for p in proofs_A_melt])
    record("P8_checkstate_A", http=200, body=st if not isinstance(st, dict) else {k: st[k] for k in list(st)[:3]})
except Exception as e:
    record("P8_checkstate_A", verdict="ERROR", error=str(e)[:200])

print("=== RUNG COMPLETE ===")
with open("out/rotation-rung.json", "w") as f:
    json.dump(out, f, indent=2)
print("wrote out/rotation-rung.json")
