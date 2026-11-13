# Cashu Conformance Matrix — 2026-11-13 22:43 UTC

**Targets** (identity captured at run start):
- `https://signut.cashu.exchange` — Signet Cashu Mint / Nutshell-CF/0.0.1

**Summary**: 22 passed, 0 failed, 1 skipped (23 total)

## NUT-12 DLEQ

| Scenario | `Signet Cashu Mint@Nutshell-CF/0.0.1` |
|---|---|
| `dleq_proofs_present_in_mint_response` | ✅ |
| `dleq_proof_valid` | ✅ |
| `dleq_proof_absent_graceful` | ⏭️ |
| `dleq_proof_in_signature_response` | ✅ |
| `dleq_invalid_proof_rejected` | ✅ |
| `dleq_proof_in_restore_response` | ✅ |
| `hash_e_test_vector_verification` | ✅ |

## NUT-12 HTLC SIG_INPUTS

| Scenario | `Signet Cashu Mint@Nutshell-CF/0.0.1` |
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

| Scenario | `Signet Cashu Mint@Nutshell-CF/0.0.1` |
|---|---|
| `htlc_sigall_preimage_only_no_pubkeys_succeeds` | ✅ |
| `htlc_sigall_preimage_only_fails` | ✅ |
| `htlc_sigall_signature_only_fails` | ✅ |
| `htlc_sigall_requires_preimage_and_transaction_signature` | ✅ |
| `htlc_sigall_wrong_preimage_fails` | ✅ |
| `htlc_sigall_locktime_after_expiry_refund_succeeds` | ✅ |
| `htlc_sigall_multisig_2of3` | ✅ |
| `htlc_sigall_receiver_path_after_locktime` | ✅ |
