# Cashu Conformance Matrix — 2026-07-28 08:24 UTC

**Summary**: 23 passed, 3 failed, 0 skipped (26 total)

## NUT-11 P2PK SIG_ALL

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `p2pk_sigall_requires_transaction_signature` | ✅ |
| `p2pk_sigall_sig_inputs_fail` | ✅ |
| `p2pk_sigall_multisig_2of3` | ✅ |
| `p2pk_sigall_wrong_signer_fails` | ✅ |
| `p2pk_sigall_duplicate_signatures_fail` | ✅ |
| `p2pk_sigall_locktime_before_expiry_primary_only` | ✅ |
| `p2pk_sigall_locktime_after_expiry_primary_still_works` | ❌ |
| `p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend` | ✅ |
| `p2pk_sigall_multisig_locktime_primary_still_works` | ❌ |
| `p2pk_sigall_mixed_proofs_different_data_fail` | ✅ |
| `p2pk_sigall_mixed_proofs_different_kind_fail` | ✅ |
| `p2pk_sigall_mixed_proofs_different_tags_fail` | ✅ |
| `p2pk_sigall_multisig_before_locktime` | ✅ |
| `p2pk_sigall_more_signatures_than_required` | ✅ |
| `p2pk_sigall_refund_multisig_2of2` | ✅ |
| `p2pk_sigall_output_amounts_swapped_fail` | ✅ |

> ❌ `p2pk_sigall_locktime_after_expiry_primary_still_works` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold not met. 0 < 1', 'code': 30006}

> ❌ `p2pk_sigall_multisig_locktime_primary_still_works` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold not met. 0 < 1', 'code': 30006}

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
