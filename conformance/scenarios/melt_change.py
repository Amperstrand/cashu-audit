"""NUT-08 melt change scenarios — 2 tests.

NUT-08/NUT-23: a melt that overpays (fee reserve the backend did not
spend, plus over-funding) must return `change` — blind signatures for the
request's blank outputs, amounts mint-assigned, in blank-output order —
and only when blank outputs were provided. Measured gap 2026-11-04
(FINDINGS-2026-11-04-gonuts-residue §B3): gonuts v0.16.0 returned none;
fixed on the fix/nut08-melt-change branch.

Inputs are sized to clear every reference FakeWallet's reserve (the
2026-11-04 rig lesson: a 4-sat input set was underfunded on ns 0.21.0).
Fake-backed arms spend 0 actual fee, so the honest change is
`total − melt_amount` regardless of each arm's reserve estimate.
"""
from __future__ import annotations

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret
from conformance.scenarios import (
    fmt_body,
    scenario,
    ScenarioResult,
    Result,
)


@scenario("melt_change_returned_for_overpay", "NUT-08 Melt Change")
def _(mint: MintClient) -> ScenarioResult:
    """Melt overpaying with blank outputs: PAID + spendable change summing
    to the full overpay."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(16)
    total = sum(p.amount for p in proofs)

    melt_resp = mint.create_fresh_melt_quote(2)
    quote_id = melt_resp["quote"]
    melt_amount = melt_resp.get("amount", 2)

    # blank outputs: amounts ignored (NUT-08: Bob imprints his own);
    # provide enough of them to represent the full overpay decomposition
    # (14 = 8+4+2 — one blank would cap the change at the largest note,
    # which every implementation does but is not the row's question)
    blanks = builder.create_outputs(15, lambda: generate_secret())
    api_blanks = [
        {"amount": 0, "id": o["id"], "B_": o["B_"]}
        for o in builder.outputs_to_api(blanks)
    ]

    code, body = mint.melt(quote_id, [p.to_dict() for p in proofs], api_blanks)
    if code != 200 or not isinstance(body, dict) or body.get("state") != "PAID":
        return ScenarioResult(
            "melt_change_returned_for_overpay", "NUT-08 Melt Change",
            Result.FAIL, f"melt did not settle PAID: {code} {fmt_body(body)}",
        )

    change = body.get("change") or []
    if not change:
        return ScenarioResult(
            "melt_change_returned_for_overpay", "NUT-08 Melt Change",
            Result.FAIL,
            f"no change returned for a {total}-sat melt of a {melt_amount}-sat "
            "invoice with blank outputs (NUT-08/NUT-23 divergence)",
        )

    # zero-value signatures are omitted and order is the blank outputs'.
    # The exact change depends on the fee the arm's backend actually
    # spent (0 ≤ fee_spent ≤ fee_reserve — the reference FakeWallets
    # differ: ns spends up to its reserve, cdk part of it, the gonuts
    # fake spends 0), so the spec-stable assertion is the NUT-08 range.
    change_sum = sum(s.get("amount", 0) for s in change)
    fee_reserve = melt_resp.get("fee_reserve", 0)
    # NUT-02 input fees are part of the melt equation and must be inside the
    # bounds (2026-11-12: murdawkmedia caught their omission — the cashu-cf
    # testnut active keyset charges input_fee_ppk=10, i.e. 1 sat rounded per
    # input, which made its honest change=12 fall outside our old [13,14]).
    input_fees = builder.calc_fee(len(proofs))
    upper = total - melt_amount - input_fees      # backend spent nothing
    lower = total - melt_amount - fee_reserve - input_fees  # whole reserve spent
    if not (lower <= change_sum <= upper):
        return ScenarioResult(
            "melt_change_returned_for_overpay", "NUT-08 Melt Change",
            Result.FAIL,
            f"change sums to {change_sum}, want [{lower}, {upper}] "
            f"(total {total} − amount {melt_amount} − fee spent ≤ reserve {fee_reserve})",
        )
    if len(change) > len(blanks):
        return ScenarioResult(
            "melt_change_returned_for_overpay", "NUT-08 Melt Change",
            Result.FAIL,
            f"{len(change)} change signatures for {len(blanks)} blank outputs",
        )

    # the change must unblind to spendable proofs (swap them back)
    _, keys = builder.get_active_keyset()
    try:
        change_proofs = builder.unblind_signatures(change, blanks, keys)
    except Exception as e:
        return ScenarioResult(
            "melt_change_returned_for_overpay", "NUT-08 Melt Change",
            Result.FAIL, f"change does not unblind: {e}",
        )
    swap_amount = change_sum - builder.calc_fee(len(change_proofs))
    if swap_amount < 1:
        return ScenarioResult(
            "melt_change_returned_for_overpay", "NUT-08 Melt Change",
            Result.SKIP, f"change {change_sum} too small to swap after fees",
        )
    outputs = builder.create_outputs(swap_amount, lambda: generate_secret())
    swap_code, swap_body = mint.try_swap(
        [p.to_dict() for p in change_proofs], builder.outputs_to_api(outputs)
    )
    if swap_code != 200:
        return ScenarioResult(
            "melt_change_returned_for_overpay", "NUT-08 Melt Change",
            Result.FAIL,
            f"change proofs not spendable: swap {swap_code} {fmt_body(swap_body)}",
        )

    return ScenarioResult(
        "melt_change_returned_for_overpay", "NUT-08 Melt Change",
        Result.PASS,
        f"{change_sum} sats change returned, unblinded and re-spent "
        f"({len(change)} sigs for {len(blanks)} blanks)",
    )


@scenario("melt_change_omitted_without_outputs", "NUT-08 Melt Change")
def _(mint: MintClient) -> ScenarioResult:
    """Overpaying melt WITHOUT blank outputs: PAID, no change — the
    overpay is simply not claimed (spec: change only if outputs)."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(16)
    total = sum(p.amount for p in proofs)

    melt_resp = mint.create_fresh_melt_quote(2)
    quote_id = melt_resp["quote"]
    melt_amount = melt_resp.get("amount", 2)
    if total <= melt_amount:
        return ScenarioResult(
            "melt_change_omitted_without_outputs", "NUT-08 Melt Change",
            Result.SKIP, "fixture needs an overpay",
        )

    code, body = mint.melt(quote_id, [p.to_dict() for p in proofs])
    if code != 200 or not isinstance(body, dict) or body.get("state") != "PAID":
        return ScenarioResult(
            "melt_change_omitted_without_outputs", "NUT-08 Melt Change",
            Result.FAIL, f"melt did not settle PAID: {code} {fmt_body(body)}",
        )
    change = body.get("change") or []
    if change:
        return ScenarioResult(
            "melt_change_omitted_without_outputs", "NUT-08 Melt Change",
            Result.FAIL,
            f"change returned without blank outputs: {fmt_body(change)[:120]}",
        )
    return ScenarioResult(
        "melt_change_omitted_without_outputs", "NUT-08 Melt Change",
        Result.PASS, "PAID without outputs, no change claimed",
    )
