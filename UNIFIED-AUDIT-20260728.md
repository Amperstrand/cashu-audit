# Unified Cashu Audit: OpenTollGate Ecosystem — 2026-07-28

## Executive Summary

Comprehensive audit of every Cashu touchpoint across the OpenTollGate project ecosystem. Covers 4 repositories, 3 audit layers, and identifies 8 findings (3 fixed, 5 open).

---

## Repositories Audited

| Repo | Version | Cashu Library | Layer 1 | Layer 3 | Key Findings |
|---|---|---|---|---|---|
| **gonuts-tollgate** | v0.10.0 | (is the library) | ✅ 85 quotes | ✅ 5 signoffs + post-fix | 2 fixed, 2 open |
| **tollgate-module-basic-go** | upstream/main | gonuts v0.10.0 | ✅ PR #327 | ✅ 3 signoffs | 3 open |
| **tollgate-captive-portal-site** | main | cashu-ts v2.2.2 | ✅ added 2026-07-28 | ✅ 1 signoff (first ever) | 1 open |
| **cdk-go evaluation** | research | cdk-go (FFI) | N/A | Research only | Migration risk map |

---

## Cashu Flow: End-to-End

```
User's Cashu Wallet (Nutshell/cashu-ts/Wallet)
    │
    │ Cashu token (V3 cashuA or V4 cashuB)
    ▼
Captive Portal SPA (tollgate-captive-portal-site)
    │ cashu-ts v2.2.2 getDecodedToken() — V3 ✓ V4 ✓
    │ Wraps in Nostr event (kind 21000)
    │ POST application/json to :2121/
    ▼
TollGate Backend (tollgate-module-basic-go)
    │ extractCashuToken() — extracts from Nostr event "payment" tag
    │ cashu.DecodeToken() [gonuts] — V3 ✓ V4 ✗
    │ tollwallet.Receive() — calls gonuts wallet.Receive()
    │ No spending condition validation
    ▼
gonuts-tollgate (the Cashu library)
    │ wallet.Receive() — HTTP to mint, claim proofs
    │ NUT-11: duplicate tag detection ✓ (fixed)
    │ NUT-14: HTLC signature bypass ✗ (open)
    │ V4 CBOR decoding ✗ (open)
    ▼
Cashu Mint (CDK/Nutshell/custom)
    │ /v1/mint/bolt11 — mint quotes
    │ /v1/melt/quote/bolt11 — melt quotes
    │ /v1/swap — token swaps
    │ /v1/checkstate — spent checks
```

---

## All Findings

### Resolved (since initial audit)

| ID | Finding | Repo | Fix | Verified |
|---|---|---|---|---|
| NUT11-F1 | Duplicate P2PK tags silently overwritten | gonuts | `seen` map in ParseP2PKTags | ✅ 2026-07-28 |
| NUT04-W1 | Missing accounting fields in mint quote | gonuts | `amount_paid/issued/updated_at` added | ✅ 2026-07-28 |
| TG-NUT05-W1 | String-based spent detection (fragile) | tollgate | Documented; typed error requested from gonuts | ✅ Documented |

### Open — High Severity

| ID | Finding | Repo | Impact | Issue |
|---|---|---|---|---|
| TG-NUT00-F1 | V4 token decoding fails (CBOR struct tags) | gonuts | Modern wallet users can't pay TollGate | #326 |
| TG-NUT11-F1 | No spending condition validation | tollgate | Attacker credits internet with unspendable P2PK-locked tokens | #324 |
| TG-NUT14-F1 | HTLC signature bypass (pubkeys without n_sigs) | gonuts | Attacker spends HTLC tokens without required signatures | #328 |

### Open — Medium/Low Severity

| ID | Finding | Repo | Impact | Issue |
|---|---|---|---|---|
| TG-NUT00-F2 | DecodeToken error masking | gonuts | V4 error hidden, V3 error surfaces | Documented |
| TG-NUT00-F3 | Fund() uses V4-only decode path | tollgate | V3 tokens fail in CLI funding | #325 |
| TG-NUT00-F4 | Stale comment "cashuA" in Fund() | tollgate | Misleading | Documented |
| PORTAL-F1 | Portal V4-ready but backend V3-only | captive-portal | User-facing incompatibility | Documented in signoff |

---

## greatspectations Adoption Status

| Repo | Quotes | specquotes.toml | CI | Coverage |
|---|---|---|---|---|
| gonuts-tollgate | 85 (16 NUTs) | ✅ | ✅ | Good |
| tollgate-module-basic-go | 3 (added today) | ✅ PR #327 | Pending | Minimal |
| tollgate-captive-portal-site | 2 (added today) | ✅ | Pending | Minimal |
| cdk-go | N/A | N/A | N/A | N/A |

---

## CDK-Go Migration Risk Assessment

| Operation | gonuts | CDK-go | Migration Risk |
|---|---|---|---|
| V3 token decode | ✅ | ✅ | Low |
| V4 token decode | ❌ broken | ✅ native | **Fixes V4 issue** |
| V4 token encode | ✅ | ✅ | Low |
| P2PK validation | Partial (fixed dup tags) | ✅ full | Medium |
| HTLC validation | ❌ bypass open | ✅ full | **Fixes HTLC issue** |
| Wallet Receive | ✅ | ✅ | Low |
| Wallet Send | ✅ | ✅ | Low |
| MIPS support | ✅ pure Go | ❌ CGO/FFI | **HIGH** — no MIPS |
| Error types | String matching | Typed errors | Medium |

**Critical blocker**: cdk-go requires CGO (Rust FFI). OpenWrt MIPS routers may not have a C toolchain. This is tracked in #271.

---

## Issue Tracker

All issues filed during this audit:

| Issue | Repo | Severity | Status |
|---|---|---|---|
| #324 | tollgate-module-basic-go | HIGH | Open |
| #325 | tollgate-module-basic-go | MEDIUM | Open |
| #326 | tollgate-module-basic-go | HIGH | Open |
| #327 | tollgate-module-basic-go | — | PR (spec quotes) |
| #328 | tollgate-module-basic-go | HIGH | Open |

---

## Recommendations

### Immediate (before next release)
1. Fix V4 CBOR decoding in gonuts (#326) — add `cbor` struct tags to TokenV4
2. Add spendability check in tollgate Receive (#324) — reject P2PK/HTLC-locked tokens
3. Fix NUT-14 HTLC bypass in gonuts (#328) — require signatures when pubkeys present

### Short-term (next sprint)
4. Improve DecodeToken error diagnostics — log V4 error before V3 fallback
5. Fix Fund() to use generic DecodeToken (#325)
6. Add more greatspectations quotes to tollgate-module-basic-go
7. Run captive-portal-site conformance tests

### Long-term (CDK migration)
8. Evaluate cdk-go MIPS support (critical blocker)
9. Plan gonuts → CDK migration per NUT
10. Full Layer 4 runtime conformance suite against production mints
