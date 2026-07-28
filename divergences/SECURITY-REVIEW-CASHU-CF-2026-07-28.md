# Security Review Findings — cashu-cf (2026-07-28)

Source: Post-implementation security review of ISSUE-029–037 fixes.
Full report: [SECURITY-REVIEW-2026-07-28.md](https://github.com/Amperstrand/cashu-cf/blob/main/docs/security/SECURITY-REVIEW-2026-07-28.md)

## Summary

3-hunter parallel audit found 5 vulnerabilities in recently shipped spec compliance fixes.
All 5 were confirmed via PoC and fixed in commit `89f4c6a`.

## Findings

| # | Severity | Finding | CWE | Root Cause |
|---|----------|---------|-----|------------|
| H1 | CRITICAL | Batch mint double-mint race | CWE-367 | Batch path lacked `setMintQuoteIssuing` locking that non-batch path had |
| H2 | HIGH | Quote ID leaked in BOLT11 invoice | CWE-200 | Comment said truncate to 16 chars, code used full 36-char UUID |
| H3 | MEDIUM | No max outputs in batch mint → DoS | CWE-400 | Batch path omitted `maxMintOutputs` validation |
| H4 | MEDIUM | No batch limit on check endpoint → DoS | CWE-770 | Batch check lacked `MAX_BATCH_SIZE` |
| H5 | LOW | x-coord dedup bypass via `0x` prefix | CWE-345 | `getXCoordinate` didn't normalize hex before comparison |

## Pattern: Missing Validation Parity Between Code Paths

The most impactful finding (H1) was caused by the batch mint path not having the same
locking mechanism as the non-batch path. This is a common pattern: when adding a new
code path (batch), the developer copied the validation logic but missed the locking/reservation
layer that the original path had evolved over time.

**Recommendation**: When adding new API endpoints that perform the same core operation
as existing endpoints, audit for ALL layers of protection in the original path:
1. Input validation
2. Rate limiting / size limits
3. Atomic state reservations / locks
4. Idempotency mechanisms
5. Error rollback / cleanup

## Pattern: Code-Comment Mismatch

H2 was caused by a comment saying "use short 16-character ID" but the code using the
full value. The truncation was intended but never implemented.

**Recommendation**: Comments that describe security-relevant intent should be enforced
by code, not just documented. Consider linting rules or code review checklists that
verify security comments match implementation.
