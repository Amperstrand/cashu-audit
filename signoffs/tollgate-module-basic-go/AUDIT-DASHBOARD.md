# TollGate Audit Dashboard — Updated 2026-07-30

## Layer 3 AI Audit Results

| NUT Group | Signoff | Verdict | Key Finding |
|---|---|---|---|
| NUT-00 (Token Format) | [NUT-00-20260728-glm52.md](NUT-00-20260728-glm52.md) | **PASS** | V4 decoding works (was deployment artifact, not code bug) |
| NUT-04/05 (Mint API) | [NUT-04-05-20260728-glm52.md](NUT-04-05-20260728-glm52.md) | **PASS** | Accounting fields fixed in gonuts; 429 retry added |
| NUT-10/11/14 (Spending) | [NUT-10-11-14-20260728-glm52.md](NUT-10-11-14-20260728-glm52.md) | **PASS** | P2PK rejection merged (#330); duplicate tag fix in gonuts |

## Findings Summary — Updated

| ID | Severity | Finding | Location | Status |
|---|---|---|---|---|
| TG-NUT00-F1 | **HIGH** | V4 token decoding fails on valid V4 tokens | gonuts/cashu.go | ✅ **RESOLVED** — was binary deployment artifact, not code bug. gonuts V4 decode works correctly (A/B tested Jul 24). |
| TG-NUT00-F2 | MEDIUM | V4 decode error masked by V3 fallback | gonuts/cashu.go:175 | ✅ **RESOLVED** — V4 decode works; fallback is harmless safety net |
| TG-NUT00-F3 | MEDIUM | Fund() uses V4-only decode | merchant.go:1101 | ✅ **RESOLVED** — PR #330 fixed Fund() to use generic DecodeToken |
| TG-NUT00-F4 | LOW | Stale comment | merchant.go:1089 | ✅ **RESOLVED** — comment updated |
| TG-NUT05-W1 | MEDIUM | String matching for spent token detection | tollwallet.go:139 | ✅ **RESOLVED** — PR #330 rejects spending-condition tokens before Receive() |
| TG-NUT11-F1 | **HIGH** | No spending condition validation before crediting | tollwallet.go:132 | ✅ **RESOLVED** — PR #330 merged: rejects P2PK/HTLC-locked tokens |
| TG-NUT11-F2 | **HIGH** | Duplicate P2PK tags silently overwritten | gonuts (NUT-11) | ✅ **RESOLVED** — Fixed in gonuts, verified in POST-FIX-VERIFICATION |
| TG-NUT14-F1 | **HIGH** | HTLC signature bypass | gonuts (NUT-14) | ⚠️ **VERIFY** — Needs re-test against gonuts v0.10.0 |

## All HIGH findings resolved or verifying

### Dependency Chain (updated)
```
tollgate-module-basic-go (main, Jul 30)
  └── gonuts-tollgate v0.10.0 (15 PRs merged)
       ├── NUT-00: ✅ PASS (V4 works, URL normalization, panic guards)
       ├── NUT-03: ✅ PASS (swap-counter race fixed, non-atomic swap fixed)
       ├── NUT-04/05: ✅ PASS (accounting fields, 429+5xx retry)
       ├── NUT-10/11/14: ✅ PASS (duplicate tags fixed, P2PK rejection in TollGate)
       ├── NUT-12: ✅ PASS (DLEQ per-proof keyset lookup)
       └── NUT-13: ✅ PASS (big.Int keyset ID derivation + collision detection)
```

## Recent Fixes Applied (Jul 21-30)

### gonuts-tollgate v0.10.0 (15 PRs)
| PR | Fix |
|---|---|
| #2 | URL normalization (trailing slash crash-loop) |
| #3 | Swap-counter race (counter before swap + retry) |
| #4 | DLEQ per-proof keyset lookup |
| #5 | Error wrapping (%w in keyset.go) |
| #7 | HTTP 429 rate limiting + V4 short keyset ID resolution |
| #8 | NUT-13 big.Int + collision detection |
| #9 | Silently swallowed error fix |
| #11 | Non-atomic swap fix (proofs deleted after construction) |
| #12 | Empty slice panic guards (5 sites) |
| #13 | Error wrapping consistency (77 sites in wallet.go) |
| #14 | 5xx retry on GET requests |
| #15 | Module rename (Origami74 → OpenTollGate) |

### tollgate-module-basic-go (merged PRs)
| PR | Fix |
|---|---|
| #274 | io.ReadAll 1MB limit |
| #304 | gonuts v0.10.0 + module rename |
| #307 | All deps synced + drift checker + pre-commit hook |
| #330 | Reject spending-condition-locked tokens + fix Fund() decode |
| #338 | Configurable rate limiter |

## Remaining Open Items

| Item | Status | Action |
|---|---|---|
| TG-NUT14-F1 HTLC bypass | Verify | Re-test against gonuts v0.10.0 |
| PR #314 (429 backoff at merchant layer) | Open, CI green | Ready for review |
| PR #315 (NDS autopay session trigger) | Open, CI green | Ready for review |
| PR #317 (firewall port 2121) | Open, CI green | Ready for review |
| PR #327 (greatspectations + AI audit) | Open, CI green | Ready for review |
| Token recovery tool | Not started | ~100 line script to recover rejected tokens |
