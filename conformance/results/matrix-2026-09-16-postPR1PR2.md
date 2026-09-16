# Cashu Conformance Matrix — 2026-09-16 21:11 UTC

**Summary**: 189 passed, 15 failed, 20 skipped (224 total)

## Invoice Description

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `invoice_description_truncated_quote_id` | ⏭️ | ⏭️ |

## NUT-00 Secret Encoding

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `secret_encoding_control_spendable` | ⏭️ | ✅ |
| `secret_encoding_entropy_trap_rejected` | ⏭️ | ❌ |
| `secret_encoding_forged_c_rejected` | ✅ | ✅ |

> ❌ `secret_encoding_entropy_trap_rejected` @ `https://testnut.cashu.exchange`: MINT ACCEPTED entropy-blinded proof: lenient at the NUT-00 verification boundary (would mask buggy wallets)

## NUT-02 Keysets

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `keysets_returns_active_keyset` | ✅ | ✅ |
| `keys_returns_pubkey_for_amount` | ✅ | ✅ |
| `keyset_has_correct_unit` | ✅ | ✅ |
| `keyset_fee_ppk_present` | ✅ | ✅ |
| `multiple_keysets_unit_filter` | ✅ | ✅ |
| `keyset_keys_are_valid_pubkeys` | ✅ | ✅ |

## NUT-04 Accounting

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `mint_quote_has_accounting_fields` | ✅ | ✅ |
| `mint_quote_uuid_v7` | ✅ | ✅ |
| `mint_quote_accounting_after_payment` | ✅ | ✅ |
| `mint_quote_accounting_after_mint` | ⏭️ | ✅ |
| `mint_quote_updated_at_monotonic` | ⏭️ | ✅ |

## NUT-08 Fees

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `fee_zero_ppk_swap_succeeds` | ✅ | ⏭️ |
| `fee_calculated_correctly` | ✅ | ✅ |
| `fee_insufficient_outputs_fails` | ✅ | ✅ |
| `fee_exact_balance_succeeds` | ✅ | ✅ |
| `fee_melt_quote_includes_fee_reserve` | ✅ | ✅ |
| `fee_per_proof_not_per_amount` | ⏭️ | ✅ |

## Melt spending conditions

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `melt_p2pk_unsigned_fails` | ❌ | ❌ |
| `melt_p2pk_signed_succeeds` | ✅ | ✅ |
| `melt_p2pk_sigall_unsigned_fails` | ❌ | ❌ |
| `melt_p2pk_sigall_transaction_signature_succeeds` | ❌ | ✅ |
| `melt_htlc_preimage_only_no_pubkeys_succeeds` | ✅ | ✅ |
| `melt_htlc_preimage_only_fails` | ❌ | ❌ |
| `melt_htlc_signature_only_fails` | ❌ | ❌ |
| `melt_htlc_preimage_and_signature_succeeds` | ✅ | ✅ |
| `melt_htlc_sigall_preimage_and_transaction_signature_succeeds` | ❌ | ✅ |
| `melt_p2pk_post_locktime_anyone_can_spend` | ✅ | ✅ |
| `melt_p2pk_before_locktime_wrong_key_fails` | ❌ | ❌ |
| `melt_p2pk_before_locktime_correct_key_succeeds` | ✅ | ✅ |

> ❌ `melt_p2pk_unsigned_fails` @ `https://signut.cashu.exchange`: got 200: {'quote': '01a0abfe-6bed-72a8-8410-c0283385390b', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lntbs40n1p42kqdysp5gwxeqvrzmk6wvaqj6kn7pjjj6frgn2p34pe87egz3sk3ce02fr6spp589pz0f6cykjt8ytr

> ❌ `melt_p2pk_unsigned_fails` @ `https://testnut.cashu.exchange`: got 200: {'quote': '01a0ac0c-4eb1-7531-a900-a2eae50021ab', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lnbc40n1qyqqqqqyd59l6k2982sgfj5khdrvecsjys7cqkcmthlzduxq8md7s8w4nh5x42c9xgwwt4us', 'fee_re

> ❌ `melt_p2pk_sigall_unsigned_fails` @ `https://signut.cashu.exchange`: got 200: {'quote': '01a0abfe-d1aa-710d-acb1-1c4c4f4eb5c6', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lntbs40n1p42kqd7sp55uvx2q7jprtzddu09205zcqef7jv4w3xradsry33604wwm7pjl0qpp5npucqqfr8csupzpz

> ❌ `melt_p2pk_sigall_unsigned_fails` @ `https://testnut.cashu.exchange`: got 200: {'quote': '01a0ac0c-8004-7748-95ef-6ec6242dd203', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lnbc40n1qyqqqqqyq0n5dry5aqye3mjhxt94jqfg62wtwng3x4us8d2cylwzu7ajv9ux42c98uravzww', 'fee_re

> ❌ `melt_p2pk_sigall_transaction_signature_succeeds` @ `https://signut.cashu.exchange`: got 400: {'error': 'payment_failed', 'detail': "HTTP status: 500 Destination said it doesn't know invoice: Malformed error reply", 'code': '10000'}

> ❌ `melt_htlc_preimage_only_fails` @ `https://signut.cashu.exchange`: got 200: {'quote': '01a0abff-37a9-76b6-b3c8-4b733294375d', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lntbs40n1p42kqwcsp50egugrmkf7ae74kflnpzgeygw6nlw93cf7ump827wzs642nlx43qpp5dngd9jut66nkv0vn

> ❌ `melt_htlc_preimage_only_fails` @ `https://testnut.cashu.exchange`: got 200: {'quote': '01a0ac0c-c155-727d-bf81-071fb20df1de', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lnbc40n1qyqqqqqyzp2ygp9jcxnymp8yhq5nw5kgjyhjjyhtkzdem46n6jnx4gqr4wsk42c9furxmpgx', 'fee_re

> ❌ `melt_htlc_signature_only_fails` @ `https://signut.cashu.exchange`: got 200: {'quote': '01a0abff-6256-775e-be75-8648e11d8a95', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lntbs40n1p42kq0rsp5xa8t7jfmw28zg2em9q4lymyluyc4z533ltvyxf9lsy7mh3zdh57qpp5m0n9w29e3ed2za2v

> ❌ `melt_htlc_signature_only_fails` @ `https://testnut.cashu.exchange`: got 200: {'quote': '01a0ac0c-d0e0-7098-83a0-a49604175b17', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lnbc40n1qyqqqqqy9apqnud6np80t4gkdj0shlfnf5anfsf6fs7z0ghwr92r2kuyddnx42c92vxejp72', 'fee_re

> ❌ `melt_htlc_sigall_preimage_and_transaction_signature_succeeds` @ `https://signut.cashu.exchange`: got 400: {'error': 'payment_failed', 'detail': "HTTP status: 500 Destination said it doesn't know invoice: Malformed error reply", 'code': '10000'}

> ❌ `melt_p2pk_before_locktime_wrong_key_fails` @ `https://signut.cashu.exchange`: got 200: {'quote': '01a0abff-dde9-71e3-a930-5ff0c9030699', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lntbs40n1p42kqsrsp5d2sz59etekgharttrpd0me26jrg0hpgw5mg5yavludmtdzfcez2spp50wcthnn7mp73kr2h

> ❌ `melt_p2pk_before_locktime_wrong_key_fails` @ `https://testnut.cashu.exchange`: got 200: {'quote': '01a0ac0d-319d-7618-b0b9-424589c6e3b0', 'amount': 4, 'unit': 'sat', 'method': 'bolt11', 'request': 'lnbc40n1qyqqqqqy9scjgc4s6wa9znsn58plpy2wjsme3llj2gy472tjzslvrul7wmsx42c9dsckzm85', 'fee_re

## NUT-11 P2PK SIG_ALL

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `p2pk_sigall_requires_transaction_signature` | ✅ | ✅ |
| `p2pk_sigall_sig_inputs_fail` | ✅ | ✅ |
| `p2pk_sigall_multisig_2of3` | ✅ | ✅ |
| `p2pk_sigall_wrong_signer_fails` | ✅ | ✅ |
| `p2pk_sigall_duplicate_signatures_fail` | ✅ | ✅ |
| `p2pk_sigall_locktime_before_expiry_primary_only` | ✅ | ✅ |
| `p2pk_sigall_locktime_after_expiry_primary_still_works` | ⏭️ | ✅ |
| `p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend` | ✅ | ✅ |
| `p2pk_sigall_multisig_locktime_primary_still_works` | ✅ | ✅ |
| `p2pk_sigall_mixed_proofs_different_data_fail` | ✅ | ✅ |
| `p2pk_sigall_mixed_proofs_different_kind_fail` | ⏭️ | ✅ |
| `p2pk_sigall_mixed_proofs_different_tags_fail` | ✅ | ✅ |
| `p2pk_sigall_multisig_before_locktime` | ✅ | ✅ |
| `p2pk_sigall_more_signatures_than_required` | ✅ | ✅ |
| `p2pk_sigall_refund_multisig_2of2` | ✅ | ✅ |
| `p2pk_sigall_output_amounts_swapped_fail` | ✅ | ✅ |

## NUT-11 P2PK SIG_INPUTS

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `p2pk_swap_unsigned_fails` | ✅ | ✅ |
| `p2pk_swap_signed_succeeds` | ⏭️ | ✅ |
| `p2pk_wrong_signer_fails` | ✅ | ✅ |
| `p2pk_locktime_after_expiry_primary_still_works` | ✅ | ✅ |
| `p2pk_locktime_after_expiry_refund_succeeds` | ✅ | ✅ |
| `p2pk_multisig_2of3` | ⏭️ | ✅ |
| `p2pk_partial_signatures_fail` | ✅ | ✅ |
| `p2pk_duplicate_signatures_fail` | ✅ | ✅ |
| `p2pk_locktime_before_expiry_refund_blocked` | ✅ | ✅ |
| `p2pk_locktime_after_expiry_no_refund_anyone_can_spend` | ✅ | ✅ |

## NUT-12 DLEQ

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `dleq_proofs_present_in_mint_response` | ⏭️ | ✅ |
| `dleq_proof_valid` | ⏭️ | ✅ |
| `dleq_proof_absent_graceful` | ⏭️ | ⏭️ |
| `dleq_proof_in_signature_response` | ✅ | ✅ |
| `dleq_invalid_proof_rejected` | ✅ | ✅ |
| `hash_e_test_vector_verification` | ✅ | ✅ |

## NUT-12 HTLC SIG_INPUTS

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `htlc_preimage_only_no_pubkeys_succeeds` | ✅ | ✅ |
| `htlc_preimage_only_fails` | ✅ | ✅ |
| `htlc_signature_only_fails` | ✅ | ✅ |
| `htlc_swap_preimage_and_signature_succeeds` | ✅ | ✅ |
| `htlc_wrong_preimage_fails` | ✅ | ✅ |
| `htlc_locktime_after_expiry_refund_succeeds` | ✅ | ✅ |
| `htlc_multisig_2of3` | ✅ | ✅ |
| `htlc_receiver_path_after_locktime` | ✅ | ✅ |

## NUT-12 HTLC SIG_ALL

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `htlc_sigall_preimage_only_no_pubkeys_succeeds` | ✅ | ✅ |
| `htlc_sigall_preimage_only_fails` | ✅ | ✅ |
| `htlc_sigall_signature_only_fails` | ✅ | ✅ |
| `htlc_sigall_requires_preimage_and_transaction_signature` | ✅ | ✅ |
| `htlc_sigall_wrong_preimage_fails` | ✅ | ✅ |
| `htlc_sigall_locktime_after_expiry_refund_succeeds` | ⏭️ | ✅ |
| `htlc_sigall_multisig_2of3` | ✅ | ✅ |
| `htlc_sigall_receiver_path_after_locktime` | ✅ | ✅ |

## NUT-13 Deterministic Secrets

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `nut13_keyset_id_integer` | ✅ | ✅ |
| `nut13_secret_derivation` | ✅ | ✅ |
| `nut13_restore_works` | ⏭️ | ✅ |

## NUT-18 Payment Request

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `nut18_payment_request_decode` | ✅ | ✅ |
| `nut18_payment_request_amount` | ✅ | ✅ |

## NUT-20 Quote Sig

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `nut20_locked_quote_requires_signature` | ⏭️ | ✅ |
| `nut20_locked_quote_valid_signature_succeeds` | ⏭️ | ✅ |
| `nut20_locked_quote_wrong_signature_fails` | ✅ | ✅ |
| `nut20_quote_echoes_pubkey` | ✅ | ✅ |

## NUT-26 Bech32m

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `nut26_encode_token_v4` | ✅ | ✅ |
| `nut26_decode_token_v4` | ✅ | ✅ |

## NUT-29 Batch Ops

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `batch_check_returns_quotes` | ✅ | ✅ |
| `batch_check_rejects_too_many` | ✅ | ✅ |
| `batch_mint_rejects_too_many_outputs` | ✅ | ✅ |

## NUT-03 Swap Basics

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `swap_valid_proofs_succeeds` | ✅ | ✅ |
| `swap_already_spent_fails` | ✅ | ✅ |
| `swap_wrong_keyset_fails` | ✅ | ✅ |

## NUT-04 Mint Quote Basics

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `mint_quote_creates_invoice` | ✅ | ✅ |
| `mint_quote_zero_amount_fails` | ✅ | ✅ |
| `mint_tokens_after_quote` | ❌ | ✅ |

> ❌ `mint_tokens_after_quote` @ `https://signut.cashu.exchange`: quote never paid after 30 retries

## NUT-05 Melt Basics

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `melt_quote_creates_quote` | ✅ | ✅ |
| `melt_valid_proofs_succeeds` | ✅ | ✅ |

## NUT-07 Checkstate Basics

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `checkstate_unspent_returns_unspent` | ✅ | ✅ |
| `checkstate_spent_returns_spent` | ✅ | ✅ |

## NUT-09 Restore Basics

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `restore_returns_signatures` | ❌ | ✅ |

> ❌ `restore_returns_signatures` @ `https://signut.cashu.exchange`: no signatures in response: {'outputs': [], 'signatures': []}

## NUT-00 Token Format Basics

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `token_v3_parses` | ✅ | ✅ |
| `token_v4_parses` | ✅ | ✅ |

## NUT-19 Cache Basics

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `mint_info_nut19_supported` | ✅ | ✅ |

## NUT-06 Mint Info Basics

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `mint_info_returns_required_fields` | ✅ | ✅ |

## Security: Concurrency

| Scenario | `https://signut.cashu.exchange` | `https://testnut.cashu.exchange` |
|---|---|---|
| `concurrent_double_melt_rejected` | ✅ | ✅ |
| `sequential_double_melt_rejected` | ✅ | ✅ |
