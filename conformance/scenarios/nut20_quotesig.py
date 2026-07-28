"""NUT-20 quote signature conformance scenarios — 4 tests.

NUT-20 allows locking a mint quote to a secp256k1 public key.
The mint must then verify a BIP-340 Schnorr signature before
allowing the mint operation.

Signature message format (Cashu_MintQuoteSig_v1):
    SHA256(
        b"Cashu_MintQuoteSig_v1"
        || len32(quote_bytes) || quote_bytes
        || for each output:
            len32(amount_bytes) || amount_bytes
            || len32(B_bytes) || B_bytes
    )

where len32(x) = 4-byte big-endian length of x,
amount_bytes = minimal big-endian encoding,
B_bytes = raw decoded hex of B_.
"""
from __future__ import annotations

import hashlib
import struct
import time

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import KeyPair, generate_secret
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
)

CAT = "NUT-20 Quote Sig"


def _amount_to_bytes(amount: int) -> bytes:
    if amount == 0:
        return b""
    return amount.to_bytes((amount.bit_length() + 7) // 8, "big")


def _construct_nut20_message(quote_id: str, outputs: list[dict]) -> bytes:
    parts = bytearray()
    parts.extend(b"Cashu_MintQuoteSig_v1")

    quote_bytes = quote_id.encode("utf-8")
    parts.extend(struct.pack(">I", len(quote_bytes)))
    parts.extend(quote_bytes)

    for output in outputs:
        amount_bytes = _amount_to_bytes(output["amount"])
        parts.extend(struct.pack(">I", len(amount_bytes)))
        parts.extend(amount_bytes)

        b_bytes = bytes.fromhex(output["B_"])
        parts.extend(struct.pack(">I", len(b_bytes)))
        parts.extend(b_bytes)

    return hashlib.sha256(bytes(parts)).digest()


def _wait_for_paid(mint: MintClient, qid: str, retries: int = 30) -> bool:
    for _ in range(retries):
        time.sleep(1)
        try:
            status = mint.check_mint_quote(qid)
            if isinstance(status, dict) and status.get("state") == "PAID":
                return True
        except RuntimeError:
            pass
    return False


@scenario("nut20_locked_quote_requires_signature", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Mint quote with pubkey rejects mint without signature."""
    kp = KeyPair.generate()
    amount = 8

    try:
        quote = mint.mint_quote_with_pubkey(amount, kp.pub_hex)
    except RuntimeError as e:
        return ScenarioResult(
            "nut20_locked_quote_requires_signature", CAT,
            Result.SKIP, f"mint does not support NUT-20 pubkey: {e}",
        )

    qid = quote["quote"]
    if not _wait_for_paid(mint, qid):
        return ScenarioResult(
            "nut20_locked_quote_requires_signature", CAT,
            Result.SKIP, "quote never reached PAID",
        )

    builder = ProofBuilder(mint)
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)

    code, body = mint.try_mint(qid, api_outputs)

    if code >= 400:
        return ScenarioResult(
            "nut20_locked_quote_requires_signature", CAT,
            Result.PASS, f"mint without sig rejected ({code})",
        )
    return ScenarioResult(
        "nut20_locked_quote_requires_signature", CAT,
        Result.FAIL,
        f"expected rejection, got {code}: {str(body)[:200]}",
    )


@scenario("nut20_locked_quote_valid_signature_succeeds", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Mint with correct NUT-20 signature succeeds."""
    kp = KeyPair.generate()
    amount = 8

    try:
        quote = mint.mint_quote_with_pubkey(amount, kp.pub_hex)
    except RuntimeError as e:
        return ScenarioResult(
            "nut20_locked_quote_valid_signature_succeeds", CAT,
            Result.SKIP, f"mint does not support NUT-20 pubkey: {e}",
        )

    qid = quote["quote"]
    if not _wait_for_paid(mint, qid):
        return ScenarioResult(
            "nut20_locked_quote_valid_signature_succeeds", CAT,
            Result.SKIP, "quote never reached PAID",
        )

    builder = ProofBuilder(mint)
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)

    msg_hash = _construct_nut20_message(qid, api_outputs)
    signature = kp.sign_schnorr(msg_hash)

    code, body = mint.try_mint(qid, api_outputs, signature=signature)

    if code == 200 and isinstance(body, dict):
        sigs = body.get("signatures", [])
        if len(sigs) == len(outputs):
            return ScenarioResult(
                "nut20_locked_quote_valid_signature_succeeds", CAT,
                Result.PASS, f"{len(sigs)} signatures minted with valid sig",
            )
    return ScenarioResult(
        "nut20_locked_quote_valid_signature_succeeds", CAT,
        Result.FAIL, f"got {code}: {str(body)[:200]}",
    )


@scenario("nut20_locked_quote_wrong_signature_fails", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Mint with wrong NUT-20 signature fails."""
    kp_lock = KeyPair.generate()
    kp_wrong = KeyPair.generate()
    amount = 8

    try:
        quote = mint.mint_quote_with_pubkey(amount, kp_lock.pub_hex)
    except RuntimeError as e:
        return ScenarioResult(
            "nut20_locked_quote_wrong_signature_fails", CAT,
            Result.SKIP, f"mint does not support NUT-20 pubkey: {e}",
        )

    qid = quote["quote"]
    if not _wait_for_paid(mint, qid):
        return ScenarioResult(
            "nut20_locked_quote_wrong_signature_fails", CAT,
            Result.SKIP, "quote never reached PAID",
        )

    builder = ProofBuilder(mint)
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)

    msg_hash = _construct_nut20_message(qid, api_outputs)
    wrong_sig = kp_wrong.sign_schnorr(msg_hash)

    code, body = mint.try_mint(qid, api_outputs, signature=wrong_sig)

    if code >= 400:
        return ScenarioResult(
            "nut20_locked_quote_wrong_signature_fails", CAT,
            Result.PASS, f"wrong sig rejected ({code})",
        )
    return ScenarioResult(
        "nut20_locked_quote_wrong_signature_fails", CAT,
        Result.FAIL,
        f"expected rejection, got {code}: {str(body)[:200]}",
    )


@scenario("nut20_quote_echoes_pubkey", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Response includes pubkey when set in the mint quote request."""
    kp = KeyPair.generate()

    try:
        quote = mint.mint_quote_with_pubkey(8, kp.pub_hex)
    except RuntimeError as e:
        return ScenarioResult(
            "nut20_quote_echoes_pubkey", CAT,
            Result.SKIP, f"mint does not support NUT-20 pubkey: {e}",
        )

    echoed = quote.get("pubkey", "")
    if echoed and echoed == kp.pub_hex:
        return ScenarioResult(
            "nut20_quote_echoes_pubkey", CAT,
            Result.PASS, f"pubkey echoed: {echoed[:20]}...",
        )
    return ScenarioResult(
        "nut20_quote_echoes_pubkey", CAT,
        Result.FAIL,
        f"expected pubkey={kp.pub_hex[:20]}..., got {echoed!r}",
    )
