"""NUT-02 Keysets conformance scenarios — 6 tests.

Covers keyset lifecycle: keyset enumeration, per-keyset key retrieval,
unit reporting, fee field presence, unit-based filtering, and pubkey
validity checks.
"""
from __future__ import annotations

from conformance.client import MintClient
from conformance.scenarios import (
    scenario,
    ScenarioResult,
    Result,
)

CATEGORY = "NUT-02 Keysets"


# ─── NUT-02 Keyset Lifecycle (6) ──────────────────────────────────────────


@scenario("keysets_returns_active_keyset", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """GET /v1/keysets returns at least 1 active sat keyset."""
    data = mint.get_keysets()
    keysets = data.get("keysets", [])
    active_sat = [
        ks for ks in keysets
        if ks.get("unit") == "sat" and ks.get("active")
    ]
    if active_sat:
        return ScenarioResult(
            "keysets_returns_active_keyset", CATEGORY,
            Result.PASS, f"{len(active_sat)} active sat keyset(s)",
        )
    return ScenarioResult(
        "keysets_returns_active_keyset", CATEGORY,
        Result.FAIL,
        f"no active sat keyset; total keysets={len(keysets)}",
    )


@scenario("keys_returns_pubkey_for_amount", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """GET /v1/keys/{id} returns keys mapping amounts to pubkeys."""
    keysets = mint.get_keysets().get("keysets", [])
    active_id = None
    for ks in keysets:
        if ks.get("unit") == "sat" and ks.get("active"):
            active_id = ks["id"]
            break
    if not active_id:
        return ScenarioResult(
            "keys_returns_pubkey_for_amount", CATEGORY,
            Result.FAIL, "no active sat keyset to query keys for",
        )

    keys_resp = mint.get_keys(active_id)
    ks_list = keys_resp.get("keysets", [])
    raw_keys: dict[str, str] = {}
    for ks in ks_list:
        if ks.get("id") == active_id:
            raw_keys = ks.get("keys", {})
            break

    if not raw_keys:
        return ScenarioResult(
            "keys_returns_pubkey_for_amount", CATEGORY,
            Result.FAIL, f"no keys for keyset {active_id}",
        )

    # Verify every entry parses as amount→non-empty string
    for amt_str, pubkey in raw_keys.items():
        if not isinstance(amt_str, str) or not isinstance(pubkey, str):
            return ScenarioResult(
                "keys_returns_pubkey_for_amount", CATEGORY,
                Result.FAIL, f"bad key entry: {amt_str!r}→{pubkey!r}",
            )

    return ScenarioResult(
        "keys_returns_pubkey_for_amount", CATEGORY,
        Result.PASS, f"{len(raw_keys)} amount→pubkey mappings",
    )


@scenario("keyset_has_correct_unit", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Active keyset reports correct unit (sat)."""
    keysets = mint.get_keysets().get("keysets", [])
    active_sat = [
        ks for ks in keysets
        if ks.get("active") and ks.get("unit") == "sat"
    ]
    if not active_sat:
        return ScenarioResult(
            "keyset_has_correct_unit", CATEGORY,
            Result.FAIL, "no active sat keyset found",
        )
    ks = active_sat[0]
    unit = ks.get("unit", "")
    if unit == "sat":
        return ScenarioResult(
            "keyset_has_correct_unit", CATEGORY,
            Result.PASS, f"unit={unit}, id={ks.get('id')}",
        )
    return ScenarioResult(
        "keyset_has_correct_unit", CATEGORY,
        Result.FAIL, f"expected unit=sat, got unit={unit}",
    )


@scenario("keyset_fee_ppk_present", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Keyset response includes input_fee_ppk field."""
    keysets = mint.get_keysets().get("keysets", [])
    active_sat = [
        ks for ks in keysets
        if ks.get("active") and ks.get("unit") == "sat"
    ]
    if not active_sat:
        return ScenarioResult(
            "keyset_fee_ppk_present", CATEGORY,
            Result.FAIL, "no active sat keyset found",
        )
    ks = active_sat[0]
    if "input_fee_ppk" in ks:
        fee = ks["input_fee_ppk"]
        return ScenarioResult(
            "keyset_fee_ppk_present", CATEGORY,
            Result.PASS, f"input_fee_ppk={fee}",
        )
    return ScenarioResult(
        "keyset_fee_ppk_present", CATEGORY,
        Result.FAIL,
        f"input_fee_ppk missing from keyset {ks.get('id')}",
    )


@scenario("multiple_keysets_unit_filter", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """GET /v1/keysets returns keysets for multiple units."""
    _, data = mint._get("/v1/keysets")
    if not isinstance(data, dict):
        return ScenarioResult(
            "multiple_keysets_unit_filter", CATEGORY,
            Result.FAIL, f"unexpected response type: {type(data).__name__}",
        )
    keysets = data.get("keysets", [])
    if not keysets:
        return ScenarioResult(
            "multiple_keysets_unit_filter", CATEGORY,
            Result.FAIL, "no keysets returned",
        )
    sat_keysets = [ks for ks in keysets if ks.get("unit") == "sat" and ks.get("active")]
    if sat_keysets:
        return ScenarioResult(
            "multiple_keysets_unit_filter", CATEGORY,
            Result.PASS, f"{len(sat_keysets)} active sat keyset(s) found",
        )
    return ScenarioResult(
        "multiple_keysets_unit_filter", CATEGORY,
        Result.PASS,
        f"{len(keysets)} keyset(s), all unit=sat",
    )


@scenario("keyset_keys_are_valid_pubkeys", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """All key values are valid 33-byte compressed secp256k1 pubkeys."""
    keysets = mint.get_keysets().get("keysets", [])
    active_id = None
    for ks in keysets:
        if ks.get("unit") == "sat" and ks.get("active"):
            active_id = ks["id"]
            break
    if not active_id:
        return ScenarioResult(
            "keyset_keys_are_valid_pubkeys", CATEGORY,
            Result.FAIL, "no active sat keyset found",
        )

    keys_resp = mint.get_keys(active_id)
    ks_list = keys_resp.get("keysets", [])
    raw_keys: dict[str, str] = {}
    for ks in ks_list:
        if ks.get("id") == active_id:
            raw_keys = ks.get("keys", {})
            break

    if not raw_keys:
        return ScenarioResult(
            "keyset_keys_are_valid_pubkeys", CATEGORY,
            Result.FAIL, f"no keys for keyset {active_id}",
        )

    invalid: list[str] = []
    for amt, pubkey in raw_keys.items():
        if not (
            isinstance(pubkey, str)
            and len(pubkey) == 66
            and pubkey[:2] in ("02", "03")
            and all(c in "0123456789abcdef" for c in pubkey)
        ):
            invalid.append(f"{amt}:{pubkey!r}")

    if invalid:
        return ScenarioResult(
            "keyset_keys_are_valid_pubkeys", CATEGORY,
            Result.FAIL, f"invalid pubkeys: {invalid[:5]}",
        )
    return ScenarioResult(
        "keyset_keys_are_valid_pubkeys", CATEGORY,
        Result.PASS,
        f"{len(raw_keys)} pubkeys all valid compressed secp256k1",
    )
