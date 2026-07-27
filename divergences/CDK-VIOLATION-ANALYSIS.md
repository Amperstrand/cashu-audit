# CDK Spec Violation Analysis: NUT-11 Duplicate Tags + n_sigs Validation

> **Date**: 2026-07-26
> **Analyst**: GLM-5.2 in opencode (max reasoning)
> **Target**: CDK @ v0.15.1 (experiment/greatspectations-audit branch)
> **Comparison**: Nutshell @ main, cashu-cf @ main
> **Status**: Internal finding — NOT filed on upstream cashubtc/cdk

## Overview

Our Layer 3 AI audit of CDK found 2 spec violations in NUT-11 (Pay-To-Pubkey) spending condition verification. Both are in the `spending_conditions.rs` tag-parsing path used by the mint when verifying proofs. This document presents the spec text, the code behavior, a logical argument for why each is a violation, a concrete experiment design proving the violation, and a comparison with Nutshell's behavior.

---

## Violation 1: Duplicate Tags — First-Match Instead of Rejection

### Spec text (NUT-11, line 85)

> Each of the above tags may appear exactly **ONCE** in a P2PK secret. If a tag appears more than once, the P2PK secret is malformed and the Proof **MUST** be rejected as unspendable.

This is an unconditional MUST. The spec says: duplicate tag → malformed secret → proof unspendable. No exceptions.

### CDK behavior

**File**: `crates/cashu/src/nuts/nut10/spending_conditions.rs:336-371`

```rust
for tag_vec in tags {
    let tag = Tag::try_from(tag_vec)?;
    match tag {
        Tag::LockTime(lt) => { if locktime.is_none() { locktime = Some(lt); } }
        Tag::PubKeys(pks) => { if pubkeys.is_none() { pubkeys = Some(pks); } }
        Tag::Refund(keys) => { if refund_keys.is_none() { refund_keys = Some(keys); } }
        Tag::SigFlag(sf) => { if sig_flag.is_none() { sig_flag = Some(sf); } }
        Tag::NSigs(sigs) => { if num_sigs.is_none() { num_sigs = Some(sigs); } }
        Tag::NSigsRefund(sigs) => { if num_sigs_refund.is_none() { num_sigs_refund = Some(sigs); } }
        Tag::Custom(_, _) => {}
    }
}
```

The `if X.is_none()` guard means: **first occurrence wins, subsequent duplicates are silently ignored**. The proof is NOT rejected. It remains spendable using the first tag's values.

This is intentional — the test `test_duplicate_tags_first_match` (spending_conditions.rs:417-449) explicitly documents this behavior as designed.

### Argument: Why this is a spec violation

1. **The spec text is unambiguous**: "MUST be rejected as unspendable" — this is RFC 2119 MUST, the strongest normative keyword.
2. **"Malformed" applies to the entire secret**: The spec says "the P2PK secret is malformed" — not "the duplicate tag is ignored." A malformed secret means the proof should be permanently unspendable.
3. **First-match creates a semantic ambiguity**: If a secret has `["locktime", "100"]` and `["locktime", "200"]`, which locktime applies? CDK picks 100 (first). But the spender might have intended 200 (second). This is a semantic divergence that the spec prevents by requiring rejection.
4. **Security consideration**: An attacker could craft a proof with duplicate tags where the first tag values are favorable to them (e.g., lower n_sigs) and the second values are what the sender intended. The recipient sees the "intended" values in the secret but the mint uses the first (attacker's) values.

### Experiment design: Proving the violation

**Setup**: Create a P2PK proof with duplicate `locktime` tags.

```
Secret: ["P2PK", {
    "nonce": "<random>",
    "data": "<pubkey_A>",
    "tags": [
        ["locktime", "1000000000"],   // first locktime (past — refund path open)
        ["locktime", "9999999999"],   // second locktime (far future — no refund)
        ["refund", "<pubkey_B>"],
        ["n_sigs", "1"],
        ["n_sigs_refund", "1"]
    ]
}]
```

**Expected per spec**: Proof is malformed → unspendable by anyone.

**Actual CDK behavior**: 
- Uses `locktime = 1000000000` (first occurrence)
- Locktime is in the past → refund path is open
- Attacker with `pubkey_B` can spend via refund path

**Proof of violation**: The proof IS spendable (via refund path using the first locktime value), contradicting the spec's "MUST be rejected as unspendable."

### Nutshell comparison

**File**: `cashu/mint/conditions.py` — `get_tag()` method (line ~35-39)

```python
def get_tag(self, tag_name: str) -> str | None:
    for tag in self.tags:
        if tag[0] == tag_name and len(tag) >= 2:
            return tag[1]
    return None
```

Nutshell also returns the first match. **Nutshell has the same violation** — it does not reject duplicate tags either. Both CDK and Nutshell use first-match-wins.

**Corrected understanding**: Our earlier cross-impl audit (documented in `FINDING-CDK-2252-outdated.md`) found that CDK #2252 incorrectly claimed Nutshell "rejects duplicate tags." In reality, both implementations have the same non-compliant behavior.

### Recommendation

1. **Add tag uniqueness validation at parse time** in both CDK and Nutshell
2. **Implementation**: After parsing all tags, check if any tag name appears more than once. If yes, reject the proof as unspendable.
3. **cashu-cf already does this** — `hasDuplicateTags()` check added in the NUT-11 audit fix (commit 379e541). cashu-cf is the ONLY implementation that correctly rejects duplicate tags.
4. **Severity**: Low — the attack requires crafting a proof with duplicate tags, which wallets don't normally produce. But it IS a spec violation.

---

## Violation 2: n_sigs > Pubkeys Not Validated on Verification Path

### Spec text (NUT-11, line 87)

> If `n_sigs` or `n_sigs_refund` is not a positive integer, or exceeds the total number of keys in its pathway, the P2PK secret is malformed and the Proof **MUST** be rejected as unspendable.

Again, unconditional MUST. Two conditions trigger rejection:
- n_sigs not a positive integer → reject
- n_sigs > total keys in pathway → reject

### CDK behavior

**Construction path** (`Conditions::validate`, spending_conditions.rs:184-200):
```rust
fn validate(&self, primary_key_count: u64) -> Result<(), Error> {
    if let Some(n) = self.num_sigs {
        if n == 0 { return Err(...ZeroSignaturesRequired); }
        let available_keys = primary_key_count + self.pubkeys.as_ref().map(Vec::len).unwrap_or(0) as u64;
        if n > available_keys {
            return Err(Error::NUT11(Error::ImpossibleMultisigConfiguration));
        }
    }
    // ...
}
```

This IS validated — but only when constructing conditions via `Conditions::new()`. This is the WALLET-side path (when creating a P2PK secret).

**Verification path** (`TryFrom<Vec<Vec<String>>> for Conditions`, spending_conditions.rs:326-408):
- Parses tags from the proof's secret
- Checks `num_sigs == 0` → rejects (line 373-378)
- Checks `refund_keys vs num_sigs_refund` → rejects if mismatch (line 380-397)
- Does NOT check `num_sigs > (primary_key_count + pubkeys.len())`

**The gap**: When a mint receives a proof with `n_sigs=5` but only 2 pubkeys, the verification-path parsing accepts it. The primary path becomes unspendable (can never get 5 sigs from 2 keys), but the refund path (if present) remains usable.

### Argument: Why this is a spec violation

1. **"The P2PK secret is malformed"**: The spec doesn't say "the primary pathway fails." It says the SECRET is malformed. A malformed secret should make the proof permanently unspendable.
2. **"MUST be rejected as unspendable"**: Unspendable means NO pathway works. But CDK allows the refund pathway.
3. **The `validate()` method proves the developers knew this check was needed** — it exists on the construction path but was omitted from the verification path.
4. **Attack scenario**: 
   - Attacker creates a proof with `n_sigs=99` (impossible for primary), `locktime=1` (immediately expired), `refund=["attacker_key"]`, `n_sigs_refund=1`
   - The primary path is impossible (99 sigs from 2 keys)
   - The locktime has passed → refund path is open
   - Attacker spends via refund path with their key
   - **The original holder's pubkeys are irrelevant** — they can't prevent the refund spend
   - Per spec: this proof should be unspendable entirely

### Experiment design: Proving the violation

**Setup**: Create a P2PK proof with impossible n_sigs but valid refund.

```python
secret = ["P2PK", {
    "nonce": "<random>",
    "data": "<victim_pubkey>",        # primary key (victim)
    "tags": [
        ["pubkeys", "<victim_pubkey_2>"],  # 2 total primary keys
        ["n_sigs", "99"],              # impossible: 99 > 2 keys
        ["locktime", "1"],             # immediately expired (Unix epoch + 1 sec)
        ["refund", "<attacker_pubkey>"],
        ["n_sigs_refund", "1"]         # attacker needs 1 sig
    ]
}]
```

**Expected per spec**: Proof is malformed (n_sigs=99 > 2 keys) → unspendable by anyone.

**Actual CDK behavior**:
- Parsing accepts the secret (no n_sigs > pubkeys check on verify path)
- Primary path: impossible (99 sigs from 2 keys — can never satisfy)
- Locktime expired → refund path opens
- Attacker provides 1 valid Schnorr signature from `<attacker_pubkey>`
- **Proof is spent by attacker** — contradicts "MUST be rejected as unspendable"

**Proof of violation**: The proof IS spendable (via refund path), contradicting the spec.

### Nutshell comparison

**File**: `cashu/mint/conditions.py:158-161`

```python
if len(pubkeys) < n_sigs_required or len(signatures) < n_sigs_required:
    raise TransactionError(
        f"Not enough pubkeys ({len(pubkeys)}) or signatures ({signatures}) for n_sigs ({n_sigs_required})"
    )
```

Nutshell checks `len(pubkeys) < n_sigs_required` — but **at verification time, not at parse time**. This means:
- The primary path IS rejected (not enough pubkeys for n_sigs)
- But the check is per-pathway, not on the secret itself
- The refund path is independently checked: `len(refund_pubkeys) < refund_n_sigs`
- If refund has enough keys, the refund path succeeds

**Conclusion**: Nutshell has a **similar but slightly different deviation**:
- CDK: doesn't validate at all on verify path → primary path fails naturally
- Nutshell: validates at verify time → primary path explicitly rejected
- Both: refund path remains usable despite malformed secret

Neither implementation rejects the proof as "unspendable" — both allow the refund pathway.

### Recommendation

1. **Validate n_sigs against pubkey count at SECRET PARSING time** (before any pathway verification)
2. If `n_sigs > (1 + len(pubkeys_tag))` for P2PK: reject entire proof as malformed
3. If `n_sigs_refund > len(refund_tag)` when refund tag present: reject entire proof
4. This check should happen in `TryFrom<Vec<Vec<String>>> for Conditions` (CDK) and in `P2PKSecret.from_secret()` (Nutshell)
5. **Severity**: Medium — the attack requires crafting a malformed secret, but the refund-path escape is a real security concern. A victim who receives tokens with an impossible n_sigs might assume they're unspendable (per spec), but an attacker with refund keys can still spend them.

---

## Summary: Cross-Implementation Compliance

| Violation | Spec says | CDK does | Nutshell does | cashu-cf does |
|---|---|---|---|---|
| **Duplicate tags** | MUST reject as unspendable | First-match-wins (accepts) | First-match-wins (accepts) | **Rejects all duplicates** ✅ |
| **n_sigs > pubkeys** | MUST reject as unspendable | Not validated on verify path (refund usable) | Validated at verify time (refund still usable) | **Rejects upfront** ✅ |

**cashu-cf is the ONLY implementation that correctly implements both requirements.** CDK and Nutshell both deviate.

## Why document internally?

1. **These are reference implementations** — filing issues on upstream could be seen as criticism without offering fixes
2. **The spec itself may need clarification** — "malformed secret" vs "impossible pathway" needs spec author input
3. **Our cashu-audit project is the right place** to track these findings with full analysis
4. **When the Cashu community is ready**, these findings can be shared constructively

## Recommended next steps

1. **Share with Cashu community** when appropriate — these findings benefit all implementations
2. **Clarify spec** — does "malformed secret" mean "reject entirely" or "reject the affected pathway"?
3. **Add tests** — the experiment designs above should become test vectors in all 3 implementations
4. **Consider whether cashu-cf's strictness is correct or overly strict** — it's possible the spec authors intended pathway-level rejection, not whole-proof rejection
