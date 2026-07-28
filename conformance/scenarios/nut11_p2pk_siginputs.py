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
    p2pk_proofs = builder.swap_to_p2pk(regular, secret_fn, total)
    return p2pk_proofs


@scenario("p2pk_swap_unsigned_fails", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_reject(code, body):
        return ScenarioResult("p2pk_swap_unsigned_fails", "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "swap rejected as expected")
    return ScenarioResult("p2pk_swap_unsigned_fails", "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"expected rejection, got {code}")


@scenario("p2pk_swap_signed_succeeds", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    for p in proofs:
        p.witness = json.dumps({"signatures": [key.sign_schnorr(p.secret.encode("utf-8"))]})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_success(code, body):
        return ScenarioResult("p2pk_swap_signed_succeeds", "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "swap succeeded with valid signature")
    return ScenarioResult("p2pk_swap_signed_succeeds", "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"expected success, got {code}: {str(body)[:200]}")


@scenario("p2pk_wrong_signer_fails", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    lock_key = KeyPair.generate()
    wrong_key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(lock_key.pub_hex)
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    for p in proofs:
        p.witness = json.dumps({"signatures": [wrong_key.sign_schnorr(p.secret.encode("utf-8"))]})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_reject(code, body):
        return ScenarioResult("p2pk_wrong_signer_fails", "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "wrong signer rejected")
    return ScenarioResult("p2pk_wrong_signer_fails", "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"expected rejection for wrong signer, got {code}")


@scenario("p2pk_locktime_after_expiry_primary_still_works", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(
        key.pub_hex,
        locktime=past_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    for p in proofs:
        p.witness = json.dumps({"signatures": [key.sign_schnorr(p.secret.encode("utf-8"))]})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_success(code, body):
        return ScenarioResult("p2pk_locktime_after_expiry_primary_still_works",
                              "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "primary path still works after locktime")
    return ScenarioResult("p2pk_locktime_after_expiry_primary_still_works",
                          "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"primary path failed after locktime: {code}: {str(body)[:200]}")


@scenario("p2pk_locktime_after_expiry_refund_succeeds", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(
        key.pub_hex,
        locktime=past_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    for p in proofs:
        p.witness = json.dumps({"signatures": [refund_key.sign_schnorr(p.secret.encode("utf-8"))]})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_success(code, body):
        return ScenarioResult("p2pk_locktime_after_expiry_refund_succeeds",
                              "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "refund path works after locktime")
    return ScenarioResult("p2pk_locktime_after_expiry_refund_succeeds",
                          "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"refund path failed: {code}: {str(body)[:200]}")


@scenario("p2pk_multisig_2of3", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(
        keys[0].pub_hex,
        pubkeys=[keys[1].pub_hex, keys[2].pub_hex],
        n_sigs=2,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    for p in proofs:
        sigs = [keys[0].sign_schnorr(p.secret.encode("utf-8")),
                keys[1].sign_schnorr(p.secret.encode("utf-8"))]
        p.witness = json.dumps({"signatures": sigs})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_success(code, body):
        return ScenarioResult("p2pk_multisig_2of3", "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "2-of-3 multisig accepted")
    return ScenarioResult("p2pk_multisig_2of3", "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"2-of-3 multisig failed: {code}: {str(body)[:200]}")


@scenario("p2pk_partial_signatures_fail", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(
        keys[0].pub_hex,
        pubkeys=[keys[1].pub_hex, keys[2].pub_hex],
        n_sigs=2,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    for p in proofs:
        sigs = [keys[0].sign_schnorr(p.secret.encode("utf-8"))]
        p.witness = json.dumps({"signatures": sigs})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_reject(code, body):
        return ScenarioResult("p2pk_partial_signatures_fail", "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "partial signatures rejected")
    return ScenarioResult("p2pk_partial_signatures_fail", "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"expected rejection for partial sigs, got {code}")


@scenario("p2pk_duplicate_signatures_fail", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(
        keys[0].pub_hex,
        pubkeys=[keys[1].pub_hex, keys[2].pub_hex],
        n_sigs=2,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    for p in proofs:
        sig = keys[0].sign_schnorr(p.secret.encode("utf-8"))
        p.witness = json.dumps({"signatures": [sig, sig]})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_reject(code, body):
        return ScenarioResult("p2pk_duplicate_signatures_fail", "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "duplicate signatures rejected")
    return ScenarioResult("p2pk_duplicate_signatures_fail", "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"expected rejection for duplicate sigs, got {code}")


@scenario("p2pk_locktime_before_expiry_refund_blocked", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    future_locktime = int(time.time()) + 3600
    secret_fn = lambda: build_p2pk_secret(
        key.pub_hex,
        locktime=future_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    for p in proofs:
        p.witness = json.dumps({"signatures": [refund_key.sign_schnorr(p.secret.encode("utf-8"))]})

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_reject(code, body):
        return ScenarioResult("p2pk_locktime_before_expiry_refund_blocked",
                              "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "refund path correctly blocked before locktime")
    return ScenarioResult("p2pk_locktime_before_expiry_refund_blocked",
                          "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"refund should be blocked before locktime, got {code}")


@scenario("p2pk_locktime_after_expiry_no_refund_anyone_can_spend", "NUT-11 P2PK SIG_INPUTS")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(
        key.pub_hex,
        locktime=past_locktime,
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn, amount=4)

    inputs = [p.to_dict() for p in proofs]
    outputs = builder.outputs_to_api(builder.create_outputs(4, lambda: generate_secret()))
    code, body = mint.swap(inputs, outputs)

    if expect_success(code, body):
        return ScenarioResult("p2pk_locktime_after_expiry_no_refund_anyone_can_spend",
                              "NUT-11 P2PK SIG_INPUTS", Result.PASS,
                              "anyone-can-spend after locktime (no refund tag)")
    return ScenarioResult("p2pk_locktime_after_expiry_no_refund_anyone_can_spend",
                          "NUT-11 P2PK SIG_INPUTS", Result.FAIL,
                          f"expected anyone-can-spend, got {code}: {str(body)[:200]}")
