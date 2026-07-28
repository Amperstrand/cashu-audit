"""NUT-11 melt-pathway spending-condition scenarios — 12 tests.

Tests P2PK and HTLC spending conditions on the melt (NUT-05) pathway.
Each scenario:
  1. Mints regular proofs and swaps them for P2PK/HTLC-conditioned proofs
  2. Creates a melt quote (FakeWallet auto-pays any invoice)
  3. Attempts to melt using the conditioned proofs as inputs
  4. Verifies the melt succeeds (state=PAID) or fails (spending condition
     not satisfied → 400/403)

SIG_ALL melt message includes the quote_id appended at the end:
    secret_0 || C_0 || ... || amount_0 || B_0 || ... || quote_id
"""
from __future__ import annotations

import hashlib
import json
import time

from conformance.builder import (
    ProofBuilder,
    Proof,
    OutputResult,
    build_p2pk_secret,
    build_htlc_secret,
    sigall_melt_message,
    set_sigall_witness,
    generate_htlc_preimage,
    set_htlc_witness,
)
from conformance.client import MintClient
from conformance.crypto import KeyPair, generate_secret
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
)

CATEGORY = "Melt spending conditions"


# ─── helpers ──────────────────────────────────────────────────────────────


def _swap_for_condition(
    builder: ProofBuilder,
    mint: MintClient,
    secret_fn,
    amount: int = 8,
) -> list[Proof]:
    """Mint regular proofs and swap them for proofs with spending conditions."""
    regular = builder.mint_proofs(amount)
    total = sum(p.amount for p in regular)
    num_inputs = len(regular)
    swap_amount = total - num_inputs
    if swap_amount < 1:
        raise RuntimeError(
            f"Amount too small: {total} - {num_inputs} fee = {swap_amount}"
        )
    return builder.swap_to_p2pk(regular, secret_fn, swap_amount)


def _set_witness(proofs: list[Proof], key: KeyPair) -> None:
    """Set per-input SIG_INPUTS witness (signature over sha256(secret))."""
    for p in proofs:
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        p.witness = json.dumps({"signatures": [key.sign_schnorr(msg)]})


def _create_melt_quote(mint: MintClient) -> str:
    """Create a melt quote for a dummy invoice (FakeWallet auto-pays).

    Returns the quote_id. Sleeps briefly to let the FakeWallet process.
    """
    resp = mint.melt_quote("dummy-melt-invoice")
    time.sleep(2)
    return resp["quote"]


def _change_outputs(builder: ProofBuilder, proofs: list[Proof]) -> list[OutputResult]:
    """Create change outputs for the melt, accounting for input fees + margin.

    output_total = sum(proofs) - len(proofs) - 1
    """
    total = sum(p.amount for p in proofs)
    change = max(0, total - len(proofs) - 1)
    if change < 1:
        return []
    return builder.create_outputs(change, lambda: generate_secret())


def _try_melt(
    mint: MintClient,
    builder: ProofBuilder,
    proofs: list[Proof],
    quote_id: str,
) -> tuple[int, object]:
    """Attempt a melt with *proofs* as inputs.

    Creates change outputs automatically. Returns (status_code, body).
    """
    inputs = [p.to_dict() for p in proofs]
    change = _change_outputs(builder, proofs)
    outputs = builder.outputs_to_api(change) if change else None
    return mint.melt(quote_id, inputs, outputs)


def _melt_paid(code: int, body) -> bool:
    """True when the melt succeeded — HTTP 200 with state=PAID."""
    if code != 200:
        return False
    if isinstance(body, dict):
        return body.get("state") == "PAID"
    return False


def _melt_blocked(code: int, body) -> bool:
    """True when the melt was rejected (spending condition not satisfied).

    Accepts explicit error codes (400/403/422) or 200-without-PAID.
    """
    if _melt_paid(code, body):
        return False
    if code in (400, 403, 422):
        return True
    if code == 200 and isinstance(body, dict):
        return body.get("state") != "PAID"
    return False


# ─── P2PK melt scenarios (4) ──────────────────────────────────────────────


@scenario("melt_p2pk_unsigned_fails", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with unsigned P2PK proofs should fail."""
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_blocked(code, body):
        return ScenarioResult(
            "melt_p2pk_unsigned_fails", CATEGORY, Result.PASS, "unsigned melt rejected"
        )
    return ScenarioResult(
        "melt_p2pk_unsigned_fails", CATEGORY, Result.FAIL, f"got {code}: {str(body)[:200]}"
    )


@scenario("melt_p2pk_signed_succeeds", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with correctly signed P2PK proofs should succeed."""
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    _set_witness(proofs, key)
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_paid(code, body):
        return ScenarioResult(
            "melt_p2pk_signed_succeeds", CATEGORY, Result.PASS, "signed melt paid"
        )
    return ScenarioResult(
        "melt_p2pk_signed_succeeds", CATEGORY, Result.FAIL, f"got {code}: {str(body)[:200]}"
    )


@scenario("melt_p2pk_sigall_unsigned_fails", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with unsigned SIG_ALL P2PK proofs should fail."""
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    quote_id = _create_melt_quote(mint)
    # No witness — SIG_ALL requires a transaction signature
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_blocked(code, body):
        return ScenarioResult(
            "melt_p2pk_sigall_unsigned_fails",
            CATEGORY,
            Result.PASS,
            "unsigned SIG_ALL melt rejected",
        )
    return ScenarioResult(
        "melt_p2pk_sigall_unsigned_fails",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


@scenario("melt_p2pk_sigall_transaction_signature_succeeds", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with correct SIG_ALL transaction signature should succeed."""
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    quote_id = _create_melt_quote(mint)

    # Create change outputs BEFORE signing — the SIG_ALL melt message
    # includes output amounts and B_ values, then appends quote_id.
    change = _change_outputs(builder, proofs)
    output_amounts = [(o.amount, o.B_) for o in change]
    message = sigall_melt_message(proofs, output_amounts, quote_id)
    set_sigall_witness(proofs, key, message)

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(change) if change else None
    code, body = mint.melt(quote_id, inputs, outputs)
    if _melt_paid(code, body):
        return ScenarioResult(
            "melt_p2pk_sigall_transaction_signature_succeeds",
            CATEGORY,
            Result.PASS,
            "SIG_ALL melt paid",
        )
    return ScenarioResult(
        "melt_p2pk_sigall_transaction_signature_succeeds",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


# ─── HTLC melt scenarios (5) ──────────────────────────────────────────────


@scenario("melt_htlc_preimage_only_no_pubkeys_succeeds", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with valid HTLC preimage (no pubkeys) should succeed."""
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(hash_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    set_htlc_witness(proofs, preimage_hex)
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_paid(code, body):
        return ScenarioResult(
            "melt_htlc_preimage_only_no_pubkeys_succeeds",
            CATEGORY,
            Result.PASS,
            "HTLC preimage melt paid",
        )
    return ScenarioResult(
        "melt_htlc_preimage_only_no_pubkeys_succeeds",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


@scenario("melt_htlc_preimage_only_fails", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with wrong HTLC preimage should fail."""
    _, hash_hex = generate_htlc_preimage()
    wrong_preimage = generate_secret()  # random 32-byte hex — won't hash to hash_hex
    secret_fn = lambda: build_htlc_secret(hash_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    set_htlc_witness(proofs, wrong_preimage)
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_blocked(code, body):
        return ScenarioResult(
            "melt_htlc_preimage_only_fails",
            CATEGORY,
            Result.PASS,
            "wrong preimage rejected",
        )
    return ScenarioResult(
        "melt_htlc_preimage_only_fails",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


@scenario("melt_htlc_signature_only_fails", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with valid signature but missing preimage should fail.

    HTLC always requires the preimage even when pubkeys/signatures are
    present.
    """
    preimage_hex, hash_hex = generate_htlc_preimage()
    key = KeyPair.generate()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    # Set signatures but NO preimage
    for p in proofs:
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        p.witness = json.dumps({"signatures": [key.sign_schnorr(msg)]})
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_blocked(code, body):
        return ScenarioResult(
            "melt_htlc_signature_only_fails",
            CATEGORY,
            Result.PASS,
            "missing preimage rejected",
        )
    return ScenarioResult(
        "melt_htlc_signature_only_fails",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


@scenario("melt_htlc_preimage_and_signature_succeeds", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with preimage + valid SIG_INPUTS signature should succeed."""
    preimage_hex, hash_hex = generate_htlc_preimage()
    key = KeyPair.generate()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    # Each proof needs its own preimage + signature over sha256(secret)
    for p in proofs:
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        p.witness = json.dumps(
            {"preimage": preimage_hex, "signatures": [key.sign_schnorr(msg)]}
        )
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_paid(code, body):
        return ScenarioResult(
            "melt_htlc_preimage_and_signature_succeeds",
            CATEGORY,
            Result.PASS,
            "preimage + sig melt paid",
        )
    return ScenarioResult(
        "melt_htlc_preimage_and_signature_succeeds",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


@scenario("melt_htlc_sigall_preimage_and_transaction_signature_succeeds", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Melt with preimage + SIG_ALL transaction signature should succeed."""
    preimage_hex, hash_hex = generate_htlc_preimage()
    key = KeyPair.generate()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1, sigflag="SIG_ALL"
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    quote_id = _create_melt_quote(mint)

    # SIG_ALL: sign the melt message (inputs + outputs + quote_id)
    change = _change_outputs(builder, proofs)
    output_amounts = [(o.amount, o.B_) for o in change]
    message = sigall_melt_message(proofs, output_amounts, quote_id)
    msg_hash = hashlib.sha256(message.encode("utf-8")).digest()
    sig = key.sign_schnorr(msg_hash)

    # Every proof needs the preimage; all share the same SIG_ALL signature
    for p in proofs:
        p.witness = json.dumps({"preimage": preimage_hex, "signatures": [sig]})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(change) if change else None
    code, body = mint.melt(quote_id, inputs, outputs)
    if _melt_paid(code, body):
        return ScenarioResult(
            "melt_htlc_sigall_preimage_and_transaction_signature_succeeds",
            CATEGORY,
            Result.PASS,
            "HTLC SIG_ALL melt paid",
        )
    return ScenarioResult(
        "melt_htlc_sigall_preimage_and_transaction_signature_succeeds",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


# ─── Additional melt scenarios (3) ────────────────────────────────────────


@scenario("melt_p2pk_post_locktime_anyone_can_spend", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """After locktime with no refund tag, anyone can spend — melt succeeds."""
    key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, locktime=past_locktime)
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    # No witness — locktime expired, no refund keys → anyone-can-spend
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_paid(code, body):
        return ScenarioResult(
            "melt_p2pk_post_locktime_anyone_can_spend",
            CATEGORY,
            Result.PASS,
            "anyone-can-spend melt paid",
        )
    return ScenarioResult(
        "melt_p2pk_post_locktime_anyone_can_spend",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


@scenario("melt_p2pk_before_locktime_wrong_key_fails", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Before locktime with wrong key should fail."""
    key = KeyPair.generate()
    wrong_key = KeyPair.generate()
    future_locktime = int(time.time()) + 3600
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, locktime=future_locktime)
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    _set_witness(proofs, wrong_key)
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_blocked(code, body):
        return ScenarioResult(
            "melt_p2pk_before_locktime_wrong_key_fails",
            CATEGORY,
            Result.PASS,
            "wrong key rejected",
        )
    return ScenarioResult(
        "melt_p2pk_before_locktime_wrong_key_fails",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )


@scenario("melt_p2pk_before_locktime_correct_key_succeeds", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Before locktime with correct key should succeed (primary always works)."""
    key = KeyPair.generate()
    future_locktime = int(time.time()) + 3600
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, locktime=future_locktime)
    builder = ProofBuilder(mint)
    proofs = _swap_for_condition(builder, mint, secret_fn)
    _set_witness(proofs, key)
    quote_id = _create_melt_quote(mint)
    code, body = _try_melt(mint, builder, proofs, quote_id)
    if _melt_paid(code, body):
        return ScenarioResult(
            "melt_p2pk_before_locktime_correct_key_succeeds",
            CATEGORY,
            Result.PASS,
            "correct key melt paid",
        )
    return ScenarioResult(
        "melt_p2pk_before_locktime_correct_key_succeeds",
        CATEGORY,
        Result.FAIL,
        f"got {code}: {str(body)[:200]}",
    )
