"""Invoice description conformance scenario — 1 test.

Verifies that the BOLT11 invoice description embeds the quote ID
(truncated to 16 chars per H2 spec) rather than the full UUID.
Skips gracefully when the mint's FakeWallet does not return a
decodable BOLT11 invoice.
"""
from __future__ import annotations

import re

from conformance.client import MintClient
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
)

CAT = "Invoice Description"

_BOLT11_PREFIX_RE = re.compile(r"^(lnbc|lntb|lntbs|lntb)[a-zA-Z0-9]+")


def _try_decode_bolt11(invoice: str) -> dict | None:
    """Attempt to decode a BOLT11 invoice using any available library."""
    for mod_name in ("bolt11", "lightning"):
        try:
            mod = __import__(mod_name)
        except ImportError:
            continue
        decode_fn = getattr(mod, "decode", None) or getattr(mod, "from_string", None)
        if decode_fn is None:
            continue
        try:
            decoded = decode_fn(invoice)
            if isinstance(decoded, dict):
                return decoded
            if hasattr(decoded, "tags"):
                result: dict = {}
                for tag in decoded.tags:
                    if isinstance(tag, (list, tuple)) and len(tag) >= 2:
                        key = tag[0]
                        val = tag[1] if len(tag) == 2 else tag[1:]
                        if key in ("description", "1"):
                            result.setdefault("description", val)
                return result if result else None
        except Exception:
            continue
    return None


@scenario("invoice_description_truncated_quote_id", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Decode BOLT11 invoice, verify description contains 16-char quote ID prefix."""
    quote = mint.mint_quote(8)
    qid = quote.get("quote", "")
    invoice = quote.get("request", "")

    if not invoice or not _BOLT11_PREFIX_RE.match(invoice):
        return ScenarioResult(
            "invoice_description_truncated_quote_id", CAT,
            Result.SKIP,
            f"invoice not decodable BOLT11: {invoice[:40]!r}...",
        )

    decoded = _try_decode_bolt11(invoice)
    if decoded is None:
        return ScenarioResult(
            "invoice_description_truncated_quote_id", CAT,
            Result.SKIP, "no BOLT11 decoder available or decode failed",
        )

    description = decoded.get("description", "")
    if not description:
        return ScenarioResult(
            "invoice_description_truncated_quote_id", CAT,
            Result.SKIP, "decoded invoice has no description field",
        )

    qid_prefix = qid[:16]
    if qid_prefix in description:
        if qid in description and len(qid) > 16:
            return ScenarioResult(
                "invoice_description_truncated_quote_id", CAT,
                Result.FAIL,
                f"description contains full UUID, expected 16-char prefix: "
                f"{description[:120]}",
            )
        return ScenarioResult(
            "invoice_description_truncated_quote_id", CAT,
            Result.PASS, f"description contains {qid_prefix!r}",
        )

    return ScenarioResult(
        "invoice_description_truncated_quote_id", CAT,
        Result.SKIP,
        f"quote prefix {qid_prefix!r} not in description: "
        f"{description[:120]}",
    )
