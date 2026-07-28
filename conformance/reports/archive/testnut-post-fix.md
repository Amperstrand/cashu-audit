# Cashu Conformance Matrix — 2026-07-28 14:48 UTC

**Summary**: 37 passed, 17 failed, 0 skipped (54 total)

## Melt spending conditions

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `melt_p2pk_unsigned_fails` | ✅ |
| `melt_p2pk_signed_succeeds` | ✅ |
| `melt_p2pk_sigall_unsigned_fails` | ✅ |
| `melt_p2pk_sigall_transaction_signature_succeeds` | ❌ |
| `melt_htlc_preimage_only_no_pubkeys_succeeds` | ✅ |
| `melt_htlc_preimage_only_fails` | ✅ |
| `melt_htlc_signature_only_fails` | ✅ |
| `melt_htlc_preimage_and_signature_succeeds` | ✅ |
| `melt_htlc_sigall_preimage_and_transaction_signature_succeeds` | ❌ |
| `melt_p2pk_post_locktime_anyone_can_spend` | ❌ |
| `melt_p2pk_before_locktime_wrong_key_fails` | ✅ |
| `melt_p2pk_before_locktime_correct_key_succeeds` | ✅ |

> ❌ `melt_p2pk_sigall_transaction_signature_succeeds` @ `https://testnut.cashu.exchange`: got 500: {'error': 'internal_error', 'detail': 'Melt operation failed: candidateMessages is not defined', 'code': 10000}

> ❌ `melt_htlc_sigall_preimage_and_transaction_signature_succeeds` @ `https://testnut.cashu.exchange`: got 500: {'error': 'internal_error', 'detail': 'Melt operation failed: candidateMessages is not defined', 'code': 10000}

> ❌ `melt_p2pk_post_locktime_anyone_can_spend` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'No witness in proof', 'code': 30006}

## NUT-11 P2PK SIG_ALL

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `p2pk_sigall_requires_transaction_signature` | ✅ |
| `p2pk_sigall_sig_inputs_fail` | ✅ |
| `p2pk_sigall_multisig_2of3` | ❌ |
| `p2pk_sigall_wrong_signer_fails` | ✅ |
| `p2pk_sigall_duplicate_signatures_fail` | ✅ |
| `p2pk_sigall_locktime_before_expiry_primary_only` | ❌ |
| `p2pk_sigall_locktime_after_expiry_primary_still_works` | ❌ |
| `p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend` | ❌ |
| `p2pk_sigall_multisig_locktime_primary_still_works` | ❌ |
| `p2pk_sigall_mixed_proofs_different_data_fail` | ✅ |
| `p2pk_sigall_mixed_proofs_different_kind_fail` | ✅ |
| `p2pk_sigall_mixed_proofs_different_tags_fail` | ✅ |
| `p2pk_sigall_multisig_before_locktime` | ❌ |
| `p2pk_sigall_more_signatures_than_required` | ❌ |
| `p2pk_sigall_refund_multisig_2of2` | ❌ |
| `p2pk_sigall_output_amounts_swapped_fail` | ✅ |

> ❌ `p2pk_sigall_multisig_2of3` @ `https://testnut.cashu.exchange`: got 400: {'error': 'invalid_request', 'detail': 'candidateMessages is not defined', 'code': 14005}

> ❌ `p2pk_sigall_locktime_before_expiry_primary_only` @ `https://testnut.cashu.exchange`: primary failed: 400

> ❌ `p2pk_sigall_locktime_after_expiry_primary_still_works` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Locktime expired: SIG_ALL verification failed for both pathways', 'code': 30006}

> ❌ `p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'No witness provided for SIG_ALL', 'code': 30006}

> ❌ `p2pk_sigall_multisig_locktime_primary_still_works` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Locktime expired: SIG_ALL verification failed for both pathways', 'code': 30006}

> ❌ `p2pk_sigall_multisig_before_locktime` @ `https://testnut.cashu.exchange`: got 400: {'error': 'invalid_request', 'detail': 'candidateMessages is not defined', 'code': 14005}

> ❌ `p2pk_sigall_more_signatures_than_required` @ `https://testnut.cashu.exchange`: got 400: {'error': 'invalid_request', 'detail': 'candidateMessages is not defined', 'code': 14005}

> ❌ `p2pk_sigall_refund_multisig_2of2` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Locktime expired: SIG_ALL verification failed for both pathways', 'code': 30006}

## NUT-11 P2PK SIG_INPUTS

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `p2pk_swap_unsigned_fails` | ✅ |
| `p2pk_swap_signed_succeeds` | ✅ |
| `p2pk_wrong_signer_fails` | ✅ |
| `p2pk_locktime_after_expiry_primary_still_works` | ✅ |
| `p2pk_locktime_after_expiry_refund_succeeds` | ✅ |
| `p2pk_multisig_2of3` | ✅ |
| `p2pk_partial_signatures_fail` | ✅ |
| `p2pk_duplicate_signatures_fail` | ✅ |
| `p2pk_locktime_before_expiry_refund_blocked` | ✅ |
| `p2pk_locktime_after_expiry_no_refund_anyone_can_spend` | ❌ |

> ❌ `p2pk_locktime_after_expiry_no_refund_anyone_can_spend` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'No witness in proof', 'code': 30006}

## NUT-12 HTLC SIG_INPUTS

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `htlc_preimage_only_no_pubkeys_succeeds` | ✅ |
| `htlc_preimage_only_fails` | ✅ |
| `htlc_signature_only_fails` | ✅ |
| `htlc_swap_preimage_and_signature_succeeds` | ✅ |
| `htlc_wrong_preimage_fails` | ✅ |
| `htlc_locktime_after_expiry_refund_succeeds` | ✅ |
| `htlc_multisig_2of3` | ✅ |
| `htlc_receiver_path_after_locktime` | ✅ |

## NUT-12 HTLC SIG_ALL

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `htlc_sigall_preimage_only_no_pubkeys_succeeds` | ❌ |
| `htlc_sigall_preimage_only_fails` | ✅ |
| `htlc_sigall_signature_only_fails` | ✅ |
| `htlc_sigall_requires_preimage_and_transaction_signature` | ❌ |
| `htlc_sigall_wrong_preimage_fails` | ✅ |
| `htlc_sigall_locktime_after_expiry_refund_succeeds` | ❌ |
| `htlc_sigall_multisig_2of3` | ❌ |
| `htlc_sigall_receiver_path_after_locktime` | ❌ |

> ❌ `htlc_sigall_preimage_only_no_pubkeys_succeeds` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Invalid P2PK witness: missing signatures array', 'code': 30006}

> ❌ `htlc_sigall_requires_preimage_and_transaction_signature` @ `https://testnut.cashu.exchange`: got 400: {'error': 'invalid_request', 'detail': 'candidateMessages is not defined', 'code': 14005}

> ❌ `htlc_sigall_locktime_after_expiry_refund_succeeds` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Locktime expired: SIG_ALL verification failed for both pathways', 'code': 30006}

> ❌ `htlc_sigall_multisig_2of3` @ `https://testnut.cashu.exchange`: got 400: {'error': 'invalid_request', 'detail': 'candidateMessages is not defined', 'code': 14005}

> ❌ `htlc_sigall_receiver_path_after_locktime` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Locktime expired: SIG_ALL verification failed for both pathways', 'code': 30006}
