# Cashu Conformance Matrix — 2026-11-04 00:44 UTC

**Targets** (identity captured at run start):
- `http://127.0.0.1:4430` — gonuts-sigall-branch / gonuts/0.4.0

**Summary**: 120 passed, 3 failed, 5 skipped (128 total)

## Invoice Description

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `invoice_description_truncated_quote_id` | ⏭️ |

## NUT-00 error identity

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `errid_swap_unknown_keyset_code_12001` | ✅ |
| `errid_swap_duplicate_inputs_code_11007` | ✅ |
| `errid_swap_underfunded_code_11005` | ❌ |
| `errid_swap_spent_proofs_code_11001` | ✅ |
| `errid_swap_outputs_already_signed_code_11003` | ❌ |
| `errid_mint_quote_unit_unsupported_code_11013` | ❌ |
| `errid_validation_error_nut00_envelope` | ✅ |
| `errid_p2pk_wrong_witness_reasoned_rejection` | ✅ |

> ❌ `errid_swap_underfunded_code_11005` @ `http://127.0.0.1:4430`: want 11005, got http=400 code=11002: code=11002 detail='amount of input proofs is below amount needed for transaction'

> ❌ `errid_swap_outputs_already_signed_code_11003` @ `http://127.0.0.1:4430`: want 11003, got http=400 code=10002: code=10002 detail='blinded message already signed'

> ❌ `errid_mint_quote_unit_unsupported_code_11013` @ `http://127.0.0.1:4430`: want 11013, got http=400 code=11005: code=11005 detail="unit 'usd' not supported"

## NUT-00 Secret Encoding

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `secret_encoding_control_spendable` | ✅ |
| `secret_encoding_entropy_trap_rejected` | ✅ |
| `secret_encoding_forged_c_rejected` | ✅ |

## NUT-02 Keysets

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `keysets_returns_active_keyset` | ✅ |
| `keys_returns_pubkey_for_amount` | ✅ |
| `keyset_has_correct_unit` | ✅ |
| `keyset_fee_ppk_present` | ✅ |
| `multiple_keysets_unit_filter` | ✅ |
| `keyset_keys_are_valid_pubkeys` | ✅ |

## NUT-04 Accounting

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `mint_quote_has_accounting_fields` | ✅ |
| `mint_quote_uuid_v7` | ✅ |
| `mint_quote_accounting_after_payment` | ✅ |
| `mint_quote_accounting_after_mint` | ✅ |
| `mint_quote_updated_at_monotonic` | ✅ |

## NUT-08 Fees

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `fee_zero_ppk_swap_succeeds` | ✅ |
| `fee_calculated_correctly` | ✅ |
| `fee_insufficient_outputs_fails` | ✅ |
| `fee_exact_balance_succeeds` | ✅ |
| `fee_melt_quote_includes_fee_reserve` | ✅ |
| `fee_per_proof_not_per_amount` | ⏭️ |

## Melt spending conditions

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `melt_p2pk_unsigned_fails` | ✅ |
| `melt_p2pk_signed_succeeds` | ✅ |
| `melt_p2pk_sigall_unsigned_fails` | ✅ |
| `melt_p2pk_sigall_transaction_signature_succeeds` | ✅ |
| `melt_htlc_preimage_only_no_pubkeys_succeeds` | ✅ |
| `melt_htlc_preimage_only_fails` | ✅ |
| `melt_htlc_signature_only_fails` | ✅ |
| `melt_htlc_preimage_and_signature_succeeds` | ✅ |
| `melt_htlc_sigall_preimage_and_transaction_signature_succeeds` | ✅ |
| `melt_p2pk_post_locktime_anyone_can_spend` | ✅ |
| `melt_p2pk_before_locktime_wrong_key_fails` | ✅ |
| `melt_p2pk_before_locktime_correct_key_succeeds` | ✅ |

## NUT-11 P2PK SIG_ALL

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `p2pk_sigall_requires_transaction_signature` | ✅ |
| `p2pk_sigall_sig_inputs_fail` | ✅ |
| `p2pk_sigall_multisig_2of3` | ✅ |
| `p2pk_sigall_wrong_signer_fails` | ✅ |
| `p2pk_sigall_duplicate_signatures_fail` | ✅ |
| `p2pk_sigall_locktime_before_expiry_primary_only` | ✅ |
| `p2pk_sigall_locktime_after_expiry_primary_still_works` | ✅ |
| `p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend` | ✅ |
| `p2pk_sigall_multisig_locktime_primary_still_works` | ✅ |
| `p2pk_sigall_mixed_proofs_different_data_fail` | ✅ |
| `p2pk_sigall_mixed_proofs_different_kind_fail` | ✅ |
| `p2pk_sigall_mixed_proofs_different_tags_fail` | ✅ |
| `p2pk_sigall_multisig_before_locktime` | ✅ |
| `p2pk_sigall_more_signatures_than_required` | ✅ |
| `p2pk_sigall_refund_multisig_2of2` | ✅ |
| `p2pk_sigall_output_amounts_swapped_fail` | ✅ |

## NUT-11 P2PK SIG_INPUTS

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
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
| `p2pk_locktime_after_expiry_no_refund_anyone_can_spend` | ✅ |

## NUT-12 DLEQ

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `dleq_proofs_present_in_mint_response` | ✅ |
| `dleq_proof_valid` | ✅ |
| `dleq_proof_absent_graceful` | ⏭️ |
| `dleq_proof_in_signature_response` | ✅ |
| `dleq_invalid_proof_rejected` | ✅ |
| `dleq_proof_in_restore_response` | ✅ |
| `hash_e_test_vector_verification` | ✅ |

## NUT-12 HTLC SIG_INPUTS

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
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

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `htlc_sigall_preimage_only_no_pubkeys_succeeds` | ✅ |
| `htlc_sigall_preimage_only_fails` | ✅ |
| `htlc_sigall_signature_only_fails` | ✅ |
| `htlc_sigall_requires_preimage_and_transaction_signature` | ✅ |
| `htlc_sigall_wrong_preimage_fails` | ✅ |
| `htlc_sigall_locktime_after_expiry_refund_succeeds` | ✅ |
| `htlc_sigall_multisig_2of3` | ✅ |
| `htlc_sigall_receiver_path_after_locktime` | ✅ |

## NUT-13 Deterministic Secrets

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `nut13_keyset_id_integer` | ✅ |
| `nut13_secret_derivation` | ✅ |
| `nut13_restore_works` | ✅ |

## NUT-17 Websocket

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `ws_mint_quote_subscribe_initial_state` | ✅ |
| `ws_mint_quote_unsubscribe_ok` | ✅ |
| `ws_mint_quote_unknown_quote_rejected` | ✅ |

## NUT-18 Payment Request

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `nut18_payment_request_decode` | ✅ |
| `nut18_payment_request_amount` | ✅ |

## NUT-20 Quote Sig

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `nut20_locked_quote_requires_signature` | ✅ |
| `nut20_locked_quote_valid_signature_succeeds` | ✅ |
| `nut20_locked_quote_wrong_signature_fails` | ✅ |
| `nut20_quote_echoes_pubkey` | ✅ |

## NUT-26 Bech32m

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `nut26_encode_token_v4` | ✅ |
| `nut26_decode_token_v4` | ✅ |

## NUT-29 Batch Ops

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `batch_check_returns_quotes` | ✅ |
| `batch_check_rejects_too_many` | ⏭️ |
| `batch_mint_rejects_too_many_outputs` | ⏭️ |

## NUT-03 Swap Basics

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `swap_valid_proofs_succeeds` | ✅ |
| `swap_already_spent_fails` | ✅ |
| `swap_wrong_keyset_fails` | ✅ |

## NUT-04 Mint Quote Basics

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `mint_quote_creates_invoice` | ✅ |
| `mint_quote_zero_amount_fails` | ✅ |
| `mint_tokens_after_quote` | ✅ |

## NUT-05 Melt Basics

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `melt_quote_creates_quote` | ✅ |
| `melt_valid_proofs_succeeds` | ✅ |

## NUT-07 Checkstate Basics

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `checkstate_unspent_returns_unspent` | ✅ |
| `checkstate_spent_returns_spent` | ✅ |

## NUT-09 Restore Basics

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `restore_returns_signatures` | ✅ |

## NUT-00 Token Format Basics

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `token_v3_parses` | ✅ |
| `token_v4_parses` | ✅ |

## NUT-19 Cache Basics

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `mint_info_nut19_supported` | ✅ |

## NUT-06 Mint Info Basics

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `mint_info_returns_required_fields` | ✅ |

## NUT-03 Keyless Amounts

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `swap_never_signs_keyless_amount` | ✅ |
| `mint_never_signs_keyless_amount` | ✅ |

## NUT-19 Replay Caching

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `swap_replay_returns_cached_response` | ✅ |
| `melt_replay_returns_cached_response` | ✅ |

## Security: Concurrency

| Scenario | `gonuts-sigall-branch@gonuts/0.4.0` |
|---|---|
| `concurrent_double_melt_rejected` | ✅ |
| `sequential_double_melt_rejected` | ✅ |
