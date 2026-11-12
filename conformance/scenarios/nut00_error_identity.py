"""NUT-00 error-identity scenarios (audit #68 item A).

Assert the SPEC identity of mint rejections — HTTP 400 + {"detail",
"code"} with the error_codes.md numeric code — never any-4xx-is-pass.
Today's implementations diverge on most of these; each arm's divergence
is recorded in its expected-fail seed (conformance/expected-fail-*.json)
with the measured code, so the suite both encodes the convergence target
and documents current truth.

Wire basis (conformance/results/error-identity/, 2026-11-04):
  gonuts v0.16.0 (info: gonuts/0.4.0), cdk-mintd 0.18.1,
  nutshell 0.21.0, cashu-cf testnut (Nutshell-CF/0.0.1) + local
  miniflare lock runs.
"""
from __future__ import annotations

import json

from conformance.builder import ProofBuilder, build_p2pk_secret
from conformance.client import MintClient
from conformance.crypto import KeyPair, generate_secret
from conformance.scenarios import (
    fmt_body,
    scenario,
    ScenarioResult,
    Result,
    expect_reject,
)

CATEGORY = "NUT-00 error identity"


def expect_code(expected: int):
    """Reject AND with the exact spec error code in a NUT-00 envelope."""
    def check(status: int, body) -> bool:
        if not expect_reject(status, body):
            return False
        return isinstance(body, dict) and body.get("code") == expected
    return check


def _note(name: str, ok: bool, status: int, body, want: str) -> ScenarioResult:
    got = (
        f"{body.get('code')}" if isinstance(body, dict) and "code" in body
        else f"no-code ({str(body)[:60]})"
    )
    return ScenarioResult(
        name, CATEGORY,
        Result.PASS if ok else Result.FAIL,
        f"want {want}, got http={status} code={got}: {fmt_body(body, 140)}",
    )


@scenario("errid_swap_unknown_keyset_code_12001", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Swap output with an unknown keyset id — spec: 12001 keyset not known."""
    builder = ProofBuilder(mint)
    keyset_id, _ = builder.get_active_keyset()
    proofs = builder.mint_proofs(4)
    out = builder.outputs_to_api(
        builder.create_outputs(4 - builder.calc_fee(1), generate_secret)
    )
    for o in out:
        o["id"] = "00" * 8
    code, body = mint.try_swap([p.to_dict() for p in proofs], out)
    ok = expect_code(12001)(code, body)
    return _note("errid_swap_unknown_keyset_code_12001", ok, code, body, "12001")


@scenario("errid_swap_duplicate_inputs_code_11007", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Same proof listed twice — spec: 11007 duplicate inputs."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    out = builder.outputs_to_api(
        builder.create_outputs(8 - builder.calc_fee(1), generate_secret)
    )
    code, body = mint.try_swap([proofs[0].to_dict()] * 2, out)
    ok = expect_code(11007)(code, body)
    return _note("errid_swap_duplicate_inputs_code_11007", ok, code, body, "11007")


@scenario("errid_swap_underfunded_code_11005", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Inputs worth less than outputs — spec: 11005 transaction not balanced."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    out = builder.outputs_to_api(builder.create_outputs(16, generate_secret))
    code, body = mint.try_swap([p.to_dict() for p in proofs], out)
    ok = expect_code(11005)(code, body)
    return _note("errid_swap_underfunded_code_11005", ok, code, body, "11005")


@scenario("errid_swap_spent_proofs_code_11001", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Re-spend consumed proofs — spec: 11001 proofs already spent."""
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    out = builder.outputs_to_api(
        builder.create_outputs(8 - builder.calc_fee(1), generate_secret)
    )
    code, body = mint.try_swap([p.to_dict() for p in proofs], out)
    if code != 200:
        return ScenarioResult(
            "errid_swap_spent_proofs_code_11001", CATEGORY, Result.FAIL,
            f"control swap failed: {code}: {fmt_body(body, 120)}",
        )
    out2 = builder.outputs_to_api(
        builder.create_outputs(8 - builder.calc_fee(1), generate_secret)
    )
    code, body = mint.try_swap([p.to_dict() for p in proofs], out2)
    ok = expect_code(11001)(code, body)
    return _note("errid_swap_spent_proofs_code_11001", ok, code, body, "11001")


@scenario("errid_swap_outputs_already_signed_code_11003", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Fresh inputs, already-signed outputs — spec: 11003 outputs already
    signed. Distinct from an exact-request NUT-19 replay (which cached
    mints answer 200): only the OUTPUTS are reused here."""
    builder = ProofBuilder(mint)
    first = builder.mint_proofs(8)
    out = builder.outputs_to_api(
        builder.create_outputs(8 - builder.calc_fee(1), generate_secret)
    )
    code, body = mint.try_swap([p.to_dict() for p in first], out)
    if code != 200:
        return ScenarioResult(
            "errid_swap_outputs_already_signed_code_11003", CATEGORY, Result.FAIL,
            f"control swap failed: {code}: {fmt_body(body, 120)}",
        )
    second = builder.mint_proofs(8)
    code, body = mint.try_swap([p.to_dict() for p in second], out)
    ok = expect_code(11003)(code, body)
    return _note("errid_swap_outputs_already_signed_code_11003", ok, code, body, "11003")


@scenario("errid_mint_quote_unit_unsupported_code_11013", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Mint quote for an unsupported unit — spec: 11013 unit not supported.

    Env-aware (2026-11-12): multi-unit mints (testnut serves usd) inverted
    the old hardcoded 'usd' premise into a false FAIL. Pick a unit absent
    from the mint's keysets; if every candidate is supported, SKIP loudly
    (nothing unsupported to test) rather than pin a wrong premise.
    """
    try:
        units = {k.get("unit") for k in mint.get_keys().get("keysets", []) if k.get("unit")}
    except Exception:
        units = {"sat"}
    candidates = ["eth", "eur", "xau", "usd"]
    unsupported = next((u for u in candidates if u not in units), None)
    if unsupported is None:
        return ScenarioResult(
            "errid_mint_quote_unit_unsupported_code_11013", CATEGORY, Result.SKIP,
            f"all candidate units supported by this mint ({sorted(units)}) — no unsupported-unit leg possible",
        )
    code, body = mint._post("/v1/mint/quote/bolt11", {"amount": 64, "unit": unsupported})
    ok = expect_code(11013)(code, body)
    return _note("errid_mint_quote_unit_unsupported_code_11013", ok, code, body, f"11013 (unit={unsupported})")


@scenario("errid_validation_error_nut00_envelope", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """Malformed crypto field (non-hex C) must still produce the NUT-00
    envelope: HTTP 400 + a JSON object carrying `detail` and `code`.
    Framework-level rejection shapes (422 pydantic/axum text) fail this —
    a wallet's error parser gets nothing to branch on."""
    builder = ProofBuilder(mint)
    keyset_id, _ = builder.get_active_keyset()
    proofs = builder.mint_proofs(4)
    out = builder.outputs_to_api(
        builder.create_outputs(4 - builder.calc_fee(1), generate_secret)
    )
    bad = {
        "amount": 4,
        "secret": generate_secret(),
        "C": "not-hex-at-all",
        "id": keyset_id,
    }
    code, body = mint.try_swap([bad] + [p.to_dict() for p in proofs[1:]], out)
    ok = (
        code == 400
        and isinstance(body, dict)
        and isinstance(body.get("detail"), str)
        and isinstance(body.get("code"), int)
    )
    return _note("errid_validation_error_nut00_envelope", ok, code, body, "400+{detail,code}")


@scenario("errid_p2pk_wrong_witness_reasoned_rejection", CATEGORY)
def _(mint: MintClient) -> ScenarioResult:
    """P2PK proof spent with a wrong-pubkey signature. The spec assigns no
    dedicated code, so the identity assertion is the REASON: the rejection
    must diagnose the witness/signature/threshold, not collapse into a
    generic invalid-proof identity (the class of the #68 matrix)."""
    import hashlib

    builder = ProofBuilder(mint)
    key = KeyPair.generate()
    wrong_key = KeyPair.generate()
    funded = builder.mint_proofs(8)
    p2pk = builder.swap_to_p2pk(
        funded,
        lambda: build_p2pk_secret(key.pub_hex),
        max(1, 8 - builder.calc_fee(len(funded))),
    )
    for p in p2pk:
        msg = hashlib.sha256(p.secret.encode()).digest()
        p.witness = json.dumps({"signatures": [wrong_key.sign_schnorr(msg)]})
    out = builder.outputs_to_api(
        builder.create_outputs(
            max(1, sum(q.amount for q in p2pk) - builder.calc_fee(len(p2pk))),
            generate_secret,
        )
    )
    code, body = mint.try_swap([p.to_dict() for p in p2pk], out)
    text = str(body).lower()
    ok = expect_reject(code, body) and any(
        s in text for s in ("signature", "witness", "threshold", "spend condition")
    )
    return ScenarioResult(
        "errid_p2pk_wrong_witness_reasoned_rejection", CATEGORY,
        Result.PASS if ok else Result.FAIL,
        f"got {code}: {fmt_body(body, 140)}",
    )
