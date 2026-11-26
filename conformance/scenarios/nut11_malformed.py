"""NUT-11 malformed-secret scenarios — the 2026-11-19 spec churn (#474).

Pins the malformation rules from cashubtc/nuts commit 67b82e1b
("NUT-11, NUT-14: a key-only spending condition tag is malformed"):

  1. a spending-condition tag appearing MORE THAN ONCE -> the proof MUST
     be rejected as unspendable (the pre-existing rule, re-worded);
  2. a spending-condition tag with NO VALUE ("key only") -> the proof
     MUST be rejected as unspendable (the NEW rule);
  3. non-condition NUT-10 tags in the secret are legal and MUST be
     ignored when evaluating the P2PK lock (the other NEW rule).

Each scenario mints regular proofs, swaps them into a P2PK proof whose
secret carries the shaped tags, then attempts to spend that proof via
/v1/swap with a valid SIG_INPUTS witness — expecting rejection for the
malformed shapes and success for the decorated-but-legal shape.
"""
from __future__ import annotations

import hashlib
import json

from conformance.builder import (
    OutputResult,
    ProofBuilder,
    Proof,
    build_p2pk_secret,
)
from conformance.client import MintClient
from conformance.crypto import KeyPair, generate_secret
from conformance.scenarios import (
    fmt_body,
    scenario,
    ScenarioResult,
    Result,
)

CATEGORY = "NUT-11 malformed secrets (#474)"


def _secret_with_tags(data_pubkey: str, tags: list[list[str]]) -> str:
    """A P2PK secret with EXACTLY the tags given (no defaults)."""
    secret_obj = ["P2PK", {
        "nonce": generate_secret(),
        "data": data_pubkey,
        "tags": tags,
    }]
    return json.dumps(secret_obj, separators=(",", ":"))


def _swap_for_condition(
    builder: ProofBuilder,
    mint: MintClient,
    secret_fn,
    amount: int = 8,
) -> list[Proof]:
    """Mint regular proofs and swap them for the shaped-secret proof."""
    regular = builder.mint_proofs(amount)
    total = sum(p.amount for p in regular)
    swap_amount = total - builder.calc_fee(len(regular))
    if swap_amount < 1:
        raise RuntimeError(f"Amount too small: {total} - fee = {swap_amount}")
    return builder.swap_to_p2pk(regular, secret_fn, swap_amount)


def _set_witness(proofs: list[Proof], key: KeyPair) -> None:
    """Per-input SIG_INPUTS witness (signature over sha256(secret))."""
    for p in proofs:
        msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
        p.witness = json.dumps({"signatures": [key.sign_schnorr(msg)]})


def _spend(builder: ProofBuilder, mint: MintClient, p2pk: list[Proof]) -> tuple[int, object]:
    """Spend the P2PK proofs back to regular outputs (witness already set)."""
    inputs = [p.to_dict() for p in p2pk]
    total = sum(p.amount for p in p2pk)
    fee = builder.calc_fee(len(p2pk))
    outputs = builder.create_outputs(total - fee, lambda: generate_secret())
    return mint.try_swap(inputs, builder.outputs_to_api(outputs))


@scenario("nut11 duplicate spending tag rejected", CATEGORY)
def duplicate_spending_tag(mint: MintClient) -> ScenarioResult:
    """#474 rule 1: 'sigflag' twice -> malformed -> unspendable."""
    key = KeyPair.generate()
    builder = ProofBuilder(mint)
    tags = [
        ["sigflag", "SIG_INPUTS"],
        ["sigflag", "SIG_INPUTS"],  # duplicate: malformed
        ["n_sigs", "1"],
    ]
    p2pk = _swap_for_condition(builder, mint, lambda: _secret_with_tags(key.pub_hex, tags))
    _set_witness(p2pk, key)
    code, data = _spend(builder, mint, p2pk)
    ok = code in (400, 403)
    return ScenarioResult(
        name="nut11 duplicate spending tag rejected",
        category=CATEGORY,
        result=Result.PASS if ok else Result.FAIL,
        note=f"duplicate-tag spend rejected ({code}): {fmt_body(data)}" if not ok
        else f"duplicate-tag spend rejected ({code})",
    )


@scenario("nut11 key-only spending tag rejected", CATEGORY)
def key_only_spending_tag(mint: MintClient) -> ScenarioResult:
    """#474 rule 2 (NEW): '["locktime"]' with no value -> unspendable."""
    key = KeyPair.generate()
    builder = ProofBuilder(mint)
    tags = [
        ["sigflag", "SIG_INPUTS"],
        ["n_sigs", "1"],
        ["locktime"],  # key-only: malformed per #474
    ]
    p2pk = _swap_for_condition(builder, mint, lambda: _secret_with_tags(key.pub_hex, tags))
    _set_witness(p2pk, key)
    code, data = _spend(builder, mint, p2pk)
    ok = code in (400, 403)
    return ScenarioResult(
        name="nut11 key-only spending tag rejected",
        category=CATEGORY,
        result=Result.PASS if ok else Result.FAIL,
        note=f"key-only-tag spend rejected ({code}): {fmt_body(data)}" if not ok
        else f"key-only-tag spend rejected ({code})",
    )


@scenario("nut11 non-condition nut10 tag ignored", CATEGORY)
def non_condition_tag_ignored(mint: MintClient) -> ScenarioResult:
    """#474 rule 3 (NEW): other NUT-10 tags MUST be ignored by the lock."""
    key = KeyPair.generate()
    builder = ProofBuilder(mint)
    tags = [
        ["sigflag", "SIG_INPUTS"],
        ["n_sigs", "1"],
        ["custom", "transport", "mail"],  # non-condition NUT-10 tag
    ]
    p2pk = _swap_for_condition(builder, mint, lambda: _secret_with_tags(key.pub_hex, tags))
    _set_witness(p2pk, key)
    code, data = _spend(builder, mint, p2pk)
    ok = code == 200
    return ScenarioResult(
        name="nut11 non-condition nut10 tag ignored",
        category=CATEGORY,
        result=Result.PASS if ok else Result.FAIL,
        note=f"decorated spend succeeded ({code})" if ok
        else f"decorated spend REJECTED ({code}) — mint must ignore non-condition tags: {fmt_body(data)}",
    )
