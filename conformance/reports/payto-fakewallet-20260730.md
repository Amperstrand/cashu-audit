
============================================================
Testing mint: https://payto.fakewallet.cashu.exchange
============================================================
  [1/109] invoice_description_truncated_quote_id ... ⏭️ invoice not decodable BOLT11: 'dummy-mint-8-5b1b00aee4769e8f1a89bc77e25'...
  [2/109] keysets_returns_active_keyset ... ✅ 1 active sat keyset(s)
  [3/109] keys_returns_pubkey_for_amount ... ✅ 18 amount→pubkey mappings
  [4/109] keyset_has_correct_unit ... ✅ unit=sat, id=00ccf364d93b8ded
  [5/109] keyset_fee_ppk_present ... ✅ input_fee_ppk=0
  [6/109] multiple_keysets_unit_filter ... ✅ 1 active sat keyset(s) found
  [7/109] keyset_keys_are_valid_pubkeys ... ✅ 18 pubkeys all valid compressed secp256k1
  [8/109] mint_quote_has_accounting_fields ... ❌ missing fields: ['amount_paid', 'amount_issued', 'updated_at']
  [9/109] mint_quote_uuid_v7 ... ❌ quote='7aa72f1cceb41108e2a572527eedef30' does not match UUID v7 pattern
  [10/109] mint_quote_accounting_after_payment ... ❌ amount_paid=-1, expected 8
  [11/109] mint_quote_accounting_after_mint ... ❌ amount_issued=-1, expected 8
  [12/109] mint_quote_updated_at_monotonic ... ❌ no updated_at in initial response
  [13/109] fee_zero_ppk_swap_succeeds ... ✅ fee_ppk=0, swapped 8 sats with 0 fee, 1 sigs returned
  [14/109] fee_calculated_correctly ... ✅ fee_ppk=0, 1 inputs, fee=0, output=8
  [15/109] fee_insufficient_outputs_fails ... ✅ rejected swap requesting 9 (max=8, fee=0)
  [16/109] fee_exact_balance_succeeds ... ✅ exact balance: input=8, fee=0, output=8
  [17/109] fee_melt_quote_includes_fee_reserve ... ✅ fee_reserve=0
  [18/109] fee_per_proof_not_per_amount ... ⏭️ fee_ppk=0, cannot distinguish per-proof vs per-amount
  [19/109] melt_p2pk_unsigned_fails ... ✅ unsigned melt rejected
  [20/109] melt_p2pk_signed_succeeds ... ✅ signed melt paid
  [21/109] melt_p2pk_sigall_unsigned_fails ... ✅ unsigned SIG_ALL melt rejected
  [22/109] melt_p2pk_sigall_transaction_signature_succeeds ... ✅ SIG_ALL melt paid
  [23/109] melt_htlc_preimage_only_no_pubkeys_succeeds ... ✅ HTLC preimage melt paid
  [24/109] melt_htlc_preimage_only_fails ... ✅ wrong preimage rejected
  [25/109] melt_htlc_signature_only_fails ... ✅ missing preimage rejected
  [26/109] melt_htlc_preimage_and_signature_succeeds ... ✅ preimage + sig melt paid
  [27/109] melt_htlc_sigall_preimage_and_transaction_signature_succeeds ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold 
  [28/109] melt_p2pk_post_locktime_anyone_can_spend ... ✅ anyone-can-spend melt paid
  [29/109] melt_p2pk_before_locktime_wrong_key_fails ... ✅ wrong key rejected
  [30/109] melt_p2pk_before_locktime_correct_key_succeeds ... ✅ correct key melt paid
  [31/109] p2pk_sigall_requires_transaction_signature ... ✅ rejected
  [32/109] p2pk_sigall_sig_inputs_fail ... ✅ rejected
  [33/109] p2pk_sigall_multisig_2of3 ... ✅ 2-of-3 accepted
  [34/109] p2pk_sigall_wrong_signer_fails ... ✅ rejected
  [35/109] p2pk_sigall_duplicate_signatures_fail ... ✅ duplicate rejected
  [36/109] p2pk_sigall_locktime_before_expiry_primary_only ... ✅ primary works, refund blocked
  [37/109] p2pk_sigall_locktime_after_expiry_primary_still_works ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold 
  [38/109] p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend ... ✅ anyone-can-spend
  [39/109] p2pk_sigall_multisig_locktime_primary_still_works ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold 
  [40/109] p2pk_sigall_mixed_proofs_different_data_fail ... ✅ mixed data rejected
  [41/109] p2pk_sigall_mixed_proofs_different_kind_fail ... ✅ mixed kind rejected
  [42/109] p2pk_sigall_mixed_proofs_different_tags_fail ... ✅ mixed tags rejected
  [43/109] p2pk_sigall_multisig_before_locktime ... ✅ 2-of-3 before locktime accepted
  [44/109] p2pk_sigall_more_signatures_than_required ... ✅ extra sigs accepted
  [45/109] p2pk_sigall_refund_multisig_2of2 ... ✅ 2-of-2 refund accepted
  [46/109] p2pk_sigall_output_amounts_swapped_fail ... ❌ got 200
  [47/109] p2pk_swap_unsigned_fails ... ✅ rejected
  [48/109] p2pk_swap_signed_succeeds ... ✅ succeeded
  [49/109] p2pk_wrong_signer_fails ... ✅ rejected
  [50/109] p2pk_locktime_after_expiry_primary_still_works ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold 
  [51/109] p2pk_locktime_after_expiry_refund_succeeds ... ✅ refund works after expiry
  [52/109] p2pk_multisig_2of3 ... ✅ 2-of-3 accepted
  [53/109] p2pk_partial_signatures_fail ... ✅ partial rejected
  [54/109] p2pk_duplicate_signatures_fail ... ✅ duplicate rejected
  [55/109] p2pk_locktime_before_expiry_refund_blocked ... ✅ refund blocked before expiry
  [56/109] p2pk_locktime_after_expiry_no_refund_anyone_can_spend ... ✅ anyone-can-spend
  [57/109] dleq_proofs_present_in_mint_response ... ✅ 1/1 signatures have dleq
  [58/109] dleq_proof_valid ... ✅ 1 DLEQ proofs verified
  [59/109] dleq_proof_absent_graceful ... ⏭️ mint provides DLEQ — absent-case not applicable
  [60/109] dleq_proof_in_signature_response ... ✅ 1 swap-response DLEQ proofs verified
  [61/109] dleq_invalid_proof_rejected ... ✅ tampered e and s both correctly rejected
  [62/109] hash_e_test_vector_verification ... ✅ hash_e + 2 DLEQ test vectors verified
  [63/109] htlc_preimage_only_no_pubkeys_succeeds ... ✅ preimage accepted
  [64/109] htlc_preimage_only_fails ... ✅ wrong preimage rejected
  [65/109] htlc_signature_only_fails ... ✅ signature without preimage rejected
  [66/109] htlc_swap_preimage_and_signature_succeeds ... ✅ preimage + signature accepted
  [67/109] htlc_wrong_preimage_fails ... ✅ wrong preimage with valid sig rejected
  [68/109] htlc_locktime_after_expiry_refund_succeeds ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Invalid HTLC witness
  [69/109] htlc_multisig_2of3 ... ✅ 2-of-3 multisig + preimage accepted
  [70/109] htlc_receiver_path_after_locktime ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold 
  [71/109] htlc_sigall_preimage_only_no_pubkeys_succeeds ... ✅ preimage accepted (SIG_ALL)
  [72/109] htlc_sigall_preimage_only_fails ... ✅ wrong preimage rejected (SIG_ALL)
  [73/109] htlc_sigall_signature_only_fails ... ✅ signature without preimage rejected (SIG_ALL)
  [74/109] htlc_sigall_requires_preimage_and_transaction_signature ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold 
  [75/109] htlc_sigall_wrong_preimage_fails ... ✅ wrong preimage with valid sig rejected (SIG_ALL)
  [76/109] htlc_sigall_locktime_after_expiry_refund_succeeds ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Invalid HTLC witness
  [77/109] htlc_sigall_multisig_2of3 ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold 
  [78/109] htlc_sigall_receiver_path_after_locktime ... ❌ got 403: {'error': 'spending_condition_not_met', 'detail': 'Signature threshold 
  [79/109] nut13_keyset_id_integer ... ✅ test vector verified; 1 mint keyset(s) computed: 00ccf364…→1523938486
  [80/109] nut13_secret_derivation ... ✅ secrets for counter 0 and 1 derived correctly from test mnemonic
  [81/109] nut13_restore_works ... ✅ 1 signature(s) restored, C_ values match originals
  [82/109] nut18_payment_request_decode ... ✅ decoded successfully: id=7f4a2b39, unit=sat, 1 mint(s)
  [83/109] nut18_payment_request_amount ... ✅ amount=10 sat decoded correctly
  [84/109] nut20_locked_quote_requires_signature ... ✅ mint without sig rejected (400)
  [85/109] nut20_locked_quote_valid_signature_succeeds ... ❌ got 400: {'error': 'quote_pubkey_no_signature', 'detail': 'Mint quote requires a
  [86/109] nut20_locked_quote_wrong_signature_fails ... ✅ wrong sig rejected (400)
  [87/109] nut20_quote_echoes_pubkey ... ✅ pubkey echoed: 02f6a3a4f83df86f89af...
  [88/109] nut26_encode_token_v4 ... ✅ minimal and description test vectors encoded correctly
  [89/109] nut26_decode_token_v4 ... ✅ minimal + description vectors decoded: id=7f4a2b39, amount=100, desc=Test paymen
  [90/109] batch_check_returns_quotes ... ✅ states=['PAID', 'PAID']
  [91/109] batch_check_rejects_too_many ... ❌ expected batch_too_large, got 404: {'error': 'quote_not_found', 'detail': 'Quote
  [92/109] batch_mint_rejects_too_many_outputs ... ❌ expected too_many_outputs, got 400: {'error': 'quote_not_found', 'detail': 'Quot
  [93/109] swap_valid_proofs_succeeds ... ✅ 1 signatures returned
  [94/109] swap_already_spent_fails ... ✅ double-spend rejected (422)
  [95/109] swap_wrong_keyset_fails ... ✅ wrong keyset rejected
  [96/109] mint_quote_creates_invoice ... ✅ invoice starts with dummy-
  [97/109] mint_quote_zero_amount_fails ... ✅ zero amount rejected
  [98/109] mint_tokens_after_quote ... ✅ 1 signatures minted
  [99/109] melt_quote_creates_quote ... ✅ amount=4, fee=0
  [100/109] melt_valid_proofs_succeeds ... ✅ melt settled PAID
  [101/109] checkstate_unspent_returns_unspent ... ✅ 1/1 UNSPENT
  [102/109] checkstate_spent_returns_spent ... ✅ 1/1 SPENT
  [103/109] restore_returns_signatures ... ✅ 1 signatures restored
  [104/109] token_v3_parses ... ✅ V3 token parsed: 1 proofs
  [105/109] token_v4_parses ... ✅ V4 token parsed: 1 proofs with DLEQ
  [106/109] mint_info_nut19_supported ... ❌ nut19 not found in nuts list
  [107/109] mint_info_returns_required_fields ... ✅ name=PayTo FakeWallet Mint, version=Nutshell-CF/0.0.1
  [108/109] concurrent_double_melt_rejected ... ✅ exactly one melt paid; loser rejected with HTTP 400
  [109/109] sequential_double_melt_rejected ... ✅ first melt paid; second rejected with HTTP 400

Matrix written to reports/matrix.md

20 failure(s) detected
