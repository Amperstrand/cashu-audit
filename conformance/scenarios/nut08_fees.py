"""NUT-08 Fee calculation conformance scenarios — 6 tests.

Fee model: input_fee_ppk per keyset,
    fee = ceil(num_inputs * fee_ppk / 1000)
Swap invariant: output_amount + fee <= input_amount.
"""
from __future__ import annotations

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
    expect_reject,
)


# ─── NUT-08 Fees (6) ─────────────────────────────────────────────────────


@scenario("fee_zero_ppk_swap_succeeds", "NUT-08 Fees")
def _(mint: MintClient) -> ScenarioResult:
    """With fee_ppk=0, swap output amount equals input amount (no fee deducted).

    Skips on testnut (fee_ppk=10) and any mint with non-zero input fees.

    To run this scenario, target a mint configured with input_fee_ppk=0:
    - Local Nutshell: MINT_INPUT_FEE_PPK=0 in .env
    - cashu-cf: KEYSETS={"sat":{"1":{"input_fee_ppk":0}}} in wrangler.toml
    """
    builder = ProofBuilder(mint)
    builder.get_active_keyset()
    fee_ppk = builder._fee_ppk
    if fee_ppk != 0:
        return ScenarioResult(
            "fee_zero_ppk_swap_succeeds", "NUT-08 Fees",
            Result.SKIP, f"mint fee_ppk={fee_ppk}, requires fee_ppk=0",
        )
    proofs = builder.mint_proofs(8)
    total = sum(p.amount for p in proofs)
    fee = builder.calc_fee(len(proofs))
    swap_amount = total - fee  # == total when fee_ppk == 0
    outputs = builder.create_outputs(swap_amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    inputs = [p.to_dict() for p in proofs]
    result = mint.swap(inputs, api_outputs)
    signatures = result.get("signatures", [])
    if len(signatures) == len(outputs):
        return ScenarioResult(
            "fee_zero_ppk_swap_succeeds", "NUT-08 Fees",
            Result.PASS,
            f"fee_ppk=0, swapped {total} sats with 0 fee, "
            f"{len(signatures)} sigs returned",
        )
    return ScenarioResult(
        "fee_zero_ppk_swap_succeeds", "NUT-08 Fees",
        Result.FAIL,
        f"expected {len(outputs)} sigs, got {len(signatures)}",
    )


@scenario("fee_calculated_correctly", "NUT-08 Fees")
def _(mint: MintClient) -> ScenarioResult:
    """Verify fee = ceil(inputs * fee_ppk / 1000) by checking swap balance.

    Mints proofs, swaps with output = total - calc_fee(n_inputs), and
    confirms the mint accepts (fee deducted exactly as formula predicts)
    and the returned signatures sum to the expected output amount.
    """
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    total = sum(p.amount for p in proofs)
    n_inputs = len(proofs)
    fee_ppk = builder._fee_ppk
    expected_fee = builder.calc_fee(n_inputs)
    swap_amount = total - expected_fee
    if swap_amount < 1:
        return ScenarioResult(
            "fee_calculated_correctly", "NUT-08 Fees",
            Result.SKIP,
            f"swap_amount < 1 (total={total}, fee={expected_fee})",
        )
    outputs = builder.create_outputs(swap_amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    inputs = [p.to_dict() for p in proofs]
    code, body = mint.try_swap(inputs, api_outputs)
    if code != 200:
        return ScenarioResult(
            "fee_calculated_correctly", "NUT-08 Fees",
            Result.FAIL,
            f"swap failed ({code}): {str(body)[:200]}",
        )
    result = body if isinstance(body, dict) else {}
    signatures = result.get("signatures", [])
    returned_total = sum(s.get("amount", 0) for s in signatures)
    if returned_total == swap_amount:
        return ScenarioResult(
            "fee_calculated_correctly", "NUT-08 Fees",
            Result.PASS,
            f"fee_ppk={fee_ppk}, {n_inputs} inputs, "
            f"fee={expected_fee}, output={returned_total}",
        )
    return ScenarioResult(
        "fee_calculated_correctly", "NUT-08 Fees",
        Result.FAIL,
        f"expected output={swap_amount}, got {returned_total} "
        f"(fee_ppk={fee_ppk}, n={n_inputs})",
    )


@scenario("fee_insufficient_outputs_fails", "NUT-08 Fees")
def _(mint: MintClient) -> ScenarioResult:
    """Swap requesting output_amount > input_total - fee should be rejected.

    Asks for one sat more than the fee-adjusted balance allows.
    """
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    total = sum(p.amount for p in proofs)
    n_inputs = len(proofs)
    fee = builder.calc_fee(n_inputs)
    excess_amount = total - fee + 1  # one sat over the limit
    outputs = builder.create_outputs(excess_amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    inputs = [p.to_dict() for p in proofs]
    code, body = mint.try_swap(inputs, api_outputs)
    if expect_reject(code, body):
        return ScenarioResult(
            "fee_insufficient_outputs_fails", "NUT-08 Fees",
            Result.PASS,
            f"rejected swap requesting {excess_amount} "
            f"(max={total - fee}, fee={fee})",
        )
    return ScenarioResult(
        "fee_insufficient_outputs_fails", "NUT-08 Fees",
        Result.FAIL,
        f"expected rejection, got {code}: {str(body)[:200]}",
    )


@scenario("fee_exact_balance_succeeds", "NUT-08 Fees")
def _(mint: MintClient) -> ScenarioResult:
    """Swap with output_amount = input_total - fee exactly should succeed.

    This is the boundary case: every satoshi of input is accounted for
    between output and fee, leaving zero remainder.
    """
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    total = sum(p.amount for p in proofs)
    n_inputs = len(proofs)
    fee = builder.calc_fee(n_inputs)
    exact_amount = total - fee
    if exact_amount < 1:
        return ScenarioResult(
            "fee_exact_balance_succeeds", "NUT-08 Fees",
            Result.SKIP,
            f"exact_amount < 1 (total={total}, fee={fee})",
        )
    outputs = builder.create_outputs(exact_amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    inputs = [p.to_dict() for p in proofs]
    code, body = mint.try_swap(inputs, api_outputs)
    if code == 200:
        return ScenarioResult(
            "fee_exact_balance_succeeds", "NUT-08 Fees",
            Result.PASS,
            f"exact balance: input={total}, fee={fee}, output={exact_amount}",
        )
    return ScenarioResult(
        "fee_exact_balance_succeeds", "NUT-08 Fees",
        Result.FAIL,
        f"expected success, got {code}: {str(body)[:200]}",
    )


@scenario("fee_melt_quote_includes_fee_reserve", "NUT-08 Fees")
def _(mint: MintClient) -> ScenarioResult:
    """Melt quote response includes the fee_reserve field (NUT-08)."""
    mint_resp = mint.mint_quote(4)
    invoice = mint_resp["request"]
    melt_resp = mint.melt_quote(invoice)
    if "fee_reserve" in melt_resp:
        return ScenarioResult(
            "fee_melt_quote_includes_fee_reserve", "NUT-08 Fees",
            Result.PASS,
            f"fee_reserve={melt_resp['fee_reserve']}",
        )
    return ScenarioResult(
        "fee_melt_quote_includes_fee_reserve", "NUT-08 Fees",
        Result.FAIL,
        f"missing fee_reserve: {str(melt_resp)[:200]}",
    )


@scenario("fee_per_proof_not_per_amount", "NUT-08 Fees")
def _(mint: MintClient) -> ScenarioResult:
    """Fee is per-proof (input count), not per-sat amount.

    A single 64-sat proof (amount 64 = 2^6, so one input) should incur
    the same fee as a single 1-sat proof: calc_fee(1).  If the mint
    charged proportionally to amount, swapping the 64-sat proof with
    output = 64 - calc_fee(1) would fail because the real fee would be
    far higher.
    """
    builder = ProofBuilder(mint)
    builder.get_active_keyset()
    fee_ppk = builder._fee_ppk
    if fee_ppk == 0:
        return ScenarioResult(
            "fee_per_proof_not_per_amount", "NUT-08 Fees",
            Result.SKIP,
            "fee_ppk=0, cannot distinguish per-proof vs per-amount",
        )

    # Single high-value proof: 64 = 2^6 -> 1 proof of amount 64
    proofs_hi = builder.mint_proofs(64)
    n_hi = len(proofs_hi)
    total_hi = sum(p.amount for p in proofs_hi)
    fee_per_input = builder.calc_fee(1)
    swap_amount = total_hi - fee_per_input
    if swap_amount < 1:
        return ScenarioResult(
            "fee_per_proof_not_per_amount", "NUT-08 Fees",
            Result.SKIP,
            f"swap_amount < 1 (total={total_hi}, fee={fee_per_input})",
        )
    outputs = builder.create_outputs(swap_amount, lambda: generate_secret())
    code, body = mint.try_swap(
        [p.to_dict() for p in proofs_hi],
        builder.outputs_to_api(outputs),
    )
    if code == 200:
        return ScenarioResult(
            "fee_per_proof_not_per_amount", "NUT-08 Fees",
            Result.PASS,
            f"{n_hi} proof of {total_hi} sats: fee={fee_per_input} "
            f"(per-proof, not per-amount)",
        )
    return ScenarioResult(
        "fee_per_proof_not_per_amount", "NUT-08 Fees",
        Result.FAIL,
        f"64-sat single-proof swap failed with fee={fee_per_input} ({code}); "
        f"mint may charge per-amount — {str(body)[:150]}",
    )
