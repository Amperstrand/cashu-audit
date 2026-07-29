"""NUT-26 bech32m encoding conformance scenarios — 2 tests.

NUT-26 defines an alternative encoding for payment requests using
Bech32m with TLV (Tag-Length-Value) serialisation.  The mint does not
directly handle bech32m, but these tests verify encoding/decoding
conformance using the spec test vectors from ``26-test.md``.

Format: ``creqb`` + ``1`` + bech32m( TLV(payment_request) )
"""
from __future__ import annotations

from typing import Any

from conformance.client import MintClient
from conformance.scenarios import scenario, ScenarioResult, Result

CAT = "NUT-26 Bech32m"

# ─── Bech32m primitives (BIP-173 / BIP-350) ─────────────────────────────

_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32M_CONST = 0x2BC830A3


def _bech32_polymod(values: list[int]) -> int:
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= gen[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _bech32m_create_checksum(hrp: str, data: list[int]) -> list[int]:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ _BECH32M_CONST
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _bech32m_verify_checksum(hrp: str, data: list[int]) -> bool:
    return _bech32_polymod(_bech32_hrp_expand(hrp) + data) == _BECH32M_CONST


def _bech32_encode(hrp: str, data: list[int]) -> str:
    combined = data + _bech32m_create_checksum(hrp, data)
    return hrp + "1" + "".join(_CHARSET[d] for d in combined)


def _bech32_decode(bech: str) -> tuple[str | None, list[int] | None]:
    bech = bech.strip()
    # Reject mixed case
    if bech.lower() != bech and bech.upper() != bech:
        return (None, None)
    bech = bech.lower()
    pos = bech.rfind("1")
    if pos < 1 or pos + 7 > len(bech):
        return (None, None)
    if not all(x in _CHARSET for x in bech[pos + 1 :]):
        return (None, None)
    hrp = bech[:pos]
    data = [_CHARSET.find(x) for x in bech[pos + 1 :]]
    if _bech32m_verify_checksum(hrp, data):
        return (hrp, data[:-6])
    return (None, None)


def _convertbits(
    data: list[int], frombits: int, tobits: int, pad: bool = True
) -> list[int]:
    """Convert between bit-widths (e.g. 8↔5 for bech32m)."""
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            raise ValueError("invalid value for convertbits")
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (tobits - bits)) & maxv)
    return ret


# ─── TLV codec for CREQB payment requests ───────────────────────────────

# Top-level TLV tags (NUT-26 spec §TLV Structure)
_TLV_ID = 0x01
_TLV_AMOUNT = 0x02
_TLV_UNIT = 0x03
_TLV_SINGLE_USE = 0x04
_TLV_MINT = 0x05
_TLV_DESCRIPTION = 0x06


def _tlv_encode_record(tag: int, value: bytes) -> bytes:
    """Encode a single TLV record: tag(1B) + length(2B BE) + value."""
    return bytes([tag]) + len(value).to_bytes(2, "big") + value


def _tlv_decode(data: bytes) -> list[tuple[int, bytes]]:
    """Decode a sequence of TLV records → list of (tag, value)."""
    records: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(data):
        if offset + 3 > len(data):
            raise ValueError("truncated TLV header")
        tag = data[offset]
        length = int.from_bytes(data[offset + 1 : offset + 3], "big")
        offset += 3
        if offset + length > len(data):
            raise ValueError("truncated TLV value")
        value = data[offset : offset + length]
        records.append((tag, value))
        offset += length
    return records


def _payment_request_to_tlv(pr: dict[str, Any]) -> bytes:
    """Encode a payment-request dict into TLV bytes (CREQB data payload)."""
    parts = bytearray()
    if "i" in pr:
        parts += _tlv_encode_record(_TLV_ID, pr["i"].encode("utf-8"))
    if "a" in pr:
        parts += _tlv_encode_record(
            _TLV_AMOUNT, int(pr["a"]).to_bytes(8, "big")
        )
    if "u" in pr:
        unit = pr["u"]
        if unit == "sat":
            parts += _tlv_encode_record(_TLV_UNIT, b"\x00")
        else:
            parts += _tlv_encode_record(_TLV_UNIT, unit.encode("utf-8"))
    if "s" in pr:
        parts += _tlv_encode_record(
            _TLV_SINGLE_USE, b"\x01" if pr["s"] else b"\x00"
        )
    if "m" in pr:
        for mint_url in pr["m"]:
            parts += _tlv_encode_record(
                _TLV_MINT, mint_url.encode("utf-8")
            )
    if "d" in pr:
        parts += _tlv_encode_record(
            _TLV_DESCRIPTION, pr["d"].encode("utf-8")
        )
    return bytes(parts)


def _tlv_to_payment_request(
    records: list[tuple[int, bytes]],
) -> dict[str, Any]:
    """Decode TLV records back into a payment-request dict."""
    pr: dict[str, Any] = {}
    mints: list[str] = []
    for tag, value in records:
        if tag == _TLV_ID:
            pr["i"] = value.decode("utf-8")
        elif tag == _TLV_AMOUNT:
            pr["a"] = int.from_bytes(value, "big")
        elif tag == _TLV_UNIT:
            pr["u"] = "sat" if value == b"\x00" else value.decode("utf-8")
        elif tag == _TLV_SINGLE_USE:
            pr["s"] = value == b"\x01"
        elif tag == _TLV_MINT:
            mints.append(value.decode("utf-8"))
        elif tag == _TLV_DESCRIPTION:
            pr["d"] = value.decode("utf-8")
    if mints:
        pr["m"] = mints
    return pr


def _creqb_encode(pr: dict[str, Any]) -> str:
    """Encode a payment request to a CREQB bech32m string (uppercase)."""
    tlv = _payment_request_to_tlv(pr)
    data5 = _convertbits(list(tlv), 8, 5, pad=True)
    return _bech32_encode("creqb", data5).upper()


def _creqb_decode(creqb_str: str) -> dict[str, Any] | None:
    """Decode a CREQB bech32m string to a payment-request dict."""
    hrp, data5 = _bech32_decode(creqb_str)
    if hrp != "creqb" or data5 is None:
        return None
    tlv_bytes = bytes(_convertbits(data5, 5, 8, pad=False))
    records = _tlv_decode(tlv_bytes)
    return _tlv_to_payment_request(records)


# ─── NUT-26 test vectors (from 26-test.md) ──────────────────────────────

_TV_MINIMAL_PR = {
    "i": "7f4a2b39",
    "u": "sat",
    "m": ["https://mint.example.com"],
}
_TV_MINIMAL_CREQB = (
    "CREQB1QYQQSDMXX3SNYC3N8YPSQQGQQ5QPS6R5W3C8XW309AKKJMN59EJ"
    "HSCTDWPKX2TNRDAKSYP0LHG"
)

_TV_DESC_PR = {
    "i": "desc_test",
    "a": 100,
    "u": "sat",
    "m": ["https://mint.example.com"],
    "d": "Test payment description",
}
_TV_DESC_CREQB = (
    "CREQB1QYQQJER9WD347AR9WD6QYQQGQQQQQQQQQQQXGQCQQYQQ2QQCDP68"
    "GURN8GHJ7MTFDE6ZUETCV9KHQMR99E3K7MGXQQV9GETNWSS8QCTED4JKUA"
    "PQV3JHXCMJD9C8G6T0DCFLJJRX"
)


# ─── Scenario 1: encode ──────────────────────────────────────────────────


@scenario("nut26_encode_token_v4", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Verify V4 bech32m encoding produces the expected CREQB string."""
    # Encode the minimal payment request
    encoded = _creqb_encode(_TV_MINIMAL_PR)
    if encoded != _TV_MINIMAL_CREQB:
        return ScenarioResult(
            "nut26_encode_token_v4",
            CAT,
            Result.FAIL,
            f"encoding mismatch:\n  expected: {_TV_MINIMAL_CREQB}\n"
            f"  got:      {encoded}",
        )

    # Also verify the description vector (tests amount + description encoding)
    encoded_desc = _creqb_encode(_TV_DESC_PR)
    if encoded_desc != _TV_DESC_CREQB:
        return ScenarioResult(
            "nut26_encode_token_v4",
            CAT,
            Result.FAIL,
            f"description vector mismatch:\n  expected: "
            f"{_TV_DESC_CREQB}\n  got:      {encoded_desc}",
        )

    return ScenarioResult(
        "nut26_encode_token_v4",
        CAT,
        Result.PASS,
        "minimal and description test vectors encoded correctly",
    )


# ─── Scenario 2: decode ──────────────────────────────────────────────────


@scenario("nut26_decode_token_v4", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Verify V4 bech32m decoding extracts expected fields."""
    decoded = _creqb_decode(_TV_MINIMAL_CREQB)
    if decoded is None:
        return ScenarioResult(
            "nut26_decode_token_v4",
            CAT,
            Result.FAIL,
            "bech32m decode returned None (checksum or format error)",
        )

    # Verify required fields
    if decoded.get("i") != _TV_MINIMAL_PR["i"]:
        return ScenarioResult(
            "nut26_decode_token_v4",
            CAT,
            Result.FAIL,
            f"id mismatch: expected {_TV_MINIMAL_PR['i']!r}, "
            f"got {decoded.get('i')!r}",
        )
    if decoded.get("u") != _TV_MINIMAL_PR["u"]:
        return ScenarioResult(
            "nut26_decode_token_v4",
            CAT,
            Result.FAIL,
            f"unit mismatch: expected {_TV_MINIMAL_PR['u']!r}, "
            f"got {decoded.get('u')!r}",
        )
    if decoded.get("m") != _TV_MINIMAL_PR["m"]:
        return ScenarioResult(
            "nut26_decode_token_v4",
            CAT,
            Result.FAIL,
            f"mints mismatch: expected {_TV_MINIMAL_PR['m']!r}, "
            f"got {decoded.get('m')!r}",
        )

    # Also verify the description vector round-trips
    decoded_desc = _creqb_decode(_TV_DESC_CREQB)
    if decoded_desc is None:
        return ScenarioResult(
            "nut26_decode_token_v4",
            CAT,
            Result.FAIL,
            "description vector decode returned None",
        )
    if decoded_desc.get("a") != _TV_DESC_PR["a"]:
        return ScenarioResult(
            "nut26_decode_token_v4",
            CAT,
            Result.FAIL,
            f"amount mismatch: expected {_TV_DESC_PR['a']}, "
            f"got {decoded_desc.get('a')}",
        )
    if decoded_desc.get("d") != _TV_DESC_PR["d"]:
        return ScenarioResult(
            "nut26_decode_token_v4",
            CAT,
            Result.FAIL,
            f"description mismatch: expected {_TV_DESC_PR['d']!r}, "
            f"got {decoded_desc.get('d')!r}",
        )

    return ScenarioResult(
        "nut26_decode_token_v4",
        CAT,
        Result.PASS,
        "minimal + description vectors decoded: "
        f"id={decoded.get('i')}, amount={decoded_desc.get('a')}, "
        f"desc={decoded_desc.get('d', '')[:20]}",
    )
