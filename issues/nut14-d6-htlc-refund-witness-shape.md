# d6 — HTLC refund via SIG_INPUTS signatures-only witness: cdk rejects the documented Sender Pathway

**Status:** INTERNAL RESEARCH (overview build, 2026-09-09). Nothing filed.
**Upstream novelty:** PARTIAL — the divergence is known (cdk#2252 item 6,
the flagship "vice versa" bricking). Our additions: (a) the rejecting
error is actively misleading; (b) the wallet-emission vector makes it a
live bricking path today; (c) the spec text favors nutshell. Strongest
cdk-side filing candidate.

## What we found (measured 2026-09-09)

HTLC secret, expired locktime, 1-of-1 refund keys, SIG_INPUTS; witness =
`{"signatures":[<valid refund sig over sha256(secret)>]}` — **no preimage
field**. Nutshell 0.20.3: ACCEPT (refund path verifies; preimage optional).
cdk-mintd/0.18.0: REJECT — the JSON shape deserializes as `P2PKWitness`,
`verify_htlc` demands an `HTLCWitness`, and the mint returns **code 50000
"Secret is not a HTLC secret"** — which names the wrong object: the secret
IS HTLC; the *witness envelope* is the "wrong" shape.

NUT-14 Sender Pathway: "The sender(s) listed in the `refund` tag can spend
the proof once the `locktime` … has 'expired' **by providing
signature(s)** as per the NUT-11 rules for Refund MultiSig." Preimage is
the *Receiver* pathway's credential; nothing in the spec says the sender
must ship an empty `preimage` field to please the envelope parser.

## How we tested

- Probe cell `d6_htlc_refund_sigs_only_witness` (`build_htlc_secret` with
  expired locktime + refund keys; signatures-only witness per proof).
- Same arms/lifecycle/evidence as d1; stable ×2.
- Cross-check: `reference-reports/cdk.json` measured this cell ACCEPT on an
  older cdk — the rejection arrived with a cdk upgrade (softfork-by-upgrade,
  POSITION doc's corollary, live).

## Community discussion (summary)

- cdk#2252 item 6 records it (with the note that cdk accepts in SIG_ALL
  mode — the inconsistency is internal to cdk).
- nutshell#1126 (2026-08-19) shows `WitnessForP2pkOrHtlc.from_p2pk_witness`
  folding absent-vs-malformed witnesses into one error on the nutshell
  side — same envelope-vs-intent confusion family, opposite direction.
- No thread adjudicates HTLCWitness.preimage optionality (census checked);
  the spec's witness-format section shows the field but never marks it
  required or optional.

## Historic context

- 2023: NUT-14 written; witness shape unspecified beyond the JSON sketch.
- 2026-07-23: cdk#2252 item 6.
- 2026-09-09: measured REJECT(cdk)/ACCEPT(nutshell), error text captured.

## Links (internal reference; no upstream engagement)

- cashubtc/cdk#2252 (item 6) — tracked, reference-only
- cashubtc/nutshell#1126 + PR #1130 — witness-shape error handling
- cashubtc/nuts 14.md — Sender Pathway + witness format sections
- Census: `research/CENSUS-nut10-11-14-correct-behaviour.md`

## Follow-up measurement (2026-09-09, same arms): the incompatibility is total

Extended the probe with two witness-shape variants (frozen predictions,
both refuted in informative directions — `ab-d6-witness-frontier` results):

| witness shape | cdk 0.18.0 | nutshell 0.20.3 |
|---|---|---|
| preimage absent (d6) | REJECT 50000 | ACCEPT |
| `"preimage": null` (d6b) | REJECT 50000 | ACCEPT |
| `"preimage": "00"×32` — present, wrong (d6c) | **ACCEPT** | **REJECT 11000 "HTLC preimage does not match."** |

cdk routes on *presence of a non-null preimage* and never verifies its
value on the refund path; nutshell treats it as optional but verifies it
whenever present. The accepted sets intersect only at the **true
preimage**, which the refund sender never holds. Consequences:

1. **No wallet emission shape spends an HTLC refund on both mints.** The
   earlier "one-line emission change" idea is dead: cashu-cf's current
   sigs-only shape bricks at cdk; a dummy-preimage shape bricks at
   nutshell. Mint-specific emission is not a strategy. Only the cdk fix or
   a spec ruling restores the Sender Pathway cross-implementation.
2. cdk accepting a *wrong* preimage on the refund path is spec-defensible
   (Sender Pathway needs no preimage) — arguably the most faithful of the
   three behaviors.
3. nutshell's reject-wrong-preimage is a stricter-than-spec guard
   ("if present, must be valid") — reasonable, but it is the half that
   makes the intersection empty.
4. For channels (nuts#296): the refund path is the failure-mode recovery;
   an incompatible refund pathway means channel failure recovery is
   mint-dependent. Blocks channel work until resolved.

**Upstream novelty upgraded:** the empty-intersection fact and the
routing mechanism are ours and untracked anywhere. This is now the lead
candidate for the cdk#2252 comment / cdk issue.

## Wallet-emission + regression-window evidence (added 2026-09-09, second pass)

- **cashu-ts (v4 bundled lib) omits the preimage field when absent**
  (`preimage !== void 0 ? { preimage } : {}` — installed `cashu-ts.es.js`);
  cashu-cf emits signatures-only. **The default emission of both major TS
  wallets is the shape cdk rejects.** This is not an edge case — it is the
  natural wallet behavior everywhere.
- **Regression window pinned**: SatsAndSports' checker measured cdk 0.16.0
  at 58/58 *including* the sigs-only refund succeeding (2026-05-18); our
  0.18.0 run rejects. The flip landed between 0.16.0 and 0.18.0; the error
  string predates it (2024-04, commit `db14c117`). A silent softfork inside
  two minor releases, missed by every suite that counts any-reject as pass
  — the checker itself "passed" `htlc_signature_only_fails` on cdk for the
  WRONG reason (the envelope error, not a preimage error).
- Channels context: nuts#296 (Spilman) uses locktime refunds as failure-mode
  recovery and its PoC ships its own test mint — see
  `research/CHANNELS-nuts296-p2bk.md`.

## Release-preview update (2026-09-09, MEASURED): the incompatibility heals at the next release

The `ab-matrix:nutshell-main` git arm (upstream main + 42 unreleased
commits, run `version-matrix-20260909-224356`) flips **d6c → ACCEPT**:
main's refund path no longer verifies a present preimage. Updated
intersection:

| witness shape | cdk 0.18.0 | nutshell image 0.20.3 | nutshell main (next) |
|---|---|---|---|
| preimage absent (d6) | REJECT | ACCEPT | ACCEPT |
| preimage null (d6b) | REJECT | ACCEPT | ACCEPT |
| preimage dummy (d6c) | ACCEPT | REJECT | **ACCEPT** |

**Post-release, `{"preimage": <any 64-hex>, "signatures": [...]}` spends
refunds on BOTH cdk and nutshell-next.** The empty-intersection finding is
specific to the current image pair. Revised consequences:

1. Wallet guidance becomes release-dependent: the natural emission (absent
   preimage — cashu-ts/cashu-cf today) works at the current image but
   bricks at cdk; the dummy-preimage shape works at cdk and nutshell-next
   but bricks at the current image. No static emission covers all three
   live behaviors; post-release, dummy-preimage is universal.
2. The cdk-side fix (accept signatures-only as HTLCWitness, or at minimum
   stop returning the misleading 50000) is still correct and still wanted
   — wallets' default emission bricks at cdk TODAY — but the
   "total incompatibility" is temporary if nutshell ships main as-is.
3. Upstream filing angle: lead with the measured cdk behavior + the
   release-preview table; nutshell's change is already merged and
   documented in cdk#2252's table (which, we can now say, was right about
   main all along — zero frozen-prediction mismatches on the main arm).

## Direction (our read)

Two-part fix, both cheap: (1) cdk treats a signatures-only witness on an
HTLC secret as an HTLCWitness with absent preimage (matching its own
SIG_ALL behavior) — or minimally fixes the error to name the witness and
use a witness-kind code; (2) nuts marks `HTLCWitness.preimage` optional,
deciding this for every future implementation. Wallet angle (open):
cashu-cf emits signatures-only refunds today → **bricked at cdk mints**;
verify cashu-ts's emission shape before any channel work.
