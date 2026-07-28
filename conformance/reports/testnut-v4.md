# Cashu Conformance Matrix — 2026-07-28 08:11 UTC

**Summary**: 9 passed, 1 failed, 0 skipped (10 total)

## NUT-11 P2PK SIG_INPUTS

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `p2pk_swap_unsigned_fails` | ✅ |
| `p2pk_swap_signed_succeeds` | ✅ |
| `p2pk_wrong_signer_fails` | ✅ |
| `p2pk_locktime_after_expiry_primary_still_works` | ❌ |
| `p2pk_locktime_after_expiry_refund_succeeds` | ✅ |
| `p2pk_multisig_2of3` | ✅ |
| `p2pk_partial_signatures_fail` | ✅ |
| `p2pk_duplicate_signatures_fail` | ✅ |
| `p2pk_locktime_before_expiry_refund_blocked` | ✅ |
| `p2pk_locktime_after_expiry_no_refund_anyone_can_spend` | ✅ |

> ❌ `p2pk_locktime_after_expiry_primary_still_works` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold not met. 0 < 1', 'code': 30006}
