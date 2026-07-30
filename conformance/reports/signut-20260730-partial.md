
============================================================
Testing mint: https://signut.cashu.exchange
============================================================
  [1/109] invoice_description_truncated_quote_id ... ⏭️ no BOLT11 decoder available or decode failed
  [2/109] keysets_returns_active_keyset ... ✅ 1 active sat keyset(s)
  [3/109] keys_returns_pubkey_for_amount ... ✅ 10 amount→pubkey mappings
  [4/109] keyset_has_correct_unit ... ✅ unit=sat, id=00eb682aaccde657
  [5/109] keyset_fee_ppk_present ... ✅ input_fee_ppk=0
  [6/109] multiple_keysets_unit_filter ... ✅ 1 active sat keyset(s) found
  [7/109] keyset_keys_are_valid_pubkeys ... ✅ 10 pubkeys all valid compressed secp256k1
  [8/109] mint_quote_has_accounting_fields ... ✅ amount_paid=0, amount_issued=0, updated_at=1785430745
  [9/109] mint_quote_uuid_v7 ... ✅ quote=019fb3f7-302a-7558-95a0-46bb5fcb46ad
  [10/109] mint_quote_accounting_after_payment ... ✅ amount_paid=8 == amount=8
  [11/109] mint_quote_accounting_after_mint ... ✅ amount_issued=8 == amount=8
  [12/109] mint_quote_updated_at_monotonic ... ✅ 1785430762 → 1785430771 → 1785430771
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
  [27/109] melt_htlc_sigall_preimage_and_transaction_signature_succeeds ... ✅ HTLC SIG_ALL melt paid
  [28/109] melt_p2pk_post_locktime_anyone_can_spend ... ✅ anyone-can-spend melt paid
  [29/109] melt_p2pk_before_locktime_wrong_key_fails ... ✅ wrong key rejected
  [30/109] melt_p2pk_before_locktime_correct_key_succeeds ... ✅ correct key melt paid
  [31/109] p2pk_sigall_requires_transaction_signature ... ✅ rejected
  [32/109] p2pk_sigall_sig_inputs_fail ... ✅ rejected
  [33/109] p2pk_sigall_multisig_2of3 ... ✅ 2-of-3 accepted
  [34/109] p2pk_sigall_wrong_signer_fails ... ✅ rejected
  [35/109] p2pk_sigall_duplicate_signatures_fail ... ✅ duplicate rejected
  [36/109] p2pk_sigall_locktime_before_expiry_primary_only ... ✅ primary works, refund blocked
  [37/109] p2pk_sigall_locktime_after_expiry_primary_still_works ... ✅ primary works after expiry
  [38/109] p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend ... ✅ anyone-can-spend
  [39/109] p2pk_sigall_multisig_locktime_primary_still_works ... ✅ multisig primary works after locktime
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
  [50/109] p2pk_locktime_after_expiry_primary_still_works ... ✅ primary works after expiry
  [51/109] p2pk_locktime_after_expiry_refund_succeeds ... ✅ refund works after expiry
  [52/109] p2pk_multisig_2of3 ... ✅ 2-of-3 accepted
  [53/109] p2pk_partial_signatures_fail ... ✅ partial rejected
  [54/109] p2pk_duplicate_signatures_fail ... ✅ duplicate rejected
  [55/109] p2pk_locktime_before_expiry_refund_blocked ... ✅ refund blocked before expiry
  [56/109] p2pk_locktime_after_expiry_no_refund_anyone_can_spend ... ✅ anyone-can-spend
  [57/109] dleq_proofs_present_in_mint_response ... ⏭️ Exception: RuntimeError: mint failed (400): {'detail': 'Quote request is not pai
  [58/109] dleq_proof_valid ... 