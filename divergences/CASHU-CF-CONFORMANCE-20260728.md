# cashu-cf Conformance Findings — testnut.cashu.exchange — 2026-07-28

54 scenarios run, 43 PASS, 11 FAIL (80% pass rate).

## Bug #1: P2PK primary pathway dropped after locktime (3 failures)

**Affected scenarios:**
- `p2pk_locktime_after_expiry_primary_still_works` (SIG_INPUTS)
- `p2pk_sigall_locktime_after_expiry_primary_still_works` (SIG_ALL)
- `p2pk_sigall_multisig_locktime_primary_still_works` (SIG_ALL multisig)

**Spec violation:** NUT-11 says "Locktime Multisig conditions continue to
apply" after locktime expiry. cashu-cf drops the primary pathway and
only allows the refund pathway.

**Same bug as:** nutshell #1009

**CDK status:** PASS (CDK correctly keeps primary active after locktime)

## Bug #2: HTLC receiver path fails after locktime (2 failures)

**Affected scenarios:**
- `htlc_receiver_path_after_locktime` (SIG_INPUTS)
- `htlc_sigall_receiver_path_after_locktime` (SIG_ALL)

**Root cause:** Same pathway independence bug as #1 — after locktime
expiry, the receiver path (preimage) should still work alongside the
refund path. cashu-cf drops it.

## Bug #3: HTLC refund requires preimage (2 failures)

**Affected scenarios:**
- `htlc_locktime_after_expiry_refund_succeeds` (SIG_INPUTS)
- `htlc_sigall_locktime_after_expiry_refund_succeeds` (SIG_ALL)

**Error:** "Invalid HTLC witness: missing preimage"

**Spec:** NUT-14 refund pathway should work with refund signatures only,
no preimage required. cashu-cf incorrectly requires a preimage for the
refund path.

## Bug #4: HTLC + SIG_ALL signature verification broken (4 failures)

**Affected scenarios:**
- `htlc_sigall_preimage_only_no_pubkeys_succeeds`
- `htlc_sigall_requires_preimage_and_transaction_signature`
- `htlc_sigall_multisig_2of3`
- `melt_htlc_sigall_preimage_and_transaction_signature_succeeds`

**Error:** "Signature threshold not met. 0 < 1"

**Root cause:** cashu-cf returns zero valid signatures for HTLC + SIG_ALL
proofs. P2PK + SIG_ALL works correctly (14/16 pass), and HTLC + SIG_INPUTS
works correctly (6/8 pass). The bug is specific to the HTLC + SIG_ALL
verification path.

**Likely cause:** cashu-cf may incorrectly include the HTLC `data` field
(a SHA256 hash) as a signing pubkey, making signature verification
impossible. Or the SIG_ALL message verification path for HTLC secrets
has a separate code path that doesn't extract pubkeys from tags correctly.

**CDK status:** PASS for all HTLC SIG_ALL scenarios.

## Bug #5: SIG_ALL + locktime drops primary pathway (shared, 3 failures)

**Affected scenarios:**
- `p2pk_sigall_locktime_after_expiry_primary_still_works`
- `p2pk_sigall_multisig_locktime_primary_still_works`
- `htlc_sigall_receiver_path_after_locktime`

**Root cause (confirmed by testing):**

After locktime expiry with sigflag=SIG_ALL, both Nutshell and cashu-cf
check ONLY refund signatures, ignoring primary signatures entirely.

Test results (Nutshell, legacy SIG_ALL mode):
- Primary key signature → 400 "signature threshold not met. 0 < 1"
- Refund key signature → 200 (success)
- Both signatures → would succeed but proofs already spent by refund test

**Contrast with SIG_INPUTS:**
- SIG_INPUTS + locktime: Nutshell correctly keeps primary pathway (8/8 HTLC pass)
- SIG_ALL + locktime: Nutshell drops primary pathway (3 shared failures)

**CDK:** Passes all 3 scenarios — handles both pathways regardless of sigflag.

**Conclusion:** The SIG_ALL verification path has a separate code path for
locktime handling that doesn't implement pathway independence correctly.
Both Nutshell and cashu-cf independently have this bug. CDK does not.

## Bug #4 root cause confirmed: HTLC handler ignores SIG_ALL signatures

**Definitive test (2026-07-28):**

| Test | Config | Result |
|------|--------|--------|
| A | HTLC + SIG_ALL, witness on proofs[0] only | 403 "0 < 1" |
| B | HTLC + SIG_ALL, witness on ALL proofs | 403 "0 < 1" |
| C | P2PK + SIG_ALL, witness on proofs[0] only | 200 ✅ |

P2PK + SIG_ALL works correctly. HTLC + SIG_ALL fails regardless of
witness placement. The SIG_ALL message format is correct (proven by
P2PK success). The issue is in cashu-cf's HTLC spending condition
handler — it does not properly verify SIG_ALL signatures for HTLC secrets.

**Likely cause:** cashu-cf's HTLC handler has a separate code path that
either doesn't extract pubkeys from the HTLC secret's tags for SIG_ALL
verification, or incorrectly treats the HTLC `data` field (a SHA-256
hash) as a signing pubkey (which would always fail since a hash is not
a valid secp256k1 public key).
