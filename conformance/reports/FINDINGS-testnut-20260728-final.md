# Conformance Findings — testnut.cashu.exchange (2026-07-28)

## Summary

**78 PASS / 3 FAIL / 1 SKIP** (81 scenarios + new scenarios pending)

## Failures (3 — all require ISSUE-044 redeployment)

| # | Scenario | Error | Fix |
|---|----------|-------|-----|
| 1 | `melt_p2pk_post_locktime_anyone_can_spend` | "No witness in proof" | ISSUE-044 — fixed in `674b8a3`, needs deploy |
| 2 | `p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend` | "No witness provided" | ISSUE-044 — same fix |
| 3 | `p2pk_locktime_after_expiry_no_refund_anyone_can_spend` | "No witness in proof" | ISSUE-044 — same fix |

All 3 are the same root cause: after locktime expiry with no refund keys, proofs should be
anyone-can-spend but the mint requires a witness. Fix committed but not yet deployed.

## Resolved (2 — fixed in this session)

| # | Scenario | Was | Now | Fix |
|---|----------|-----|-----|-----|
| 1 | `melt_p2pk_sigall_transaction_signature_succeeds` | ❌ | ✅ | Conformance mode detection fix (`935d255`) |
| 2 | `melt_htlc_sigall_preimage_and_transaction_signature_succeeds` | ❌ | ✅ | Same fix |

Root cause: conformance test detected "nutshell" in version string and used legacy SIG_ALL
message format. cashu-cf version is "Nutshell-CF/0.0.1" which is NOT the Python Nutshell.

## Coverage by NUT

| NUT | Scenarios | Status |
|-----|-----------|--------|
| NUT-01/06 | 6 | ✅ All pass |
| NUT-02 | 6 | ✅ All pass |
| NUT-03 | 3 | ✅ All pass |
| NUT-04 | 2 | ✅ Pass (more scenarios pending) |
| NUT-05 | 3 | ✅ All pass |
| NUT-07 | 2 | ✅ All pass |
| NUT-08 | 6 | ✅ All pass (1 skip: fee_ppk≠0) |
| NUT-09 | 1 | ✅ Pass |
| NUT-11 P2PK | 20+ | ✅ All pass (3 anyone-can-spend need deploy) |
| NUT-14 HTLC | 10+ | ✅ All pass |
| NUT-19 | 1 | ✅ Pass |
| NUT-20 | 0 | Pending (new scenarios being added) |
| NUT-29 | 0 | Pending (new scenarios being added) |
