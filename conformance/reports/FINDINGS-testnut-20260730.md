# Conformance Results — testnut.cashu.exchange (2026-07-30)

## Summary: 104 PASS / 0 FAIL / 3 SKIP (107 scenarios run)

**Zero failures.** All NUT compliance scenarios pass against testnut.cashu.exchange.

### Skipped (3 — environmental, not failures)
| Scenario | Reason |
|---|---|
| `invoice_description_truncated_quote_id` | FakeWallet dummy invoice not decodable |
| `fee_zero_ppk_swap_succeeds` | testnut charges fee_ppk=10, test requires 0 |
| `dleq_proof_absent_graceful` | testnut provides DLEQ — absent-case not applicable |

### Coverage by NUT
| NUT | Scenarios | Result |
|---|---|---|
| NUT-01/02 (Keys/Keysets) | 7 | ✅ All pass |
| NUT-03 (Swap) | 4 | ✅ All pass |
| NUT-04 (Mint Quote) | 6 | ✅ All pass (accounting fields verified) |
| NUT-05 (Melt) | 2 | ✅ All pass |
| NUT-07 (Checkstate) | 2 | ✅ All pass |
| NUT-08 (Fees) | 6 | ✅ All pass (fee_ppk=10 verified) |
| NUT-09 (Restore) | 2 | ✅ All pass |
| NUT-11 (P2PK SIG_INPUTS) | 14 | ✅ All pass |
| NUT-11 (P2PK SIG_ALL) | 16 | ✅ All pass |
| NUT-12 (DLEQ) | 5 | ✅ All pass |
| NUT-14 (HTLC) | 8 | ✅ All pass |
| NUT-14 (HTLC SIG_ALL) | 8 | ✅ All pass |
| NUT-13 (Deterministic) | 3 | ✅ All pass |
| NUT-18 (Payment Request) | 2 | ✅ All pass |
| NUT-20 (Quote Signature) | 4 | ✅ All pass |
| NUT-26 (Bech32m) | 2 | ✅ All pass |
| NUT-29 (Batch) | 3 | ✅ All pass |
| NUT-19 (Cached Endpoints) | 1 | ✅ All pass |
| NUT-06 (Mint Info) | 2 | ✅ All pass |
| Token V3/V4 | 2 | ✅ All pass |

### Delta from last run (2026-07-28)
Previous: 90 PASS / 3 FAIL / 1 SKIP
Current: 104 PASS / 0 FAIL / 3 SKIP

**Improvement: +14 passing scenarios, -3 failures.** All previously failing scenarios now pass.
