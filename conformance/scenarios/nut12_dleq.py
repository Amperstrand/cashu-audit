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


@scenario("dleq_invalid_proof_rejected", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Tampered DLEQ proof fails verification (negative test).

    Takes a valid DLEQ proof from a live mint, flips a byte in ``s``,
    and confirms our verifier rejects it. This exercises the
    Chaum-Pedersen negative path: ``R1 = s*G - e*A`` will not produce
    the expected ``e`` when ``s`` is corrupted.
    """
    builder = ProofBuilder(mint)
    outputs, signatures = _mint_with_raw_sigs(builder, mint, 8)
    if not signatures:
        return ScenarioResult(
            "dleq_invalid_proof_rejected", CAT,
            Result.FAIL, "no signatures returned from mint",
        )
    # Graceful skip when the mint does not provide DLEQ
    if not all(_has_dleq(s) for s in signatures):
        return ScenarioResult(
            "dleq_invalid_proof_rejected", CAT,
            Result.SKIP, "mint does not provide DLEQ proofs",
        )

    _, keys = builder.get_active_keyset()
    sig = signatures[0]
    out = outputs[0]
    amt = sig.get("amount", out.amount)
    a_hex = keys.get(amt, keys.get(1, ""))
    if not a_hex:
        return ScenarioResult(
            "dleq_invalid_proof_rejected", CAT,
            Result.FAIL, f"no mint pubkey for amount {amt}",
        )

    dleq = sig["dleq"]

    # Sanity: the original proof should verify
    if not _verify_dleq(out.B_, sig["C_"], dleq["e"], dleq["s"], a_hex):
        return ScenarioResult(
            "dleq_invalid_proof_rejected", CAT,
            Result.FAIL, "original DLEQ proof did not verify (precondition)",
        )

    # Tamper s: flip the last hex nibble
    s_bytes = bytearray(bytes.fromhex(dleq["s"]))
    s_bytes[-1] ^= 0x01  # flip LSB
    tampered_s = s_bytes.hex()

    # Tampered proof must fail verification
    if _verify_dleq(out.B_, sig["C_"], dleq["e"], tampered_s, a_hex):
        return ScenarioResult(
            "dleq_invalid_proof_rejected", CAT,
            Result.FAIL, "tampered DLEQ proof was accepted (should be rejected)",
        )

    # Also tamper e: flip a byte and verify rejection
    e_bytes = bytearray(bytes.fromhex(dleq["e"]))
    e_bytes[-1] ^= 0x01
    tampered_e = e_bytes.hex()

    if _verify_dleq(out.B_, sig["C_"], tampered_e, dleq["s"], a_hex):
        return ScenarioResult(
            "dleq_invalid_proof_rejected", CAT,
            Result.FAIL, "tampered-e DLEQ proof was accepted (should be rejected)",
        )

    return ScenarioResult(
        "dleq_invalid_proof_rejected", CAT,
        Result.PASS,
        "tampered e and s both correctly rejected",
    )


@scenario("hash_e_test_vector_verification", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Verify hash_e and DLEQ verification against official NUT-12 test vectors.

    Pure crypto test — does not require the mint to support DLEQ.
    Uses the known-answer test vectors from ``nuts/tests/12-tests.md``.

    Vector 1 — hash_e function::

        R1 = R2 = K  = 0200...01
        C_            = 02a9acc1e4...
        hash_e(R1,R2,K,C_) = a4dc034b...

    Vector 2 — BlindSignature DLEQ (full Chaum-Pedersen)::

        A  = 0279be667e... (generator G)
        B_ = C_ = 02a9acc1e4...
        e  = 9818e061ee...
        s  = 9818e061ee...da
    """
    # ── Vector 1: hash_e known-answer ──────────────────────────────
    R1_hex = "020000000000000000000000000000000000000000000000000000000000000001"
    R2_hex = "020000000000000000000000000000000000000000000000000000000000000001"
    K_hex = "020000000000000000000000000000000000000000000000000000000000000001"
    C_hash_hex = "02a9acc1e48c25eeeb9289b5031cc57da9fe72f3fe2861d264bdc074209b107ba2"
    expected_hash = "a4dc034b74338c28c6bc3ea49731f2a24440fc7c4affc08b31a93fc9fbe6401e"

    R1 = PublicKey(bytes.fromhex(R1_hex))
    R2 = PublicKey(bytes.fromhex(R2_hex))
    K = PublicKey(bytes.fromhex(K_hex))
    C_hash = PublicKey(bytes.fromhex(C_hash_hex))

    computed = _hash_e(R1, R2, K, C_hash).hex()
    if computed != expected_hash:
        return ScenarioResult(
            "hash_e_test_vector_verification", CAT,
            Result.FAIL,
            f"hash_e mismatch: expected {expected_hash}, got {computed}",
        )

    # ── Vector 2: BlindSignature DLEQ (full Chaum-Pedersen) ────────
    A_hex = "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"
    B_hex = "02a9acc1e48c25eeeb9289b5031cc57da9fe72f3fe2861d264bdc074209b107ba2"
    C_sig_hex = "02a9acc1e48c25eeeb9289b5031cc57da9fe72f3fe2861d264bdc074209b107ba2"
    e_tv = "9818e061ee51d5c8edc3342369a554998ff7b4381c8652d724cdf46429be73d9"
    s_tv = "9818e061ee51d5c8edc3342369a554998ff7b4381c8652d724cdf46429be73da"

    if not _verify_dleq(B_hex, C_sig_hex, e_tv, s_tv, A_hex):
        return ScenarioResult(
            "hash_e_test_vector_verification", CAT,
            Result.FAIL,
            "BlindSignature DLEQ test vector failed verification",
        )

    # ── Vector 3: Deterministic nonce derivation ───────────────────
    a_hex = "0000000000000000000000000000000000000000000000000000000000000002"
    A_det = "02c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5"
    B_det = "02a9acc1e48c25eeeb9289b5031cc57da9fe72f3fe2861d264bdc074209b107ba2"
    C_det = "0244eccfc7a348274458bb38044c7f3c389b3c2086c7ec18b5812d2877ab937787"
    e_det = "2a16ffee280aff3c429045607f9b8e0bf8b35910c44c1b20b9dfaf01b263d7b3"
    s_det = "9df27731238334718d120d4f74611a7c668233f988e687ac3fb188f0a34a2dab"

    if not _verify_dleq(B_det, C_det, e_det, s_det, A_det):
        return ScenarioResult(
            "hash_e_test_vector_verification", CAT,
            Result.FAIL,
            "Deterministic nonce DLEQ test vector failed verification",
        )

    return ScenarioResult(
        "hash_e_test_vector_verification", CAT,
        Result.PASS,
        "hash_e + 2 DLEQ test vectors verified",
    )
