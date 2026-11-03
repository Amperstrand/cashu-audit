#!/usr/bin/env python3
"""Error-identity probe battery (audit #68 item A).

One mint URL in, one JSON capture out: for each probe class, the HTTP
status, the error `code` (if any), the envelope keys, and a truncated
detail. Identity is captured FIRST and stamped into every capture
(#40 rule: never trust a response without checking identity).

Usage:
    python3 error_identity_probe.py http://127.0.0.1:4460 gonuts
    python3 error_identity_probe.py https://testnut.cashu.exchange cashucf-testnut

FROZEN PREDICTIONS (written 2026-11-04, BEFORE the first wire run —
static analysis of gonuts v0.16.0 cashu/cashu.go, cdk 0.18.1
cdk-common/src/error.rs, nutshell 0.21.0 core/errors.py, cashu-cf
src/utils/error-handling.ts + src/core/errors.ts):

  P01 swap unknown keyset        → gonuts 12001 | cdk 12001 | nutshell 12001 | cf 12001-or-generic
  P02 swap duplicate inputs      → gonuts 11007 | cdk 11007 | nutshell 11007 | cf 14008 (ISSUE-126)
  P03 swap duplicate outputs     → gonuts 11008 | cdk 11008 | nutshell 11008 | cf ?
  P04 swap underfunded           → gonuts 11002 (InsufficientProofsAmount) | cdk 11005 | nutshell 11005 | cf 11001@402 (INSUFFICIENT_FEES)
  P05 swap spent proofs          → gonuts 11001 | cdk 11001 | nutshell 11001 | cf 30001
  P06 swap outputs-already-signed→ gonuts 10002 | cdk 11003 | nutshell 11003 | cf 200-idempotent (S9a)
  P07 swap forged C              → gonuts 10003 | cdk 10001 | nutshell 10001 | cf 14005 (S1/S2 lock)
  P08 swap non-hex C             → shape error; envelope class observed
  P09 mint quote unit "usd"      → gonuts 11005 | cdk 11013 | nutshell 11013 | cf 11005
  P10 mint quote amount 0        → gonuts 20010 | cdk 50000-or-shape | nutshell shape/500 | cf 11006
  P11 mint with bogus quote id   → gonuts 20009 (QuoteNotExist) | cdk 50000 (UnknownQuote) | nutshell 500-ish | cf 404/14005-ish
  P12 P2PK wrong witness         → gonuts 10003 | cdk 20008 | nutshell 10001-or-11000 | cf 30006@403
  P13 HTLC wrong preimage        → same class as P12 per mint (reason identity covered by nut12_htlc)
  P14 melt quote non-BOLT11      → shape error; envelope class observed
"""
from __future__ import annotations

import json
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from conformance.builder import (
    ProofBuilder,
    build_htlc_secret,
    build_p2pk_secret,
    generate_htlc_preimage,
)
from conformance.client import MintClient
from conformance.crypto import KeyPair, generate_secret


def _body_code(body) -> int | None:
    if isinstance(body, dict):
        c = body.get("code")
        return c if isinstance(c, int) else None
    return None


def _envelope_keys(body) -> list[str]:
    if isinstance(body, dict):
        return sorted(body.keys())
    return ["<non-dict>"]


def _record(results: dict, probe: str, status: int, body) -> None:
    results[probe] = {
        "http": status,
        "code": _body_code(body),
        "envelope": _envelope_keys(body),
        "detail": (body.get("detail") or body.get("error") or str(body))[:160]
        if isinstance(body, dict) else str(body)[:160],
    }


def run(url: str, label: str) -> dict:
    mint = MintClient(url)
    info = mint.get_mint_info()
    capture = {
        "label": label,
        "url": url,
        "identity": {"name": info.get("name"), "version": info.get("version")},
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "probes": {},
    }
    results = capture["probes"]
    builder = ProofBuilder(mint)
    keyset_id, _ = builder.get_active_keyset()

    # ---- P01: swap with unknown keyset in outputs (balanced inputs so the
    # keyset identity — not a balance error — fires)
    proofs_k = builder.mint_proofs(4)
    out = builder.outputs_to_api(builder.create_outputs(4 - builder.calc_fee(1), generate_secret))
    for o in out:
        o["id"] = "00" * 8
    code, body = mint.try_swap([p.to_dict() for p in proofs_k], out)
    _record(results, "P01_swap_unknown_keyset", code, body)

    # ---- funded proofs for the spend-state probes
    proofs_a = builder.mint_proofs(8)          # for P02 dup-inputs
    proofs_b = builder.mint_proofs(8)          # for P04 underfunded
    proofs_c = builder.mint_proofs(8)          # spent in a good swap → P05/P06

    # ---- P02: duplicate inputs (same real proof twice)
    fresh_out = builder.outputs_to_api(builder.create_outputs(4, generate_secret))
    dup_inputs = [proofs_a[0].to_dict()] * 2
    code, body = mint.try_swap(dup_inputs, fresh_out)
    _record(results, "P02_swap_duplicate_inputs", code, body)

    # ---- P04: underfunded swap (inputs 8 total, outputs demand 16)
    big_out = builder.outputs_to_api(builder.create_outputs(16, generate_secret))
    code, body = mint.try_swap([p.to_dict() for p in proofs_b], big_out)
    _record(results, "P04_swap_underfunded", code, body)

    # ---- successful swap of proofs_c (its outputs feed P06)
    c_out = builder.create_outputs(8 - builder.calc_fee(len(proofs_c)), generate_secret)
    c_api_out = builder.outputs_to_api(c_out)
    code, body = mint.try_swap([p.to_dict() for p in proofs_c], c_api_out)
    _record(results, "P00_swap_control_ok", code, body)

    # ---- P05: spend already-spent proofs again (balanced outputs so the
    # only failing condition is the spent state)
    re_out = builder.outputs_to_api(
        builder.create_outputs(8 - builder.calc_fee(len(proofs_c)), generate_secret)
    )
    code, body = mint.try_swap([p.to_dict() for p in proofs_c], re_out)
    _record(results, "P05_swap_spent_proofs", code, body)

    # ---- P06: replay the exact outputs of the successful swap
    # (fresh inputs so P02/P05 state changes can't mask the identity)
    proofs_d = builder.mint_proofs(8)
    code, body = mint.try_swap([p.to_dict() for p in proofs_d], c_api_out)
    _record(results, "P06_swap_outputs_already_signed", code, body)

    # ---- P07: forged C (real keyset, random point)
    forged = {
        "amount": 4,
        "secret": generate_secret(),
        "C": "02" + secrets.token_hex(32),
        "id": keyset_id,
    }
    code, body = mint.try_swap([forged], fresh_out)
    _record(results, "P07_swap_forged_C", code, body)

    # ---- P08: non-hex C
    badhex = {
        "amount": 4,
        "secret": generate_secret(),
        "C": "not-hex-at-all",
        "id": keyset_id,
    }
    code, body = mint.try_swap([badhex], fresh_out)
    _record(results, "P08_swap_nonhex_C", code, body)

    # ---- P09: mint quote with unsupported unit
    code, body = mint._post("/v1/mint/quote/bolt11", {"amount": 64, "unit": "usd"})
    _record(results, "P09_mint_quote_unit_unsupported", code, body)

    # ---- P10: mint quote with zero amount
    code, body = mint._post("/v1/mint/quote/bolt11", {"amount": 0, "unit": "sat"})
    _record(results, "P10_mint_quote_zero_amount", code, body)

    # ---- P11: mint tokens with bogus quote id
    code, body = mint._post(
        "/v1/mint/bolt11",
        {"quote": "deadbeef" * 8, "outputs": fresh_out},
    )
    _record(results, "P11_mint_bogus_quote", code, body)

    # ---- P12: P2PK proof spent with wrong witness
    p2pk_key = KeyPair.generate()
    wrong_key = KeyPair.generate()
    funded = builder.mint_proofs(8)
    swap_total = 8 - builder.calc_fee(len(funded))
    p2pk = builder.swap_to_p2pk(
        funded, lambda: build_p2pk_secret(p2pk_key.pub_hex), max(1, swap_total)
    )
    import hashlib

    for p in p2pk:
        msg = hashlib.sha256(p.secret.encode()).digest()
        p.witness = json.dumps({"signatures": [wrong_key.sign_schnorr(msg)]})
    out2 = builder.outputs_to_api(
        builder.create_outputs(max(1, sum(q.amount for q in p2pk) - builder.calc_fee(len(p2pk))), generate_secret)
    )
    code, body = mint.try_swap([p.to_dict() for p in p2pk], out2)
    _record(results, "P12_p2pk_wrong_witness", code, body)

    # ---- P13: HTLC wrong preimage (SIG_INPUTS, hash-lock only)
    _pi, hash_hex = generate_htlc_preimage()
    funded = builder.mint_proofs(8)
    swap_total = 8 - builder.calc_fee(len(funded))
    htlc = builder.swap_to_p2pk(
        funded, lambda: build_htlc_secret(hash_hex), max(1, swap_total)
    )
    wrong_preimage = secrets.token_hex(32)
    for p in htlc:
        p.witness = json.dumps({"preimage": wrong_preimage})
    out3 = builder.outputs_to_api(
        builder.create_outputs(max(1, sum(q.amount for q in htlc) - builder.calc_fee(len(htlc))), generate_secret)
    )
    code, body = mint.try_swap([p.to_dict() for p in htlc], out3)
    _record(results, "P13_htlc_wrong_preimage", code, body)

    # ---- P15: NUT-19 exact replay — same inputs AND outputs as P00's
    # successful swap. Distinct from P06 (fresh inputs, replayed outputs):
    # a cached-endpoint mint may return the identical 200 (cf S9a), while
    # a non-caching mint reports the spent inputs / signed outputs.
    code, body = mint.try_swap([p.to_dict() for p in proofs_c], c_api_out)
    _record(results, "P15_swap_exact_replay", code, body)

    # ---- P14: melt quote with a non-BOLT11 request
    code, body = mint._post("/v1/melt/quote/bolt11", {"request": "hello", "unit": "sat"})
    _record(results, "P14_melt_quote_nonbolt11", code, body)

    return capture


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    url, label = sys.argv[1], sys.argv[2]
    capture = run(url, label)
    outdir = Path(__file__).parent / "results" / "error-identity"
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{label}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(capture, indent=2))
    print(json.dumps(capture, indent=2))
    print(f"\ncapture → {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
