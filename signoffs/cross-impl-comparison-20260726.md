# Cross-Implementation Comparison: NUT-10/11/14

> **Generated**: 2026-07-26
> **Audits**: cashu-cf @ 379e541, CDK @ d033f1b, Nutshell @ 1853902
> **Auditor**: GLM-5.2 in opencode
> **Source**: CDK #2252 + independent code audit

## Executive Summary

The cross-implementation audit of NUT-10/11/14 (spending conditions) across three Cashu implementations revealed **that CDK #2252's divergence table is partially outdated**. Of the 8 documented divergences, **4-5 no longer match current Nutshell behavior**. This was discovered by the audit framework — validating its value.

## Audit Results Comparison

| Metric | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| **Overall verdict** | PASS | PASS (conditional) | PASS (conditional) |
| **PASS** | 23 | 29 | ~20 |
| **FAIL** | 0 | 2 | 1-2 |
| **WARN** | 2 (now fixed) | 4 | 3-4 |
| **Key FAILs** | — | Duplicate tags (first-match); n_sigs not validated on verify path | SIG_ALL message missing quote_id for melt |

## CDK #2252 Divergence Accuracy

The CDK #2252 issue documented 8 divergences. Our independent audit confirms some but **corrects others**:

| # | Issue | CDK #2252 says CDK does | CDK #2252 says Nutshell does | **Audit finding** | Accurate? |
|---|---|---|---|---|---|
| 1 | Malformed secrets | anyone-can-spend | fail-closed | Both confirmed | ✅ Accurate |
| 2 | Duplicate tags | first wins | rejected | **Nutshell ALSO uses first-match** (conditions.py get_tag) | ❌ WRONG — Nutshell doesn't reject |
| 3 | n_sigs > pubkeys | not validated | rejected upfront | **Nutshell validates at verify time, NOT upfront**; refund path still usable | ❌ WRONG — Nutshell doesn't block refund |
| 4 | Empty ["pubkeys"] | accepted | rejected | **Nutshell ALSO accepts** (get_tag_all returns empty list, handled gracefully) | ❌ WRONG — Nutshell accepts |
| 5 | HTLC hash case | mixed accepted | lowercase only | **Nutshell ALSO accepts mixed** (bytes.fromhex is case-insensitive) | ❌ WRONG — Nutshell accepts mixed |
| 6 | HTLC refund SIG_INPUTS | rejects | accepts | Both confirmed | ✅ Accurate |
| 7 | Duplicate sigs | errors | ignores | **Nutshell ALSO errors** (conditions.py:148-149 explicitly rejects) | ❌ WRONG — Nutshell rejects too |
| 8 | Witness on plain secret | rejects | accepts | **Nutshell ALSO rejects** (conditions.py:210-213: "witness data not allowed") | ❌ WRONG — Nutshell rejects too |

**Score: 2/8 accurate, 6/8 outdated or wrong for Nutshell.**

This means CDK and Nutshell are actually **more aligned than CDK #2252 suggests**. The divergences that DO exist are narrower than documented.

## Revised Divergence Table (Corrected)

Based on independent code audit, not CDK #2252's documentation:

| # | Issue | CDK (actual) | Nutshell (actual) | cashu-cf (actual) | Real divergence? |
|---|---|---|---|---|---|
| 1 | Malformed secrets | anyone-can-spend fallback | fail-closed for unknown kind, anyone-can-spend for malformed JSON | anyone-can-spend fallback | **YES** — CDK and cashu-cf agree; Nutshell stricter for unknown kinds |
| 2 | Duplicate tags | first-match wins | first-match wins | **FIXED**: now rejects all duplicate tags | **YES** — cashu-cf is now strictest |
| 3 | n_sigs > pubkeys | not validated on verify path | validated at verify time, not upfront | validated upfront | **PARTIAL** — cashu-cf strictest; CDK and Nutshell similar |
| 4 | Empty ["pubkeys"] | accepted | accepted | accepted (primary key from data still works) | **NO** — all three agree |
| 5 | HTLC hash case | mixed accepted | mixed accepted (bytes.fromhex) | lowercase enforced (normalizeHex) | **YES** — cashu-cf strictest |
| 6 | HTLC refund SIG_INPUTS | rejects non-HTLCWitness type | accepts (preimage optional in refund) | accepts (preimage optional in refund) | **YES** — CDK diverges |
| 7 | Duplicate sigs | errors | errors | errors | **NO** — all three agree |
| 8 | Witness on plain secret | rejects | rejects | accepts and ignores | **YES** — cashu-cf is most lenient |

## Key Findings

### Finding 1: CDK #2252 is partially outdated (HIGH)
CDK #2252's characterization of Nutshell's behavior is wrong for items 2, 3, 4, 5, 7, and 8. This means:
- The Cashu community has been working with an inaccurate divergence reference
- Some "divergences" were never real, or have been fixed in Nutshell since the issue was filed
- **Action**: File a comment on CDK #2252 with the corrected findings

### Finding 2: cashu-cf's SIG_ALL message format tries 10 variants (MEDIUM)
cashu-cf tries 10 different SIG_ALL message formats for wallet compatibility. CDK and Nutshell each use a single canonical format. This is a pragmatic compatibility hack but could mask signature verification issues.

### Finding 3: CDK has 2 spec violations (LOW)
- Duplicate tags use first-match (NUT-11 L85 says MUST reject)
- n_sigs > pubkeys not validated on verification path (NUT-11 L87 says MUST reject)
Both are low-severity — the proof becomes unspendable via the affected path, just not rejected upfront.

### Finding 4: cashu-cf is the only impl that accepts witness on plain secrets (LOW)
Both CDK and Nutshell reject witnesses on non-NUT-10 secrets. cashu-cf silently ignores them. This is the most lenient behavior — not a security issue but a divergence.

## Updated cashu-cf Alignment

With corrected Nutshell behavior:

| # | Issue | CDK | Nutshell (corrected) | cashu-cf follows |
|---|---|---|---|---|
| 1 | Malformed secrets | anyone-can-spend | fail-closed (unknown kind) | **CDK** |
| 2 | Duplicate tags | first-match | first-match | **Neither** (cashu-cf now rejects — strictest) |
| 3 | n_sigs > pubkeys | not on verify path | at verify time | **Neither** (cashu-cf rejects upfront — strictest) |
| 4 | Empty pubkeys | accepted | accepted | All agree |
| 5 | HTLC hash case | mixed | mixed | **Neither** (cashu-cf enforces lowercase — strictest) |
| 6 | HTLC refund SIG_INPUTS | rejects | accepts | **Nutshell** |
| 7 | Duplicate sigs | errors | errors | All agree |
| 8 | Witness on plain | rejects | rejects | **Neither** (cashu-cf accepts — most lenient) |

**cashu-cf is the strictest on 3 items (2, 3, 5) and the most lenient on 1 item (8).**

## Recommendations

1. **File corrected findings on CDK #2252** — the Nutshell behavior characterizations need updating
2. **Consider aligning cashu-cf DIV-8** (witness on plain secret) with CDK/Nutshell — reject rather than accept
3. **Consider aligning CDK DIV-2 and DIV-3** — reject duplicate tags upfront, validate n_sigs at parse time
4. **Clarify NUT spec** for items 4, 7, 8 where behavior is unspecified or ambiguous
