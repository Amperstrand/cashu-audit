#!/usr/bin/env python3
"""Frozen-hypothesis A/B probe: cdk#2252 NUT-10/11/14 spending-condition divergences.

8 divergences x 2 arms (cdk-mintd, nutshell). Each cell mints proofs with the
divergence-triggering secret (blind signing — the mint cannot see the secret at
construction), then attempts the spend that discriminates the two readings.

FROZEN PREDICTIONS (cdk#2252 table, verbatim; written before any run):
  cell   input class                                            cdk      nutshell(#1008)
  ctrl   canonical P2PK 1-of-1 SIG_INPUTS, valid sig            ACCEPT   ACCEPT
  ctrl   canonical HTLC lowercase hash + preimage               ACCEPT   ACCEPT
  d1     unknown kind ["MBS",{...}] secret, NO witness          ACCEPT   REJECT
         (cdk: parse-fail -> anyone-can-spend; nutshell: fail-closed)
  d2     duplicate n_sigs tags (first=1, dup=2), 1 valid sig    ACCEPT   REJECT
         (cdk: first-wins; nutshell: malformed)
  d3     n_sigs=3 > 2-key pool, expired locktime, refund sig    ACCEPT   REJECT
         (cdk: refund escape hatch; nutshell: bricked up front)
  d4     empty ["pubkeys"] multi-value tag, data-key sig        ACCEPT   REJECT
         (cdk: parses to empty list; nutshell: >=1 value required)
  d5     HTLC UPPERCASE hash + correct preimage                 ACCEPT   REJECT
         (cdk: from_str any-case; nutshell: lowercase-only per NUT-14)
  d6     HTLC refund, SIG_INPUTS signatures-ONLY witness        REJECT   ACCEPT
         (cdk: witness deserializes as P2PKWitness -> IncorrectWitnessKind;
          nutshell: HTLCWitness.preimage optional -> refund verifies)
  d7     duplicate signature from same key in one witness       REJECT   ACCEPT
         (cdk: DuplicateSignature error; nutshell: extra sig ignored)
  d8     witness on plain (non-NUT-10) secret                   REJECT   ACCEPT
         (cdk: IncorrectWitnessKind; nutshell: accepted and ignored)

VERSION CAVEAT (read before calling any mismatch a refutation):
  - The nutshell column describes PR #1008 (the strict/spec-literal branch the
    issue reviews). If the running image predates #1008, d2 is expected to flip
    to ACCEPT (CROSS-IMPLEMENTATION-GUIDE 6.4 measured first-wins), and d1/d4/
    d5/d7/d8 may also differ. Record /v1/info version with the results.
  - reference-reports/cdk.json (older cdk) measured d6=ACCEPT — the issue
    claims current cdk rejects. d6 is the live question for the cdk arm.
  Mismatch = version drift or probe bug until proven otherwise (house rule).

MEASURED 2026-09-09 (post-hoc annotation; frozen predictions above untouched):
  cdk-mintd/0.18.0: 10/10 cells match the cdk column (d6 detail: code 50000
    "Secret is not a HTLC secret" — the IncorrectWitnessKind path).
  Nutshell/0.20.3: only d1 and d6 match the issue's nutshell column; d2/d3/d4/
    d5 flipped to ACCEPT (lenient, cdk-like) and d7/d8 flipped to REJECT
    (code 11000 "signatures must be unique." / "witness data not allowed
    without a spending condition."). All cells stable across 2 runs.
  NET: of the 8 documented divergences, only #1 (unknown kind) and #6 (HTLC
  refund via SIG_INPUTS sigs-only witness) remain between these releases;
  the other six have converged. The cdk#2252 table is stale w.r.t. 0.20.3 —
  divergence report should be written from the measured matrix.
  Results: conformance/reports/ab-p2pk-htlc-2026-09-09.json

MEASURED 2026-09-09, follow-up (d6 witness-shape frontier; predictions for
d6b/d6c were frozen before each run and left in PRED unmodified):
  d6  preimage ABSENT : cdk REJECT(50000) | nutshell ACCEPT
  d6b preimage null   : cdk REJECT(50000) | nutshell ACCEPT   [d6b cdk prediction REFUTED]
  d6c preimage "00"*32 (wrong): cdk ACCEPT | nutshell REJECT(11000
      "HTLC preimage does not match.")                        [d6c nutshell prediction REFUTED]
  Conclusion: cdk routes by presence-of-non-null-preimage and never verifies
  the value on the refund path; nutshell treats preimage as optional but
  verifies it whenever present. Accepted-shape sets intersect ONLY at the
  true preimage — which the refund sender never has. NO witness shape
  spends an HTLC refund on both mints: the NUT-14 Sender Pathway is
  cross-implementation incompatible. Follow-up results:
  conformance/reports/ab-d6-witness-frontier-2026-09-09.json

MEASURED 2026-09-09, follow-up 2 (d1b lock-voiding; prediction frozen,
cdk entry REFUTED in the safe direction):
  d1b P2PK kind with garbage `data` ("0"*60), no witness:
    cdk 0.18.0      REJECT (400, 20008 "P2PK spend conditions are not met")
    nutshell 0.20.3 REJECT (400, code 0 "Witness is missing for p2pk signature")
  cdk#2252's claim that "malformed pubkeys in data" fall to the
  anyone-can-spend fallback is STALE for current cdk — the malformed-lock
  theft vector does not exist on 0.18.0. d1's residual exposure is
  unknown-kind secrets only (future kinds, e.g. channels). Note the
  nutshell-image rejection is also for the "wrong" reason (missing witness,
  not malformed secret — the published 0.20.3 image predates the #1008
  validators; nutshell-main rejects as malformed). Run:
  conformance/runs/version-matrix-20260909-220059.json

Environment (per conformance/CROSS-IMPLEMENTATION-GUIDE.md sections 3-4):
  docker run -d -p 3338:3338 --name nutshell -e MINT_LIGHTNING_BACKEND=FakeWallet \
    -e MINT_PRIVATE_KEY=<fresh hex> -e MINT_HOST=0.0.0.0 -e MINT_PORT=3338 cashubtc/nutshell:latest
  docker run -d -p 3339:3338 --name cdk-mintd -e CDK_MINTD_BACKEND=FakeWallet \
    -e CDK_MINTD_MINT_INFO_NAME="CDK Test Mint" -e CDK_MINTD_SEED=<fresh hex> \
    -e CDK_MINTD_HOST=0.0.0.0 -e CDK_MINTD_PORT=3338 cashubtc/mintd:0.18.0
(ghcr.io/cashubtc/cdk-mintd is registry-denied; Docker Hub cashubtc/mintd is
 the working published image — 0.18.0 pinned, postdates the cdk#2252 filing.)
Fresh keys per arm (same key = same keyset = camouflage hazard). Run >= twice
for flake detection: --repeat 2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conformance.builder import (  # noqa: E402
    Proof,
    ProofBuilder,
    build_htlc_secret,
    build_p2pk_secret,
    generate_htlc_preimage,
)
from conformance.client import MintClient  # noqa: E402
from conformance.crypto import KeyPair, generate_secret  # noqa: E402

PRED = {
    "cdk": {
        "ctrl_p2pk_canonical": "ACCEPT",
        "ctrl_htlc_canonical": "ACCEPT",
        "d1_unknown_kind_no_witness": "ACCEPT",
        "d1b_malformed_pubkey_lock_voiding": "ACCEPT",  # REFUTED 2026-09-09: cdk 0.18.0 REJECT (20008) — see MEASURED
        "d2_duplicate_tags_first_wins": "ACCEPT",
        "d3_nsigs_exceeds_pubkeys_refund": "ACCEPT",
        "d4_empty_pubkeys_tag": "ACCEPT",
        "d5_htlc_uppercase_hash": "ACCEPT",
    "d6_htlc_refund_sigs_only_witness": "REJECT",
    "d6b_htlc_refund_preimage_null": "ACCEPT",  # REFUTED 2026-09-09: cdk REJECT (see MEASURED)
    "d6c_htlc_refund_dummy_preimage": "ACCEPT",
    "d7_duplicate_signature": "REJECT",
    "d8_witness_on_plain_secret": "REJECT",
    },
    "nutshell": {
        "ctrl_p2pk_canonical": "ACCEPT",
        "ctrl_htlc_canonical": "ACCEPT",
        "d1_unknown_kind_no_witness": "REJECT",
        "d1b_malformed_pubkey_lock_voiding": "REJECT",
        "d2_duplicate_tags_first_wins": "REJECT",
        "d3_nsigs_exceeds_pubkeys_refund": "REJECT",
        "d4_empty_pubkeys_tag": "REJECT",
        "d5_htlc_uppercase_hash": "REJECT",
        "d6_htlc_refund_sigs_only_witness": "ACCEPT",
        "d6b_htlc_refund_preimage_null": "ACCEPT",
        "d6c_htlc_refund_dummy_preimage": "ACCEPT",
        "d7_duplicate_signature": "ACCEPT",
        "d8_witness_on_plain_secret": "ACCEPT",
    },
}


# ---------------------------------------------------------------------------
# Raw NUT-10 secret construction (bypasses house builders for MALFORMED shapes
# the builders intentionally cannot express — string assembly only, no crypto).
# ---------------------------------------------------------------------------

def raw_nut10_secret(kind: str, data: str, tags: list[list[str]]) -> str:
    obj = [kind, {"nonce": generate_secret(), "data": data, "tags": tags}]
    return json.dumps(obj, separators=(",", ":"))


def sig_over_secret(key: KeyPair, secret: str) -> str:
    return key.sign_schnorr(hashlib.sha256(secret.encode("utf-8")).digest())


# ---------------------------------------------------------------------------
# Lifecycle helpers (house patterns: fee-aware, powers-of-2, fresh secrets)
# ---------------------------------------------------------------------------

def mint_target(builder: ProofBuilder, secret_fn, amount: int) -> list[Proof]:
    """Mint regular proofs, then swap for target-secret proofs (blind signing)."""
    regular = builder.mint_proofs(amount)
    total = sum(p.amount for p in regular)
    swap_amount = total - builder.calc_fee(len(regular))
    if swap_amount < 1:
        raise RuntimeError(f"amount too small: {total} - fee = {swap_amount}")
    # Retry on rate limit: a 429'd swap is not processed, so the regular
    # proofs are still unspent and the swap can be safely re-attempted
    # (fresh blinded outputs each attempt).
    for attempt in range(RATE_RETRY):
        try:
            return builder.swap_to_p2pk(regular, secret_fn, swap_amount)
        except RuntimeError as e:
            if "429" not in str(e) or attempt == RATE_RETRY - 1:
                raise
            print(f"    rate-limited, backing off {RATE_BACKOFF}s ...", flush=True)
            time.sleep(RATE_BACKOFF)


def try_spend(mint: MintClient, builder: ProofBuilder, proofs: list[Proof]) -> dict:
    """Swap the target proofs away to fresh plain-secret outputs; record verdict."""
    total = sum(p.amount for p in proofs)
    swap_total = max(1, total - builder.calc_fee(len(proofs)))
    outputs = builder.outputs_to_api(
        builder.create_outputs(swap_total, generate_secret)
    )
    code, body = mint.try_swap([p.to_dict() for p in proofs], outputs)
    # A 429 is not a verdict: the request was not processed. Retry in place.
    for attempt in range(RATE_RETRY):
        if code != 429:
            break
        print(f"    rate-limited, backing off {RATE_BACKOFF}s ...", flush=True)
        time.sleep(RATE_BACKOFF)
        code, body = mint.try_swap([p.to_dict() for p in proofs], outputs)
    return {
        "verdict": "ACCEPT" if code == 200 else "REJECT",
        "code": code,
        "detail": str(body)[:200],
    }


def set_witness(proofs: list[Proof], witness_fn) -> None:
    for p in proofs:
        p.witness = json.dumps(witness_fn(p))


# ---------------------------------------------------------------------------
# The 8 divergence cells + 2 controls. Each returns the spend verdict.
# ---------------------------------------------------------------------------

def cell_ctrl_p2pk(mint: MintClient, builder: ProofBuilder) -> dict:
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex)  # SIG_INPUTS 1-of-1
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(proofs, lambda p: {"signatures": [sig_over_secret(key, p.secret)]})
    return try_spend(mint, builder, proofs)


def cell_ctrl_htlc(mint: MintClient, builder: ProofBuilder) -> dict:
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(hash_hex)  # lowercase hash
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(proofs, lambda p: {"preimage": preimage_hex})
    return try_spend(mint, builder, proofs)


def cell_d1_unknown_kind(mint: MintClient, builder: ProofBuilder) -> dict:
    # ["MBS", {...}] — NUT-10-shaped, unknown kind. Spend with NO witness:
    # cdk falls back to anyone-can-spend only when no witness is attached.
    key = KeyPair.generate()
    secret_fn = lambda: raw_nut10_secret("MBS", key.pub_hex, [["sigflag", "SIG_INPUTS"]])
    proofs = mint_target(builder, secret_fn, AMOUNT)
    for p in proofs:
        p.witness = None  # explicit: cdk leniency requires witness absent
    return try_spend(mint, builder, proofs)


def cell_d1b_malformed_pubkey(mint: MintClient, builder: ProofBuilder) -> dict:
    # KNOWN kind (P2PK) with garbage in `data` — the live lock-voiding cell.
    # cdk#2252 lists "malformed pubkeys in data" under the parse-fail
    # fallback: at a lenient mint this is "P2PK-locked" money that is
    # possession-spendable (recipient-fraud vector). FROZEN PREDICTION:
    # cdk ACCEPT (fallback), nutshell REJECT (fail-closed validation).
    secret_fn = lambda: raw_nut10_secret("P2PK", "0" * 60, [["sigflag", "SIG_INPUTS"]])
    proofs = mint_target(builder, secret_fn, AMOUNT)
    for p in proofs:
        p.witness = None
    return try_spend(mint, builder, proofs)


def cell_d2_duplicate_tags(mint: MintClient, builder: ProofBuilder) -> dict:
    # Two n_sigs tags: first=1 (satisfiable with 1 sig), duplicate=2.
    # cdk first-wins -> the provided sig satisfies; nutshell -> malformed.
    key = KeyPair.generate()
    tags = [["sigflag", "SIG_INPUTS"], ["n_sigs", "1"], ["n_sigs", "2"]]
    secret_fn = lambda: raw_nut10_secret("P2PK", key.pub_hex, tags)
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(proofs, lambda p: {"signatures": [sig_over_secret(key, p.secret)]})
    return try_spend(mint, builder, proofs)


def cell_d3_nsigs_exceeds(mint: MintClient, builder: ProofBuilder) -> dict:
    # Pool = data + 1 pubkeys tag = 2 keys, n_sigs = 3 (unsatisfiable primary),
    # expired locktime + 1-of-1 refund. Spend via refund after expiry:
    # cdk keeps the refund hatch; nutshell bricks the proof up front.
    main = KeyPair.generate()
    extra = KeyPair.generate()
    refund_key = KeyPair.generate()
    past = int(time.time()) - 10
    tags = [
        ["sigflag", "SIG_INPUTS"],
        ["pubkeys", extra.pub_hex],
        ["n_sigs", "3"],
        ["locktime", str(past)],
        ["refund", refund_key.pub_hex],
        ["n_sigs_refund", "1"],
    ]
    secret_fn = lambda: raw_nut10_secret("P2PK", main.pub_hex, tags)
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(proofs, lambda p: {"signatures": [sig_over_secret(refund_key, p.secret)]})
    return try_spend(mint, builder, proofs)


def cell_d4_empty_pubkeys_tag(mint: MintClient, builder: ProofBuilder) -> dict:
    # ["pubkeys"] with zero values. cdk: empty list -> 1-of-1 via data.
    # nutshell: multi-value tags must have >= 1 value.
    key = KeyPair.generate()
    tags = [["sigflag", "SIG_INPUTS"], ["pubkeys"], ["n_sigs", "1"]]
    secret_fn = lambda: raw_nut10_secret("P2PK", key.pub_hex, tags)
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(proofs, lambda p: {"signatures": [sig_over_secret(key, p.secret)]})
    return try_spend(mint, builder, proofs)


def cell_d5_htlc_uppercase(mint: MintClient, builder: ProofBuilder) -> dict:
    # NUT-14 hash in UPPERCASE hex, correct preimage supplied.
    preimage_hex, hash_hex = generate_htlc_preimage()
    secret_fn = lambda: build_htlc_secret(hash_hex.upper())
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(proofs, lambda p: {"preimage": preimage_hex})
    return try_spend(mint, builder, proofs)


def cell_d6_htlc_refund_sigs_only(mint: MintClient, builder: ProofBuilder) -> dict:
    # HTLC, expired locktime, refund key. Witness carries ONLY signatures —
    # no "preimage" key — so cdk deserializes it as P2PKWitness and (per the
    # issue) verify_htlc rejects with IncorrectWitnessKind; nutshell's
    # HTLCWitness has optional preimage and verifies the refund path.
    refund_key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    past = int(time.time()) - 10
    secret_fn = lambda: build_htlc_secret(
        hash_hex, locktime=past, refund_keys=[refund_key.pub_hex], n_sigs_refund=1
    )
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(proofs, lambda p: {"signatures": [sig_over_secret(refund_key, p.secret)]})
    return try_spend(mint, builder, proofs)


def cell_d6b_htlc_refund_preimage_null(mint: MintClient, builder: ProofBuilder) -> dict:
    # d6 with an explicit "preimage": null alongside the refund signatures.
    # FROZEN PREDICTION (both arms): ACCEPT — hypothesis that cdk's
    # HTLCWitness deserializes Option<str> null -> HTLC-shaped envelope ->
    # refund verifies. REFUTED on cdk 2026-09-09: identical 50000 "Secret is
    # not a HTLC secret" — JSON null routes to P2PKWitness like an absent
    # field. Prediction left frozen; the mismatch is the record.
    refund_key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    past = int(time.time()) - 10
    secret_fn = lambda: build_htlc_secret(
        hash_hex, locktime=past, refund_keys=[refund_key.pub_hex], n_sigs_refund=1
    )
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(
        proofs,
        lambda p: {"preimage": None, "signatures": [sig_over_secret(refund_key, p.secret)]},
    )
    return try_spend(mint, builder, proofs)


def cell_d6c_htlc_refund_dummy_preimage(mint: MintClient, builder: ProofBuilder) -> dict:
    # d6 with a present-but-DUMMY preimage ("00"*32 — wrong by construction).
    # FROZEN PREDICTION: cdk ACCEPT (routing hypothesis: a present non-null
    # preimage makes the witness deserialize as HTLCWitness, and the refund
    # pathway per NUT-14 verifies signatures only — so a wrong preimage
    # should neither be required nor checked); nutshell ACCEPT. If cdk
    # ACCEPTS, wallets can de-brick refunds by emitting any 64-hex dummy —
    # and cdk not verifying a present preimage on the refund path is itself
    # a finding. If cdk REJECTS, its SIG_INPUTS refund path effectively
    # requires the true preimage (Sender Pathway unusable at cdk).
    refund_key = KeyPair.generate()
    _preimage_hex, hash_hex = generate_htlc_preimage()
    past = int(time.time()) - 10
    secret_fn = lambda: build_htlc_secret(
        hash_hex, locktime=past, refund_keys=[refund_key.pub_hex], n_sigs_refund=1
    )
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(
        proofs,
        lambda p: {"preimage": "00" * 32,
                   "signatures": [sig_over_secret(refund_key, p.secret)]},
    )
    return try_spend(mint, builder, proofs)


def cell_d7_duplicate_signature(mint: MintClient, builder: ProofBuilder) -> dict:
    # Same valid signature twice from the one required key.
    key = KeyPair.generate()
    secret_fn = lambda: build_p2pk_secret(key.pub_hex)
    proofs = mint_target(builder, secret_fn, AMOUNT)
    set_witness(
        proofs,
        lambda p: (lambda sig: {"signatures": [sig, sig]})(sig_over_secret(key, p.secret)),
    )
    return try_spend(mint, builder, proofs)


def cell_d8_witness_on_plain(mint: MintClient, builder: ProofBuilder) -> dict:
    # Plain hex secret with a well-formed (but irrelevant) witness attached.
    stray = KeyPair.generate()
    proofs = mint_target(builder, generate_secret, AMOUNT)
    set_witness(proofs, lambda p: {"signatures": [sig_over_secret(stray, p.secret)]})
    return try_spend(mint, builder, proofs)


CELLS = [
    ("ctrl_p2pk_canonical", cell_ctrl_p2pk),
    ("ctrl_htlc_canonical", cell_ctrl_htlc),
    ("d1_unknown_kind_no_witness", cell_d1_unknown_kind),
    ("d1b_malformed_pubkey_lock_voiding", cell_d1b_malformed_pubkey),
    ("d2_duplicate_tags_first_wins", cell_d2_duplicate_tags),
    ("d3_nsigs_exceeds_pubkeys_refund", cell_d3_nsigs_exceeds),
    ("d4_empty_pubkeys_tag", cell_d4_empty_pubkeys_tag),
    ("d5_htlc_uppercase_hash", cell_d5_htlc_uppercase),
    ("d6_htlc_refund_sigs_only_witness", cell_d6_htlc_refund_sigs_only),
    ("d6b_htlc_refund_preimage_null", cell_d6b_htlc_refund_preimage_null),
    ("d6c_htlc_refund_dummy_preimage", cell_d6c_htlc_refund_dummy_preimage),
    ("d7_duplicate_signature", cell_d7_duplicate_signature),
    ("d8_witness_on_plain_secret", cell_d8_witness_on_plain),
]

AMOUNT = 8  # module-level default; set from argv in main()
RATE_RETRY = 6
RATE_BACKOFF = 20  # nutshell 0.20.x rate-limits bursts; fixed-window resets in ~1min


def main() -> int:
    global AMOUNT
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cdk", default="http://127.0.0.1:3339",
                        help="cdk-mintd base URL (default %(default)s)")
    parser.add_argument("--nutshell", default="http://127.0.0.1:3338",
                        help="nutshell base URL (default %(default)s)")
    parser.add_argument("--arm", action="append", metavar="NAME=URL", default=None,
                        help="repeatable extra/override arm, e.g. cdk-0.17.6=http://127.0.0.1:34101."
                             " Replaces the default cdk/nutshell pair when given."
                             " Predictions resolve by family: NAME or NAME's dash-prefix"
                             " must match a PRED key (cdk|nutshell); other arms run verdict-only.")
    parser.add_argument("--out", default="/tmp/ab-p2pk-htlc-results.json",
                        help="results JSON path (default %(default)s)")
    parser.add_argument("--amount", type=int, default=8, help="mint amount per cell")
    parser.add_argument("--cells", default="",
                        help="comma-separated cell names to run (default: all)")
    parser.add_argument("--repeat", type=int, default=1,
                        help="runs per cell (framework: >=2 for flake detection)")
    parser.add_argument("--pace", type=float, default=2.0,
                        help="seconds between cells (nutshell rate limiter)")
    args = parser.parse_args()
    AMOUNT = args.amount

    if args.arm:
        arms = {}
        for spec in args.arm:
            name, sep, url = spec.partition("=")
            if not sep or not name or not url:
                print(f"bad --arm spec {spec!r} (want NAME=URL)", file=sys.stderr)
                return 2
            arms[name] = url
    else:
        arms = {"cdk": args.cdk, "nutshell": args.nutshell}
    results: dict[str, dict] = {}

    for arm, url in arms.items():
        mint = MintClient(url)
        try:
            info = mint.get_mint_info()
        except Exception as e:
            print(f"{arm}: UNREACHABLE at {url} ({e}) — see docstring for setup", flush=True)
            return 2
        ident = info.get("version", "?")
        results[arm] = {"identity": ident, "url": url, "cells": {}}
        print(f"\n=== {arm} @ {url} (version {ident}) ===", flush=True)

        for name, fn in [c for c in CELLS if not args.cells
                         or c[0] in set(args.cells.split(","))]:
            runs = []
            for i in range(args.repeat):
                # Every exception path precedes the final spend, so a failed
                # cell never consumed its inputs — whole-cell retry is safe.
                for attempt in range(RATE_RETRY):
                    try:
                        runs.append(fn(mint, ProofBuilder(mint)))
                        break
                    except Exception as e:
                        if "429" not in str(e) or attempt == RATE_RETRY - 1:
                            runs.append({"verdict": "ERROR", "code": 0,
                                         "detail": f"{type(e).__name__}: {e}"})
                        else:
                            print(f"    rate-limited, backing off {RATE_BACKOFF}s ...",
                                  flush=True)
                            time.sleep(RATE_BACKOFF)
                if i < args.repeat - 1:
                    time.sleep(1)
            verdict = runs[-1]["verdict"]
            stable = all(r["verdict"] == verdict for r in runs)
            results[arm]["cells"][name] = {"runs": runs, "verdict": verdict,
                                           "stable": stable}
            note = "" if stable else " UNSTABLE"
            print(f"  {name}: {verdict} (http {runs[-1]['code']}){note}", flush=True)
            print(f"    {runs[-1]['detail'][:120]}", flush=True)
            time.sleep(args.pace)

    json.dump(results, open(args.out, "w"), indent=1)
    print(f"\nresults -> {args.out}")

    print("\nFROZEN PREDICTION CHECK (mismatch = version drift or probe bug"
          " until proven otherwise):")
    ok = True
    any_pred_checked = False
    for arm in results:
        family = arm if arm in PRED else arm.split("-", 1)[0]
        preds = PRED.get(family)
        if not preds:
            print(f"  {arm}: no frozen predictions for family {family!r}"
                  " — verdict-only arm")
            continue
        for cell, want in preds.items():
            if cell not in results[arm]["cells"]:
                continue
            any_pred_checked = True
            got = results[arm]["cells"][cell]["verdict"]
            match = got == want
            if not match:
                ok = False
            print(f"  {arm}/{cell}: predicted {want}, got {got}"
                  f" {'OK' if match else 'MISMATCH'}")
    ctrl_ok = all(
        results[a]["cells"][c]["verdict"] == "ACCEPT"
        for a in arms
        for c in ("ctrl_p2pk_canonical", "ctrl_htlc_canonical")
        if c in results[a]["cells"]
    )
    if not ctrl_ok:
        print("WARNING: a control failed — divergence cells on that arm are"
              " untrusted; fix the environment before analyzing.")
    print("HYPOTHESIS:", "CONFIRMED" if ok and ctrl_ok else
          "PARTIAL/REFUTED — analyze (version first, then probe)")
    return 0 if ok and ctrl_ok else 1


if __name__ == "__main__":
    sys.exit(main())
