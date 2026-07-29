"""NUT-18 payment request conformance scenarios — 2 tests.

NUT-18 defines payment requests — a Cashu-native payment primitive.
Payment requests are CBOR-encoded and base64url-encoded with a ``creq``
prefix.  The mint does not process payment requests directly, but these
tests verify the encoding/decoding conformance using spec test vectors.

Format: ``creq`` + base64url( version_byte + CBOR_map )
"""
from __future__ import annotations

import base64
from typing import Any

from conformance.client import MintClient
from conformance.scenarios import scenario, ScenarioResult, Result

CAT = "NUT-18 Payment Request"

# ─── NUT-18 test vectors (from 18-tests.md) ──────────────────────────────

# Minimal Payment Request — only required fields
_TV_MINIMAL_CREQ = (
    "creqAo2FpaDdmNGEyYjM5YXVjc2F0YW2BeBhodHRwczovL21pbnQuZXhhbXBsZS5jb20="
)
_TV_MINIMAL = {
    "i": "7f4a2b39",
    "u": "sat",
    "m": ["https://mint.example.com"],
}

# Basic Payment Request — includes amount and transport
_TV_BASIC_CREQ = (
    "creqApWF0gaNhdGVub3N0cmFheKlucHJvZmlsZTFxcXNnbTZxZmEzYzhkdHoyZnZ6aHZm"
    "cWVhY213bTBlNTBwZTNrNXRmbXZwamptbjB2ajdtMnRncHozbWh4dWU2OXVoaHlldHZ2"
    "OXVqdWVycGQ0Nmh4dG5mZHVxM3dhbW53dmF6N3RtanY0a3h6N2Z3OHFlbnh2ZXd3ZGN4"
    "emNtOTl1cXM2YW1ud3Zhejd0bXdkYWVqdW1yMGRzNGxqaDduYWeBgmFuYjE3YWloYjdh"
    "OTAxNzZhYQphdWNzYXRhbYF3aHR0cHM6Ly84MzMzLnNwYWNlOjMzMzg"
)
_TV_BASIC_AMOUNT = 10


# ─── Minimal CBOR decoder ────────────────────────────────────────────────


def _cbor_decode(data: bytes, offset: int = 0) -> tuple[Any, int]:
    """Decode a single CBOR value starting at *offset*.

    Supports the subset needed for NUT-18 payment requests:
    unsigned ints, negative ints, byte strings, text strings,
    arrays, maps, and simple values (true/false/null).
    """
    if offset >= len(data):
        raise ValueError("unexpected end of CBOR data")

    b = data[offset]
    major = b >> 5
    info = b & 0x1F
    offset += 1

    # Read argument
    if info < 24:
        arg = info
    elif info == 24:
        arg = data[offset]
        offset += 1
    elif info == 25:
        arg = int.from_bytes(data[offset : offset + 2], "big")
        offset += 2
    elif info == 26:
        arg = int.from_bytes(data[offset : offset + 4], "big")
        offset += 4
    elif info == 27:
        arg = int.from_bytes(data[offset : offset + 8], "big")
        offset += 8
    else:
        raise ValueError(f"unsupported CBOR info value: {info}")

    if major == 0:  # unsigned integer
        return arg, offset
    if major == 1:  # negative integer
        return -1 - arg, offset
    if major == 2:  # byte string
        return data[offset : offset + arg], offset + arg
    if major == 3:  # text string
        return data[offset : offset + arg].decode("utf-8"), offset + arg
    if major == 4:  # array
        items: list[Any] = []
        for _ in range(arg):
            item, offset = _cbor_decode(data, offset)
            items.append(item)
        return items, offset
    if major == 5:  # map
        result: dict[Any, Any] = {}
        for _ in range(arg):
            key, offset = _cbor_decode(data, offset)
            value, offset = _cbor_decode(data, offset)
            result[key] = value
        return result, offset
    if major == 7:  # simple / float
        if arg == 20:
            return False, offset
        if arg == 21:
            return True, offset
        if arg == 22:
            return None, offset
        return arg, offset

    raise ValueError(f"unsupported CBOR major type: {major}")


def _decode_creq(creq_str: str) -> dict[str, Any]:
    """Decode a ``creq…`` payment request string to a dict."""
    if not creq_str.startswith("creq"):
        raise ValueError("not a creq payment request")
    raw = base64.urlsafe_b64decode(creq_str[4:])
    version = raw[0]
    if version != 0:
        raise ValueError(f"unsupported payment request version: {version}")
    decoded, _ = _cbor_decode(raw, 1)
    return decoded


# ─── Scenario 1: decode ──────────────────────────────────────────────────


@scenario("nut18_payment_request_decode", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Verify a creq payment request decodes to expected fields."""
    try:
        decoded = _decode_creq(_TV_MINIMAL_CREQ)
    except Exception as e:
        return ScenarioResult(
            "nut18_payment_request_decode",
            CAT,
            Result.FAIL,
            f"decode error: {type(e).__name__}: {e}",
        )

    expected_keys = {"i", "u", "m"}
    missing = expected_keys - set(decoded.keys())
    if missing:
        return ScenarioResult(
            "nut18_payment_request_decode",
            CAT,
            Result.FAIL,
            f"missing fields after decode: {missing}",
        )

    if decoded["i"] != _TV_MINIMAL["i"]:
        return ScenarioResult(
            "nut18_payment_request_decode",
            CAT,
            Result.FAIL,
            f"id mismatch: expected {_TV_MINIMAL['i']!r}, "
            f"got {decoded['i']!r}",
        )
    if decoded["u"] != _TV_MINIMAL["u"]:
        return ScenarioResult(
            "nut18_payment_request_decode",
            CAT,
            Result.FAIL,
            f"unit mismatch: expected {_TV_MINIMAL['u']!r}, "
            f"got {decoded['u']!r}",
        )
    if decoded["m"] != _TV_MINIMAL["m"]:
        return ScenarioResult(
            "nut18_payment_request_decode",
            CAT,
            Result.FAIL,
            f"mints mismatch: expected {_TV_MINIMAL['m']!r}, "
            f"got {decoded['m']!r}",
        )

    return ScenarioResult(
        "nut18_payment_request_decode",
        CAT,
        Result.PASS,
        f"decoded successfully: id={decoded['i']}, "
        f"unit={decoded['u']}, "
        f"{len(decoded['m'])} mint(s)",
    )


# ─── Scenario 2: amount ──────────────────────────────────────────────────


@scenario("nut18_payment_request_amount", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Verify the amount field in a decoded payment request is correct."""
    try:
        decoded = _decode_creq(_TV_BASIC_CREQ)
    except Exception as e:
        return ScenarioResult(
            "nut18_payment_request_amount",
            CAT,
            Result.FAIL,
            f"decode error: {type(e).__name__}: {e}",
        )

    if "a" not in decoded:
        return ScenarioResult(
            "nut18_payment_request_amount",
            CAT,
            Result.FAIL,
            "no 'a' (amount) field in decoded payment request",
        )

    amount = decoded["a"]
    if amount != _TV_BASIC_AMOUNT:
        return ScenarioResult(
            "nut18_payment_request_amount",
            CAT,
            Result.FAIL,
            f"amount mismatch: expected {_TV_BASIC_AMOUNT}, got {amount}",
        )

    return ScenarioResult(
        "nut18_payment_request_amount",
        CAT,
        Result.PASS,
        f"amount={amount} sat decoded correctly",
    )
