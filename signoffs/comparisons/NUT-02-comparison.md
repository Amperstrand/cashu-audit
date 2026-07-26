# Cross-Implementation Comparison: NUT-02 (Keysets and Fees)

**Date:** 2026-07-26
**Spec:** cashubtc/nuts @ 734f60e — `02.md` (Keysets and fees, `mandatory`)
**Implementations compared:**
- **cashu-cf** @ c1e3907 (TypeScript / Cloudflare Workers)
- **CDK** @ d033f1b (Rust / `cashu` + `cdk` crates)
- **Nutshell** @ 18539020 (Python / FastAPI)
**Auditor model:** GLM-5.1/5.2 in opencode

---

## Summary Table

| Metric | cashu-cf | CDK | Nutshell |
|--------|----------|-----|----------|
| **Verdict** | PASS WITH FINDINGS | PASS | PASS |
| **PASS** | 11 | 9 (5 MUST + 4 algorithm/format) | 15 |
| **FAIL** | 1 | 0 | 0 |
| **WARN** | 0 (5 findings: 1 critical, 1 minor, 3 info) | 0 (3 non-blocking obs) | 1 |
| **Critical Finding** | **YES** (F1: V1 default) | No | No |

---

## Consensus Areas (All Three Agree)

### Fee Calculation Formula — Exact Match
All three implement `(sum_fees + 999) // 1000` identically:
- **cashu-cf**: `Math.floor((sumPpk + 999) / 1000)` — `nut02.ts:24`. Equivalent for non-negative integers.
- **CDK**: `(sum_fee.checked_add(999)?).checked_div(1000)?` — `fees.rs:46-48`. Adds overflow protection.
- **Nutshell**: `(sum(...) + 999) // 1000` — `verification.py:300-304`. Python floor division.

All three correctly handle multi-keyset fee summing (per-proof keyset lookup).

### V2 Keyset ID Derivation Algorithm — Exact Match
All three verified step-by-step against spec L59-89:

| Step | cashu-cf | CDK | Nutshell |
|------|----------|-----|----------|
| Sort by amount ascending | `keyset.ts:402-406` | `nut02.rs:sort_by_key` | `keys.py:81` |
| Join `"amount:pubkey_hex"` with `,` | `keyset.ts:408` | `nut02.rs:join(",")` | `keys.py:84-86` |
| Append `\|unit:{unit}` | `keyset.ts:409` | `nut02.rs:push_str` | `keys.py:89` |
| Append `\|input_fee_ppk:{n}` if >0 | `keyset.ts:411` | `nut02.rs:201-203` | `keys.py:92-93` |
| SHA256 of UTF-8 preimage | `keyset.ts:413` | `nut02.rs:Sha256::hash` | `keys.py:100` |
| Prefix `"01"` + full hash | `keyset.ts:414` | `nut02.rs:Version01` | `keys.py:103` |

### V1 Keyset ID Derivation (Deprecated) — Exact Match
All three implement the deprecated V1 algorithm (sort → concat pubkeys → SHA256 → first 14 hex chars → prefix `"00"`). Algorithm verified correct in all three.

### Active Keyset Enforcement
All three enforce that new outputs (BlindedMessages/BlindSignatures) must be from active keysets only:
- **cashu-cf**: `features.ts:620-623` (swap), `melt.ts:2071-2072` (melt change).
- **CDK**: `KeySetInfosMethods::active()` iterator filter provided; enforcement in `cdk-mintd`.
- **Nutshell**: `verification.py:134-138` — rejects inactive keyset IDs in outputs.

### input_fee_ppk Default = 0
All three correctly default `input_fee_ppk` to `0` when absent/null per spec L157.

---

## Key Divergences

### 1. CRITICAL: Default Keyset ID Version (cashu-cf FAIL)

This is the **most significant divergence across all four NUTs audited**.

| Implementation | Default Version Byte | Status |
|----------------|---------------------|--------|
| **cashu-cf** | **`00` (V1, deprecated)** | **FAIL** — spec L61 says current version is `01` |
| CDK | `01` (V2, current) | PASS |
| Nutshell | `01` (V2, current) for ≥0.20; legacy dispatch for older | PASS |

**Spec (L61):** "The currently used version byte is `01`."
**Spec (L91):** "V1 keysets are 8 bytes long... **deprecated**."

**cashu-cf code:** `src/env.ts:496` defaults `getKeysetIdVersion()` to `'1'` (V1) when `KEYSET_ID_VERSION` env is unset. All deployed environments (testnut, rugs, signut, etc.) produce V1 keyset IDs (16 hex chars: `00` + 14 chars).

**Impact:** Wallets that compute V2 IDs per the current spec will see ID mismatches with cashu-cf mints. CDK and Nutshell both emit V2 IDs by default. This is tracked as **ISSUE-016** with a clear migration path (`KEYSET_ID_VERSION=dual` → `KEYSET_ID_VERSION=2`), but status is `todo` — not yet deployed.

**Mitigating factor:** The V2 derivation code EXISTS and is algorithmically correct in cashu-cf. It's gated behind a feature flag that defaults to V1.

### 2. Balance Equation: Strict Equality vs. Overpayment

| Implementation | Enforcement | Spec Alignment |
|----------------|-------------|----------------|
| **cashu-cf** | `inputAmount - outputAmount >= requiredFee` (allows overpayment) | Deviation — spec L40 shows `==` |
| **CDK** | `input_amount == output_amount + fee` (strict, in mint layer) | Strict |
| **Nutshell** | `sum_outputs + fees_inputs - sum_inputs == 0` (strict equality) | Strict |

cashu-cf intentionally permits overpayment (inputs exceeding required output+fee), matching Nutshell reference behavior per a code comment. This is **not a security risk** (mint never loses funds) and spec-compliant wallets computing exact fees always pass. But it's a literal deviation from the spec's `==` formulation.

Nutshell's audit notes its enforcement is "strictly stronger than spec" because it accounts for NUT-02 per-keyset input fees.

### 3. final_expiry Preimage Guard

| Implementation | Guard Condition | Spec Reference |
|----------------|----------------|----------------|
| **cashu-cf** | `if (finalExpiry && finalExpiry > 0)` | Correct — matches spec L86-87 |
| **CDK** | `if let Some(e) = expiry { if e > 0 { ... } }` | Correct — matches spec |
| **Nutshell** | `if final_expiry is not None:` (missing `!= 0`) | **WARN** — omits `!= 0` guard |

Nutshell's `derive_keyset_id_v2` (`keys.py:96-97`) omits the `and final_expiry != 0` clause from the spec reference. If `final_expiry == 0` were passed, Nutshell would include `|final_expiry:0` in the preimage, producing a different keyset ID than spec-strict implementations.

**Impact:** Negligible — `final_expiry == 0` means "expired at Unix epoch (1970)" which is semantically nonsensical and unreachable in any code path. All three auditors agree this is theoretical only.

### 4. final_expiry Storage and Emission

| Implementation | Stored in Keyset Metadata? | Emitted in API? |
|----------------|---------------------------|-----------------|
| **cashu-cf** | **No** — `KeysetMeta` type lacks `final_expiry` field | Always `null` (V2 derivation accepts it as param but `deriveKeysetFromParams` never passes it) |
| **CDK** | `Option<u64>` on `KeySet`/`KeySetInfo` | Omitted from JSON when `None` (via `skip_serializing_if`) |
| **Nutshell** | `Optional[int]` on `MintKeyset` | Emitted when set; `None` omitted via `response_model_exclude_none` |

cashu-cf cannot set keyset expiries at all — `final_expiry` is always `null` in responses. This is spec-compliant (MAY be omitted) but prevents operators from using the feature. Tracked as F3 (INFO).

### 5. `active` Field on `/v1/keys/{keyset_id}` Response

| Implementation | Behavior for Inactive Keyset Lookup |
|----------------|-------------------------------------|
| **cashu-cf** | **Hardcodes `active: true`** regardless of actual status (F2, MINOR) |
| **CDK** | `Option<bool>` — reflects actual status, omitted if None |
| **Nutshell** | `keyset.active` — reflects actual status |

cashu-cf's `router.ts:417` hardcodes `active: true` even when a wallet requests keys for an inactive keyset (to verify old proofs). This could mislead wallets into thinking they can mint new ecash from an inactive keyset.

### 6. Overflow Protection

| Implementation | Integer Overflow Handling |
|----------------|--------------------------|
| **cashu-cf** | JS `Number` — no explicit overflow check (safe up to 2^53) |
| **CDK** | `checked_add`/`checked_mul` with `AmountOverflow` error — robust |
| **Nutshell** | Python int (arbitrary precision) — no overflow possible |

CDK is the only implementation with explicit overflow protection in fee calculation. This is a robustness improvement beyond the spec.

### 7. VecSkipError on Response Deserialization (CDK-specific)

CDK uses `VecSkipError` on both `KeysetResponse.keysets` and `KeysResponse.keysets`, silently dropping malformed entries. This is a forward-compatibility design choice but could mask mint bugs. cashu-cf and Nutshell parse more strictly.

---

## Overall Assessment

**NUT-02 reveals the most significant inter-implementation divergence of the four NUTs compared.** While all three correctly implement the fee formula and keyset ID derivation *algorithms*, they diverge on **default configuration** and **strictness posture**:

### Critical Issue
- **cashu-cf defaults to deprecated V1 keyset IDs** (ISSUE-016). This is the only FAIL across all 12 signoffs in this comparison set. CDK and Nutshell both default to V2. The V2 code exists in cashu-cf and is correct, but the feature flag defaults to V1. **This is an interoperability risk** — wallets computing V2 IDs per the current spec will mismatch.

### Strictness Spectrum
- **Strictest:** Nutshell (15 PASS, 1 theoretical WARN, strict equality enforcement, reflects actual active status)
- **Middle:** CDK (clean PASS, overflow protection, but VecSkipError masks errors)
- **Most permissive:** cashu-cf (allows overpayment, hardcodes active:true, defaults to V1, doesn't store final_expiry)

### Interoperability
The fee calculation and V2 keyset ID derivation algorithms are **byte-for-byte identical** across all three. A wallet computing fees or keyset IDs will get the same results from any of the three implementations (assuming V2 is enabled on cashu-cf). The V1 default on cashu-cf is the sole interoperability barrier.

**Recommendation:** cashu-cf should prioritize ISSUE-016 (V1→V2 migration) as it is the only blocking interop issue across these three implementations.
