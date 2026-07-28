# Scenario: SIG_ALL State Transitions (#1009)

> **Source**: [cashubtc/nutshell#1009](https://github.com/cashubtc/nutshell/issues/1009)
> **Severity**: High (20/58 scenarios fail in Nutshell)
> **Affects**: Nutshell (confirmed 20 failures), CDK (0 failures), cashu-cf (needs testing)

## Description

Nutshell's SIG_ALL spending condition verification rejects valid spends in multiple state combinations. The primary P2PK SIG_ALL path should remain valid after locktime expiry (with refund being additive, not exclusive), but Nutshell rejects it.

## Test matrix (58 scenarios)

From the [NUT-10 compatibility checker](https://github.com/SatsAndSports/nut10_compatibility_checker):

### P2PK SIG_INPUTS (10 scenarios)
| # | Scenario | Expected | Nutshell | CDK |
|---|---|---|---|---|
| 1 | p2pk_swap_unsigned_fails | REJECT | ✅ | ✅ |
| 2 | p2pk_partial_signatures_fail | REJECT | ✅ | ✅ |
| 3 | p2pk_swap_signed_succeeds | ACCEPT | ✅ | ✅ |
| 4 | p2pk_multisig_2of3 | ACCEPT | ✅ | ✅ |
| 5 | p2pk_locktime_before_expiry_primary_only | ACCEPT primary | ✅ | ✅ |
| 6 | p2pk_locktime_after_expiry_primary_still_works | ACCEPT primary | ✅ | ✅ |
| 7 | p2pk_locktime_after_expiry_no_refund_anyone_can_spend | ACCEPT | ✅ | ✅ |
| 8 | p2pk_multisig_locktime_primary_still_works | ACCEPT | ✅ | ✅ |
| 9 | p2pk_wrong_signer_fails | REJECT | ✅ | ✅ |
| 10 | p2pk_duplicate_signatures_fail | REJECT | ✅ | ✅ |

### HTLC SIG_INPUTS (8 scenarios)
| # | Scenario | Expected | Nutshell | CDK |
|---|---|---|---|---|
| 11 | htlc_preimage_only_fails | REJECT | ✅ | ✅ |
| 12 | htlc_preimage_only_no_pubkeys_succeeds | ACCEPT | ✅ | ✅ |
| 13 | htlc_signature_only_fails | REJECT | ✅ | ✅ |
| 14 | htlc_swap_preimage_and_signature_succeeds | ACCEPT | ✅ | ✅ |
| 15 | htlc_wrong_preimage_fails | REJECT | ✅ | ✅ |
| 16 | htlc_locktime_after_expiry_refund_succeeds | ACCEPT | ✅ | ✅ |
| 17 | htlc_multisig_2of3 | ACCEPT | ✅ | ✅ |
| 18 | htlc_receiver_path_after_locktime | ACCEPT | ✅ | ✅ |

### P2PK SIG_ALL (13 scenarios)
| # | Scenario | Expected | Nutshell | CDK |
|---|---|---|---|---|
| 19 | p2pk_sigall_requires_transaction_signature | REJECT unsigned | ✅ | ✅ |
| 20 | p2pk_sigall_sig_inputs_fail | REJECT | ✅ | ✅ |
| 21 | p2pk_sigall_multisig_2of3 | ACCEPT | ✅ | ✅ |
| 22 | p2pk_sigall_wrong_signer_fails | REJECT | ✅ | ✅ |
| 23 | p2pk_sigall_duplicate_signatures_fail | REJECT | ✅ | ✅ |
| 24 | p2pk_sigall_locktime_before_expiry_primary_only | ACCEPT primary | ✅ | ✅ |
| 25 | **p2pk_sigall_locktime_after_expiry_primary_still_works** | ACCEPT | **❌ FAIL** | ✅ |
| 26 | p2pk_sigall_locktime_after_expiry_no_refund_anyone_can_spend | ACCEPT | ✅ | ✅ |
| 27 | **p2pk_sigall_multisig_locktime_primary_still_works** | ACCEPT | **❌ FAIL** | ✅ |
| 28 | p2pk_sigall_mixed_proofs_different_data_fail | REJECT | ✅ | ✅ |
| 29 | p2pk_sigall_mixed_proofs_different_kind_fail | REJECT | ✅ | ✅ |
| 30 | p2pk_sigall_mixed_proofs_different_tags_fail | REJECT | ✅ | ✅ |
| 31 | p2pk_sigall_more_signatures_than_required | ACCEPT | ✅ | ✅ |

### HTLC SIG_ALL (7 scenarios)
| # | Scenario | Expected | Nutshell | CDK |
|---|---|---|---|---|
| 32 | **htlc_sigall_preimage_only_no_pubkeys_succeeds** | ACCEPT | **❌ FAIL** | ✅ |
| 33 | htlc_sigall_preimage_only_fails | REJECT | ✅ | ✅ |
| 34 | htlc_sigall_signature_only_fails | REJECT | ✅ | ✅ |
| 35 | **htlc_sigall_requires_preimage_and_transaction_signature** | ACCEPT | **❌ FAIL** | ✅ |
| 36 | htlc_sigall_wrong_preimage_fails | REJECT | ✅ | ✅ |
| 37 | **htlc_sigall_locktime_after_expiry_refund_succeeds** | ACCEPT | **❌ FAIL** | ✅ |
| 38 | **htlc_sigall_multisig_2of3** | ACCEPT | **❌ FAIL** | ✅ |
| 39 | **htlc_sigall_receiver_path_after_locktime** | ACCEPT | **❌ FAIL** | ✅ |

### Melt variants (19 scenarios)
Same scenarios as above but submitted via POST /v1/melt/bolt11 instead of POST /v1/swap.
Additional failures in melt path:
- melt_p2pk_sigall_transaction_signature_succeeds → **❌ FAIL** in Nutshell
- melt_htlc_sigall_preimage_only_no_pubkeys_succeeds → **❌ FAIL** in Nutshell
- melt_htlc_sigall_preimage_only_fails → HTTP 500 instead of protocol rejection
- melt_htlc_sigall_preimage_and_transaction_signature_succeeds → **❌ FAIL** in Nutshell

## Root cause

Nutshell's `conditions.py` uses an exclusive if/elif structure for locktime states:
```python
if locktime and locktime < now:
    # ONLY refund path — primary path not tried
else:
    # ONLY primary path
```

The spec says primary path should remain valid AND refund path should be additive. The correct structure is:
```python
if can_use_main_path:
    try primary path
if locktime_expired:
    try refund path
```

## How to test

### Using the NUT-10 compatibility checker (recommended)

```bash
# Build (if not already built)
cd ~/src/nut10_compatibility_checker/compat-runner
cargo build --release

# Run against cashu-cf
./target/release/compat-runner --mint-url http://localhost:8787 --suite all

# Run against CDK
./target/release/compat-runner  # starts embedded CDK mint

# Run against Nutshell
./target/release/compat-runner --mint-url http://localhost:3338 --suite all
```

### Using Python E2E (basic checks only)

```bash
python3 e2e/lib/mint_client.py --mint-url http://localhost:8787 --scenario all
```

## cashu-cf status

**Needs testing.** cashu-cf's `verifyP2PKSigInputs` uses the correct structure:
```typescript
if (locktime && locktime < now) {
    // ONLY refund keys
} else {
    // ONLY primary keys
}
```

Wait — this is the same exclusive structure as Nutshell! cashu-cf might have the same bug. The difference is that cashu-cf's SIG_ALL path (`verifySigAll`) tries 10 candidate message formats, which might mask some failures. But the structural issue is the same.

**This is a high-priority finding to test.**
