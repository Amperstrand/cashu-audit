"""NUT-00 secret-encoding convention scenarios — 2 tests.

NUT-00 defines the Proof secret as a *string*; `hash_to_curve` consumes the
UTF-8 bytes of that exact string (spec: "secret is the secret message and is
a utf-8 encoded string"). The mint verifies `C == a * hash_to_curve(utf8(secret))`
at spend time only — blind signing cannot detect how `B_` was derived.

The trap: a wallet that blinds the RAW ENTROPY a hex secret was derived from
(instead of the UTF-8 bytes of the string) receives valid-looking signatures,
DLEQ proofs and tokens that are permanently unspendable at every conforming
mint. This divergence has shipped in multiple independent implementations
(two wallet ports, a Java NUT-11 platform-charset bug), so these scenarios
pin both sides of the boundary:

1. ``secret_encoding_control_spendable`` — the string convention (this
   codebase's ``step1_alice``) must yield spendable proofs.
2. ``secret_encoding_entropy_trap_rejected`` — proofs blinded over the raw
   entropy must be REJECTED by the mint. A mint that accepts them is lenient
   at the verification boundary (it would also accept tokens from buggy
   wallets, hiding the fault until tokens move to a conforming mint).

Vector alignment: the canonical Y values for both derivations of the
hex-looking secret "deadbeef"×8 are pinned in
``conformance/reference-vectors/nut00-secret-encoding.json`` (cross-validated
against cdk, nutshell, nucula, cashu-core-lite and cashu-ts).
"""
from __future__ import annotations

import os
import time

from coincurve import PrivateKey

from conformance.builder import ProofBuilder
from conformance.client import MintClient
from conformance.crypto import generate_secret, hash_to_curve, pubkey_add, step3_alice
from conformance.scenarios import scenario, ScenarioResult, Result

CAT = "NUT-00 Secret Encoding"

TRAP_SECRET = "deadbeef" * 8
TRAP_CORRECT_Y = "0244d4bdec44e84725e2b6d9d7a2896df8bc27b482e84e0cb2144272d318375bc3"
TRAP_WRONG_Y = "02a265a770fac13ca9467f4b53e2429dbf37a22d9e6bf0c550682dc49952805640"


def _mint_outputs(mint: MintClient, amount: int, api_outputs: list[dict]) -> list[dict]:
    """Create a paid quote and mint the given outputs, retrying until paid."""
    quote = mint.mint_quote(amount)
    quote_id = quote["quote"]
    result = None
    for _ in range(30):
        try:
            result = mint.mint_tokens(quote_id, api_outputs)
            break
        except RuntimeError:
            time.sleep(1)
    if result is None:
        result = mint.mint_tokens(quote_id, api_outputs)
    return result.get("signatures", [])


@scenario("secret_encoding_control_spendable", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Proofs built with the string convention (utf8 of the hex string) spend."""
    builder = ProofBuilder(mint)
    amount = 64
    outputs = builder.create_outputs(amount, lambda: generate_secret())
    api_outputs = builder.outputs_to_api(outputs)
    signatures = _mint_outputs(mint, amount, api_outputs)
    if not signatures:
        return ScenarioResult(
            "secret_encoding_control_spendable", CAT,
            Result.FAIL, "no signatures returned from mint",
        )
    _keyset_id, keys = builder.get_active_keyset()
    proofs = builder.unblind_signatures(signatures, outputs, keys)
    swap_total = amount - builder.calc_fee(len(proofs))
    swap_outputs = builder.create_outputs(swap_total, lambda: generate_secret())
    result = mint.swap([p.to_dict() for p in proofs], builder.outputs_to_api(swap_outputs))
    if result.get("signatures"):
        return ScenarioResult(
            "secret_encoding_control_spendable", CAT,
            Result.PASS,
            "utf8(hex-string) convention mints and swaps cleanly",
        )
    return ScenarioResult(
        "secret_encoding_control_spendable", CAT,
        Result.FAIL, "swap returned no signatures for correct-convention proofs",
    )


@scenario("secret_encoding_entropy_trap_rejected", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Proofs blinded over the raw entropy (not the string) must be rejected.

    Binds B_ to hash_to_curve(raw_entropy) while publishing the hex string as
    the secret — the exact footgun that produces permanently unspendable
    tokens. A conforming mint MUST reject the swap with a proof-verification
    error (NUT error code 10001 family).
    """
    # local sanity first: the two derivations must yield different points
    entropy = os.urandom(32)
    secret_str = entropy.hex()
    Y_string = hash_to_curve(secret_str.encode("utf-8"))
    Y_entropy = hash_to_curve(entropy)
    if Y_string.format().hex() == Y_entropy.format().hex():
        return ScenarioResult(
            "secret_encoding_entropy_trap_rejected", CAT,
            Result.FAIL,
            "local hash_to_curve cannot distinguish string vs entropy derivation",
        )

    builder = ProofBuilder(mint)
    keyset_id, keys = builder.get_active_keyset()

    # blind the RAW ENTROPY (the trap)
    amount = 64
    r = PrivateKey()
    B_ = pubkey_add(Y_entropy, r.public_key)
    api_outputs = [{"amount": amount, "id": keyset_id, "B_": B_.format().hex()}]
    signatures = _mint_outputs(mint, amount, api_outputs)
    if not signatures:
        return ScenarioResult(
            "secret_encoding_entropy_trap_rejected", CAT,
            Result.FAIL, "no signatures returned from mint",
        )

    # unblind: C = C_ - r*A (algebra is identical for both conventions)
    A_hex = keys[amount]
    from coincurve import PublicKey
    C_ = PublicKey(bytes.fromhex(signatures[0]["C_"]))
    C = step3_alice(C_, r, PublicKey(bytes.fromhex(A_hex)))

    trap_proof = {
        "amount": amount,
        "secret": secret_str,
        "C": C.format().hex(),
        "id": keyset_id,
    }
    swap_total = amount - builder.calc_fee(1)
    swap_outputs = builder.create_outputs(swap_total, lambda: generate_secret())
    code, data = mint.try_swap([trap_proof], builder.outputs_to_api(swap_outputs))
    if code == 200:
        return ScenarioResult(
            "secret_encoding_entropy_trap_rejected", CAT,
            Result.FAIL,
            "MINT ACCEPTED entropy-blinded proof: lenient at the NUT-00 "
            "verification boundary (would mask buggy wallets)",
        )
    body = str(data)
    if "10001" in body or "not verified" in body.lower() or "could not verify" in body.lower():
        return ScenarioResult(
            "secret_encoding_entropy_trap_rejected", CAT,
            Result.PASS,
            f"entropy-blinded proof rejected as expected ({code}: {body[:120]})",
        )
    return ScenarioResult(
        "secret_encoding_entropy_trap_rejected", CAT,
        Result.PASS,
        f"rejected with HTTP {code} (non-standard error body — verify manually): {body[:160]}",
    )


@scenario("secret_encoding_forged_c_rejected", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """A proof with a random (forged) C must be rejected by every mint.

    Companion to ``secret_encoding_entropy_trap_rejected``: distinguishes
    "lenient dual-encoding verification" (accepts utf8- and entropy-bound
    proofs, rejects forgeries) from "no signature verification" (accepts
    forgeries — a critical mint vulnerability).
    """
    from coincurve import PrivateKey as SK
    builder = ProofBuilder(mint)
    keyset_id, _keys = builder.get_active_keyset()

    secret_str = generate_secret()
    forged_C = SK().public_key.format().hex()  # random valid point as fake C
    forged_proof = {"amount": 4, "secret": secret_str, "C": forged_C, "id": keyset_id}

    swap_total = 4 - builder.calc_fee(1)
    swap_outputs = builder.create_outputs(max(swap_total, 1), lambda: generate_secret())
    code, data = mint.try_swap([forged_proof], builder.outputs_to_api(swap_outputs))
    if code == 200:
        return ScenarioResult(
            "secret_encoding_forged_c_rejected", CAT,
            Result.FAIL,
            "MINT ACCEPTED a forged C: no blind-signature verification on the "
            "swap path (critical — arbitrary token fabrication)",
        )
    return ScenarioResult(
        "secret_encoding_forged_c_rejected", CAT,
        Result.PASS,
        f"forged C rejected ({code}: {str(data)[:120]})",
    )
