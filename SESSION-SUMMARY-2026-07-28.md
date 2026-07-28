# Session Summary — 2026-07-28

## Overview

Comprehensive Cashu spec compliance, security audit, and cross-implementation
conformance testing session across cashu-cf and cashu-audit.

## Key Metrics

| Metric | Start | End | Delta |
|--------|-------|-----|-------|
| cashu-cf issues resolved | 0 | 14 | +14 |
| Security vulnerabilities fixed | 0 | 5 | +5 |
| Conformance scenarios | 0 | 100 | +100 |
| Official test vector tests | 0 | 29 | +29 |
| Unit tests passing | 1409 | 1547+ | +138+ |
| Conformance pass rate | N/A | 97% | 97/100 |

## Spec Compliance Fixes (ISSUE-029–044)

| Issue | NUT | Description | Priority |
|-------|-----|-------------|----------|
| 029 | NUT-04 | Accounting fields (amount_paid, amount_issued, updated_at) | P0 |
| 030 | NUT-11 | P2PK sigflag rejection, x-coord dedup, locktime dual-pathway | P0 |
| 031 | NUT-14 | HTLC preimage optional, receiver always, sender after locktime | P0 |
| 032 | NUT-29 | Batch validation (10 gaps: method, size, sigs, expiry, unit) | P1 |
| 033 | NUT-20 | Quote signature binary format (domain separator + len32) | P0 |
| 034 | NUT-05 | UUID v7 quote IDs + melt response method field | P1 |
| 035 | NUT-07 | Witness field in checkstate for spent proofs | P2 |
| 036 | NUT-10 | Witness rejection on non-conditioned proofs | P2 |
| 037 | NUT-00 | V4 token URL trailing slash normalization | P2 |
| 038 | CRUD | Dual-write consistency (KV/SQL state mismatch) | P1 |
| 039 | NUT-04 | Partial mint amount_issued persistence | P2 |
| 040 | Deps | Deprecated uuid@10 → uuid@14 upgrade | P2 |
| 041 | Security | Private key prefix in debug logs → [REDACTED] | P2 |
| 042 | Security | Raw error messages in API responses sanitized | P2 |
| 043 | NUT-11 | SIG_ALL mode detection (conformance test fix) | P1 |
| 044 | NUT-11 | Anyone-can-spend after locktime without witness | P1 |

## Security Vulnerabilities (H1–H5)

| # | Severity | Finding | CWE |
|---|----------|---------|-----|
| H1 | CRITICAL | Batch mint double-mint race (no locking) | CWE-367 |
| H2 | HIGH | Full quote ID in BOLT11 invoice description | CWE-200 |
| H3 | MEDIUM | No max outputs in batch mint (DoS) | CWE-400 |
| H4 | MEDIUM | No batch size on check endpoint (DoS) | CWE-770 |
| H5 | LOW | x-coord dedup bypass via 0x prefix | CWE-345 |

## Conformance Suite (cashu-audit)

100 scenarios across 14 NUT categories:

| NUT | Scenarios | Status |
|-----|-----------|--------|
| NUT-01/06 | 6 | ✅ |
| NUT-02 | 6 | ✅ |
| NUT-03 | 3 | ✅ |
| NUT-04 | 7 | ✅ |
| NUT-05 | 3 | ✅ |
| NUT-07 | 2 | ✅ |
| NUT-08 | 6 | ✅ (1 skip: fee_ppk) |
| NUT-09 | 1 | ✅ |
| NUT-11 | 38 | ✅ |
| NUT-12/DLEQ | 6 | ✅ (1 skip: DLEQ absent) |
| NUT-14 | 16 | ✅ |
| NUT-19 | 1 | ✅ |
| NUT-20 | 4 | ✅ |
| NUT-29 | 3 | ✅ |
| Invoice | 1 | ⏭️ (skip: dummy invoice) |
| **Total** | **100** | **97 PASS / 0 FAIL / 3 SKIP** |

## Cross-Implementation Testing

- Framework supports any Cashu mint via `--mint URL`
- Nutshell + CDK Docker setup documented
- 8 known divergences catalogued
- Comparison matrix generation automated

## Deployment Status

testnut.cashu.exchange deployed with latest fixes.
**Needs final redeployment** for commit `e7d0d70` (SIG_ALL anyone-can-spend fix).
