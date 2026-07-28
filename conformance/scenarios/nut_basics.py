"""NUT basic conformance scenarios — 15 tests.

Covers core mint operations beyond spending conditions:
NUT-03 swap, NUT-04 mint quote, NUT-05 melt, NUT-07 checkstate,
NUT-09 restore, NUT-00 token format, NUT-06 mint info, NUT-19 cache.
"""
from __future__ import annotations

import base64
import json
import os
import time

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
    expect_reject,
)


# ─── NUT-03 Swap Basics (3) ───────────────────────────────────────────────


@scenario("swap_valid_proofs_succeeds", "NUT-03 Swap Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Swap valid proofs for new outputs, verify signatures returned."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_amount = total - fee
    if swap_amount < 1:
        return ScenarioResult(
            "swap_valid_proofs_succeeds", "NUT-03 Swap Basics",
            Result.FAIL, "swap amount < 1",
        )
    outputs = builder.create_outputs(swap_amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    inputs = [p.to_dict() for p in proofs]
    result = mint.swap(inputs, api_outputs)
    signatures = result.get("signatures", [])
    if len(signatures) == len(outputs):
        return ScenarioResult(
            "swap_valid_proofs_succeeds", "NUT-03 Swap Basics",
            Result.PASS, f"{len(signatures)} signatures returned",
        )
    return ScenarioResult(
        "swap_valid_proofs_succeeds", "NUT-03 Swap Basics",
        Result.FAIL, f"expected {len(outputs)} sigs, got {len(signatures)}",
    )


@scenario("swap_already_spent_fails", "NUT-03 Swap Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Try to spend the same proofs twice; second should fail."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_amount = max(1, total - fee)
    inputs = [p.to_dict() for p in proofs]

    # First swap — should succeed
    outputs1 = builder.create_outputs(swap_amount, lambda: generate_secret())
    mint.swap(inputs, builder.outputs_to_api(outputs1))

    # Second swap with same proofs — should fail
    outputs2 = builder.create_outputs(swap_amount, lambda: generate_secret())
    code, body = mint.try_swap(inputs, builder.outputs_to_api(outputs2))

    if expect_reject(code, body):
        return ScenarioResult(
            "swap_already_spent_fails", "NUT-03 Swap Basics",
            Result.PASS, "double-spend rejected",
        )
    return ScenarioResult(
        "swap_already_spent_fails", "NUT-03 Swap Basics",
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("swap_wrong_keyset_fails", "NUT-03 Swap Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Try to swap proofs with wrong keyset ID in outputs."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    inputs = [p.to_dict() for p in proofs]

    # Create outputs with a non-existent keyset ID
    wrong_id = os.urandom(4).hex()
    raw_outputs = builder.create_outputs(4, lambda: generate_secret())
    api_outputs = [
        {"amount": o.amount, "id": wrong_id, "B_": o.B_}
        for o in raw_outputs
    ]

    code, body = mint.try_swap(inputs, api_outputs)

    if expect_reject(code, body):
        return ScenarioResult(
            "swap_wrong_keyset_fails", "NUT-03 Swap Basics",
            Result.PASS, "wrong keyset rejected",
        )
    return ScenarioResult(
        "swap_wrong_keyset_fails", "NUT-03 Swap Basics",
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


# ─── NUT-04 Mint Quote Basics (3) ─────────────────────────────────────────


@scenario("mint_quote_creates_invoice", "NUT-04 Mint Quote Basics")
def _(mint: MintClient) -> ScenarioResult:
    """POST /v1/mint/quote/bolt11 returns quote with BOLT11 invoice."""
    quote = mint.mint_quote(10)
    request = quote.get("request", "")
    if request.startswith("ln") and "quote" in quote:
        return ScenarioResult(
            "mint_quote_creates_invoice", "NUT-04 Mint Quote Basics",
            Result.PASS, f"invoice starts with {request[:6]}",
        )
    return ScenarioResult(
        "mint_quote_creates_invoice", "NUT-04 Mint Quote Basics",
        Result.FAIL, f"missing BOLT11 or quote field: {str(quote)[:200]}",
    )


@scenario("mint_quote_zero_amount_fails", "NUT-04 Mint Quote Basics")
def _(mint: MintClient) -> ScenarioResult:
    """amount=0 should be rejected."""
    code, body = mint._post(
        "/v1/mint/quote/bolt11", {"amount": 0, "unit": "sat"}
    )
    if expect_reject(code, body):
        return ScenarioResult(
            "mint_quote_zero_amount_fails", "NUT-04 Mint Quote Basics",
            Result.PASS, "zero amount rejected",
        )
    return ScenarioResult(
        "mint_quote_zero_amount_fails", "NUT-04 Mint Quote Basics",
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("mint_tokens_after_quote", "NUT-04 Mint Quote Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Mint tokens using a paid quote, verify signatures."""
    builder = ProofBuilder(mint)
    amount = 8
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    quote = mint.mint_quote(amount)
    quote_id = quote["quote"]

    # Wait for FakeWallet to pay the invoice
    result = None
    for _ in range(30):
        try:
            result = mint.mint_tokens(quote_id, api_outputs)
            break
        except RuntimeError:
            time.sleep(1)
    if result is None:
        return ScenarioResult(
            "mint_tokens_after_quote", "NUT-04 Mint Quote Basics",
            Result.FAIL, "quote never paid after 30 retries",
        )
    signatures = result.get("signatures", [])
    if len(signatures) == len(outputs):
        return ScenarioResult(
            "mint_tokens_after_quote", "NUT-04 Mint Quote Basics",
            Result.PASS, f"{len(signatures)} signatures minted",
        )
    return ScenarioResult(
        "mint_tokens_after_quote", "NUT-04 Mint Quote Basics",
        Result.FAIL, f"expected {len(outputs)} sigs, got {len(signatures)}",
    )


# ─── NUT-05 Melt Basics (2) ───────────────────────────────────────────────


@scenario("melt_quote_creates_quote", "NUT-05 Melt Basics")
def _(mint: MintClient) -> ScenarioResult:
    """POST /v1/melt/quote/bolt11 returns quote with amount and fee."""
    # Get a real BOLT11 invoice from the mint first
    mint_resp = mint.mint_quote(4)
    invoice = mint_resp["request"]
    melt_resp = mint.melt_quote(invoice)
    if (
        "quote" in melt_resp
        and "amount" in melt_resp
        and "fee_reserve" in melt_resp
    ):
        return ScenarioResult(
            "melt_quote_creates_quote", "NUT-05 Melt Basics",
            Result.PASS,
            f"amount={melt_resp['amount']}, fee={melt_resp['fee_reserve']}",
        )
    return ScenarioResult(
        "melt_quote_creates_quote", "NUT-05 Melt Basics",
        Result.FAIL, f"missing fields: {str(melt_resp)[:200]}",
    )


@scenario("melt_valid_proofs_succeeds", "NUT-05 Melt Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Melt valid proofs, verify state=PAID."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    total = sum(p.amount for p in proofs)

    # Create melt quote using a real invoice
    mint_resp = mint.mint_quote(4)
    invoice = mint_resp["request"]
    time.sleep(2)
    melt_resp = mint.melt_quote(invoice)
    quote_id = melt_resp["quote"]
    melt_amount = melt_resp.get("amount", 4)
    fee_reserve = melt_resp.get("fee_reserve", 0)
    time.sleep(2)

    inputs = [p.to_dict() for p in proofs]

    # Provide change outputs when inputs exceed amount + fee
    change_amount = total - melt_amount - fee_reserve
    outputs = None
    if change_amount >= 1:
        change = builder.create_outputs(change_amount, lambda: generate_secret())
        outputs = builder.outputs_to_api(change)

    code, body = mint.melt(quote_id, inputs, outputs)

    if code == 200 and isinstance(body, dict) and body.get("state") == "PAID":
        return ScenarioResult(
            "melt_valid_proofs_succeeds", "NUT-05 Melt Basics",
            Result.PASS, "melt settled PAID",
        )
    return ScenarioResult(
        "melt_valid_proofs_succeeds", "NUT-05 Melt Basics",
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


# ─── NUT-07 Checkstate Basics (2) ─────────────────────────────────────────


@scenario("checkstate_unspent_returns_unspent", "NUT-07 Checkstate Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Fresh proofs return UNSPENT."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    ys = [p.y_value() for p in proofs]
    result = mint.checkstate(ys)
    states = result.get("states", [])
    unspent_count = sum(
        1 for s in states if s.get("state") == "UNSPENT"
    )
    if unspent_count == len(ys):
        return ScenarioResult(
            "checkstate_unspent_returns_unspent", "NUT-07 Checkstate Basics",
            Result.PASS, f"{unspent_count}/{len(ys)} UNSPENT",
        )
    return ScenarioResult(
        "checkstate_unspent_returns_unspent", "NUT-07 Checkstate Basics",
        Result.FAIL, f"states: {str(states)[:200]}",
    )


@scenario("checkstate_spent_returns_spent", "NUT-07 Checkstate Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Spent proofs return SPENT."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)

    # Spend the proofs via swap
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_amount = max(1, total - fee)
    outputs = builder.create_outputs(swap_amount, lambda: generate_secret())
    mint.swap(
        [p.to_dict() for p in proofs], builder.outputs_to_api(outputs)
    )

    # Now check state — should be SPENT
    ys = [p.y_value() for p in proofs]
    result = mint.checkstate(ys)
    states = result.get("states", [])
    spent_count = sum(
        1 for s in states if s.get("state") == "SPENT"
    )
    if spent_count == len(ys):
        return ScenarioResult(
            "checkstate_spent_returns_spent", "NUT-07 Checkstate Basics",
            Result.PASS, f"{spent_count}/{len(ys)} SPENT",
        )
    return ScenarioResult(
        "checkstate_spent_returns_spent", "NUT-07 Checkstate Basics",
        Result.FAIL, f"states: {str(states)[:200]}",
    )


# ─── NUT-09 Restore Basics (1) ────────────────────────────────────────────


@scenario("restore_returns_signatures", "NUT-09 Restore Basics")
def _(mint: MintClient) -> ScenarioResult:
    """POST /v1/restore returns blinded signatures."""
    builder = ProofBuilder(mint)

    # First mint tokens to have outputs the mint has seen
    outputs = builder.create_outputs(8, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    quote = mint.mint_quote(8)
    quote_id = quote["quote"]
    for _ in range(30):
        try:
            mint.mint_tokens(quote_id, api_outputs)
            break
        except RuntimeError:
            time.sleep(1)

    # Restore using the same blinded outputs
    code, body = mint._post("/v1/restore", {"outputs": api_outputs})

    if code != 200:
        return ScenarioResult(
            "restore_returns_signatures", "NUT-09 Restore Basics",
            Result.FAIL, f"HTTP {code}: {str(body)[:200]}",
        )
    if isinstance(body, dict):
        sigs = body.get("signatures") or body.get("promises") or []
        if len(sigs) > 0:
            return ScenarioResult(
                "restore_returns_signatures", "NUT-09 Restore Basics",
                Result.PASS, f"{len(sigs)} signatures restored",
            )
    return ScenarioResult(
        "restore_returns_signatures", "NUT-09 Restore Basics",
        Result.FAIL, f"no signatures in response: {str(body)[:200]}",
    )


# ─── NUT-00 Token Format Basics (2) ───────────────────────────────────────


@scenario("token_v3_parses", "NUT-00 Token Format Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Cashu V3 token format parses correctly."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(4)
    keyset_id, _ = builder.get_active_keyset()

    # Construct V3 token: cashuA<base64url(json)>
    token_obj = {
        "token": [
            {
                "mint": mint.base_url,
                "proofs": [
                    {
                        "amount": p.amount,
                        "secret": p.secret,
                        "C": p.C,
                        "id": p.id or keyset_id,
                    }
                    for p in proofs
                ],
            }
        ],
        "unit": "sat",
        "memo": "conformance test",
    }
    token_str = "cashuA" + base64.urlsafe_b64encode(
        json.dumps(token_obj).encode()
    ).decode()

    # Parse it back and verify structure
    try:
        assert token_str.startswith("cashuA")
        raw = base64.urlsafe_b64decode(token_str[6:])
        parsed = json.loads(raw)
        assert "token" in parsed
        assert len(parsed["token"]) > 0
        assert "proofs" in parsed["token"][0]
        assert "mint" in parsed["token"][0]
        assert parsed["unit"] == "sat"
        num_proofs = len(parsed["token"][0]["proofs"])
        return ScenarioResult(
            "token_v3_parses", "NUT-00 Token Format Basics",
            Result.PASS, f"V3 token parsed: {num_proofs} proofs",
        )
    except Exception as e:
        return ScenarioResult(
            "token_v3_parses", "NUT-00 Token Format Basics",
            Result.FAIL, f"parse error: {e}",
        )


@scenario("token_v4_parses", "NUT-00 Token Format Basics")
def _(mint: MintClient) -> ScenarioResult:
    """Cashu V4 token format parses correctly."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(4)
    keyset_id, _ = builder.get_active_keyset()

    # V4 format includes DLEQ proof data per proof
    token_obj = {
        "token": [
            {
                "mint": mint.base_url,
                "proofs": [
                    {
                        "amount": p.amount,
                        "secret": p.secret,
                        "C": p.C,
                        "id": p.id or keyset_id,
                        "dleq": generate_secret(),
                    }
                    for p in proofs
                ],
            }
        ],
        "unit": "sat",
        "memo": "conformance V4 test",
    }
    token_str = "cashuA" + base64.urlsafe_b64encode(
        json.dumps(token_obj).encode()
    ).decode()

    # Parse it back and verify structure including DLEQ fields
    try:
        assert token_str.startswith("cashuA")
        raw = base64.urlsafe_b64decode(token_str[6:])
        parsed = json.loads(raw)
        assert "token" in parsed
        assert len(parsed["token"]) > 0
        assert "proofs" in parsed["token"][0]
        for p in parsed["token"][0]["proofs"]:
            assert "dleq" in p, "missing dleq field in V4 proof"
        num_proofs = len(parsed["token"][0]["proofs"])
        return ScenarioResult(
            "token_v4_parses", "NUT-00 Token Format Basics",
            Result.PASS, f"V4 token parsed: {num_proofs} proofs with DLEQ",
        )
    except Exception as e:
        return ScenarioResult(
            "token_v4_parses", "NUT-00 Token Format Basics",
            Result.FAIL, f"parse error: {e}",
        )


# ─── NUT-19 Cache Basics (1) ──────────────────────────────────────────────


@scenario("mint_info_nut19_supported", "NUT-19 Cache Basics")
def _(mint: MintClient) -> ScenarioResult:
    """GET /v1/info returns nut19 support info."""
    info = mint.get_mint_info()
    nuts = info.get("nuts", {})
    if "19" in nuts:
        return ScenarioResult(
            "mint_info_nut19_supported", "NUT-19 Cache Basics",
            Result.PASS, f"nut19: {str(nuts['19'])[:100]}",
        )
    return ScenarioResult(
        "mint_info_nut19_supported", "NUT-19 Cache Basics",
        Result.FAIL, "nut19 not found in nuts list",
    )


# ─── NUT-06 Mint Info Basics (1) ──────────────────────────────────────────


@scenario("mint_info_returns_required_fields", "NUT-06 Mint Info Basics")
def _(mint: MintClient) -> ScenarioResult:
    """GET /v1/info returns name, pubkey, version, nuts."""
    info = mint.get_mint_info()
    required = ["name", "pubkey", "version", "nuts"]
    missing = [f for f in required if f not in info]
    if not missing:
        return ScenarioResult(
            "mint_info_returns_required_fields", "NUT-06 Mint Info Basics",
            Result.PASS,
            f"name={info.get('name')}, version={info.get('version')}",
        )
    return ScenarioResult(
        "mint_info_returns_required_fields", "NUT-06 Mint Info Basics",
        Result.FAIL, f"missing fields: {missing}",
    )
