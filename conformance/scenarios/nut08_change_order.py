"""NUT-08 melt change ordering + zero-value omission — the 2026-11-19
spec churn (nuts #436, "accepted outputs are signed after keyset
rotation; zero-value signatures MUST be omitted").

The two mint-side MUSTs that #436 sharpened:
  1. the mint MUST imprint the amounts into the LEADING blank outputs
     and return the >0-value blind signatures in the SAME ORDER as the
     blank outputs were received;
  2. the mint MUST omit all zero-value blind signatures.

Scenario shape: overpay a melt with FAR more blanks than the change
decomposition needs — the returned signature set must (a) contain only
positive amounts, (b) be fewer than the blanks provided, and (c) map,
in order, onto the LEADING blanks (matched by their B_ values).
"""
from __future__ import annotations

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret
from conformance.scenarios import fmt_body, scenario, ScenarioResult, Result

CAT = "NUT-08 Melt Change (#436)"


@scenario("melt_change_leading_order_and_omit_zero", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Overpay with excess blanks: signatures = leading blanks, >0, ordered."""
    name = "melt_change_leading_order_and_omit_zero"
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(16)
    total = sum(p.amount for p in proofs)

    melt_resp = mint.create_fresh_melt_quote(2)
    quote_id = melt_resp["quote"]
    melt_amount = melt_resp.get("amount", 2)
    if total <= melt_amount:
        return ScenarioResult(name, CAT, Result.SKIP, "fixture needs an overpay")

    # FAR more blanks than any change decomposition needs (overpay ≤ 14
    # = 8+4+2 → at most 3 non-zero signatures). create_outputs(16)
    # decomposes into powers [8,4,2,1,1] = 5 blanks — plus the mint's
    # fee behavior leaves ≥ 1 zero; give extra via a second call.
    blanks = builder.create_outputs(16, lambda: generate_secret())
    blanks += builder.create_outputs(8, lambda: generate_secret())
    blanks += builder.create_outputs(4, lambda: generate_secret())
    blanks += builder.create_outputs(2, lambda: generate_secret())
    blanks += builder.create_outputs(2, lambda: generate_secret())
    api_blanks = [
        {"amount": 0, "id": o["id"], "B_": o["B_"]}
        for o in builder.outputs_to_api(blanks)
    ]
    blank_b_list = [b["B_"] for b in api_blanks]
    n_blanks = len(api_blanks)

    code, body = mint.melt(quote_id, [p.to_dict() for p in proofs], api_blanks)
    if code != 200 or not isinstance(body, dict) or body.get("state") != "PAID":
        return ScenarioResult(name, CAT, Result.FAIL,
                              f"melt did not settle PAID: {code} {fmt_body(body)}")

    change = body.get("change") or []
    if not change:
        return ScenarioResult(name, CAT, Result.FAIL,
                              f"no change returned despite {n_blanks} blank outputs "
                              f"for a {total}-sat melt of {melt_amount} sat")

    # (a) all amounts > 0 — zero-value signatures MUST be omitted
    zero_sigs = [s for s in change if s.get("amount", 0) <= 0]
    if zero_sigs:
        return ScenarioResult(name, CAT, Result.FAIL,
                              f"zero-value blind signatures returned (#436 MUST): "
                              f"{[s.get('amount') for s in zero_sigs]}")

    # (b) fewer signatures than blanks (the omission rule's observable)
    if len(change) >= n_blanks:
        return ScenarioResult(name, CAT, Result.FAIL,
                              f"{len(change)} signatures for {n_blanks} blanks — "
                              "zero-value omission not observable")

    # (c) the returned signatures map, IN ORDER, onto the LEADING blanks:
    #     unblind change[i] with blank[i]'s r — a shuffled order produces
    #     proofs that do not verify (C_ is bound to blank[i]'s B_ by the
    #     blind-signature algebra; the wrong pairing fails to unblind
    #     into the mint's published key relationship).
    from conformance.builder import OutputResult
    _, keys = builder.get_active_keyset()
    leading = blanks[: len(change)]
    try:
        unblind = builder.unblind_signatures(change, leading, keys)
    except Exception as e:
        return ScenarioResult(name, CAT, Result.FAIL,
                              f"leading-order unblind failed (order shuffled?): {type(e).__name__}: {e}")
    for i, proof in enumerate(unblind):
        if proof.amount != change[i].get("amount"):
            return ScenarioResult(name, CAT, Result.FAIL,
                                  f"unblinded proof #{i} amount {proof.amount} != "
                                  f"signature amount {change[i].get('amount')}")

    # change sum sanity (the same NUT-02 input-fee bounds as the base row)
    change_sum = sum(s.get("amount", 0) for s in change)
    fee_reserve = melt_resp.get("fee_reserve", 0)
    input_fees = builder.calc_fee(len(proofs))
    upper = total - melt_amount - input_fees
    lower = total - melt_amount - fee_reserve - input_fees
    if not (lower <= change_sum <= upper):
        return ScenarioResult(name, CAT, Result.FAIL,
                              f"change {change_sum} outside [{lower},{upper}] "
                              "(input-fee bounds)")

    return ScenarioResult(name, CAT, Result.PASS,
                          f"{len(change)}/{n_blanks} blanks signed, leading-order "
                          f"exact, all >0, sum {change_sum} in bounds")
