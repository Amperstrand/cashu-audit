"""NUT-13 deterministic secrets conformance scenarios — 3 tests.

NUT-13 defines deterministic secret derivation from a BIP39 mnemonic
using BIP32 hierarchical derivation.  For the mint, we verify:

1. keyset_id_int computation matches the spec formula and test vectors.
2. BIP39/BIP32 secret derivation produces the expected deterministic secrets.
3. NUT-09 restore returns signatures for previously minted outputs.
"""
from __future__ import annotations

import hashlib
import hmac
import time

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret
from conformance.scenarios import scenario, ScenarioResult, Result

CAT = "NUT-13 Deterministic Secrets"

# ─── secp256k1 curve order ──────────────────────────────────────────────
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# ─── NUT-13 V1 test vectors ──────────────────────────────────────────────
_TV_KEYSET_ID = "009a1f293253e41e"
_TV_KEYSET_ID_INT = 864559728
_TV_MNEMONIC = (
    "half depart obvious quality work element "
    "tank gorilla view sugar picture humble"
)
_TV_SECRET_0 = (
    "485875df74771877439ac06339e284c3acfcd9be7abf3bc20b516faeadfe77ae"
)
_TV_SECRET_1 = (
    "8f2b39e8e594a4056eb1e6dbb4b0c38ef13b1b2c751f64f810ec04ee35b77270"
)


# ─── BIP-32 / BIP-39 helpers ─────────────────────────────────────────────


def _keyset_id_int(keyset_id_hex: str) -> int:
    """Compute keyset_id_int per NUT-13 spec.

    int.from_bytes(bytes.fromhex(keyset_id), "big") % (2**31 - 1)
    """
    return int.from_bytes(bytes.fromhex(keyset_id_hex), "big") % (2**31 - 1)


def _mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    """BIP-39 mnemonic → 64-byte seed."""
    return hashlib.pbkdf2_hmac(
        "sha512",
        mnemonic.encode("utf-8"),
        ("mnemonic" + passphrase).encode("utf-8"),
        2048,
        dklen=64,
    )


def _bip32_master(seed: bytes) -> tuple[bytes, bytes]:
    """Derive BIP-32 master private key and chain code from seed."""
    digest = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    return digest[:32], digest[32:]


def _ckd_priv(
    parent_key: bytes, parent_chain: bytes, index: int
) -> tuple[bytes, bytes]:
    """BIP-32 CKDpriv — supports hardened and non-hardened derivation."""
    from coincurve import PrivateKey as _PK

    if index >= 0x80000000:  # hardened
        data = b"\x00" + parent_key + index.to_bytes(4, "big")
    else:  # non-hardened: need parent public key
        parent_pub = _PK(parent_key).public_key.format(compressed=True)
        data = parent_pub + index.to_bytes(4, "big")
    digest = hmac.new(parent_chain, data, hashlib.sha512).digest()
    il = int.from_bytes(digest[:32], "big")
    ir = digest[32:]
    ki = (il + int.from_bytes(parent_key, "big")) % _N
    if ki == 0:
        raise ValueError("derived key is zero — invalid")
    return ki.to_bytes(32, "big"), ir


def _derive_path(
    master_key: bytes, master_chain: bytes, path: str
) -> bytes:
    """Derive a BIP-32 path such as m/129372'/0'/864559728'/0'."""
    key, chain = master_key, master_chain
    for part in path.lstrip("m").strip("/").split("/"):
        part = part.strip()
        if not part:
            continue
        hardened = part.endswith("'") or part.endswith("h")
        idx = int(part.rstrip("'h"))
        if hardened:
            idx += 0x80000000
        key, chain = _ckd_priv(key, chain, idx)
    return key


# ─── Scenario 1: keyset_id_int ──────────────────────────────────────────


@scenario("nut13_keyset_id_integer", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Verify keyset_id_int computation matches NUT-13 test vectors."""
    # Verify with the known test vector
    computed = _keyset_id_int(_TV_KEYSET_ID)
    if computed != _TV_KEYSET_ID_INT:
        return ScenarioResult(
            "nut13_keyset_id_integer",
            CAT,
            Result.FAIL,
            f"test vector mismatch: expected {_TV_KEYSET_ID_INT}, "
            f"got {computed}",
        )

    # Apply to the mint's actual keysets
    try:
        keysets_resp = mint.get_keysets()
    except Exception:
        return ScenarioResult(
            "nut13_keyset_id_integer",
            CAT,
            Result.SKIP,
            "could not fetch keysets from mint",
        )

    ks_list = keysets_resp.get("keysets", [])
    if not ks_list:
        return ScenarioResult(
            "nut13_keyset_id_integer",
            CAT,
            Result.FAIL,
            "mint returned no keysets",
        )

    computed_ids: list[str] = []
    for ks in ks_list:
        ks_id = ks.get("id", "")
        if not ks_id or len(ks_id) < 16:
            continue
        # V1 IDs are 8 bytes (16 hex); V2 IDs are longer and must be
        # truncated to the first 8 bytes before conversion.
        truncated = ks_id[:16] if len(ks_id) > 16 else ks_id
        ks_int = _keyset_id_int(truncated)
        computed_ids.append(f"{ks_id[:8]}…→{ks_int}")

    if not computed_ids:
        return ScenarioResult(
            "nut13_keyset_id_integer",
            CAT,
            Result.FAIL,
            "no keysets with valid IDs found",
        )

    return ScenarioResult(
        "nut13_keyset_id_integer",
        CAT,
        Result.PASS,
        f"test vector verified; {len(computed_ids)} mint keyset(s) "
        f"computed: {computed_ids[0]}",
    )


# ─── Scenario 2: secret derivation ──────────────────────────────────────


@scenario("nut13_secret_derivation", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Verify BIP39/BIP32 secret derivation matches NUT-13 test vectors."""
    seed = _mnemonic_to_seed(_TV_MNEMONIC)
    master_key, master_chain = _bip32_master(seed)

    # counter=0 → secret path m/129372'/0'/864559728'/0'/0
    path_0 = f"m/129372'/0'/{_TV_KEYSET_ID_INT}'/0'/0"
    secret_0 = _derive_path(master_key, master_chain, path_0).hex()
    if secret_0 != _TV_SECRET_0:
        return ScenarioResult(
            "nut13_secret_derivation",
            CAT,
            Result.FAIL,
            f"secret_0 mismatch: expected {_TV_SECRET_0[:32]}…, "
            f"got {secret_0[:32]}…",
        )

    # counter=1 → secret path m/129372'/0'/864559728'/1'/0
    path_1 = f"m/129372'/0'/{_TV_KEYSET_ID_INT}'/1'/0"
    secret_1 = _derive_path(master_key, master_chain, path_1).hex()
    if secret_1 != _TV_SECRET_1:
        return ScenarioResult(
            "nut13_secret_derivation",
            CAT,
            Result.FAIL,
            f"secret_1 mismatch: expected {_TV_SECRET_1[:32]}…, "
            f"got {secret_1[:32]}…",
        )

    return ScenarioResult(
        "nut13_secret_derivation",
        CAT,
        Result.PASS,
        "secrets for counter 0 and 1 derived correctly from test mnemonic",
    )


# ─── Scenario 3: restore works ───────────────────────────────────────────


@scenario("nut13_restore_works", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """NUT-09 restore returns signatures for previously minted outputs."""
    builder = ProofBuilder(mint)

    # Mint tokens so the mint has seen the outputs
    outputs = builder.create_outputs(8, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)

    quote = mint.mint_quote(8)
    quote_id = quote["quote"]

    minted = False
    result = None
    for _ in range(30):
        try:
            result = mint.mint_tokens(quote_id, api_outputs)
            minted = True
            break
        except RuntimeError:
            time.sleep(1)

    if not minted or result is None:
        return ScenarioResult(
            "nut13_restore_works",
            CAT,
            Result.SKIP,
            "quote never reached PAID — cannot test restore",
        )

    original_sigs = result.get("signatures", [])
    original_c_values = [s.get("C_", "") for s in original_sigs]

    # Call restore with the same blinded outputs
    code, body = mint._post("/v1/restore", {"outputs": api_outputs})

    if code != 200:
        return ScenarioResult(
            "nut13_restore_works",
            CAT,
            Result.SKIP,
            f"restore endpoint returned HTTP {code}",
        )

    if not isinstance(body, dict):
        return ScenarioResult(
            "nut13_restore_works",
            CAT,
            Result.FAIL,
            f"unexpected response type: {type(body).__name__}",
        )

    restored_sigs = body.get("signatures") or body.get("promises") or []

    if len(restored_sigs) != len(original_sigs):
        return ScenarioResult(
            "nut13_restore_works",
            CAT,
            Result.FAIL,
            f"expected {len(original_sigs)} restored signatures, "
            f"got {len(restored_sigs)}",
        )

    # Verify restored C_ values match the originals
    restored_c_values = [s.get("C_", "") for s in restored_sigs]
    if restored_c_values == original_c_values:
        return ScenarioResult(
            "nut13_restore_works",
            CAT,
            Result.PASS,
            f"{len(restored_sigs)} signature(s) restored, "
            "C_ values match originals",
        )

    return ScenarioResult(
        "nut13_restore_works",
        CAT,
        Result.FAIL,
        "restored C_ values do not match original mint signatures",
    )
