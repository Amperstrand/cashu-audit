"""NUT-12 DLEQ proof verification scenarios — 4 tests.

DLEQ (Discrete Log Equivalence) proofs prove that the mint's blind
signature C' was computed correctly from the mint's key A and the
blinded message B_.  The DLEQ proof contains (e, s) values.

Verification algorithm (Chaum-Pedersen):
    R1 = s*G - e*A       (A = mint pubkey, G = generator)
    R2 = s*B_ - e*C'     (B_ = blinded message, C' = blinded signature)
    Check: e == hash_e(R1, R2, A, C')

where hash_e is SHA-256 over the concatenation of the uncompressed
(65-byte) point hex strings — matching the Cashu reference (nutshell).

NUT-12 says: the mint SHOULD provide DLEQ proofs; wallets SHOULD
verify them and reject signatures that fail verification.  If the mint
does not return DLEQ proofs, the verification scenarios SKIP.
"""
from __future__ import annotations

import hashlib
import time

from coincurve import PrivateKey, PublicKey

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import (
    generate_secret,
    pubkey_add,
    pubkey_mul,
    pubkey_neg,
)
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
    expect_success,
)

CAT = "NUT-12 DLEQ"


# ---------------------------------------------------------------------------
# DLEQ verification helpers
# ---------------------------------------------------------------------------

def _hash_e(*points: PublicKey) -> bytes:
    """Cashu DLEQ challenge hash.

    Matches nutshell's ``hash_e``: SHA-256 over the concatenation of
    uncompressed (65-byte, ``0x04``-prefixed) point hex strings.
    """
    e_str = "".join(p.format(compressed=False).hex() for p in points)
    return hashlib.sha256(e_str.encode("utf-8")).digest()


def _verify_dleq(
    b_hex: str,
    c_blinded_hex: str,
    e_hex: str,
    s_hex: str,
    a_hex: str,
) -> bool:
    """Verify a DLEQ proof ``(e, s)``.

    Parameters are hex strings:
        b_hex          — blinded message B_  (compressed pubkey)
        c_blinded_hex  — blinded signature C' (compressed pubkey)
        e_hex          — DLEQ challenge e     (32-byte scalar)
        s_hex          — DLEQ response s      (32-byte scalar)
        a_hex          — mint public key A    (compressed pubkey)

    Returns ``True`` iff the proof is valid.
    """
    B_ = PublicKey(bytes.fromhex(b_hex))
    C_ = PublicKey(bytes.fromhex(c_blinded_hex))
    A = PublicKey(bytes.fromhex(a_hex))
    e_bytes = bytes.fromhex(e_hex)

    # R1 = s*G - e*A
    sG = PrivateKey(bytes.fromhex(s_hex)).public_key
    eA = pubkey_mul(A, e_hex)
    R1 = pubkey_add(sG, pubkey_neg(eA))

    # R2 = s*B_ - e*C'
    sB_ = pubkey_mul(B_, s_hex)
    eC_ = pubkey_mul(C_, e_hex)
    R2 = pubkey_add(sB_, pubkey_neg(eC_))

    return e_bytes == _hash_e(R1, R2, A, C_)


def _mint_with_raw_sigs(
    builder: ProofBuilder, mint: MintClient, amount: int
) -> tuple[list, list[dict]]:
    """Mint tokens, returning ``(outputs, raw_signatures)``.

    Unlike ``ProofBuilder.mint_proofs``, this exposes the raw mint
    response signatures so DLEQ fields are accessible.
    """
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    quote = mint.mint_quote(amount)
    quote_id = quote["quote"]
    result = None
    for _ in range(30):
        try:
            result = mint.mint_tokens(quote_id, api_outputs)
            break
        except RuntimeError:
            time.sleep(1)
    if result is None:
        result = mint.mint_tokens(quote_id, api_outputs)
    return outputs, result.get("signatures", [])


def _swap_with_raw_sigs(
    builder: ProofBuilder,
    mint: MintClient,
    input_proofs: list,
    amount: int,
) -> tuple[list, list[dict]]:
    """Swap inputs for new outputs, returning ``(outputs, raw_signatures)``."""
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    inputs = [p.to_dict() for p in input_proofs]
    result = mint.swap(inputs, api_outputs)
    return outputs, result.get("signatures", [])


def _has_dleq(sig: dict) -> bool:
    """Check whether a signature dict carries a usable DLEQ proof."""
    dleq = sig.get("dleq")
    return isinstance(dleq, dict) and bool(dleq.get("e")) and bool(dleq.get("s"))


# ===========================================================================
# Scenarios
# ===========================================================================

@scenario("dleq_proofs_present_in_mint_response", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Mint response signatures include ``dleq`` with ``{e, s}`` fields."""
    builder = ProofBuilder(mint)
    _outputs, signatures = _mint_with_raw_sigs(builder, mint, 8)
    if not signatures:
        return ScenarioResult(
            "dleq_proofs_present_in_mint_response", CAT,
            Result.FAIL, "no signatures returned from mint",
        )
    with_dleq = [s for s in signatures if _has_dleq(s)]
    if len(with_dleq) == len(signatures):
        return ScenarioResult(
            "dleq_proofs_present_in_mint_response", CAT,
            Result.PASS,
            f"{len(with_dleq)}/{len(signatures)} signatures have dleq",
        )
    return ScenarioResult(
        "dleq_proofs_present_in_mint_response", CAT,
        Result.FAIL,
        f"only {len(with_dleq)}/{len(signatures)} signatures have dleq",
    )


@scenario("dleq_proof_valid", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """DLEQ proof verifies correctly for each minted signature."""
    builder = ProofBuilder(mint)
    outputs, signatures = _mint_with_raw_sigs(builder, mint, 8)
    if not signatures:
        return ScenarioResult(
            "dleq_proof_valid", CAT,
            Result.FAIL, "no signatures returned from mint",
        )
    # Graceful skip when the mint does not provide DLEQ
    if not all(_has_dleq(s) for s in signatures):
        return ScenarioResult(
            "dleq_proof_valid", CAT,
            Result.SKIP, "mint does not provide DLEQ proofs",
        )

    _, keys = builder.get_active_keyset()
    for sig, out in zip(signatures, outputs):
        amt = sig.get("amount", out.amount)
        a_hex = keys.get(amt, keys.get(1, ""))
        if not a_hex:
            return ScenarioResult(
                "dleq_proof_valid", CAT,
                Result.FAIL, f"no mint pubkey for amount {amt}",
            )
        dleq = sig["dleq"]
        if not _verify_dleq(out.B_, sig["C_"], dleq["e"], dleq["s"], a_hex):
            return ScenarioResult(
                "dleq_proof_valid", CAT,
                Result.FAIL,
                f"DLEQ verification failed for amount {amt} "
                f"(B_={out.B_[:16]}… C_={sig['C_'][:16]}…)",
            )
    return ScenarioResult(
        "dleq_proof_valid", CAT,
        Result.PASS,
        f"{len(signatures)} DLEQ proofs verified",
    )


@scenario("dleq_proof_absent_graceful", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """When DLEQ is absent, proofs are still spendable (graceful degradation)."""
    builder = ProofBuilder(mint)
    outputs, signatures = _mint_with_raw_sigs(builder, mint, 8)
    if not signatures:
        return ScenarioResult(
            "dleq_proof_absent_graceful", CAT,
            Result.FAIL, "no signatures returned from mint",
        )
    # If the mint *does* provide DLEQ the absent-case precondition is not met
    if any(_has_dleq(s) for s in signatures):
        return ScenarioResult(
            "dleq_proof_absent_graceful", CAT,
            Result.SKIP, "mint provides DLEQ — absent-case not applicable",
        )
    # Mint does not provide DLEQ: verify the proofs are nonetheless spendable
    _, keys = builder.get_active_keyset()
    proofs = builder.unblind_signatures(signatures, outputs, keys)
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_amount = max(1, total - fee)
    swap_outputs = builder.create_outputs(swap_amount, lambda: generate_secret())
    code, body = mint.try_swap(
        [p.to_dict() for p in proofs],
        builder.outputs_to_api(swap_outputs),
    )
    if expect_success(code, body):
        return ScenarioResult(
            "dleq_proof_absent_graceful", CAT,
            Result.PASS, "proofs spendable without DLEQ",
        )
    return ScenarioResult(
        "dleq_proof_absent_graceful", CAT,
        Result.FAIL, f"swap failed ({code}): {str(body)[:200]}",
    )


@scenario("dleq_proof_in_signature_response", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Swap (NUT-03) response signatures also carry DLEQ proofs."""
    builder = ProofBuilder(mint)

    # Mint proofs to use as swap inputs
    proofs = builder.mint_proofs(8)
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_amount = max(1, total - fee)

    # Swap and capture the raw response signatures
    outputs, signatures = _swap_with_raw_sigs(
        builder, mint, proofs, swap_amount
    )
    if not signatures:
        return ScenarioResult(
            "dleq_proof_in_signature_response", CAT,
            Result.FAIL, "no signatures returned from swap",
        )
    # Graceful skip when the swap response does not include DLEQ
    if not all(_has_dleq(s) for s in signatures):
        return ScenarioResult(
            "dleq_proof_in_signature_response", CAT,
            Result.SKIP, "swap response does not include DLEQ proofs",
        )

    # Verify each DLEQ proof in the swap response
    _, keys = builder.get_active_keyset()
    for sig, out in zip(signatures, outputs):
        amt = sig.get("amount", out.amount)
        a_hex = keys.get(amt, keys.get(1, ""))
        if not a_hex:
            return ScenarioResult(
                "dleq_proof_in_signature_response", CAT,
                Result.FAIL, f"no mint pubkey for amount {amt}",
            )
        dleq = sig["dleq"]
        if not _verify_dleq(out.B_, sig["C_"], dleq["e"], dleq["s"], a_hex):
            return ScenarioResult(
                "dleq_proof_in_signature_response", CAT,
                Result.FAIL,
                f"DLEQ verification failed for swap output amount {amt}",
            )
    return ScenarioResult(
        "dleq_proof_in_signature_response", CAT,
        Result.PASS,
        f"{len(signatures)} swap-response DLEQ proofs verified",
    )
