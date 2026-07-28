# Cashu Conformance Matrix — 2026-07-28 15:34 UTC

**Summary**: 58 passed, 11 failed, 0 skipped (69 total)

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

> ❌ `melt_p2pk_sigall_transaction_signature_succeeds` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'SIG_ALL verification failed: no candidate message verified', 'code': 30006}

> ❌ `melt_htlc_sigall_preimage_and_transaction_signature_succeeds` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'SIG_ALL verification failed: no candidate message verified', 'code': 30006}

> ❌ `melt_p2pk_post_locktime_anyone_can_spend` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'No witness in proof', 'code': 30006}

## NUT-11 P2PK SIG_ALL

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `p2pk_sigall_requires_transaction_signature` | ✅ |
| `p2pk_sigall_sig_inputs_fail` | ✅ |
| `p2pk_sigall_multisig_2of3` | ✅ |
| `p2pk_sigall_wrong_signer_fails` | ✅ |
| `p2pk_sigall_duplicate_signatures_fail` | ✅ |
| `p2pk_sigall_locktime_before_expiry_primary_only` | ✅ |
| `p2pk_sigall_locktime_after_expiry_primary_still_works` | ✅ |
| `p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend` | ❌ |
| `p2pk_sigall_multisig_locktime_primary_still_works` | ✅ |
| `p2pk_sigall_mixed_proofs_different_data_fail` | ✅ |
| `p2pk_sigall_mixed_proofs_different_kind_fail` | ✅ |
| `p2pk_sigall_mixed_proofs_different_tags_fail` | ✅ |
| `p2pk_sigall_multisig_before_locktime` | ✅ |
| `p2pk_sigall_more_signatures_than_required` | ✅ |
| `p2pk_sigall_refund_multisig_2of2` | ✅ |
| `p2pk_sigall_output_amounts_swapped_fail` | ❌ |

> ❌ `p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'No witness provided for SIG_ALL', 'code': 30006}

> ❌ `p2pk_sigall_output_amounts_swapped_fail` @ `https://testnut.cashu.exchange`: got 200

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
| `htlc_sigall_requires_preimage_and_transaction_signature` | ✅ |
| `htlc_sigall_wrong_preimage_fails` | ✅ |
| `htlc_sigall_locktime_after_expiry_refund_succeeds` | ❌ |
| `htlc_sigall_multisig_2of3` | ✅ |
| `htlc_sigall_receiver_path_after_locktime` | ✅ |

> ❌ `htlc_sigall_preimage_only_no_pubkeys_succeeds` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Invalid P2PK witness: missing signatures array', 'code': 30006}

> ❌ `htlc_sigall_locktime_after_expiry_refund_succeeds` @ `https://testnut.cashu.exchange`: got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold not met. 0 < 1', 'code': 30006}

## NUT-03 Swap Basics

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `swap_valid_proofs_succeeds` | ✅ |
| `swap_already_spent_fails` | ❌ |
| `swap_wrong_keyset_fails` | ✅ |

> ❌ `swap_already_spent_fails` @ `https://testnut.cashu.exchange`: got 422: {'error': 'token_already_spent', 'detail': 'Proof already spent: 024d240d314ae796...', 'code': 30001}

## NUT-04 Mint Quote Basics

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `mint_quote_creates_invoice` | ❌ |
| `mint_quote_zero_amount_fails` | ✅ |
| `mint_tokens_after_quote` | ✅ |

> ❌ `mint_quote_creates_invoice` @ `https://testnut.cashu.exchange`: missing BOLT11 or quote field: {'quote': '019fa95d-0d7d-7663-9383-63ac530eab57', 'request': 'dummy-mint-10-72920edc5dc0b9c077d8f48edd71297682ceaf4e13925b118d5e8fbb5d97f84e-exp1785252875', 'state': 'UNPAID', 'amount': 10, 'unit': 's

## NUT-05 Melt Basics

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `melt_quote_creates_quote` | ✅ |
| `melt_valid_proofs_succeeds` | ❌ |

> ❌ `melt_valid_proofs_succeeds` @ `https://testnut.cashu.exchange`: got 500: {'error': 'internal_error', 'detail': 'Melt operation failed: Not enough blank outputs (1) for change split (2)', 'code': 10000}

## NUT-07 Checkstate Basics

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `checkstate_unspent_returns_unspent` | ✅ |
| `checkstate_spent_returns_spent` | ✅ |

## NUT-09 Restore Basics

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `restore_returns_signatures` | ✅ |

## NUT-00 Token Format Basics

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `token_v3_parses` | ✅ |
| `token_v4_parses` | ✅ |

## NUT-19 Cache Basics

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `mint_info_nut19_supported` | ✅ |

## NUT-06 Mint Info Basics

| Scenario | `https://testnut.cashu.exchange` |
|---|---|
| `mint_info_returns_required_fields` | ✅ |
