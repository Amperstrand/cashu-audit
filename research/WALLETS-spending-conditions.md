# Wallet-side spending conditions — emission, verification, known breakage

*2026-09-09. Internal research. The mint-side matrix lives in
`divergences/NUT-10-11-14.md`; this is the other half: what wallets PUT ON
THE WIRE and what they check locally.*

## Witness emission on HTLC refund spends (the d6 surface)

| Wallet | Emission when preimage unknown | Source | At cdk 0.18.0 | At nutshell 0.20.3 |
|---|---|---|---|---|
| cashu-ts (v4, bundled lib) | **omits the field** — `preimage !== void 0 ? { preimage } : {}` | grep of installed `cashu-ts.es.js` | REJECT (50000) | ACCEPT |
| cashu-cf (ours) | signatures-only | divergence DB §6 / audit | REJECT (50000) | ACCEPT |
| nutshell wallet (main) | `WitnessForP2pkOrHtlc` — preimage-optional by design; signs P2PK-style, P2BK-aware | `cashu/wallet/p2pk.py` (origin/main) | n/a (wallet, not mint) | ACCEPT |

**The default emission of both major TS wallets is exactly the shape cdk
rejects.** No static emission works on both mints (measured d6/d6b/d6c:
cdk wants a present non-null preimage and never checks it; nutshell wants
absent/null or correct). Conclusion stands: this is a mint-side/spec-side
bug, not a wallet bug — but wallet-side *mitigation* is possible only by
mint sniffing, which is not a strategy.

## Local (receive-time) verification

**Measured/determined 2026-09-09 (third pass): no wallet-vs-mint
interpretation split exists among the majors on duplicate tags.**
- cashu-ts (v4 bundle): tag getter is `.find((t) => t[0] === name)` —
  **first-tag-wins, duplicates silently ignored** — identical to both
  references' mint-side reading. Also enforces its own hard limits
  ("Too many pubkeys", duplicate-key checks) — cashu-ts#578 hardening.
- nutshell (git main, post-#1008): wallet and mint share
  `parse_spending_condition` in `cashu/core/nuts/nut10.py` — consistent
  by construction.
- cashu-cf: first-match family (divergence DB).
- Residual d2 hazard is therefore the **accept/reject split**, not the
  interpretation split: wallets happily display/verify locks that a
  spec-literal mint (DotNet) will refuse to spend. Wallet-side rejection
  of malformed secrets (the a1denvalu3 split's other half) is implemented
  in cashu-ts#578 but only for its own construction paths, not for
  received-token validation — that remains an open probe target.
- Known wallet-side breakage, community-reported: **cashu.me #511** —
  P2PK-locked proofs rejected on receive (from our AUDIT-REPORT census;
  same class: wallet-side condition handling diverging from mint-side).

## The three parallel harnesses (consolidation opportunity)

1. **Ours**: `conformance/scenarios/` (~100 scenarios; reference reports
   for cdk/nutshell/nutmix/cashu-cf mints; matrix runner).
2. **SatsAndSports**: `nut10_compatibility_checker` (58 scenarios, swap+
   melt, published tracked results, legacy-SIG_ALL mode).
3. **cashu-ts integration suite**: run by robwoodgate against real
   nutshell/cdk builds — how #1126 (witness error-code churn) was found.

Identical naming scheme (our suite and the checker share scenario names);
three artifacts, one test-space. Consolidation candidate — and the
checker's Nutmix run proves the value: it caught **over-acceptance**
(invalid HTLC SIG_ALL spends succeeding) that pass/fail-style suites
without "unexpectedly succeeded" checks can miss. Our suite records
FAIL for expected-reject scenarios but does not distinguish
rejected-for-right-reason (the checker's `htlc_signature_only_fails` on
cdk "passed" on a 50000 error that is actually the WRONG reason — the
envelope error, not a preimage error). **Improvement for our suite:
assert on error codes/details for expected-rejects, not just status.**

## Error-text census (wallet-facing surface, 2026-09-09 measured)

| condition | cdk 0.18.0 | nutshell 0.20.3 |
|---|---|---|
| HTLC sigs-only refund | 50000 "Secret is not a HTLC secret" (names the wrong object) | — (accepts) |
| HTLC wrong-preimage refund | — (accepts!) | 11000 "HTLC preimage does not match." |
| P2PK dup sigs | 20008 "P2PK spend conditions are not met" | 11000 "signatures must be unique." |
| witness on plain | 20008 "Witness is not a p2pk witness" | 11000 "witness data not allowed without a spending condition." |
| unknown kind | — (accepts, no witness) | 400 code 0 "'MBS' is not a valid SecretKind" |

Historical (from checker + #1126): nutshell 0.20.0 leaked `code 0`
AssertionError-flavored messages ("Witness is missing for p2pk signature");
post-#1008 main folds absent-vs-malformed witness into one message.
Feeds `issues/error-code-registry.md` (#6).

## Open items

1. cashu-ts: confirm emission path in src (bundled-lib grep is strong but
   not a source read) + whether its HTLC melt path differs from swap.
2. Wallet-parse vs mint-verify differential probe (d2 vector).
3. Read PoC close/recovery emission shapes (`cashu_spilman_channels`).
4. Extend our suite's expected-rejects to assert error identity.

## P2PK wire capture status (2026-09-11, post _request interception)

**What works:** The `_request` interception on `wallet._mint` captures mint quote
requests (POST /v1/mint/quote/bolt11). Verified in htlc_refund cells.

**What doesn't work:** P2PK send operations (`ops.send()`) produce no wire
captures. The `_request` interception on `wallet._mint` doesn't catch them.

**Root cause:** The `WalletOps.send()` method likely uses a different internal
Mint instance or HTTP client than `wallet._mint._request`. The cashu-ts v4
source shows `requestWithAuth()` calling `this._request`, but the WalletOps
class may have its own `_request` reference that isn't affected by our
interception of `wallet._mint._request`.

**Alternative approaches for future investigation:**
1. Proxy on globalThis.fetch (catches captured references)
2. tcpdump on the mint container (catches ALL network traffic)
3. Intercept the Mint class constructor to wrap ALL instances
4. Direct POST /v1/swap testing via raw HTTP (bypasses wallet library)

**Impact:** The d6 witness emission data (which shapes cashu-ts actually puts
on the wire for HTLC refunds) is still not captured. This is the missing
evidence for the upstream d6 filing.
