"""Constructs Cashu proofs with specific spending conditions (P2PK, HTLC).

End-to-end flow:
1. Mint regular proofs via the mint API (NUT-04 → NUT-03)
2. Swap them for new outputs whose secrets are P2PK/HTLC NUT-10 encoded
3. Unblind the signatures to get spendable proofs
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Literal

from .client import MintClient
from .crypto import KeyPair, generate_secret, hash_to_curve, step1_alice, step3_alice, pubkey_neg


@dataclass
class Proof:
    amount: int
    secret: str
    C: str
    id: str
    witness: str | None = None

    def to_dict(self) -> dict:
        d = {"amount": self.amount, "secret": self.secret, "C": self.C, "id": self.id}
        if self.witness:
            d["witness"] = self.witness
        return d

    def y_value(self) -> str:
        from .crypto import hash_to_curve
        return hash_to_curve(self.secret.encode("utf-8")).format().hex()


@dataclass
class OutputResult:
    B_: str
    r_hex: str
    amount: int
    secret: str


def build_p2pk_secret(
    data_pubkey: str,
    *,
    pubkeys: list[str] | None = None,
    n_sigs: int = 1,
    locktime: int | None = None,
    refund_keys: list[str] | None = None,
    n_sigs_refund: int | None = None,
    sigflag: str = "SIG_INPUTS",
) -> str:
    tags: list[list[str]] = [["sigflag", sigflag]]
    if pubkeys:
        tags.append(["pubkeys"] + pubkeys)
    tags.append(["n_sigs", str(n_sigs)])
    if locktime is not None:
        tags.append(["locktime", str(locktime)])
    if refund_keys:
        tags.append(["refund"] + refund_keys)
    if n_sigs_refund is not None:
        tags.append(["n_sigs_refund", str(n_sigs_refund)])

    secret_obj = ["P2PK", {
        "nonce": generate_secret(),
        "data": data_pubkey,
        "tags": tags,
    }]
    return json.dumps(secret_obj, separators=(",", ":"))


def build_htlc_secret(
    hash_hex: str,
    *,
    pubkeys: list[str] | None = None,
    n_sigs: int = 0,
    locktime: int | None = None,
    refund_keys: list[str] | None = None,
    n_sigs_refund: int | None = None,
    sigflag: str = "SIG_INPUTS",
) -> str:
    tags: list[list[str]] = [["sigflag", sigflag]]
    if pubkeys:
        tags.append(["pubkeys"] + pubkeys)
    if n_sigs > 0:
        tags.append(["n_sigs", str(n_sigs)])
    if locktime is not None:
        tags.append(["locktime", str(locktime)])
    if refund_keys:
        tags.append(["refund"] + refund_keys)
    if n_sigs_refund is not None:
        tags.append(["n_sigs_refund", str(n_sigs_refund)])

    secret_obj = ["HTLC", {
        "nonce": generate_secret(),
        "data": hash_hex,
        "tags": tags,
    }]
    return json.dumps(secret_obj, separators=(",", ":"))


class ProofBuilder:
    def __init__(self, mint: MintClient):
        self.mint = mint
        self._keyset_cache: tuple[str, dict[int, str]] | None = None
        self._fee_ppk = 0
        if get_sigall_mode(mint.base_url) == "standard":
            try:
                info = mint.get_mint_info()
                version = info.get("version", "").lower()
                if "nutshell" in version:
                    set_sigall_mode(mint.base_url, "legacy")
            except Exception:
                pass

    def get_active_keyset(self, unit: str = "sat") -> tuple[str, dict[int, str]]:
        if self._keyset_cache:
            return self._keyset_cache
        keysets = self.mint.get_keysets()
        active_id = None
        active_fee_ppk = 0
        for ks in keysets.get("keysets", []):
            if ks.get("unit") == unit and ks.get("active"):
                active_id = ks["id"]
                active_fee_ppk = ks.get("input_fee_ppk", 0)
                break
        if not active_id:
            raise RuntimeError(f"No active {unit} keyset")
        keys_resp = self.mint.get_keys(active_id)
        ks_list = keys_resp.get("keysets", [])
        mint_pubkey_for_amount_1 = ""
        keys: dict[int, str] = {}
        for ks in ks_list:
            if ks.get("id") == active_id:
                raw_keys = ks.get("keys", {})
                for k, v in raw_keys.items():
                    try:
                        amt = int(k)
                        keys[amt] = v
                        if amt == 1:
                            mint_pubkey_for_amount_1 = v
                    except ValueError:
                        pass
                break
        self._keyset_cache = (active_id, keys)
        self._fee_ppk = active_fee_ppk
        return self._keyset_cache

    def calc_fee(self, num_inputs: int) -> int:
        fee_ppk = getattr(self, "_fee_ppk", 0)
        return -(-num_inputs * fee_ppk // 1000)

    def _amount_to_powers(self, amount: int) -> list[int]:
        powers = []
        i = 0
        while amount > 0:
            if amount & 1:
                powers.append(2**i)
            amount >>= 1
            i += 1
        return powers

    def create_outputs(self, amount: int, secret_fn) -> list[OutputResult]:
        keyset_id, _ = self.get_active_keyset()
        powers = self._amount_to_powers(amount)
        results: list[OutputResult] = []
        for p in powers:
            secret_str = secret_fn()
            B_, r = step1_alice(secret_str)
            results.append(OutputResult(
                B_=B_.format().hex(),
                r_hex=r.to_hex(),
                amount=p,
                secret=secret_str,
            ))
        return results

    def outputs_to_api(self, outputs: list[OutputResult]) -> list[dict]:
        keyset_id, _ = self.get_active_keyset()
        return [{"amount": o.amount, "id": keyset_id, "B_": o.B_} for o in outputs]

    def unblind_signatures(self, sigs: list[dict], outputs: list[OutputResult], keys: dict[int, str]) -> list[Proof]:
        from coincurve import PublicKey as PubKey
        proofs: list[Proof] = []
        for sig, out in zip(sigs, outputs):
            amt = sig.get("amount", out.amount)
            mint_pubkey_hex = keys.get(amt, keys.get(1, ""))
            if not mint_pubkey_hex:
                raise RuntimeError(f"No mint pubkey for amount {amt}")
            A = PubKey(bytes.fromhex(mint_pubkey_hex))
            C_blinded = PubKey(bytes.fromhex(sig["C_"]))
            from coincurve import PrivateKey as PK
            r_priv = PK(bytes.fromhex(out.r_hex))
            C = step3_alice(C_blinded, r_priv, A)
            proofs.append(Proof(
                amount=amt,
                secret=out.secret,
                C=C.format().hex(),
                id=sig.get("id", ""),
            ))
        return proofs

    def mint_proofs(self, amount: int, secret_fn=None) -> list[Proof]:
        if secret_fn is None:
            secret_fn = lambda: generate_secret()

        outputs = self.create_outputs(amount, secret_fn)
        api_outputs = self.outputs_to_api(outputs)

        quote = self.mint.mint_quote(amount)
        quote_id = quote["quote"]

        for _ in range(30):
            try:
                result = self.mint.mint_tokens(quote_id, api_outputs)
                break
            except RuntimeError:
                time.sleep(1)
        else:
            result = self.mint.mint_tokens(quote_id, api_outputs)
        signatures = result.get("signatures", [])

        keyset_id, keys = self.get_active_keyset()
        return self.unblind_signatures(signatures, outputs, keys)

    def swap_to_p2pk(self, input_proofs: list[Proof], secret_fn, total_amount: int) -> list[Proof]:
        outputs = self.create_outputs(total_amount, secret_fn)
        api_outputs = self.outputs_to_api(outputs)
        inputs = [p.to_dict() for p in input_proofs]

        result = self.mint.swap(inputs, api_outputs)
        signatures = result.get("signatures", [])

        keyset_id, keys = self.get_active_keyset()
        return self.unblind_signatures(signatures, outputs, keys)

    def sign_p2pk_witness(self, proofs: list[Proof], keypair: KeyPair) -> str:
        import json as _json
        import hashlib
        sigs = []
        for p in proofs:
            msg = hashlib.sha256(p.secret.encode("utf-8")).digest()
            sig = keypair.sign_schnorr(msg)
            sigs.append(sig)
        return _json.dumps({"signatures": sigs})


def sigall_swap_message(inputs: list[Proof], output_amounts: list[tuple[int, str]]) -> str:
    msg = ""
    for p in inputs:
        msg += p.secret
        msg += p.C
    for amount, b_hex in output_amounts:
        msg += str(amount)
        msg += b_hex
    return msg


def sigall_swap_message_legacy(inputs: list[Proof], output_amounts: list[tuple[int, str]]) -> str:
    msg = ""
    for p in inputs:
        msg += p.secret
    for _, b_hex in output_amounts:
        msg += b_hex
    return msg


_SIGALL_MODE_CACHE: dict[str, str] = {}


def get_sigall_mode(mint_url: str) -> str:
    return _SIGALL_MODE_CACHE.get(mint_url, "standard")


def set_sigall_mode(mint_url: str, mode: str):
    _SIGALL_MODE_CACHE[mint_url] = mode


def sigall_swap_message_for(mint_url: str, inputs: list[Proof], output_amounts: list[tuple[int, str]]) -> str:
    if get_sigall_mode(mint_url) == "legacy":
        return sigall_swap_message_legacy(inputs, output_amounts)
    return sigall_swap_message(inputs, output_amounts)


def sigall_melt_message(inputs: list[Proof], output_amounts: list[tuple[int, str]], quote_id: str) -> str:
    return sigall_swap_message(inputs, output_amounts) + quote_id


def sigall_melt_message_legacy(inputs: list[Proof], output_amounts: list[tuple[int, str]], quote_id: str) -> str:
    return sigall_swap_message_legacy(inputs, output_amounts) + quote_id


def sigall_melt_message_for(mint_url: str, inputs: list[Proof], output_amounts: list[tuple[int, str]], quote_id: str) -> str:
    if get_sigall_mode(mint_url) == "legacy":
        return sigall_melt_message_legacy(inputs, output_amounts, quote_id)
    return sigall_melt_message(inputs, output_amounts, quote_id)


def set_sigall_witness(proofs: list[Proof], keypair: KeyPair, message: str):
    import hashlib
    msg_hash = hashlib.sha256(message.encode("utf-8")).digest()
    sig = keypair.sign_schnorr(msg_hash)
    proofs[0].witness = json.dumps({"signatures": [sig]})


def try_sigall_spend(
    mint,
    proofs: list[Proof],
    sign_keys: list[KeyPair] | None,
    output_amounts: list[tuple[int, str]],
    api_outputs: list[dict],
    preimage: str | None = None,
) -> tuple[int, object]:
    import hashlib
    url = mint.base_url
    cached = get_sigall_mode(url)

    modes_to_try = [cached] if cached != "standard" else ["standard", "legacy"]
    if cached == "legacy":
        modes_to_try = ["legacy"]

    last_code, last_body = 400, {}
    for mode in modes_to_try:
        if mode == "legacy":
            msg = sigall_swap_message_legacy(proofs, output_amounts)
        else:
            msg = sigall_swap_message(proofs, output_amounts)

        msg_hash = hashlib.sha256(msg.encode("utf-8")).digest()
        witness: dict = {}
        if preimage is not None:
            witness["preimage"] = preimage
        if sign_keys:
            witness["signatures"] = [k.sign_schnorr(msg_hash) for k in sign_keys]
        for p in proofs:
            p.witness = None
        proofs[0].witness = json.dumps(witness)

        last_code, last_body = mint.try_swap([p.to_dict() for p in proofs], api_outputs)

        body_str = str(last_body)
        if last_code == 200:
            set_sigall_mode(url, mode)
            return last_code, last_body
        if "0 < " in body_str and sign_keys and mode == "standard" and cached == "standard":
            set_sigall_mode(url, "legacy")
            continue
        return last_code, last_body

    return last_code, last_body


def generate_htlc_preimage() -> tuple[str, str]:
    import hashlib
    import os
    preimage_bytes = os.urandom(32)
    preimage_hex = preimage_bytes.hex()
    hash_hex = hashlib.sha256(preimage_bytes).hexdigest()
    return preimage_hex, hash_hex


def set_htlc_witness(proofs: list[Proof], preimage: str, signatures: list[str] | None = None):
    witness: dict = {"preimage": preimage}
    if signatures:
        witness["signatures"] = signatures
    for p in proofs:
        p.witness = json.dumps(witness)
