"""Security: concurrency scenarios — regression tests for cashu-cf race fixes.

These are not NUT conformance checks; they verify concurrency invariants that
the NUT specs imply (a melt quote must not be paid twice) but do not spell out
as a discrete protocol test. Each scenario runs against a live mint.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret
from conformance.scenarios import scenario, ScenarioResult, Result

CATEGORY = "Security: Concurrency"


def _create_melt_quote(mint: MintClient) -> str:
    mint_resp = mint.mint_quote(4)
    invoice = mint_resp.get("request", "lnbc1000n1p")
    resp = mint.melt_quote(invoice)
    time.sleep(2)
    return resp["quote"]


def _change_outputs(builder: ProofBuilder, total: int, n_inputs: int) -> list[dict] | None:
    change = max(0, total - n_inputs - 1)
    if change < 1:
        return None
    return builder.outputs_to_api(builder.create_outputs(change, lambda: generate_secret()))


def _melt_paid(code: int, body) -> bool:
    return code == 200 and isinstance(body, dict) and body.get("state") == "PAID"


def _try_melt(mint: MintClient, builder: ProofBuilder, proofs: list, quote_id: str) -> tuple[int, object]:
    inputs = [p.to_dict() for p in proofs]
    outputs = _change_outputs(builder, sum(p.amount for p in proofs), len(inputs))
    return mint.melt(quote_id, inputs, outputs)


@scenario("concurrent_double_melt_rejected", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Two concurrent melts on the same quote with DISJOINT proof sets.

    Regression for cashu-cf issue #41 (concurrent double-melt). Before the
    atomic Compare-And-Set fix on the UNPAID→PENDING transition, both melts
    passed the read-side state check (the quote was UNPAID for both), both
    wrote PENDING via an unconditional update, and both proceeded to pay the
    invoice — burning the loser's proof set for nothing.

    With the fix, the melt handler CAS-transitions UNPAID→PENDING; the
    race-loser is rejected with 403 quote_pending before any proof is touched.
    This scenario proves exactly one of the two concurrent melts pays.
    """
    builder = ProofBuilder(mint)
    proofs_a = builder.mint_proofs(8)
    proofs_b = builder.mint_proofs(8)

    quote_id = _create_melt_quote(mint)

    with ThreadPoolExecutor(max_workers=2) as ex:
        fa = ex.submit(_try_melt, mint, builder, proofs_a, quote_id)
        fb = ex.submit(_try_melt, mint, builder, proofs_b, quote_id)
        code_a, body_a = fa.result()
        code_b, body_b = fb.result()

    paid_a = _melt_paid(code_a, body_a)
    paid_b = _melt_paid(code_b, body_b)

    if paid_a and paid_b:
        return ScenarioResult(
            "concurrent_double_melt_rejected", CATEGORY, Result.FAIL,
            f"BOTH concurrent melts paid (A={code_a}, B={code_b}) — double-melt not prevented",
        )
    if not paid_a and not paid_b:
        return ScenarioResult(
            "concurrent_double_melt_rejected", CATEGORY, Result.FAIL,
            f"neither melt paid (A={code_a}/{body_a}, B={code_b}/{body_b}) — quote may be unpayable",
        )

    loser_code, loser_body = (code_b, body_b) if paid_a else (code_a, body_a)
    return ScenarioResult(
        "concurrent_double_melt_rejected", CATEGORY, Result.PASS,
        f"exactly one melt paid; loser rejected with HTTP {loser_code}",
    )


@scenario("sequential_double_melt_rejected", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """A second melt on an already-PAID quote is rejected (baseline control).

    This is the non-concurrent counterpart of the test above. It guards the
    same invariant without the race, so a flaky concurrent run can be triaged
    against a deterministic baseline.
    """
    builder = ProofBuilder(mint)
    proofs_a = builder.mint_proofs(8)
    proofs_b = builder.mint_proofs(8)

    quote_id = _create_melt_quote(mint)

    code_a, body_a = _try_melt(mint, builder, proofs_a, quote_id)
    code_b, body_b = _try_melt(mint, builder, proofs_b, quote_id)

    if not _melt_paid(code_a, body_a):
        return ScenarioResult(
            "sequential_double_melt_rejected", CATEGORY, Result.FAIL,
            f"first melt did not pay ({code_a}/{body_a})",
        )
    if _melt_paid(code_b, body_b):
        return ScenarioResult(
            "sequential_double_melt_rejected", CATEGORY, Result.FAIL,
            f"second melt on PAID quote also paid ({code_b}) — double-melt",
        )
    return ScenarioResult(
        "sequential_double_melt_rejected", CATEGORY, Result.PASS,
        f"first melt paid; second rejected with HTTP {code_b}",
    )
