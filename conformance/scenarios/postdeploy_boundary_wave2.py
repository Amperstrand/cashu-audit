"""Post-deploy boundary wave 2 — 3 scenarios (deploy-gated standing reds).

Every scenario here pins a fix that is landed on cashu-cf main but NOT yet
deployed (as of 2026-11-13 the fleet runs ≈ c64592fe). Against undeployed
mints they are standing REDS pinned to their issues; they flip GREEN the
moment the owner's deploy window lands, giving wire-level confirmation on
the same probes we used to find the classes:

1. ``mpp_subsat_partial_boundary`` (#49, 92da59a6) — a 1500 msat MPP
   partial of a 3000 msat invoice currently mints a quote with amount=2
   (Math.ceil overcharge, verified live 2026-11-13). Post-deploy it MUST
   be rejected: 400 invalid_request, whole-satoshi detail.
2. ``nut00_strict_p2pk_hexdecode_rejected`` (#122 option A, 8a496096) —
   a P2PK witness signature computed over the DECODED BYTES of a
   hex-shaped secret was accepted by the legacy hex-decode fallback in
   verifyProofSignatureWithPrivateKey. Post-deploy (default-off escape
   hatch) it MUST be rejected. NOT YET IMPLEMENTED: the scenario needs
   cf's exact P2PK message derivation pinned (spending-conditions
   msg construction over secret+C) before the witness can be forged
   over the decoded-secret variant — tracked as the wave-2 follow-up.
3. ``melt_change_outputs_cap`` (#100, b473a00d) — 101 melt change outputs
   MUST be rejected with invalid_outputs + "max 100" (MAX_MELT_OUTPUTS).
"""
from __future__ import annotations

import json
import subprocess
import time

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret, hash_to_curve
from conformance.scenarios import scenario, ScenarioResult, Result

CAT = "Post-Deploy Boundary Wave 2"


def _cln_invoice(amount_msat: int, label: str) -> str:
    """External signet invoice from the CLN rail (self-mint invoices trip
    the internal-payment MPP rejection before the classes under test)."""
    cmd = (
        "docker exec cln-swap-signet lightning-cli --network=signet "
        f"invoice {amount_msat} {label} 'wave2-probe' 600"
    )
    out = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
         "inr2.cashu.exchange", cmd],
        capture_output=True, text=True, timeout=30, check=True,
    ).stdout
    return json.loads(out)["bolt11"]


def _melt_quote_raw(mint: MintClient, body: dict) -> tuple[int, dict | str]:
    return mint._post("/v1/melt/quote/bolt11", body)


@scenario("mpp_subsat_partial_boundary", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """#49: sub-satoshi MPP partials must be rejected (no silent ceil)."""
    # Capability probe by ATTEMPT (the /v1/info NUT-15 advertisement is
    # itself deploy-gated by #113 — pre-fix mints under-advertise).
    try:
        cap_invoice = _cln_invoice(2000, f"wave2-mppcap-{int(time.time())}")
    except Exception as e:  # rail down = SKIP loudly, never silently
        return ScenarioResult(
            "mpp_subsat_partial_boundary", CAT, Result.SKIP,
            f"CLN invoice rail unavailable: {e}",
        )
    cap_code, cap_data = _melt_quote_raw(mint, {
        "request": cap_invoice, "unit": "sat",
        "options": {"mpp": {"amount": 1000}},
    })
    cap_detail = json.dumps(cap_data) if not isinstance(cap_data, str) else cap_data
    if "not supported" in cap_detail.lower() or "not allowed" in cap_detail.lower():
        return ScenarioResult(
            "mpp_subsat_partial_boundary", CAT, Result.SKIP,
            f"backend rejects MPP outright (fakewallet arm): {cap_detail[:100]}",
        )
    try:
        invoice = _cln_invoice(3000, f"wave2-mpp-{int(time.time())}")
    except Exception as e:
        return ScenarioResult(
            "mpp_subsat_partial_boundary", CAT, Result.SKIP,
            f"CLN invoice rail unavailable: {e}",
        )
    code, data = _melt_quote_raw(mint, {
        "request": invoice, "unit": "sat",
        "options": {"mpp": {"amount": 1500}},
    })
    if code == 200:
        amount = data.get("amount") if isinstance(data, dict) else None
        return ScenarioResult(
            "mpp_subsat_partial_boundary", CAT, Result.FAIL,
            f"sub-sat partial accepted pre-fix (amount={amount}, Math.ceil "
            "overcharge live) — cashu-cf 92da59a6 not deployed (issue #49)",
        )
    detail = json.dumps(data) if not isinstance(data, str) else data
    if code == 400 and "satosh" in detail:
        return ScenarioResult(
            "mpp_subsat_partial_boundary", CAT, Result.PASS,
            f"sub-sat partial rejected with whole-sat boundary: {detail[:120]}",
        )
    return ScenarioResult(
        "mpp_subsat_partial_boundary", CAT, Result.FAIL,
        f"unexpected rejection identity ({code}): {detail[:120]}",
    )


@scenario("melt_change_outputs_cap", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """#100: melt change outputs are capped at MAX_MELT_OUTPUTS (100)."""
    builder = ProofBuilder(mint)
    amount = 64
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    signatures = None
    quote = mint.mint_quote(amount)
    for _ in range(30):
        try:
            signatures = mint.mint_tokens(quote["quote"], builder.outputs_to_api(outputs))
            break
        except RuntimeError:
            time.sleep(1)
    if not signatures:
        return ScenarioResult(
            "melt_change_outputs_cap", CAT, Result.SKIP,
            "could not mint inputs (rail flake)",
        )
    _keyset_id, keys = builder.get_active_keyset()
    proofs = builder.unblind_signatures(signatures.get("signatures", []), outputs, keys)
    melt = mint.create_fresh_melt_quote(amount=4)
    change = builder.create_outputs(amount, lambda: generate_secret())
    capped = builder.outputs_to_api(change)
    # pad to 101 change outputs (dup B_ is fine — the count check is structural)
    one = capped[0]
    body_inputs = [p.to_dict() for p in proofs]
    code, data = mint._post("/v1/melt/bolt11", {
        "quote": melt.get("quote"),
        "inputs": body_inputs,
        "outputs": [one] * 101,
    })
    detail = json.dumps(data) if not isinstance(data, str) else data
    if code == 400 and "max 100" in detail:
        return ScenarioResult(
            "melt_change_outputs_cap", CAT, Result.PASS,
            f"101 change outputs rejected: {detail[:120]}",
        )
    if code in (200, 202):
        return ScenarioResult(
            "melt_change_outputs_cap", CAT, Result.FAIL,
            f"outputs cap not enforced ({code}) — cashu-cf b473a00d not "
            "deployed (issue #100)",
        )
    if "max" in detail and "output" in detail.lower():
        return ScenarioResult(
            "melt_change_outputs_cap", CAT, Result.PASS,
            f"cap identity present: {detail[:120]}",
        )
    # A payment-path error (e.g. payment_failed) means request VALIDATION
    # passed — the cap did not fire: the standing red (fix undeployed).
    return ScenarioResult(
        "melt_change_outputs_cap", CAT, Result.FAIL,
        f"101 outputs passed validation ({code}: {detail[:100]}) — "
        "cashu-cf b473a00d not deployed (issue #100)",
    )
