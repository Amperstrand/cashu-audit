"""NUT-11 P2PK SIG_INPUTS scenarios — 10 tests.

Tests the basic P2PK spending condition pathway with per-input signatures.
These are the scenarios that caught nutshell #1009 failures related to
locktime expiry behavior.
"""
from __future__ import annotations

import json
import time

from conformance.builder import (
    ProofBuilder,
    Proof,
    build_p2pk_secret,
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


def _swap_for_p2pk(
    builder: ProofBuilder,
    mint: MintClient,
    secret_fn,
    amount: int = 8,
) -> list[Proof]:
    regular = builder.mint_proofs(amount)
    total = sum(p.amount for p in regular)
    num_inputs = len(regular)
    swap_amount = total - builder.calc_fee(num_inputs)
    if swap_amount < 1:
        raise RuntimeError(f"Amount too small: {total} - {num_inputs} fee = {swap_amount}")
    p2pk_proofs = builder.swap_to_p2pk(regular, secret_fn, swap_amount)
    return p2pk_proofs


def _try_spend(mint: MintClient, builder: ProofBuilder, proofs: list[Proof]) -> tuple[int, object]:
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_total = max(1, total - fee)
    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(swap_total, lambda: generate_secret()))
    return mint.try_swap(inputs, outputs)


def _set_witness(proofs: list[Proof], key: KeyPair):
    import hashlib
    for p in proofs:
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        p.witness = json.dumps({"signatures": [key.sign_schnorr(msg)]})


@scenario("p2pk_swap_unsigned_fails", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    code, body = _try_spend(mint, builder, proofs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_swap_unsigned_fails", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "rejected")
    return ScenarioResult("p2pk_swap_unsigned_fails", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}")


@scenario("p2pk_swap_signed_succeeds", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    _set_witness(proofs, key)
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_swap_signed_succeeds", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "succeeded")
    return ScenarioResult("p2pk_swap_signed_succeeds", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_wrong_signer_fails", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    lock_key = KeyPair.generate()
    wrong_key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(lock_key.pub_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    _set_witness(proofs, wrong_key)
    code, body = _try_spend(mint, builder, proofs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_wrong_signer_fails", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "rejected")
    return ScenarioResult("p2pk_wrong_signer_fails", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}")


@scenario("p2pk_locktime_after_expiry_primary_still_works", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, locktime=past_locktime, refund_keys=[refund_key.pub_hex], n_sigs_refund=1)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    _set_witness(proofs, key)
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_locktime_after_expiry_primary_still_works", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "primary works after expiry")
    return ScenarioResult("p2pk_locktime_after_expiry_primary_still_works", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_locktime_after_expiry_refund_succeeds", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, locktime=past_locktime, refund_keys=[refund_key.pub_hex], n_sigs_refund=1)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    _set_witness(proofs, refund_key)
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_locktime_after_expiry_refund_succeeds", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "refund works after expiry")
    return ScenarioResult("p2pk_locktime_after_expiry_refund_succeeds", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_multisig_2of3", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(keys[0].pub_hex, pubkeys=[keys[1].pub_hex, keys[2].pub_hex], n_sigs=2)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    for p in proofs:
        import hashlib
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        sigs = [keys[0].sign_schnorr(msg), keys[1].sign_schnorr(msg)]
        p.witness = json.dumps({"signatures": sigs})
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_multisig_2of3", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "2-of-3 accepted")
    return ScenarioResult("p2pk_multisig_2of3", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_partial_signatures_fail", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(keys[0].pub_hex, pubkeys=[keys[1].pub_hex, keys[2].pub_hex], n_sigs=2)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    _set_witness(proofs, keys[0])
    code, body = _try_spend(mint, builder, proofs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_partial_signatures_fail", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "partial rejected")
    return ScenarioResult("p2pk_partial_signatures_fail", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}")


@scenario("p2pk_duplicate_signatures_fail", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(keys[0].pub_hex, pubkeys=[keys[1].pub_hex, keys[2].pub_hex], n_sigs=2)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    for p in proofs:
        import hashlib
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        sig = keys[0].sign_schnorr(msg)
        p.witness = json.dumps({"signatures": [sig, sig]})
    code, body = _try_spend(mint, builder, proofs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_duplicate_signatures_fail", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "duplicate rejected")
    return ScenarioResult("p2pk_duplicate_signatures_fail", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}")


@scenario("p2pk_locktime_before_expiry_refund_blocked", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    future_locktime = int(time.time()) + 3600
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, locktime=future_locktime, refund_keys=[refund_key.pub_hex], n_sigs_refund=1)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    _set_witness(proofs, refund_key)
    code, body = _try_spend(mint, builder, proofs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_locktime_before_expiry_refund_blocked", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "refund blocked before expiry")
    return ScenarioResult("p2pk_locktime_before_expiry_refund_blocked", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}")


@scenario("p2pk_locktime_after_expiry_no_refund_anyone_can_spend", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, locktime=past_locktime)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    code, body = _try_spend(mint, builder, proofs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_locktime_after_expiry_no_refund_anyone_can_spend", "NUT-11 P2PK SIG_INPUTS", Result.PASS, "anyone-can-spend")
    return ScenarioResult("p2pk_locktime_after_expiry_no_refund_anyone_can_spend", "NUT-11 P2PK SIG_INPUTS", Result.FAIL, f"got {code}: {str(body)[:200]}")
