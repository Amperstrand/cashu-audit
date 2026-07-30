"""NUT-11 P2PK SIG_ALL conformance scenarios — 16 tests.

SIG_ALL signs the entire transaction (all inputs' secret+C and all
outputs' amount+B_) with a single signature placed on the first proof.
"""
from __future__ import annotations

import hashlib
import json
import time

from conformance.builder import (
    ProofBuilder,
    Proof,
    build_p2pk_secret,
    build_htlc_secret,
    sigall_swap_message,
    sigall_swap_message_for,
    set_sigall_witness,
    generate_htlc_preimage,
    try_sigall_spend,
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


def _prepare_outputs(builder: ProofBuilder, proofs: list[Proof]):
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_total = max(1, total - fee)
    outputs = builder.create_outputs(swap_total, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    output_amounts = [(o.amount, o.B_) for o in outputs]
    return api_outputs, output_amounts


def _attempt_swap(mint: MintClient, proofs: list[Proof], api_outputs: list[dict]) -> tuple[int, object]:
    inputs = [p.to_dict() for p in proofs]
    return mint.try_swap(inputs, api_outputs)


def _signed_sigall_swap(mint, proofs, keys, api_outputs, output_amounts) -> tuple[int, object]:
    return try_sigall_spend(mint, proofs, keys, output_amounts, api_outputs)


def _sign_sigall(mint, proofs, keys, output_amounts):
    msg = sigall_swap_message_for(mint.base_url, proofs, output_amounts)
    msg_hash = hashlib.sha256(msg.encode("utf-8")).digest()
    sigs = [k.sign_schnorr(msg_hash) for k in keys]
    proofs[0].witness = json.dumps({"signatures": sigs})


@scenario("p2pk_sigall_requires_transaction_signature", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, _ = _prepare_outputs(builder, proofs)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_sigall_requires_transaction_signature", "NUT-11 P2PK SIG_ALL", Result.PASS, "rejected")
    return ScenarioResult("p2pk_sigall_requires_transaction_signature", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}")


@scenario("p2pk_sigall_sig_inputs_fail", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    for p in proofs:
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        p.witness = json.dumps({"signatures": [key.sign_schnorr(msg)]})
    api_outputs, _ = _prepare_outputs(builder, proofs)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_sigall_sig_inputs_fail", "NUT-11 P2PK SIG_ALL", Result.PASS, "rejected")
    return ScenarioResult("p2pk_sigall_sig_inputs_fail", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}")


@scenario("p2pk_sigall_multisig_2of3", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(
        keys[0].pub_hex,
        pubkeys=[keys[1].pub_hex, keys[2].pub_hex],
        n_sigs=2,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    _sign_sigall(mint, proofs, [keys[0], keys[1]], output_amounts)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_sigall_multisig_2of3", "NUT-11 P2PK SIG_ALL", Result.PASS, "2-of-3 accepted")
    return ScenarioResult("p2pk_sigall_multisig_2of3", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_sigall_wrong_signer_fails", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    wrong_key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    _sign_sigall(mint, proofs, [wrong_key], output_amounts)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_sigall_wrong_signer_fails", "NUT-11 P2PK SIG_ALL", Result.PASS, "rejected")
    return ScenarioResult("p2pk_sigall_wrong_signer_fails", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}")


@scenario("p2pk_sigall_duplicate_signatures_fail", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(
        keys[0].pub_hex,
        pubkeys=[keys[1].pub_hex, keys[2].pub_hex],
        n_sigs=2,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    msg = sigall_swap_message(proofs, output_amounts)
    msg_hash = hashlib.sha256(msg.encode("utf-8")).digest()
    sig = keys[0].sign_schnorr(msg_hash)
    proofs[0].witness = json.dumps({"signatures": [sig, sig]})
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_sigall_duplicate_signatures_fail", "NUT-11 P2PK SIG_ALL", Result.PASS, "duplicate rejected")
    return ScenarioResult("p2pk_sigall_duplicate_signatures_fail", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}")


@scenario("p2pk_sigall_locktime_before_expiry_primary_only", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    future_locktime = int(time.time()) + 3600
    secret_fn = lambda: build_p2pk_secret(
        key.pub_hex,
        locktime=future_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)

    proofs1 = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs1, output_amounts1 = _prepare_outputs(builder, proofs1)
    _sign_sigall(mint, proofs1, [key], output_amounts1)
    code1, body1 = _attempt_swap(mint, proofs1, api_outputs1)
    if not expect_success(code1, body1):
        return ScenarioResult("p2pk_sigall_locktime_before_expiry_primary_only", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"primary failed: {code1}")

    proofs2 = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs2, output_amounts2 = _prepare_outputs(builder, proofs2)
    _sign_sigall(mint, proofs2, [refund_key], output_amounts2)
    code2, body2 = _attempt_swap(mint, proofs2, api_outputs2)
    if not expect_reject(code2, body2):
        return ScenarioResult("p2pk_sigall_locktime_before_expiry_primary_only", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"refund should be blocked: {code2}")

    return ScenarioResult("p2pk_sigall_locktime_before_expiry_primary_only", "NUT-11 P2PK SIG_ALL", Result.PASS, "primary works, refund blocked")


@scenario("p2pk_sigall_locktime_after_expiry_primary_still_works", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(
        key.pub_hex,
        locktime=past_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    _sign_sigall(mint, proofs, [key], output_amounts)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_sigall_locktime_after_expiry_primary_still_works", "NUT-11 P2PK SIG_ALL", Result.PASS, "primary works after expiry")
    return ScenarioResult("p2pk_sigall_locktime_after_expiry_primary_still_works", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, locktime=past_locktime, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, _ = _prepare_outputs(builder, proofs)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend", "NUT-11 P2PK SIG_ALL", Result.PASS, "anyone-can-spend")
    return ScenarioResult("p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_sigall_multisig_locktime_primary_still_works", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    refund_key = KeyPair.generate()
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(
        keys[0].pub_hex,
        pubkeys=[keys[1].pub_hex, keys[2].pub_hex],
        n_sigs=2,
        locktime=past_locktime,
        refund_keys=[refund_key.pub_hex],
        n_sigs_refund=1,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    _sign_sigall(mint, proofs, [keys[0], keys[1]], output_amounts)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_sigall_multisig_locktime_primary_still_works", "NUT-11 P2PK SIG_ALL", Result.PASS, "multisig primary works after locktime")
    return ScenarioResult("p2pk_sigall_multisig_locktime_primary_still_works", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_sigall_mixed_proofs_different_data_fail", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key_a = KeyPair.generate()
    key_b = KeyPair.generate()
    builder = ProofBuilder(mint)
    proofs_a = _swap_for_p2pk(builder, mint, lambda: build_p2pk_secret(key_a.pub_hex, sigflag="SIG_ALL"), amount=4)
    proofs_b = _swap_for_p2pk(builder, mint, lambda: build_p2pk_secret(key_b.pub_hex, sigflag="SIG_ALL"), amount=4)
    combined = proofs_a + proofs_b
    api_outputs, output_amounts = _prepare_outputs(builder, combined)
    _sign_sigall(mint, combined, [key_a], output_amounts)
    code, body = _attempt_swap(mint, combined, api_outputs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_sigall_mixed_proofs_different_data_fail", "NUT-11 P2PK SIG_ALL", Result.PASS, "mixed data rejected")
    return ScenarioResult("p2pk_sigall_mixed_proofs_different_data_fail", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}")


@scenario("p2pk_sigall_mixed_proofs_different_kind_fail", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    preimage_hex, hash_hex = generate_htlc_preimage()
    builder = ProofBuilder(mint)
    proofs_p2pk = _swap_for_p2pk(builder, mint, lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL"), amount=4)
    proofs_htlc = _swap_for_p2pk(builder, mint, lambda: build_htlc_secret(hash_hex, sigflag="SIG_ALL"), amount=4)
    combined = proofs_p2pk + proofs_htlc
    api_outputs, output_amounts = _prepare_outputs(builder, combined)
    _sign_sigall(mint, combined, [key], output_amounts)
    code, body = _attempt_swap(mint, combined, api_outputs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_sigall_mixed_proofs_different_kind_fail", "NUT-11 P2PK SIG_ALL", Result.PASS, "mixed kind rejected")
    return ScenarioResult("p2pk_sigall_mixed_proofs_different_kind_fail", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}")


@scenario("p2pk_sigall_mixed_proofs_different_tags_fail", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    extra_key = KeyPair.generate()
    builder = ProofBuilder(mint)
    proofs_a = _swap_for_p2pk(builder, mint, lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL"), amount=4)
    proofs_b = _swap_for_p2pk(builder, mint, lambda: build_p2pk_secret(key.pub_hex, pubkeys=[extra_key.pub_hex], n_sigs=2, sigflag="SIG_ALL"), amount=4)
    combined = proofs_a + proofs_b
    api_outputs, output_amounts = _prepare_outputs(builder, combined)
    _sign_sigall(mint, combined, [key], output_amounts)
    code, body = _attempt_swap(mint, combined, api_outputs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_sigall_mixed_proofs_different_tags_fail", "NUT-11 P2PK SIG_ALL", Result.PASS, "mixed tags rejected")
    return ScenarioResult("p2pk_sigall_mixed_proofs_different_tags_fail", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}")


@scenario("p2pk_sigall_multisig_before_locktime", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    future_locktime = int(time.time()) + 3600
    secret_fn = lambda: build_p2pk_secret(
        keys[0].pub_hex,
        pubkeys=[keys[1].pub_hex, keys[2].pub_hex],
        n_sigs=2,
        locktime=future_locktime,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    _sign_sigall(mint, proofs, [keys[0], keys[1]], output_amounts)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_sigall_multisig_before_locktime", "NUT-11 P2PK SIG_ALL", Result.PASS, "2-of-3 before locktime accepted")
    return ScenarioResult("p2pk_sigall_multisig_before_locktime", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_sigall_more_signatures_than_required", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    keys = [KeyPair.generate() for _ in range(3)]
    secret_fn = lambda: build_p2pk_secret(
        keys[0].pub_hex,
        pubkeys=[keys[1].pub_hex, keys[2].pub_hex],
        n_sigs=1,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    _sign_sigall(mint, proofs, [keys[0], keys[1], keys[2]], output_amounts)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_sigall_more_signatures_than_required", "NUT-11 P2PK SIG_ALL", Result.PASS, "extra sigs accepted")
    return ScenarioResult("p2pk_sigall_more_signatures_than_required", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_sigall_refund_multisig_2of2", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    refund_keys = [KeyPair.generate() for _ in range(2)]
    past_locktime = int(time.time()) - 10
    secret_fn = lambda: build_p2pk_secret(
        key.pub_hex,
        locktime=past_locktime,
        refund_keys=[refund_keys[0].pub_hex, refund_keys[1].pub_hex],
        n_sigs_refund=2,
        sigflag="SIG_ALL",
    )
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    _sign_sigall(mint, proofs, refund_keys, output_amounts)
    code, body = _attempt_swap(mint, proofs, api_outputs)
    if expect_success(code, body):
        return ScenarioResult("p2pk_sigall_refund_multisig_2of2", "NUT-11 P2PK SIG_ALL", Result.PASS, "2-of-2 refund accepted")
    return ScenarioResult("p2pk_sigall_refund_multisig_2of2", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}: {str(body)[:200]}")


@scenario("p2pk_sigall_output_amounts_swapped_fail", "NUT-11 P2PK SIG_ALL")
def _(mint: MintClient) -> ScenarioResult:
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex, sigflag="SIG_ALL")
    builder = ProofBuilder(mint)
    proofs = _swap_for_p2pk(builder, mint, secret_fn)
    api_outputs, output_amounts = _prepare_outputs(builder, proofs)
    _sign_sigall(mint, proofs, [key], output_amounts)
    tampered_outputs = [dict(o) for o in api_outputs]
    if len(tampered_outputs) >= 2:
        tampered_outputs[0]["B_"], tampered_outputs[1]["B_"] = \
            tampered_outputs[1]["B_"], tampered_outputs[0]["B_"]
    elif tampered_outputs:
        original_b = tampered_outputs[0]["B_"]
        if len(original_b) > 1 and original_b[1] == "2":
            tampered_outputs[0]["B_"] = "03" + original_b[2:]
        elif len(original_b) > 1 and original_b[1] == "3":
            tampered_outputs[0]["B_"] = "02" + original_b[2:]
        else:
            tampered_outputs[0]["B_"] = "00" + original_b[2:]
    code, body = _attempt_swap(mint, proofs, tampered_outputs)
    if expect_reject(code, body):
        return ScenarioResult("p2pk_sigall_output_amounts_swapped_fail", "NUT-11 P2PK SIG_ALL", Result.PASS, "tampered outputs rejected")
    return ScenarioResult("p2pk_sigall_output_amounts_swapped_fail", "NUT-11 P2PK SIG_ALL", Result.FAIL, f"got {code}")
