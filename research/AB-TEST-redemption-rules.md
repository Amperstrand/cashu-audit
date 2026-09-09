# A/B experiment: redemption rules across nutshell and cdk versions

**Date:** 2026-09-09 · **Methodology:** lightning-playground pattern — frozen
predictions written BEFORE the run, named arms, identical probes,
environment-identity guard per arm, structured comparison.

## Setup

Four mint arms on ai-legion (docker), all FakeWallet backends, identical
mnemonic-free keys per arm, distinct ports:

| Arm | Version | Identity (from /v1/info) |
|---|---|---|
| ns015 | nutshell 0.15.0 (pip-pinned container) | Nutshell/0.15.0 |
| ns0182 | nutshell 0.18.2 (official image) | Nutshell/0.18.2 |
| cdk0176 | cdk-mintd 0.17.6 (official image) | cdk-mintd/0.17.6 |
| cdk0180 | cdk-mintd 0.18.0 (official image) | cdk-mintd/0.18.0 |

Probe: per arm × derivation — mint 64 sats through a paid quote with B_
built under the derivation, unblind, swap with fee-aware powers-of-2
canonical outputs, record verdict. Derivations:
- **canonical**: H_modern(utf8(secret)) [NUT-00 spec]
- **algolegacy**: H_deprecated(utf8(secret)) [pre-0.15.1: sha256-chain, no
  domain separator] — implemented from nutshell's own shipped code
- **trap**: H_modern(hex_decode(secret)) [entropy-hashing]

## Frozen predictions (from source archaeology of shipped wheels)

Predicted BEFORE running (see transcript; source: b_dhke.py in
cashu-0.15.0/0.15.1 wheels — 0.15.0 has deprecated-primary verify with a
forward-compat fallback to the then-future domain-separated hash; 0.15.1+
flipped primary and kept the deprecated fallback; cdk never shipped
deprecated).

## Results — 12/12 CONFIRMED

| Arm | canonical | algolegacy | trap |
|---|---|---|---|
| nutshell 0.15.0 | ✅ ACCEPT (fallback) | ✅ ACCEPT (primary) | ❌ REJECT |
| nutshell 0.18.2 | ✅ ACCEPT (primary) | ✅ ACCEPT (fallback) | ❌ REJECT |
| cdk 0.17.6 | ✅ ACCEPT | ❌ **REJECT** | ❌ REJECT |
| cdk 0.18.0 | ✅ ACCEPT | ❌ **REJECT** | ❌ REJECT |

## What this proves

1. **The migration softfork is real and live**: nutshell (both eras)
   redeems algorithm-legacy tokens; cdk (both versions) refuses them. A
   nutshell→cdk migration strands every pre-0.15.1-minted token —
   redemption rules tightened by software choice, no spec change, no signal.
2. **nutshell 0.15.0 shipped forward-compat**: its verify tries
   deprecated-primary then falls back to the domain-separated hash that
   would only become primary in 0.15.1 — the bridge was built before the
   flip. Both eras accept both algorithms: nutshell is the compatibility
   maximizer on this axis.
3. **cdk is strict on both axes** (algorithm and encoding) — every non-
   canonical derivation rejected in every tested version.
4. Encoding axis (trap column): everyone strict except cashu-cf (from the
   earlier testnut measurements) — the only encoding-lenient mint we know.

## Experimenter notes (honest)

Three probe bugs before the clean run, each caught by the frozen-prediction
mismatch discipline: (1) hand-rolled point math instead of house helpers —
swapped in conformance/crypto.py; (2) cdk requires inputs == outputs + fee
exactly (my "62 for safety" — the exact inverse error of assuming fees);
(3) nutshell needs powers-of-2 output splits and its own fee (100 ppk on
0.18.2). The methodology worked as designed: predictions ≠ results meant
PROBE BUG until proven otherwise, never "interesting finding" — and the
final run confirming 12/12 is meaningful only because the mismatches were
investigated to root cause first.

Reproduce: `/tmp/ab_probe.py` (also archived in this repo:
`conformance/ab_probe.py`), arms via docker on ai-legion per the setup
table. Probe source of truth for the deprecated hash: nutshell's shipped
0.15.0 wheel.

---

## Addendum 2026-09-09: arm 5 — cdk v0.18.0 with the legacy fix

Branch: `Amperstrand/cdk@nut00-legacy-v0.18.0` (backport of
nut00-per-keyset-leniency + new legacy pre-0.15.1 hash algorithm path).
Arm configured with `legacy_algorithm_keysets = [<its keyset>]` only
(encoding allowlist left empty).

| Arm | canonical | algolegacy | trap |
|---|---|---|---|
| **cdk 0.18.0 + fix** | ✅ ACCEPT | ✅ **ACCEPT** (allowlisted) | ❌ REJECT |

**= the nutshell 0.18.2 row exactly.** The softfork is closed: a nutshell
mint migrating to cdk (this branch) keeps redeeming pre-0.15.1 tokens.
Sensor telemetry confirmed on both axes (WARN on unallowlisted match, INFO
on allowlisted acceptance).

## Community-history findings (researched 2026-09-09)

- The 0.15.1 domain-separator migration was **never debated as a compat
  question** — PR #421 ("Adjust new domain separator", 2024-02-15) has no
  discussion; the fallback simply appeared. The wallet-side deprecation
  attempts (#457/#458/#459, three tries in two days) show it was bumpy.
- cashu-ts 1.0.0 migration guide tells users to **reset counters and
  self-spend all proofs** — the change silently invalidated deterministic
  secrets with no redemption path.
- nutshell **removed** the deprecated fallback in 2026-07 (#1082 "retire
  legacy curve mapping") — the compat window was open ~2.4 years with no
  sunset signal, no error-code distinction, no spec change. Current
  nutshell (0.20.3) rejects algolegacy.
- Net: the ecosystem silently softforked three times (0.15.1 flip, cdk
  divergence, 2026 removal) with zero signaling to users or operators.
  Our position doc's three-channel signaling proposal addresses exactly
  this history.

## Deep-dive: the 2026-07 removal (PR #1082) — facts from the diff and record

**When exactly:** merged 2026-07-15 (commit 61019f2b), authored by
a1denvalu3 (community contributor, 65 repos — NOT a core maintainer),
approved by callebtc (creator). Shipped in **0.20.3, released 2026-07-22**
— seven days from merge to release. The 0.20.3 release notes list it as a
"chore" between docker fixes and Pydantic migration. **No migration
warning, no breaking-change flag, no release-notes callout.**

**Was it "on purpose"?** Yes and no. The framing is cleanup: PR title
"retire legacy curve mapping", body says "remove the obsolete
curve-mapping compatibility path". The word "obsolete" does the work —
but obsolete to whom? The fallback had been there for 2.4 years with zero
deprecation signaling (no error code, no log, no sunset date, no spec
note). What the diff actually removes:

1. **Mint-side verify fallback** (`verify_deprecated`) — pre-0.15.1 tokens
   become unredeemable at upgraded nutshell mints. THE softfork.
2. **Wallet-side blinding option** (`step1_alice_deprecated` + the
   `wallet_use_deprecated_h2c` setting, default False) — this was already
   opt-in-only and harmless (a wallet COULD choose to blind with the old
   hash for old-mint compat; that escape hatch is gone too).
3. **DLEQ verification fallback** (`carol_verify_dleq_deprecated`) — old
   tokens with DLEQ can't be peer-verified offline either.

**No issue preceded it.** No discussion in the PR (zero comments, one-line
approval). No linked issue. No reported-lost-funds issue on the tracker
(we searched: nothing). The author's intent was code hygiene — "use the
current mapping consistently" — with no evidence anyone asked "who still
redeems under the old mapping?"

**Who's actually exposed:** any nutshell mint that has been running since
before 2024-02 (0.15.1) — 2.5+ years — AND upgrades to 0.20.3+ AND still
has unspent pre-0.15.1 proofs outstanding. In practice: long-running
community mints (8333.space is the flagship example — it has run since
2023). Whether those old tokens are still in circulation is unknowable —
which is exactly our sensor's job. No mint operator has reported stranded
funds publicly (GitHub issues, Nostr searches as of 2026-09-09).

**Verdict:** not a deliberate policy decision to strand users — a
maintenance PR that deleted a compat path nobody remembered was
load-bearing, shipped without ceremony. The governance gap (no signaling,
no sunset discipline, no operator outreach) did the damage, not malice.
This is the strongest possible argument for the three-channel signaling
proposal and the sensor: when the reference mint can silently delete a
redemption path as a "chore", operators need instrumentation to know what
their outstanding liabilities redeem under — before and after upgrades.
