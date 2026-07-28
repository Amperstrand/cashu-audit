# Conformance Results — testnut.cashu.exchange (2026-07-28 Final)

## Summary: 90 PASS / 3 FAIL / 1 SKIP (94 scenarios run)

All failures require ISSUE-044 deployment (anyone-can-spend fix).

## New Scenarios (13 — all pass except 1 skip)

| NUT | Scenario | Result |
|-----|----------|--------|
| NUT-04 | mint_quote_has_accounting_fields | ✅ amount_paid, amount_issued, updated_at present |
| NUT-04 | mint_quote_uuid_v7 | ✅ UUID v7 format confirmed |
| NUT-04 | mint_quote_accounting_after_payment | ✅ amount_paid=8 after settlement |
| NUT-04 | mint_quote_accounting_after_mint | ✅ amount_issued=8 after mint |
| NUT-04 | mint_quote_updated_at_monotonic | ✅ timestamps increase |
| NUT-20 | nut20_locked_quote_requires_signature | ✅ rejected without sig |
| NUT-20 | nut20_locked_quote_valid_signature_succeeds | ✅ **NUT-20 sig format works!** |
| NUT-20 | nut20_locked_quote_wrong_signature_fails | ✅ wrong sig rejected |
| NUT-20 | nut20_quote_echoes_pubkey | ✅ pubkey echoed |
| NUT-29 | batch_check_returns_quotes | ✅ returns states |
| NUT-29 | batch_check_rejects_too_many | ✅ batch_too_large for >50 |
| NUT-29 | batch_mint_rejects_too_many_outputs | ✅ too_many_outputs for >1000 |
| Invoice | invoice_description_truncated_quote_id | ⏭️ FakeWallet dummy invoice |

## Remaining Failures (3 — all ISSUE-044)

| Scenario | Error | Fix |
|----------|-------|-----|
| melt_p2pk_post_locktime_anyone_can_spend | "No witness in proof" | ISSUE-044 fixed in `674b8a3`, needs deploy |
| p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend | "No witness provided" | Same fix |
| p2pk_locktime_after_expiry_no_refund_anyone_can_spend | "No witness in proof" | Same fix |

## Coverage

| NUT | Scenarios | Pass | Fail | Skip |
|-----|-----------|------|------|------|
| NUT-01/06 | 6 | 6 | 0 | 0 |
| NUT-02 | 6 | 6 | 0 | 0 |
| NUT-03 | 3 | 3 | 0 | 0 |
| NUT-04 | 7 | 7 | 0 | 0 |
| NUT-05 | 3 | 3 | 0 | 0 |
| NUT-07 | 2 | 2 | 0 | 0 |
| NUT-08 | 6 | 5 | 0 | 1 |
| NUT-09 | 1 | 1 | 0 | 0 |
| NUT-11 | 38 | 35 | 3 | 0 |
| NUT-12/DLEQ | 4 | 4 | 0 | 0 |
| NUT-14 | 16 | 16 | 0 | 0 |
| NUT-19 | 1 | 1 | 0 | 0 |
| NUT-20 | 4 | 4 | 0 | 0 |
| NUT-29 | 3 | 3 | 0 | 0 |
| Invoice | 1 | 0 | 0 | 1 |
| **Total** | **98** | **90** | **3** | **1** |

## Key Wins
1. **NUT-20 signature format works** — our binary domain-separated format matches what wallets produce
2. **NUT-04 accounting fields correct** — amount_paid, amount_issued, updated_at all present and accurate
3. **UUID v7 quote IDs confirmed** — deployed and generating correct format
4. **Batch limits enforced** — NUT-29 size limits working
5. **98 total conformance scenarios** — comprehensive coverage across 14 NUT categories
