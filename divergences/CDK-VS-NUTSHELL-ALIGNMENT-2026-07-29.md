# CDK vs Nutshell alignment for cashu-cf — NUT-10/11/14 spending conditions

| Field | Value |
|-------|-------|
| Date | 2026-07-29 |
| Scope | NUT-10 (spending conditions), NUT-11 (P2PK), NUT-14 (HTLC) |
| Source | [CDK #2252](https://github.com/cashubtc/cdk/issues/2252) + cashu-cf conformance (testnut) |
| Related | `NUT-10-11-14.md`, `NUT-14-HTLC-CASHU-CF-VIOLATIONS.md`, `CASHU-CF-CONFORMANCE-20260728.md` |

## Two different problems — don't conflate them

Investigation of cashu-cf #39 (HTLC + SIG_ALL) surfaced an important distinction
that should govern how we think about "align with CDK":

### Category A — cashu-cf-specific bugs (both references already agree)

These are NOT CDK-vs-Nutshell divergences. cashu-cf is simply broken; both CDK
and Nutshell pass the conformance scenario. The fix is "match the spec both
references already follow."

| GH issue | Bug | Status |
|----------|-----|--------|
| **#39** | HTLC + SIG_ALL returned 0 valid signatures | **Fixed** (`a0347e3`, `ea5b657`). Conformance: HTLC+SIG_ALL scenarios now pass. |
| #37 | Locktime expiry drops primary spending pathway (P2PK + HTLC) | **Fixed** (`1d1e401`) |
| #38 | HTLC refund path incorrectly requires preimage | **Fixed** (`1d1e401`) |
| #31 | NUT-14 HTLC spec violations (4) | **Fixed** (`1d1e401`) |

**Action:** none remaining. These are closed. No alignment decision needed —
the spec is unambiguous and both references agree.

### Category B — genuine CDK ↔ Nutshell divergences (spec-ambiguous)

These are the 8 edge cases tracked in CDK #2252 / `NUT-10-11-14.md`. Here the
spec is silent or unclear, CDK and Nutshell genuinely differ, and cashu-cf
must pick a side. **This is where the "align with CDK" decision applies.**

## Current cashu-cf alignment (re-validated 2026-07-29)

cashu-cf is currently **Nutshell-aligned** on the Category-B divergences.

| # | Divergence | CDK | Nutshell | cashu-cf today | Spec | Recommendation |
|---|------------|-----|----------|----------------|------|----------------|
| 1 | Malformed/unknown NUT-10 secret | anyone-can-spend | (now) anyone-can-spend | anyone-can-spend | NUT-10 Caution: permitted | **No change** — all 3 agree (was stale) |
| 2 | Duplicate tags | first-match | reject malformed | **reject all** (strict) | NUT-11 L85 "MUST be rejected" | **Keep cashu-cf** — strictest, spec-aligned |
| 3 | `n_sigs` > available pubkeys | not validated (refund usable) | reject upfront (blocks refund) | reject upfront | NUT-11 L87 "MUST be rejected" | **Keep cashu-cf** (Nutshell-aligned, spec-aligned) |
| 4 | Empty `["pubkeys"]` tag | accept (0 keys → anyone-can-spend) | reject (≥1 required) | accept (CDK-aligned) | unspecified | **Spec clarification needed** — lean CDK (current) |
| 5 | HTLC hash hex case | accept mixed/upper | lowercase only | normalize lowercase (Nutshell) | NUT-14: lowercase | **Keep cashu-cf** (spec-aligned) |
| 6 | HTLC refund via SIG_INPUTS sig-only witness | reject (wrong type) | accept (preimage optional) | accept (Nutshell) | NUT-14 implied | **Keep cashu-cf** (enables sender pathway) |
| 7 | Duplicate signatures from same key | error `DuplicateSignature` | ignore extra | **reject** (CDK-aligned) | unspecified | **Keep cashu-cf** (CDK-aligned — stricter/safer) |
| 8 | Witness on plain (non-NUT-10) secret | reject | (now) reject | reject | unspecified | **No change** — all 3 agree (was stale) |

### Alignment verdict

**Recommendation: do NOT blanket-align to CDK.** Of the 6 accurate divergences:

- **3 are spec-aligned already** (#2, #3, #5) — cashu-cf follows the NUT spec
  where it is explicit; changing these would move AWAY from the spec.
- **2 cashu-cf already follows CDK** (#4, #7) — no change needed.
- **1 is a Nutshell behavior worth keeping** (#6) — HTLC refund pathway
  usability; CDK's stricter witness-type rejection blocks the sender refund.

Net: cashu-cf's current mix is defensible. The only place CDK is arguably
"wrong" relative to cashu-cf is #6 (HTLC refund). If anything, CDK should
align to the cashu-cf/Nutshell behavior there.

**Where to align with CDK going forward:** for any NEW divergence discovered,
default to CDK's behavior (it's the more recently designed, typed, spec-aware
implementation) **unless** CDK clearly diverges from an explicit NUT statement
—in which case follow the spec and document the deviation here.

## cashu-cf-specific note: the SIG_ALL candidate-message compat hack

`verifySigAll` (`src/mint/spending-conditions.ts:787`) builds **10 candidate
SIG_ALL messages** (secrets+B, swap secret+C+amount+B, outputs-only, and sorted
variants) and accepts the spend if ANY verifies. This is an intentional compat
hack (commit `1950bac`) to tolerate wallet message-format divergence.

- **CDK / Nutshell:** verify against a single canonical message.
- **cashu-cf:** tries 10 variants.

This is broader than both references and is an audit warning (it relaxes
verification). It exists because real wallets (cashu-ts, Nutshell legacy)
disagreed on the SIG_ALL message format. **Recommendation for the #51 saga
refactor:** once cashu-cf standardizes on the NUT-11 canonical message
(secret+C+amount+B[+quote]) and cashu-ts converges, drop the candidate fan-out
to a single message to match CDK/Nutshell exactly.

## Open items (not divergences — operational)

These remain open but are NOT CDK/Nutshell alignment questions:
- #48 proofs stuck PENDING up to 30 min on payment timeout deferral
- #49 MPP amount conversion loses millisat precision
- #50 self-payment TOCTOU window (related to the ISSUE-049 CAS family)
- #7 old keysets never expire
- ISSUE-051 melt saga refactor (will revisit the SIG_ALL candidate hack)

## How to use this doc

When a new cashu-cf conformance failure is found:
1. Check whether BOTH CDK and Nutshell pass it. If yes → Category A (cashu-cf
   bug, fix to match spec). If no → Category B (record here as a divergence).
2. For Category B, add a row to the table above with each implementation's
   behavior and the spec reference.
3. Default resolution: follow CDK unless the NUT spec is explicit, then follow
   the spec.
