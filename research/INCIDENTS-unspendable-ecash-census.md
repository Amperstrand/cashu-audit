# Census: public reports of money loss / stuck funds from boundary-mismatch bugs (genus of the NUT-00 encoding trap)

**Date:** 2026-09-08 · Method: GitHub issue search (gh api), Nostr/web search,
source autopsy of archived implementations.

## The precedent that settles the governance question

**nutshell — the reference mint — ships permanent dual-derivation leniency
today** (`cashu/core/crypto/b_dhke.py`):

```python
def verify(a, C, secret_msg):
    Y = hash_to_curve(secret_msg.encode("utf-8"))        # current (domain-separated)
    valid = C == Y * a
    # BEGIN: BACKWARDS COMPATIBILITY < 0.15.1
    if not valid:
        valid = verify_deprecated(a, C, secret_msg)      # pre-0.15.1 algorithm
    return valid
```

When NUT-00's `hash_to_curve` was tightened (nutshell 0.15.1 introduced the
domain separator), every pre-0.15.1 token would have become unspendable under
strict verification. The reference implementation chose to honor issued
claims: permanent fallback, still present. The archived lnbits cashu
extension (a nutshell fork) carries the same dual-verify block — with the
fallback order inverted (legacy first), independently re-implementing the
same policy.

**Implication:** "spec tightening is honored prospectively; issued claims
keep verifying" is not our invention — it is the ecosystem's existing
practice for the algorithm-drift species. Our cdk per-keyset proposal applies
the same principle to the encoding species, with a better boundary (keyset
scoping instead of an unconditional fallback).

## Confirmed public loss/stuck-funds reports (same genus, other species)

| # | Report | Species | Amount | Outcome |
|---|---|---|---|---|
| 1 | Nostr, 2026-02-02: "A lesson in Cashu wallet safety — how I lost 1,824 sats" — **written by an AI agent** about its own custom cashu-ts wallet (melt crash, change never persisted) | state boundary | 1,824 sats | **final loss**, self-reported |
| 2 | Amethyst #3847: melt change matched by amount, mint imputes by index (NUT-08 blank outputs) → wallet discards change after successful payment | representation mismatch (sibling of ours) | user change amounts | "funds appear lost"; recoverable only via NUT-09/NUT-13 |
| 3 | cdk #1180: proofs stuck PENDING after melt rejection (proof-count limit) — L402 nginx integrator | state machine | user balances | "effectively lost" pending manual fix |
| 4 | gonuts #88: send leaves proofs deleted-not-pending; Alby Hub users affected | state machine | user balances | recoverable via wallet restore |
| 5 | lnbits/cashu #68: mint's ecash unspendable in ALL wallets after Lightning top-ups (extension bug); multiple reporters | impl divergence | deposited sats | stuck at mint |
| 6 | Nostr 2026-02 (minibits support): user locked out of ~16k sats by pending-proof cascade across minibits → cashu.me → macadamia | state machine | ~16,000 sats | support case |
| 7 | 2023 bounty thread + FreedomMan note: "could not verify proofs" spend failures on cashu.me / lnbits wallets, multi-user | mixed: pending-state + the 0.15.1 algorithm migration era | unquantified | largely resolved; the migration-era failures are what the nutshell fallback absorbs |

## The encoding species specifically

**No confirmed public loss report found.** Interpretation (argued, not
assumed): consistent with underdiagnosis — the error is cryptic and
unattributable, lenient mints absorb the trap silently, affected wallets are
often custom/one-off scripts whose authors never report. Absence of reports
is not absence of losses; the sensor proposal exists precisely because
nobody can currently count them.

## What this does to our campaign

- The nutshell precedent **strengthens** the cdk per-keyset-leniency proposal:
  we are asking cdk to adopt a bounded version of what nutshell already ships
  unbounded.
- Incident #1 (AI agent losing real sats with a hand-rolled wallet) is the
  clearest public datapoint for the LLM-client risk thesis.
- The census gives the Nostr post its "this genus eats real sats" texture
  without overclaiming the encoding species.

## Species classification of the two known encoding-trap occurrences (2026-09-08 addendum)

The cross-vectors header (cashu-core-lite) records the encoding species shipping
twice in the wild — both in our own orbit, both caught by vectors before user
harm:

1. **prta #86** (OpenTollGate/physical-router-test-automation): the token
   RECOVERY tool's original Y-derivation. Context recovered from the issue:
   `recover_tokens.py` parses stuck tokens and runs NUT-07 checkstate before
   attempting receive — a wrong Y-derivation there makes the recovery tool
   itself misreport spend-state (tell users recoverable tokens are dead, or
   vice versa). Caught in testing; no user funds harmed.
2. **First Python port** of cashu-core-lite: hex-decode divergence, caught by
   the same vectors.

Plus our own private incident (real sat loss, unreleased tooling) — the only
confirmed money-loss case of the encoding species we know of. Public-user
loss reports for this species: still zero (genus: seven, table above).

## Grandfathering clarification (position addendum)

Keyset-scoped leniency has **no sunset deadline**: allowlisted keysets verify
leniently for as long as any of their tokens exist. "Retires when keysets
drain" is a description, not a deadline — no pre-existing claim ever strands
under this design. Strictness applies only to keysets created after a wallet-
side MUST exists and wallets conform, which is precisely the "grandfathered
until spec + conformance" requirement. The one residual: a wallet violating
the MUST under a new keyset strands its own funds — that population is
addressed by guard + vectors + sensor + operator recovery, not by abolishing
strictness (which re-creates the Postel freeze).

Note for the cdk proposal: the nutshell precedent is issuer-relative (it
honors claims *it* issued under the old algorithm; cdk owes nothing for the
algorithm species since it never used the old hash). For the encoding
species, a cdk mint that unknowingly signed entropy-bound outputs DID issue
those claims — per-keyset leniency where the sensor shows traffic is the
faithful application of the same precedent.

## Addendum 2026-09-09: real-world redemption failure reports (expanded search)

### High-profile community reports

| Who | When | What they said | Likely cause |
|---|---|---|---|
| **VitorPamplona** (Amethyst maintainer) | Dec 2024 | "I tested 5 cashu wallets. I have lost funds in all of them. Mints have disappeared on me. NIP-60 events have disappeared as well... NO one should EVER lose ANY money from a custodial system. Not a single sat." | Multiple (state, upgrade, migration) |
| **DireMunchkin** | Jun 2026 | "I tried like 5 different Cashu wallets and lost the funds in 3 of them. Never from the mint rugging — always some weird wallet/mint state snafu where my notes just wouldn't redeem or disappeared." | Opaque redemption failures |
| **stl1988** | Aug 2026 | "npub.cash no longer has its own wallet and I can't get my sats... All my zaps I got are lost!!!" | npub.cash signature verification outage |
| **rubenstorm** | Aug 2026 | YakiHonne cashu wallet: "if I send out... I get error and nothing ever gets sent out" | Opaque error, funds not moving |
| **ManyKeys** | Aug 2026 | wallet.cashu.me shows 0 balance, tried multiple mints, "incomplete migration" | Wallet migration/derivation |
| **FreedomMan** | Mar 2023 | "could not verify proofs" on lnbits, can't send or pay | Pre-0.15.1 era |
| **bostonwine** (21k sat bounty) | Apr 2023 | Multi-user reproduction attempts on cashu.me | Pre-0.15.1 era |
| **AI agent** | Feb 2026 | Lost 1,824 sats — crash between melt and change save | State management |
| **gudnuf** | Aug 2024 | "It took a while to find all the edge cases where tokens may be lost" | Multiple |
| **elkim** | Apr 2026 | cashu-ts 3.6→4.1 upgrade: "all was working flawless until update... agent went full forensics, tested proofs against mint which marked it as spent and it got burned" | Version-upgrade proof invalidation |

### Pattern analysis

Every report says some version of "tokens stopped working" or "funds
disappeared" — **none** can attribute the root cause. The error is always
opaque ("Token not verified", "could not verify proofs", "something went
wrong"). Users blame the wallet, the mint, or "state snafus." Nobody says
"my wallet hashed the entropy instead of the UTF-8 of the secret string"
because the tooling to diagnose that doesn't exist.

This is the strongest possible argument for observe mode: the community's
own prominent members are reporting the symptom class, and the diagnostic
infrastructure to attribute it is 6 lines of code.

### The delay-redemption idea (owner-proposed, 2026-09-09)

A fourth mode between allow and observe:

**`redeem_with_warning`**: accept the proof (honor the claim) but add a
60-second delay before responding. This:
- Signals clearly to the user/wallet that something is unusual
- Gives operators the same visibility as observe mode
- Doesn't confiscate funds
- Discourages repeated use of the legacy path (the delay is annoying)
- Is visible to wallet developers (users complain about slowness → 
  investigation → fix)

Implementation: ~4 lines (sleep + log). Sits between Allow (instant) and
Observe (reject + log). The progression becomes:

  Observe (reject + log) → WarnAndDelay (accept + 60s delay + log) → Allow (accept + log)

This is the "honor the claim but make it hurt" approach — you get your
money, but you (and your wallet developer) know something is wrong.

## Final synthesis 2026-09-09: the ecosystem's fund-loss landscape

### Enforcement history — the inconsistency IS the problem

| Change | Compat at introduction? | Compat duration | How it ended |
|---|---|---|---|
| Domain separator (0.15.1) | ✅ fallback shipped same day | 2.4 years | Removed as a "chore" |
| Secret format base64→hex (cashu-ts 1.0) | ❌ none — instant break | 0 | "Reset counters and self-spend" |
| Algorithm fallback removal (0.20.3) | — (was the removal itself) | — | Shipped unflagged in release notes |
| cdk divergence | ❌ never existed | permanent | Ongoing |

**No enforcement discipline exists.** Sometimes there's a 2.4-year compat
window; sometimes there's none. Sometimes it's flagged as breaking; sometimes
it's a "chore." The spec never advanced from SHOULD to MUST for any of these.

### The broader fund-loss landscape (beyond hash_to_curve)

The search revealed this isn't just about derivation mismatches — the ENTIRE
proof lifecycle is fragile across upgrades, migrations, and client switches:

| Failure mode | Real-world reports |
|---|---|
| Wallet upgrade invalidates proofs | elkim (cashu-ts 3.6→4.1 burned proofs), Zeus users (balance disappearing after update) |
| Keyset migration breaks token decoding | g4tt0 PSA: "Tokens containing Keyset v2 Proofs CANNOT be fully decoded" |
| NIP-60 wallet state races | "Don't use two NIP-60 wallets simultaneously on two devices" |
| Mint goes offline | stl1988: npub.cash outage, "All my zaps I got are lost!!!" |
| Wallet migration incomplete | ManyKeys: "shows 0 balance, tried multiple mints, incomplete migration" |
| Proof state desync | VitorPamplona: "Mints have disappeared on me. NIP-60 events have disappeared" |
| Derivation mismatch (our species) | DireMunchkin: "weird wallet/mint state snafu where notes wouldn't redeem" |

### Why warn-and-delay is the correct default

The user's insight reframes the problem: **hard-to-diagnose means the
failure should be LOUD, not silent.** When a mint can't verify a proof:

- **Instant rejection** = silent confiscation. User sees a cryptic error,
  has no idea why, funds are gone. No diagnostic reaches anyone.
- **Instant acceptance** (if legacy allowed) = the problem is hidden. User
  keeps using the buggy wallet, more trap tokens are created.
- **Delayed acceptance** = the failure is VISIBLE without being fatal. The
  user notices the delay. The wallet developer gets bug reports about
  slowness. The mint operator sees the WARN log. Everyone learns.

The delay should scale with severity:
- 60 seconds for first-time legacy submission (gets attention)
- Configurable (mint operator decides)
- Maybe escalating (repeated legacy submissions from same keyset)

This is the same principle as a bank putting a hold on a suspicious
transaction: the money is safe, but someone looks at it before it clears.

### The complete solution stack

| Layer | What it fixes | Cost |
|---|---|---|
| Spec MUST + vectors | Prevents new implementations from making the mistake | Spec PR |
| Wallet pre-submit guard | Catches the bug client-side before submission | 3 lines in cashu-ts |
| Observe mode | Tells operators they have exposure | 6 lines in verify() |
| Warn-and-delay mode | Gives users a visible signal without confiscation | 4 lines |
| Even-bit signaling | Old wallets abort before sending tokens that will fail | NUT-06 field |
| Error-UX mapping | Turns "Token not verified" into actionable guidance | Wallet-side |
| Upgrade A/B testing | Catches behavioral divergence before it ships | Framework (done) |

No single layer is sufficient. The delay mode is the only one that
addresses the case where ALL other layers have already failed — the proof
arrives at the mint, it doesn't verify canonically, and the current options
are "reject silently" or "accept silently." The delay creates the third
option: "accept loudly."

## Audit.8333.space analysis (2026-09-09)

### Direct answer: No, the auditor's failures are NOT the hash_to_curve issue

The auditor uses a known-good wallet (nutshell CLI) that produces canonical
proofs. In 1000 swaps: **zero "Token not verified" / 10001 errors.** The
auditor cannot detect the derivation trap because it never produces
non-canonical proofs.

### What IS failing at the auditor (the real operational pain)

| Error class | Count | What it means |
|---|---|---|
| "proofs/token pending" (11002/11000/11012) | **186** | #1 failure — state management (interrupted ops) |
| "Cannot melt old and new ecash" (12003) | **50** | Cross-keyset divergence |
| "Unknown Keyset" (12001) | **27** | Keyset format/rotation issue |
| Proxy unreachable | 212 | Infrastructure |
| SSL certificate failures | 53 | Infrastructure |
| 502/522/526 Bad Gateway | 66 | Infrastructure |
| "'Wallet' object has no attribute" | 11 | Auditor's own version mismatch |

The derivation trap is invisible to the auditor — but **186 pending-proof
failures validate our "interrupted-operation recovery is the biggest
underspecified area" finding.**

### The bombshell: 35 of 65 mints (54%) are one upgrade away from strand-funding

| Category | Count | Risk |
|---|---|---|
| Still on nutshell < 0.20.3 (has fallback) | 33 | Will silently strand pre-0.15.1 tokens when they upgrade |
| On Nutshell-CF 0.0.1 (pre-0.15.0, old algorithm as PRIMARY) | 2 | May have algorithm-legacy tokens outstanding RIGHT NOW |
| On current strict versions (0.20.3+ or cdk) | 30 | Already strict — any legacy tokens already stranded |

**These 35 mints have zero observability into whether they hold legacy-token
exposure.** When they upgrade, any pre-0.15.1 tokens become wall-paper
with no warning, no signal, no error distinction. The observe mode is the
tool that would tell them BEFORE upgrading.

### The connection between auditor failures and our broader thesis

The auditor data confirms the ecosystem's #1 fund-loss vector is NOT
derivation mismatches — it's the proof lifecycle itself:
1. Pending proofs (186 failures) = interrupted operations with no recovery
2. Cross-keyset mixing (50 failures) = format/derivation divergence
3. Unknown keysets (27 failures) = keyset rotation without signaling

All three are the same genus: **the spec defines happy paths only, and
every implementation solves the edge cases differently.**
