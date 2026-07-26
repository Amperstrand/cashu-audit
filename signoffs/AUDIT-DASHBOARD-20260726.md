# Cashu Implementation Audit Dashboard

> **Date**: 2026-07-26
> **Auditor**: GLM-5.2 in opencode
> **Scope**: All mandatory NUTs (00-06) + spending conditions (10/11/14) + optional NUTs
> **Implementations**: cashu-cf (TypeScript), CDK (Rust), Nutshell (Python)

## Coverage Matrix

| NUT | Title | cashu-cf | CDK | Nutshell |
|-----|-------|----------|-----|----------|
| 00 | Cryptography and Models | ✅ Audited | ✅ Audited | ✅ Audited |
| 01 | Mint public keys | ✅ Audited | ✅ Audited | ✅ Audited |
| 02 | Keysets and fees | ✅ Audited | ✅ Audited | ✅ Audited |
| 03 | Swapping tokens | ✅ Audited | ✅ Audited | ✅ Audited |
| 04 | Minting tokens | ✅ Audited | ✅ Audited | ✅ Audited |
| 05 | Melting tokens | ✅ Audited | ✅ Audited | ✅ Audited |
| 06 | Mint info | ✅ Audited | ✅ Audited | ✅ Audited |
| 07 | Token state check | ✅ Audited | ⏳ Pending | ⏳ Pending |
| 08 | Overpaid Lightning fees | ✅ Audited | ⏳ Pending | ⏳ Pending |
| 09 | Signature restore | ✅ Audited | ⏳ Pending | ⏳ Pending |
| 10/11/14 | Spending conditions | ✅ Audited | ✅ Audited | ✅ Audited |
| 12 | DLEQ proofs | — Not impl | ⏳ Pending | ⏳ Pending |
| 13 | Deterministic secrets | — Not impl | ⏳ Pending | ⏳ Pending |
| 15 | Partial MPP | — Not impl | ⏳ Pending | ⏳ Pending |
| 17 | WebSocket subscriptions | ✅ Audited (disabled) | ⏳ Pending | ⏳ Pending |
| 19 | Cached responses | ✅ Audited | — Not audited | — Not audited |
| 20 | Signature on mint quote | ✅ Audited | — Not audited | — Not audited |
| 23 | Payment Method: BOLT11 | ✅ Audited | — Not audited | — Not audited |

## Overall Compliance Summary

| Implementation | NUTs Audited | Overall Verdict | Key Strengths | Key Concerns |
|---|---|---|---|---|
| **cashu-cf** | 14 | **PASS** | 0 FAILs across all mandatory NUTs. ISSUE-023 fixed. Duplicate tag enforcement strictest of 3 impls. | SIG_ALL uses 10 candidate message formats (compat hack). Most lenient on witness-on-plain-secret. |
| **CDK** | 8 | **PASS (conditional)** | Strong Rust type safety. Canonical SIG_ALL message format. | 2 FAILs in NUT-10/11/14 (duplicate tags, n_sigs validation). 4 WARNs on hex case. |
| **Nutshell** | 8 | **PASS (conditional)** | Reference implementation. Clean Python codebase. | Some implementation details differ from spec letter (bytes.fromhex case-insensitive, SIG_ALL message format). |

## Cross-Implementation Divergences (NUT-10/11/14)

Based on independent code audit (corrected from CDK #2252 — see `divergences/FINDING-CDK-2252-outdated.md`):

| # | Issue | cashu-cf | CDK | Nutshell | Divergence? |
|---|---|---|---|---|---|
| 1 | Malformed secrets | anyone-can-spend | anyone-can-spend | fail-closed (unknown kind) | **YES** — Nutshell stricter |
| 2 | Duplicate tags | **rejects all** | first-match | first-match | **YES** — cashu-cf strictest |
| 3 | n_sigs > pubkeys | rejects upfront | not on verify path | at verify time | **PARTIAL** |
| 4 | Empty ["pubkeys"] | accepted | accepted | accepted | NO — all agree |
| 5 | HTLC hash case | lowercase enforced | mixed accepted | mixed accepted | **YES** — cashu-cf strictest |
| 6 | HTLC refund SIG_INPUTS | accepts | rejects (wrong witness type) | accepts | **YES** — CDK diverges |
| 7 | Duplicate sigs | errors | errors | errors | NO — all agree |
| 8 | Witness on plain secret | accepts/ignores | rejects | rejects | **YES** — cashu-cf most lenient |

## Findings Summary

### cashu-cf (0 FAIL, ~14 WARN)
- **ISSUE-023 FIXED**: NUT-04 output validation changed from `===` to `<=`
- **Duplicate tags**: Fixed — strictest of all 3 implementations
- **SIG_ALL compat**: 10 message variants tried (documented as intentional)
- **Quote ID**: Uses 16-char hex instead of UUID v7 (spec says SHOULD, not MUST)

### CDK (4+ FAIL, 4+ WARN)
- **NUT-11 L85**: Duplicate tags use first-match (should reject per spec)
- **NUT-11 L87**: n_sigs > pubkeys not validated on verification path (should reject per spec)
- **HTLC hash case**: Accepts mixed/uppercase (spec says lowercase)
- **NUT-04 amount_paid/amount_issued**: Not fully implemented in all response paths

### Nutshell (~1 FAIL, 4+ WARN)
- **SIG_ALL message**: Missing `quote_id` in melt message (spec includes it)
- **bytes.fromhex**: Case-insensitive (accepts mixed-case hex, spec says lowercase)
- **Unknown kind handling**: Raises ValueError rather than clean rejection (functional but fragile)
- **Duplicate tags**: Uses first-match like CDK (should reject per spec)

## Audit Artifacts

All signoffs are in `signoffs/<impl>/NUT-XX-20260726-glm52.md`.
Cross-impl comparison for NUT-10/11/14: `signoffs/cross-impl-comparison-20260726.md`.
Divergence database: `divergences/NUT-10-11-14.md` + `divergences/FINDING-CDK-2252-outdated.md`.
