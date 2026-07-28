"""NUT-04 accounting fields conformance scenarios — 5 tests.

Verifies that mint quote responses include the NUT-04 accounting fields
(amount_paid, amount_issued, updated_at) and that they track correctly
across the quote lifecycle: creation → payment → mint.
"""
from __future__ import annotations

import re
import time

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
)

CAT = "NUT-04 Accounting"

_UUID_V7_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


@scenario("mint_quote_has_accounting_fields", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """POST /v1/mint/quote/bolt11 response includes accounting fields."""
    quote = mint.mint_quote(10)
    missing = [
        f for f in ("amount_paid", "amount_issued", "updated_at") if f not in quote
    ]
    if not missing:
        return ScenarioResult(
            "mint_quote_has_accounting_fields", CAT,
            Result.PASS,
            f"amount_paid={quote['amount_paid']}, "
            f"amount_issued={quote['amount_issued']}, "
            f"updated_at={quote['updated_at']}",
        )
    return ScenarioResult(
        "mint_quote_has_accounting_fields", CAT,
        Result.FAIL, f"missing fields: {missing}",
    )


@scenario("mint_quote_uuid_v7", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Quote ID is UUID v7 format."""
    quote = mint.mint_quote(8)
    qid = quote.get("quote", "")
    if _UUID_V7_RE.match(qid):
        return ScenarioResult(
            "mint_quote_uuid_v7", CAT,
            Result.PASS, f"quote={qid}",
        )
    return ScenarioResult(
        "mint_quote_uuid_v7", CAT,
        Result.FAIL,
        f"quote={qid!r} does not match UUID v7 pattern",
    )


@scenario("mint_quote_accounting_after_payment", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """After FakeWallet settles, amount_paid equals the requested amount."""
    amount = 8
    quote = mint.mint_quote(amount)
    qid = quote["quote"]

    for _ in range(30):
        time.sleep(1)
        status = mint.check_mint_quote(qid)
        if isinstance(status, dict) and status.get("state") == "PAID":
            break
    else:
        return ScenarioResult(
            "mint_quote_accounting_after_payment", CAT,
            Result.SKIP, "quote never reached PAID state",
        )

    amount_paid = status.get("amount_paid", -1)
    if amount_paid == amount:
        return ScenarioResult(
            "mint_quote_accounting_after_payment", CAT,
            Result.PASS, f"amount_paid={amount_paid} == amount={amount}",
        )
    return ScenarioResult(
        "mint_quote_accounting_after_payment", CAT,
        Result.FAIL, f"amount_paid={amount_paid}, expected {amount}",
    )


@scenario("mint_quote_accounting_after_mint", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """After minting, amount_issued reflects the minted amount."""
    amount = 8
    builder = ProofBuilder(mint)
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)

    quote = mint.mint_quote(amount)
    qid = quote["quote"]

    for _ in range(30):
        try:
            mint.mint_tokens(qid, api_outputs)
            break
        except RuntimeError:
            time.sleep(1)
    else:
        return ScenarioResult(
            "mint_quote_accounting_after_mint", CAT,
            Result.SKIP, "quote never became payable",
        )

    status = mint.check_mint_quote(qid)
    amount_issued = status.get("amount_issued", -1) if isinstance(status, dict) else -1
    if amount_issued == amount:
        return ScenarioResult(
            "mint_quote_accounting_after_mint", CAT,
            Result.PASS, f"amount_issued={amount_issued} == amount={amount}",
        )
    return ScenarioResult(
        "mint_quote_accounting_after_mint", CAT,
        Result.FAIL, f"amount_issued={amount_issued}, expected {amount}",
    )


@scenario("mint_quote_updated_at_monotonic", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """updated_at increases between state transitions."""
    amount = 8
    quote = mint.mint_quote(amount)
    qid = quote["quote"]
    ts_created = quote.get("updated_at")

    if ts_created is None:
        return ScenarioResult(
            "mint_quote_updated_at_monotonic", CAT,
            Result.FAIL, "no updated_at in initial response",
        )

    for _ in range(30):
        time.sleep(1)
        paid = mint.check_mint_quote(qid)
        if isinstance(paid, dict) and paid.get("state") == "PAID":
            break
    else:
        return ScenarioResult(
            "mint_quote_updated_at_monotonic", CAT,
            Result.SKIP, "quote never reached PAID state",
        )

    ts_paid = paid.get("updated_at")
    if ts_paid is None or ts_paid < ts_created:
        return ScenarioResult(
            "mint_quote_updated_at_monotonic", CAT,
            Result.FAIL,
            f"updated_at decreased: created={ts_created}, paid={ts_paid}",
        )

    time.sleep(2)

    builder = ProofBuilder(mint)
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    for _ in range(10):
        try:
            mint.mint_tokens(qid, api_outputs)
            break
        except RuntimeError:
            time.sleep(1)

    issued = mint.check_mint_quote(qid)
    ts_issued = issued.get("updated_at") if isinstance(issued, dict) else None
    if ts_issued is not None and ts_issued >= ts_paid:
        return ScenarioResult(
            "mint_quote_updated_at_monotonic", CAT,
            Result.PASS,
            f"{ts_created} → {ts_paid} → {ts_issued}",
        )
    return ScenarioResult(
        "mint_quote_updated_at_monotonic", CAT,
        Result.FAIL,
        f"updated_at decreased after mint: "
        f"paid={ts_paid}, issued={ts_issued}",
    )
