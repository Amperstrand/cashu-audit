"""NUT-12 HTLC scenarios — 16 tests (8 SIG_INPUTS + 8 SIG_ALL).

Tests Hashed Time-Locked Contract spending conditions:
- Hash-lock (preimage) pathway
- Signature pathway combined with hash-lock
- Refund pathway after locktime expiry
- Multisig variants
- Receiver-path independence from locktime

SIG_INPUTS: per-input signatures (witness on each proof, signed over
that proof's secret).
SIG_ALL: transaction-level signature (witness on first proof only,
signed over the concatenation of all inputs and outputs).
"""
from __future__ import annotations

import hashlib
import json
import time

from conformance.builder import (
    ProofBuilder,
    Proof,
    build_htlc_secret,
    generate_htlc_preimage,
    set_htlc_witness,
    sigall_swap_message,
)
from conformance.client import MintClient
from conformance.crypto import KeyPair, generate_secret
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
    expect_reject,
    expect_success,
)

CAT_IN = "NUT-12 HTLC SIG_INPUTS"
CAT_ALL = "NUT-12 HTLC SIG_ALL"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _swap_for_htlc(
    builder: ProofBuilder,
    mint: MintClient,
    secret_fn,
    amount: int = 8,
) -> list[Proof]:
    """Mint regular proofs then swap for HTLC-conditioned proofs."""
    regular = builder.mint_proofs(amount)
    total = sum(p.amount for p in regular)
    num_inputs = len(regular)
    swap_amount = total - builder.calc_fee(num_inputs)
    if swap_amount < 1:
        raise RuntimeError(
            f"Amount too small: {total} - {num_inputs} fee = {swap_amount}"
        )
    return builder.swap_to_p2pk(regular, secret_fn, swap_amount)


def _try_spend(
    mint: MintClient, builder: ProofBuilder, proofs: list[Proof]
) -> tuple[int, object]:
    """Spend proofs via swap — SIG_INPUTS (witness already set per-proof)."""
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_total = max(1, total - fee)
    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(
        builder.create_outputs(swap_total, lambda: generate_secret())
    )
    return mint.try_swap(inputs, outputs)


def _set_htlc_siginputs_witness(
    proofs: list[Proof], preimage: str, keys: list[KeyPair]
):
    """Per-proof SIG_INPUTS witness: preimage + per-proof signature."""
    for p in proofs:
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        sigs = [k.sign_schnorr(msg) for k in keys]
        p.witness = json.dumps({"preimage": preimage, "signatures": sigs})


def _set_siginputs_no_preimage(proofs: list[Proof], keys: list[KeyPair]):
    """Per-proof witness: signatures only, no preimage."""
    for p in proofs:
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        sigs = [k.sign_schnorr(msg) for k in keys]
        p.witness = json.dumps({"signatures": sigs})


def _try_spend_sigall(
    mint: MintClient,
    builder: ProofBuilder,
    proofs: list[Proof],
    sign_keys: list[KeyPair] | None = None,
    preimage: str | None = None,
) -> tuple[int, object]:
    """SIG_ALL spend: build message, sign, witness on proofs[0], swap."""
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_total = max(1, total - fee)

    swap_outputs = builder.create_outputs(swap_total, lambda: generate_secret())
    output_amounts = [(o.amount, o.B_) for o in swap_outputs]
    message = sigall_swap_message(proofs, output_amounts)

    witness: dict = {}
    if preimage is not None:
        witness["preimage"] = preimage
    if sign_keys:
        msg_hash = hashlib.sha256(message.encode("utf-8")).digest()
        witness["signatures"] = [k.sign_schnorr(msg_hash) for k in sign_keys]
    proofs[0].witness = json.dumps(witness)

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(swap_outputs)
    return mint.try_swap(inputs, outputs)


# ===========================================================================
# SIG_INPUTS scenarios (1-8)
# ===========================================================================

@scenario("htlc_preimage_only_no_pubkeys_succeeds", CAT_IN)
def _(mint: MintClient) -> ScenarioResult:
    """HTLC with just a hash-lock, no pubkeys — preimage alone spends."""
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(hash_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    set_htlc_witness(proofs, preimage_hex)
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_preimage_only_no_pubkeys_succeeds", CAT_IN,
            Result.PASS, "preimage accepted",
        )
    return ScenarioResult(
        "htlc_preimage_only_no_pubkeys_succeeds", CAT_IN,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("htlc_preimage_only_fails", CAT_IN)
def _(mint: MintClient) -> ScenarioResult:
    """Wrong preimage rejected for hash-only HTLC."""
    _preimage_hex, hash_hex = generate_htlc_preimage()
    wrong_preimage = generate_secret()
    secret_fn = lambda: build_htlc_secret(hash_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    set_htlc_witness(proofs, wrong_preimage)
    code, body = _try_spend(mint, builder, proofs)
    if expect_reject(code, body):
        return ScenarioResult(
            "htlc_preimage_only_fails", CAT_IN,
            Result.PASS, "wrong preimage rejected",
        )
    return ScenarioResult(
        "htlc_preimage_only_fails", CAT_IN,
        Result.FAIL, f"got {code}",
    )


@scenario("htlc_signature_only_fails", CAT_IN)
def _(mint: MintClient) -> ScenarioResult:
    """Signature provided but preimage missing — must be rejected."""
    key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    _set_siginputs_no_preimage(proofs, [key])
    code, body = _try_spend(mint, builder, proofs)
    if expect_reject(code, body):
        return ScenarioResult(
            "htlc_signature_only_fails", CAT_IN,
            Result.PASS, "signature without preimage rejected",
        )
    return ScenarioResult(
        "htlc_signature_only_fails", CAT_IN,
        Result.FAIL, f"got {code}",
    )


@scenario("htlc_swap_preimage_and_signature_succeeds", CAT_IN)
def _(mint: MintClient) -> ScenarioResult:
    """HTLC with pubkeys — preimage + valid signature spends."""
    key = KeyPair.generate()
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    _set_htlc_siginputs_witness(proofs, preimage_hex, [key])
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_swap_preimage_and_signature_succeeds", CAT_IN,
            Result.PASS, "preimage + signature accepted",
        )
    return ScenarioResult(
        "htlc_swap_preimage_and_signature_succeeds", CAT_IN,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("htlc_wrong_preimage_fails", CAT_IN)
def _(mint: MintClient) -> ScenarioResult:
    """Correct signature but wrong preimage — must be rejected."""
    key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    wrong_preimage = generate_secret()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    _set_htlc_siginputs_witness(proofs, wrong_preimage, [key])
    code, body = _try_spend(mint, builder, proofs)
    if expect_reject(code, body):
        return ScenarioResult(
            "htlc_wrong_preimage_fails", CAT_IN,
            Result.PASS, "wrong preimage with valid sig rejected",
        )
    return ScenarioResult(
        "htlc_wrong_preimage_fails", CAT_IN,
        Result.FAIL, f"got {code}",
    )


@scenario("htlc_locktime_after_expiry_refund_succeeds", CAT_IN)
def _(mint: MintClient) -> ScenarioResult:
    """After locktime expiry, refund key spends without preimage."""
    refund_key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_htlc_secret(
        hash_hex,
        locktime=past_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    _set_siginputs_no_preimage(proofs, [refund_key])
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_locktime_after_expiry_refund_succeeds", CAT_IN,
            Result.PASS, "refund works after expiry",
        )
    return ScenarioResult(
        "htlc_locktime_after_expiry_refund_succeeds", CAT_IN,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("htlc_multisig_2of3", CAT_IN)
def _(mint: MintClient) -> ScenarioResult:
    """HTLC requiring 2-of-3 signatures plus preimage."""
    keys = [KeyPair.generate() for _ in range(3)]
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(
        hash_hex,
        pubkeys=[k.pub_hex for k in keys],
        n_sigs=2,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    _set_htlc_siginputs_witness(proofs, preimage_hex, keys[:2])
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_multisig_2of3", CAT_IN,
            Result.PASS, "2-of-3 multisig + preimage accepted",
        )
    return ScenarioResult(
        "htlc_multisig_2of3", CAT_IN,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("htlc_receiver_path_after_locktime", CAT_IN)
def _(mint: MintClient) -> ScenarioResult:
    """Receiver (preimage) path still valid after locktime expiry."""
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    preimage_hex, hash_hex = generate_htlc_preimage()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_htlc_secret(
        hash_hex,
        pubkeys=[key.pub_hex],
        n_sigs=1,
        locktime=past_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    _set_htlc_siginputs_witness(proofs, preimage_hex, [key])
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_receiver_path_after_locktime", CAT_IN,
            Result.PASS, "receiver path works after locktime",
        )
    return ScenarioResult(
        "htlc_receiver_path_after_locktime", CAT_IN,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


# ===========================================================================
# SIG_ALL scenarios (9-16)
# ===========================================================================

@scenario("htlc_sigall_preimage_only_no_pubkeys_succeeds", CAT_ALL)
def _(mint: MintClient) -> ScenarioResult:
    """HTLC hash-lock with SIG_ALL — preimage alone spends."""
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(hash_hex, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    code, body = _try_spend_sigall(mint, builder, proofs, preimage=preimage_hex)
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_sigall_preimage_only_no_pubkeys_succeeds", CAT_ALL,
            Result.PASS, "preimage accepted (SIG_ALL)",
        )
    return ScenarioResult(
        "htlc_sigall_preimage_only_no_pubkeys_succeeds", CAT_ALL,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("htlc_sigall_preimage_only_fails", CAT_ALL)
def _(mint: MintClient) -> ScenarioResult:
    """Wrong preimage rejected with SIG_ALL."""
    _preimage_hex, hash_hex = generate_htlc_preimage()
    wrong_preimage = generate_secret()
    secret_fn = lambda: build_htlc_secret(hash_hex, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    code, body = _try_spend_sigall(
        mint, builder, proofs, preimage=wrong_preimage
    )
    if expect_reject(code, body):
        return ScenarioResult(
            "htlc_sigall_preimage_only_fails", CAT_ALL,
            Result.PASS, "wrong preimage rejected (SIG_ALL)",
        )
    return ScenarioResult(
        "htlc_sigall_preimage_only_fails", CAT_ALL,
        Result.FAIL, f"got {code}",
    )


@scenario("htlc_sigall_signature_only_fails", CAT_ALL)
def _(mint: MintClient) -> ScenarioResult:
    """SIG_ALL signature without preimage — must be rejected."""
    key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1, sigflag="SIG_ALL"
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    code, body = _try_spend_sigall(mint, builder, proofs, sign_keys=[key])
    if expect_reject(code, body):
        return ScenarioResult(
            "htlc_sigall_signature_only_fails", CAT_ALL,
            Result.PASS, "signature without preimage rejected (SIG_ALL)",
        )
    return ScenarioResult(
        "htlc_sigall_signature_only_fails", CAT_ALL,
        Result.FAIL, f"got {code}",
    )


@scenario("htlc_sigall_requires_preimage_and_transaction_signature", CAT_ALL)
def _(mint: MintClient) -> ScenarioResult:
    """HTLC with SIG_ALL — preimage + transaction signature spends."""
    key = KeyPair.generate()
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1, sigflag="SIG_ALL"
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    code, body = _try_spend_sigall(
        mint, builder, proofs, sign_keys=[key], preimage=preimage_hex
    )
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_sigall_requires_preimage_and_transaction_signature", CAT_ALL,
            Result.PASS, "preimage + SIG_ALL signature accepted",
        )
    return ScenarioResult(
        "htlc_sigall_requires_preimage_and_transaction_signature", CAT_ALL,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("htlc_sigall_wrong_preimage_fails", CAT_ALL)
def _(mint: MintClient) -> ScenarioResult:
    """Wrong preimage with correct SIG_ALL signature — rejected."""
    key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    wrong_preimage = generate_secret()
    secret_fn = lambda: build_htlc_secret(
        hash_hex, pubkeys=[key.pub_hex], n_sigs=1, sigflag="SIG_ALL"
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    code, body = _try_spend_sigall(
        mint, builder, proofs, sign_keys=[key], preimage=wrong_preimage
    )
    if expect_reject(code, body):
        return ScenarioResult(
            "htlc_sigall_wrong_preimage_fails", CAT_ALL,
            Result.PASS, "wrong preimage with valid sig rejected (SIG_ALL)",
        )
    return ScenarioResult(
        "htlc_sigall_wrong_preimage_fails", CAT_ALL,
        Result.FAIL, f"got {code}",
    )


@scenario("htlc_sigall_locktime_after_expiry_refund_succeeds", CAT_ALL)
def _(mint: MintClient) -> ScenarioResult:
    """After locktime, refund key spends via SIG_ALL without preimage."""
    refund_key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_htlc_secret(
        hash_hex,
        locktime=past_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    code, body = _try_spend_sigall(mint, builder, proofs, sign_keys=[refund_key])
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_sigall_locktime_after_expiry_refund_succeeds", CAT_ALL,
            Result.PASS, "refund works after expiry (SIG_ALL)",
        )
    return ScenarioResult(
        "htlc_sigall_locktime_after_expiry_refund_succeeds", CAT_ALL,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("htlc_sigall_multisig_2of3", CAT_ALL)
def _(mint: MintClient) -> ScenarioResult:
    """HTLC 2-of-3 multisig with SIG_ALL + preimage."""
    keys = [KeyPair.generate() for _ in range(3)]
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(
        hash_hex,
        pubkeys=[k.pub_hex for k in keys],
        n_sigs=2,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    code, body = _try_spend_sigall(
        mint, builder, proofs, sign_keys=keys[:2], preimage=preimage_hex
    )
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_sigall_multisig_2of3", CAT_ALL,
            Result.PASS, "2-of-3 multisig + preimage accepted (SIG_ALL)",
        )
    return ScenarioResult(
        "htlc_sigall_multisig_2of3", CAT_ALL,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("htlc_sigall_receiver_path_after_locktime", CAT_ALL)
def _(mint: MintClient) -> ScenarioResult:
    """Receiver (preimage) path still valid after locktime with SIG_ALL."""
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    preimage_hex, hash_hex = generate_htlc_preimage()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_htlc_secret(
        hash_hex,
        pubkeys=[key.pub_hex],
        n_sigs=1,
        locktime=past_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_htlc(builder, mint, secret_fn)
    code, body = _try_spend_sigall(
        mint, builder, proofs, sign_keys=[key], preimage=preimage_hex
    )
    if expect_success(code, body):
        return ScenarioResult(
            "htlc_sigall_receiver_path_after_locktime", CAT_ALL,
            Result.PASS, "receiver path works after locktime (SIG_ALL)",
        )
    return ScenarioResult(
        "htlc_sigall_receiver_path_after_locktime", CAT_ALL,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )
