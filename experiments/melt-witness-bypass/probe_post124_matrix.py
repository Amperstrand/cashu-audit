"""Post-ISSUE-124 verification matrix for the melt witness-bypass findings.

Verifies on a LIVE mint (default testnut) the six vectors from
cashu-audit #53 + divergences/2026-09-16-melt-quote-stage-witness-validation-gap.md (#26),
against the ISSUE-124 fixed code (deployed fleet-wide 2026-10-27).

FROZEN PREDICTIONS (before running — cashu-audit method rule 1):
  1. control_p2pk_witness_succeeds      -> 200 state PAID      (no over-blocking)
  2. p2pk_unsigned                      -> 4xx spending_condition_not_met 30006
  3. p2pk_sigall_unsigned               -> 4xx spending_condition_not_met 30006
  4. htlc_preimage_only                 -> 4xx spending_condition_not_met
  5. htlc_signature_only                -> 4xx spending_condition_not_met
  6. p2pk_before_locktime_wrong_key     -> 4xx spending_condition_not_met

Run: PYTHONPATH=. python3 ../../experiments/melt-witness-bypass/probe_post124_matrix.py [MINT]
"""
import hashlib
import json
import sys

from conformance.builder import (
    ProofBuilder, build_p2pk_secret, build_htlc_secret,
    generate_htlc_preimage, set_htlc_witness, sigall_melt_message_for,
)
from conformance.client import MintClient
from conformance.crypto import KeyPair, generate_secret

MINT = sys.argv[1] if len(sys.argv) > 1 else "https://testnut.cashu.exchange"
mint = MintClient(MINT, timeout=30)
builder = ProofBuilder(mint)

PREDICTIONS = {
    "control_p2pk_witness_succeeds": (200, None),
    "p2pk_unsigned": ("4xx", "30006"),
    "p2pk_sigall_unsigned": ("4xx", "30006"),
    "htlc_preimage_only": ("4xx", "spending"),
    "htlc_signature_only": ("4xx", "spending"),
    "p2pk_before_locktime_wrong_key": ("4xx", "spending"),
}


def fresh_conditioned_proofs(secret_fn, amount=8):
    regular = builder.mint_proofs(amount)
    total = sum(p.amount for p in regular)
    swap_amount = total - builder.calc_fee(len(regular))
    return builder.swap_to_p2pk(regular, secret_fn, swap_amount)


def melt_quote_for(amount=4):
    mq = mint.mint_quote(amount)
    q = mint.melt_quote(mq["request"])
    return q["quote"]


def do_melt(quote, proofs, outputs=None):
    inputs = [p.to_dict() for p in proofs]
    return mint.melt(quote, inputs, outputs)


results = {}

# 1. control: P2PK SIG_INPUTS with VALID witness -> expect PAID
key = KeyPair.generate()
proofs = fresh_conditioned_proofs(lambda: build_p2pk_secret(key.pub_hex))
witness = builder.sign_p2pk_witness(proofs, key)
for p in proofs:
    p.witness = witness
code, body = do_melt(melt_quote_for(), proofs)
state = body.get("state") if isinstance(body, dict) else None
results["control_p2pk_witness_succeeds"] = (code, state, "PASS" if code == 200 and state == "PAID" else "UNEXPECTED")

# 2. P2PK SIG_INPUTS unsigned
key = KeyPair.generate()
proofs = fresh_conditioned_proofs(lambda: build_p2pk_secret(key.pub_hex))
code, body = do_melt(melt_quote_for(), proofs)
results["p2pk_unsigned"] = (code, body.get("error") if isinstance(body, dict) else body, body.get("code") if isinstance(body, dict) else None)

# 3. P2PK SIG_ALL unsigned (witness would sign inputs||outputs||quote; withheld)
key = KeyPair.generate()
proofs = fresh_conditioned_proofs(lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL"))
qid = mint.melt_quote(mint.mint_quote(4)["request"])["quote"]
change_total = max(0, sum(p.amount for p in proofs) - 5)
change = builder.create_outputs(change_total, generate_secret) if change_total >= 1 else []
outputs = builder.outputs_to_api(change) if change else None
code, body = do_melt(qid, proofs, outputs)
results["p2pk_sigall_unsigned"] = (code, body.get("error") if isinstance(body, dict) else body, body.get("code") if isinstance(body, dict) else None)

# 4. HTLC preimage-only (pubkeys+n_sigs:1 set, so a signature is also required)
key = KeyPair.generate()
preimage_hex, hash_hex = generate_htlc_preimage()
proofs = fresh_conditioned_proofs(lambda: build_htlc_secret(hash_hex, pubkeys=[key.pub_hex], n_sigs=1))
set_htlc_witness(proofs, preimage_hex)  # preimage, no signatures
code, body = do_melt(melt_quote_for(), proofs)
results["htlc_preimage_only"] = (code, body.get("error") if isinstance(body, dict) else body, body.get("code") if isinstance(body, dict) else None)

# 5. HTLC signature-only (no preimage)
key = KeyPair.generate()
preimage_hex, hash_hex = generate_htlc_preimage()
proofs = fresh_conditioned_proofs(lambda: build_htlc_secret(hash_hex, pubkeys=[key.pub_hex], n_sigs=1))
sig = key.sign_schnorr(hashlib.sha256(("".join(p.secret for p in proofs)).encode()).digest())
for p in proofs:
    p.witness = json.dumps({"signatures": [sig]})  # signature, no preimage
code, body = do_melt(melt_quote_for(), proofs)
results["htlc_signature_only"] = (code, body.get("error") if isinstance(body, dict) else body, body.get("code") if isinstance(body, dict) else None)

# 6. P2PK wrong key before locktime (future locktime; spend attempt with unrelated key)
lock_key = KeyPair.generate()
wrong_key = KeyPair.generate()
proofs = fresh_conditioned_proofs(lambda: build_p2pk_secret(lock_key.pub_hex, locktime=999999999))
wrong_witness = builder.sign_p2pk_witness(proofs, wrong_key)
for p in proofs:
    p.witness = wrong_witness
code, body = do_melt(melt_quote_for(), proofs)
results["p2pk_before_locktime_wrong_key"] = (code, body.get("error") if isinstance(body, dict) else body, body.get("code") if isinstance(body, dict) else None)

print(f"=== post-124 melt witness matrix vs {MINT} ===")
all_pass = True
for name, (code, err, extra) in results.items():
    print(f"{name}: HTTP {code} error={err} code={extra}")
for name in ["p2pk_unsigned", "p2pk_sigall_unsigned", "htlc_preimage_only", "htlc_signature_only", "p2pk_before_locktime_wrong_key"]:
    code = results[name][0]
    if not (isinstance(code, int) and 400 <= code < 500):
        all_pass = False
if results["control_p2pk_witness_succeeds"][2] != "PASS":
    all_pass = False
print(f"=== VERDICT: {'ALL VECTORS ENFORCED (fix live) + control passes' if all_pass else 'DIVERGENCE REMAINS — see table'} ===")
