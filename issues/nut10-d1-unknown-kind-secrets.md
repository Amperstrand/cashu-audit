# d1 — Unknown-kind NUT-10 secrets: anyone-can-spend vs fail-closed

**Status:** INTERNAL RESEARCH (overview build, 2026-09-09). Nothing filed.
**Upstream novelty:** KNOWN — tracked as cdk#2252 item 1. Reference-only; do
not re-file. Our additions: traced the nutshell strictness to a specific
commit, and established this is 1 of only 2 divergences still live between
current releases.

## What we found (measured 2026-09-09)

A proof whose secret is NUT-10-shaped but carries an unknown `kind`
(`["MBS", {nonce, data, tags}]`) spends **without witness at cdk** (parsed as
plain anyone-can-spend secret) and is **rejected at nutshell** (`'MBS' is not
a valid SecretKind`, HTTP 400). Operational consequence: a token fine at a
cdk mint is bricked at a nutshell mint — and any *future* kind (e.g. channel
locks building on nuts#296) is bricked at every strict mint until upgraded.

## How we tested

- Probe cell `d1_unknown_kind_no_witness` in `conformance/ab_probe_p2pk_htlc.py`
  (frozen predictions written before the run, from the cdk#2252 table).
- Arms: cdk-mintd/0.18.0 (Docker Hub `cashubtc/mintd:0.18.0`, FakeWallet,
  fresh mnemonic) and Nutshell/0.20.3 (`cashubtc/nutshell:latest`, FakeWallet,
  fresh key, rate limiter off). Identity via /v1/info, stable ×2 runs.
- Lifecycle per cell: mint regular proofs → blind-swap into the
  divergence-triggering secret (the mint cannot see it — verifier-only
  coupling) → attempt the discriminating spend.
- Evidence: `conformance/reports/ab-p2pk-htlc-2026-09-09.{json,log}`.

## Community discussion (summary)

- NUT-10 carries only a Caution: unsupported kinds "**may** be treated as
  regular anyone-can-spend tokens" — permissive by design; both readings legal.
- a1denvalu3's direction on nuts#358 (2026-04-17, "as per discussion"):
  mints lenient / wallets strict — favors cdk's reading as the community
  direction; nutshell's fail-closed is stricter than anyone asked.
- Nutshell's strictness entered via callebtc's 2026-07-18 commit
  "nut10.py validates secret" (+ "test: cover strict NUT-10 validation") on
  PR #1008 — i.e., added *after* cdk#2252 had reviewed the branch, which is
  why our July divergence-DB re-validation ("all lenient") flipped in Sept.

## Historic context

- 2023: NUT-10 introduces the well-known Secret format + the Caution.
- 2025-07-28 (our DB): all three impls anyone-can-spend on unknown kind.
- 2026-07-18: nutshell adds SecretKind validation on the #1008 branch.
- 2026-08-11: #1008 merges; Nutshell 0.20.3 ships fail-closed.
- 2026-09-09: our probe measures the divergence live.

## Links (internal reference; no upstream engagement)

- cashubtc/cdk#2252 (item 1) — the tracked comparison
- cashubtc/nutshell#1008 — commits `5afc861`, `d0afdf2` (strict validation)
- cashubtc/nuts 10.md — Caution paragraph
- nuts#296 (Spilman channels) — future-kind exposure
- Dev calls: cdk discussions category ends Oct 2025 (pre-dates this); the
  2026 decision discussion is embedded in the threads above. Current hub:
  cashudevkit.org. Census follow-up lives in
  `research/CENSUS-nut10-11-14-correct-behaviour.md`.

## Follow-up measurement (2026-09-09): the malformed-lock half is dead on current cdk

Cell `d1b_malformed_pubkey_lock_voiding` (P2PK kind, garbage `data`, no
witness — the recipient-fraud vector cdk#2252 described):

- **cdk-mintd/0.18.0: REJECT** (400, code 20008 "P2PK spend conditions are
  not met") — frozen prediction (ACCEPT, from the issue's claim) REFUTED,
  in the safe direction. The "malformed pubkeys in data → anyone-can-spend"
  fallback is **stale for current cdk**.
- nutshell-0.20.3: REJECT (code 0 "Witness is missing for p2pk signature")
  — as predicted, though for the "wrong" reason: the published image
  (pre-#1008) parses the malformed P2PK and demands a witness rather than
  rejecting the malformed secret; nutshell-main rejects it as malformed.

**Revised exposure:** d1's live surface is **unknown-kind secrets only**
(future kinds — channels/nuts#296 and any new NUT-28-style extensions).
The malformed-known-kind theft vector does not exist on either current
reference. Run: `conformance/runs/version-matrix-20260909-220059.json`.

## Direction (our read)

Leave cdk as-is (spec-permitted, community-direction-aligned); nutshell's
fail-closed should either gain an anyone-can-spend fallback for
non-witness spends of unknown kinds, or the spec should explicitly bless
fail-closed and wallets must treat unknown kind + nutshell mint as
incompatible. Cheapest real fix: wallet-side warning on unknown kind at
receive-time (secret is visible then).
