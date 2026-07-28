"""NUT-29 batch operations conformance scenarios — 3 tests.

Covers batch quote checking and batch mint validation limits
defined by NUT-29 (max_batch_size advertised in NUT-06 info).
"""
from __future__ import annotations

import time

from conformance.client import MintClient
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
)

CAT = "NUT-29 Batch Ops"


@scenario("batch_check_returns_quotes", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """POST /v1/mint/quote/bolt11/check returns states for valid quotes."""
    q1 = mint.mint_quote(4)["quote"]
    q2 = mint.mint_quote(6)["quote"]
    time.sleep(1)

    code, body = mint.batch_check_quotes([q1, q2])

    if code != 200:
        return ScenarioResult(
            "batch_check_returns_quotes", CAT,
            Result.FAIL, f"HTTP {code}: {str(body)[:200]}",
        )

    if not isinstance(body, list) or len(body) != 2:
        return ScenarioResult(
            "batch_check_returns_quotes", CAT,
            Result.FAIL,
            f"expected list of 2, got {type(body).__name__} len={len(body) if isinstance(body, list) else '?'}",
        )

    for i, qid in enumerate((q1, q2)):
        entry = body[i]
        if not isinstance(entry, dict) or entry.get("quote") != qid:
            return ScenarioResult(
                "batch_check_returns_quotes", CAT,
                Result.FAIL,
                f"entry {i}: expected quote={qid}, got {entry}",
            )
        if "state" not in entry:
            return ScenarioResult(
                "batch_check_returns_quotes", CAT,
                Result.FAIL,
                f"entry {i}: missing 'state' field",
            )

    states = [e.get("state") for e in body]
    return ScenarioResult(
        "batch_check_returns_quotes", CAT,
        Result.PASS, f"states={states}",
    )


@scenario("batch_check_rejects_too_many", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """51 quote IDs triggers batch_too_large error (limit is 50)."""
    ids = [f"00000000-0000-7000-8000-0000000000{i:02d}" for i in range(1, 52)]
    code, body = mint.batch_check_quotes(ids)

    if code >= 400 and isinstance(body, dict):
        err = body.get("error", "") or body.get("code", "")
        detail = body.get("detail", "")
        if "batch" in err.lower() or "too" in err.lower() or "batch" in detail.lower():
            return ScenarioResult(
                "batch_check_rejects_too_many", CAT,
                Result.PASS, f"rejected ({code}): {err} {detail[:80]}",
            )
    return ScenarioResult(
        "batch_check_rejects_too_many", CAT,
        Result.FAIL, f"expected batch_too_large, got {code}: {str(body)[:200]}",
    )


@scenario("batch_mint_rejects_too_many_outputs", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """1001 outputs triggers too_many_outputs error (limit is 1000)."""
    fake_outputs = [
        {"amount": 1, "id": "00", "B_": "02" + "00" * 32}
        for _ in range(1001)
    ]
    code, body = mint.try_batch_mint(["fake-quote-id"], fake_outputs)

    if code >= 400 and isinstance(body, dict):
        err = body.get("error", "") or body.get("code", "")
        detail = body.get("detail", "")
        if (
            "output" in err.lower()
            or "too_many" in err.lower()
            or "output" in detail.lower()
        ):
            return ScenarioResult(
                "batch_mint_rejects_too_many_outputs", CAT,
                Result.PASS, f"rejected ({code}): {err} {detail[:80]}",
            )
    return ScenarioResult(
        "batch_mint_rejects_too_many_outputs", CAT,
        Result.FAIL,
        f"expected too_many_outputs, got {code}: {str(body)[:200]}",
    )
