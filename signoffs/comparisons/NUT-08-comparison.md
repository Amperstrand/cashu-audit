# Cross-Implementation Comparison: NUT-08 (Lightning Fee Return / Overpaid Fees)

> **Generated**: 2026-07-26
> **Auditor**: GLM-5.2 in opencode
> **Source signoffs**:
> - `signoffs/cashu-cf/NUT-08-20260726-glm52.md` — cashu-cf @ c1e3907 (TypeScript / Cloudflare Workers)
> - `signoffs/cdk/NUT-08-20260726-glm52.md` — CDK @ d033f1b (Rust, mint + wallet layers)
> - `signoffs/nutshell/NUT-08-20260726-glm52.md` — nutshell @ 1853902 (Python / FastAPI)
> **Spec**: cashubtc/nuts NUT-08 (`optional`, depends on NUT-05)

## Executive Summary

All three implementations **PASS** NUT-08. The single explicit spec MUST — return all value > 0 signatures in the same order as blank outputs received, omit value-0 signatures (L43) — is satisfied across all three. The implementations converge on the core blank-output lifecycle: wallet supplies outputs → mint computes overpaid fees → mint decomposes to keyset denominations → mint imprints amounts preserving order → mint returns only non-zero signatures.

The most significant divergence is the **overpaid fee formula**: cashu-cf's synchronous path subtracts `virtualRoutingFee` and `additionalFee` (mint profit, not LN fees) from the overpaid amount, yielding less change than the strict spec formula — and inconsistently, the async settlement paths omit these subtractions, meaning the same inputs produce different change depending on settlement path. CDK and Nutshell both use the exact spec formula (`input_amount − fees − total_paid`). Secondary divergences include insufficient-blank-outputs handling (cashu-cf rejects; CDK and Nutshell gracefully degrade) and change serialization when no change is due (Nutshell serializes `[]`; cashu-cf and CDK omit the field).

**Scope note**: The CDK audit is unique in covering **both** the mint layer (`process_melt_change` in `shared.rs`) and the **wallet layer** (`melt/saga/mod.rs` + `PreMintSecrets::from_seed_blank`). The cashu-cf and Nutshell audits cover the mint flow only (wallet-side blank output generation is out of scope for a mint audit).

## Verdict Comparison

| Metric | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| **Overall verdict** | PASS | PASS | PASS |
| **Scope** | Full mint flow (3,443 LOC) + async settlement paths | Mint + wallet layers (shared.rs + saga + nut13.rs) | Full mint flow (ledger.py + split.py + verification.py) |
| **PASS** | 14 | 7 | 11 |
| **FAIL** | 0 | 0 | 0 |
| **WARN** | 3 | 1 | 2 |
| **N/A** | 0 | 0 | 0 |
| **Blocking findings** | — | — | — |

## Requirement-by-Requirement Matrix

### Explicit MUST (L43): Ordered return of value > 0 signatures, omission of value-0

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Return all > 0 signatures in same order as blank outputs | ✅ PASS | ✅ PASS | ✅ PASS |
| Omit all value-0 signatures | ✅ PASS | ✅ PASS | ✅ PASS |
| Mechanism | `.filter(o => o.amount > 0)` on ordered array | `zip` truncation; `Amount::split()` only produces positive denominations | `outputs[:n_return_outputs]` truncation; `amount_split` only produces non-zero summands |

**Convergence**: All three satisfy the MUST. The ordering guarantee is structurally enforced: cashu-cf filters an ordered array, CDK uses Rust's index-preserving `Iterator::zip`, and Nutshell slices the first `n` outputs. Zero-value signatures are never produced because all three decomposition functions only generate positive-denomination summands.

### Overpaid Fee Formula (L39: `overpaid_fees = input_amount - fees - total_paid`)

| Implementation | Formula | Spec match? |
|---|---|---|
| **cashu-cf (sync)** | `totalInputAmount − mintFee − (quote.amount + effectiveFeeSats) − virtualRoutingFee − additionalFee` | ⚠️ **WARN** — subtracts mint profit (`virtualRoutingFee`, `additionalFee`) |
| **cashu-cf (async)** | `totalInputAmount − mintFee − (quote.amount + actualFeeSats)` | ⚠️ **WARN** — omits `virtualRoutingFee`/`additionalFee` (drift from sync) |
| **CDK** | `inputs_amount − total_spent − inputs_fee` | ✅ Exact match |
| **Nutshell** | `fee_provided − fee_paid` | ✅ Exact match |

**This is the primary cross-implementation divergence.** See §Key Divergences below.

### Blank Output Count (L15, L19-25: `max(ceil(log2(fee_reserve)), 1)`)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Formula implemented | ✅ PASS (`Math.max(Math.ceil(Math.log2(reserve)), 1)`) | ✅ PASS (`(log2 as f64).ceil() as u64).max(1)`) | — (wallet-side concern) |
| Returns 0 if `fee_reserve == 0` | ✅ PASS | ✅ PASS (early return empty) | — |
| Mint enforces minimum count | ✅ PASS (rejects with 400) | — (degrades gracefully) | — (degrades gracefully) |

**Divergence on enforcement**: cashu-cf is the only implementation that **rejects** melt requests providing fewer blank outputs than the formula requires (HTTP 400). CDK and Nutshell both gracefully degrade (keep largest denominations, drop smallest). cashu-cf's stricter posture prevents silent fund loss but goes beyond the spec (which makes output count a wallet responsibility).

### Amount Field Ignored (L115)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `amount` in blank `BlindedMessage`s ignored by mint | ✅ PASS (`requireAmount=false` validation) | ✅ PASS (unconditionally overwrites: `blinded_message.amount = *amount`) | ✅ PASS (`skip_amount_check=True` + amount overwrite) |

**Convergence**: All three discard the wallet-supplied amount and overwrite with the mint-computed denomination. Correct invariant across the board.

### `change` Field Conditional Return (L37: ONLY IF outputs provided AND inputs > total_paid − fees)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Logical condition correct | ✅ PASS | ✅ PASS | ✅ PASS |
| Field omitted when no change | ✅ PASS (conditionally spread) | ✅ PASS (`skip_serializing_if = Option::is_none`) | ⚠️ **WARN** — serialized as `[]` |

**Divergence**: Nutshell always sets `melt_quote.change = return_promises` (which defaults to `[]`), and `response_model_exclude_none=True` strips `None` but not empty lists. The response JSON contains `"change": []` in no-change cases. The spec's "ONLY IF" wording implies the field should be absent. Functionally equivalent — all surveyed wallets treat `[]`, `null`, and absent as "nothing to claim".

### NUT-06 Advertisement (L139-147)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `nuts.8: { "supported": true }` | ✅ PASS (env-overridable) | ✅ PASS (builder, enabled by default) | ✅ PASS (unconditional) |

**Convergence**: All three advertise NUT-08 support.

### Async / Late-Settlement Path

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Change computed on async settlement | ✅ PASS (MeltQuoteDO + Blink poll) | ✅ PASS (`finalize_melt_quote` → `process_melt_change`) | ✅ PASS (`get_melt_quote` late-settle branch) |
| Formula consistency with sync path | ❌ **WARN** — async omits `virtualRoutingFee`/`additionalFee` | ✅ Same formula | ✅ Same formula |

## Key Divergences

### 1. Overpaid Fee Formula (most significant)

The spec defines: `overpaid_fees = input_amount - fees - total_paid` (L39).

| Implementation | Deviation | Direction | Impact |
|---|---|---|---|
| **cashu-cf (sync)** | Subtracts `virtualRoutingFee` + `additionalFee` (mint profit) | Mint keeps more → user gets **less** change | Non-blocking; in Blink passthrough mode both are 0 (spec-compliant) |
| **cashu-cf (async)** | Omits `virtualRoutingFee`/`additionalFee` | User gets **more** change than sync path | Behavioral drift between code paths |
| **CDK** | Exact spec formula | — | None |
| **Nutshell** | Exact spec formula | — | None |

**Net effect for cashu-cf**: The same melt inputs produce different change amounts depending on whether settlement is synchronous or asynchronous. In Blink passthrough mode (`blinkPassThrough=true`), the sync formula aligns with the spec. For non-Blink backends, the user receives less change than a strict spec reading yields. Neither direction is a security issue — the mint either keeps more or gives more — but the inconsistency between code paths is a behavioral drift that could surprise wallet authors testing across settlement modes.

### 2. Insufficient Blank Outputs Handling

| Implementation | Behavior | Rationale |
|---|---|---|
| **cashu-cf** | Rejects with HTTP 400 ("Not enough blank outputs for fee_reserve") | Prevents silent fund loss; stricter than spec |
| **CDK** | Sorts amounts descending, `zip` truncates to `change_outputs.len()`, drops smallest | Least-harm degradation; only triggers with buggy/non-CDK wallets |
| **Nutshell** | Same as CDK: `n_return_outputs = min(len(outputs), len(return_amounts))`, keeps largest | Documented in docstring: "a smaller amount will be returned" |

**Analysis**: The spec makes output count a wallet responsibility ("wallets *should* send `max(ceil(log2(fee_reserve)), 1)`"). cashu-cf's rejection is the most defensive posture. CDK and Nutshell both degrade by keeping the largest denominations and dropping the smallest — the least-harm option when the wallet under-provides. In practice, all CDK/Nutshell wallets compute the correct count, so the degradation path is rarely exercised.

### 3. Change Serialization When No Change Due

| Implementation | Wire format when no change | Spec alignment |
|---|---|---|
| **cashu-cf** | `change` field omitted from response JSON | ✅ Matches "ONLY IF" wording |
| **CDK** | `change` field absent (`skip_serializing_if = Option::is_none`) | ✅ Matches "ONLY IF" wording |
| **Nutshell** | `"change": []` in response JSON | ⚠️ Stylistic divergence — `exclude_none` doesn't strip empty lists |

**Impact**: None functionally. All surveyed wallets (cashu-ts, CDK, Nutshell's own wallet) treat `change: []`, `change: null`, and absent field as semantically identical. Nutshell's divergence is cosmetic.

### 4. Backend Fee Reporting Failure

| Implementation | Behavior when backend omits `fee` on SETTLED | Flagged? |
|---|---|---|
| **cashu-cf** | Uses `actualFeeSats` from backend; behavior on missing fee not separately flagged | Not flagged |
| **CDK** | Uses `total_spent` from backend; behavior on missing fee not separately flagged | Not flagged |
| **Nutshell** | `fee_paid` defaults to 0 → full fee reserve returned to wallet → mint absorbs LN fee silently | ⚠️ **WARN** — generous failure mode |

**Impact**: Nutshell's default-to-0 means a Lightning backend that reports SETTLED without a `fee` value triggers a silent full refund of the reserve. The mint loses money on every such settlement. The spec assumes the mint can determine the actual fee (L29); the failure mode is unspecified. Nutshell's choice (treat as 0) is reasonable but worth flagging for operators using backends with weak fee reporting.

### 5. B_ Reuse / Idempotency Recovery (cashu-cf only)

cashu-cf implements `OutputsAlreadySignedError` recovery: if change outputs' `B_` values were already signed (e.g., retry after partial success), the code replays stored signatures from `BlindedMessageTracker`. This is a pragmatic idempotency measure not mentioned in the spec (WARN — implementation-specific behavior). CDK and Nutshell do not implement B_ reuse recovery for change outputs. Nutshell instead scrubs unsigned blank outputs from the DB to prevent reuse across melt attempts.

## Unique Findings Per Implementation

### cashu-cf-only findings
1. **WARN — Overpaid formula includes mint-kept fees** (N08-O1): Sync path subtracts `virtualRoutingFee`/`additionalFee`. In Blink passthrough mode, both are 0 (spec-compliant). For non-Blink backends, user gets less change.
2. **WARN — B_ reuse recovery not spec-defined** (N08-O2): Pragmatic idempotency for retries. Prevents user fund loss. Acceptable as-is.
3. **WARN — Async formula drift** (N08-A3): Async paths use simpler formula. Same inputs → different change depending on settlement path. Favors user (more change returned).
4. **Positive — Minimum blank output count enforced**: Rejects insufficient outputs with 400, preventing silent fund loss. Stricter than spec.
5. **Positive — Keyset validation**: Change output keyset validated against input keysets or active keysets; prevents cross-unit change signing.
6. **Positive — Change signatures persisted on quote**: Enables wallets that poll quote state to retrieve change after async settlement.

### CDK-only findings
1. **WARN — Degraded change return with insufficient blank outputs** (WARN-1): When `change_outputs.len() < amounts.len()`, sorts descending and drops smallest. Only triggers with buggy/non-CDK wallets. Least-harm degradation.
2. **Positive — Wallet-side coverage**: Unique in auditing the wallet melt saga's blank output generation (`PreMintSecrets::from_seed_blank`), confirming the wallet always provides sufficient outputs.
3. **Positive — DB ordering test**: `test_blind_signature_order_in_db` integration test verifies DB preserves blank output insertion order — the prerequisite for the MUST's ordering requirement.
4. **Positive — Two-layer architecture**: Clean separation between `cashu` crate (types) and `cdk` crate (mint logic). `process_melt_change` is well-factored and reusable.

### Nutshell-only findings
1. **WARN — `change` serialized as `[]` instead of omitted** (Finding 1): Cosmetic divergence. All wallets handle it identically.
2. **WARN — Silent full-refund when backend omits fee** (Finding 2): `fee_paid` defaults to 0. Mint absorbs LN fee silently. Generous failure mode (favors wallet).
3. **Positive — Unsigned blank outputs scrubbed**: Leftover outputs deleted from DB after change generation, preventing blank-output reuse across melt attempts. Good hygiene.
4. **Positive — DLEQ on change signatures**: `get_melt_quote` regenerates NUT-12 DLEQ proofs for change signatures on every read, confirming change signatures are full first-class `BlindSignature`s.
5. **Positive — Two consistent code paths**: Both `_execute_melt_payment` (sync) and `get_melt_quote` (late-settle) call the same `_generate_change_promises` with identical computation. No formula drift.

## Convergence and Divergence Summary

### Areas of Full Convergence (all 3 agree)
- MUST: value > 0 signatures returned in order; value-0 signatures omitted
- Blank-output `amount` field ignored by mint (overwritten with imprinted denomination)
- 2^n denomination decomposition (greedy largest-first)
- `change` returned only when overpaid > 0 AND outputs provided
- NUT-06 `nuts.8` advertisement
- Change computed identically across sync and async settlement (CDK, Nutshell)

### Areas of Divergence

| # | Issue | cashu-cf | CDK | Nutshell | Severity |
|---|---|---|---|---|---|
| 1 | Overpaid fee formula | ⚠️ Includes mint profit (sync) / omits it (async) | ✅ Exact spec | ✅ Exact spec | **Medium** — cashu-cf-only deviation + internal inconsistency |
| 2 | Insufficient blank outputs | ❌ Rejects (400) | ⚠️ Degrades (drops smallest) | ⚠️ Degrades (drops smallest) | **Low** — spec makes this wallet responsibility |
| 3 | `change` serialization when empty | ✅ Omitted | ✅ Omitted | ⚠️ `[]` | **Info** — cosmetic, no functional impact |
| 4 | Backend fee = 0 on SETTLED | Not flagged | Not flagged | ⚠️ Full refund (mint absorbs fee) | **Low** — operational, unspecified by spec |
| 5 | B_ reuse idempotency recovery | ⚠️ Implementation-specific | — | Scrubs unused outputs | **Info** — cashu-cf-only extension |
| 6 | Wallet-side output generation audited | — (mint only) | ✅ (melt saga) | — (mint only) | **Methodology** — CDK covers both layers |

## Recommendations

1. **cashu-cf — Align overpaid fee formula across code paths**: The sync path (`melt.ts:3081`) and async paths (`melt-quote-do.ts:205`, `poll-melts.ts:202`) should use the same formula. Either (a) subtract `virtualRoutingFee`/`additionalFee` in both paths (consistent, mint-favoring), or (b) remove them from the sync path to match the spec formula exactly. Document the chosen policy.

2. **cashu-cf — Document or remove mint-kept fee subtraction**: The `virtualRoutingFee` and `additionalFee` subtractions are mint profit, not LN fees. If intentional, document as fee policy. If not, align with the spec formula (`input_amount − fees − total_paid`).

3. **Nutshell — Distinguish "fee unknown" from "fee is zero"**: When a backend reports SETTLED with `fee=None`, either log a warning for operators or treat as unknown-fee state (skip change, hold reserve). Defaulting to 0 silently absorbs the LN fee.

4. **Nutshell — Consider omitting `change` when empty**: Initialize `return_promises = None` and only assign when `outputs` is truthy and `overpaid_fee > 0`, or add `response_model_exclude_default` to strip empty lists. Low priority — cosmetic divergence.

5. **CDK — Consider logging when truncation occurs**: When `change_outputs.len() < amounts.len()` and the degradation path fires, a `warn!` log (currently only `debug!`) would help operators detect non-compliant wallets.

6. **Cross-impl — Sync/async consistency testing**: Given cashu-cf's formula drift between settlement paths, a cross-implementation test that melts the same invoice via sync and async settlement and asserts identical change would catch this class of bug.

## Overall Assessment

NUT-08 is well-implemented across all three codebases. The explicit MUST (ordered return, zero-omission) is satisfied everywhere with strong structural guarantees. The primary area of concern is cashu-cf's overpaid fee formula, which deviates from the spec in two ways: (1) the sync path subtracts mint-kept fees (reducing user change), and (2) the async path omits them (creating internal inconsistency). Neither deviation is a security issue, but both represent correctness drift from the spec's formula. CDK and Nutshell both implement the exact spec formula with no internal inconsistency. CDK uniquely provides wallet-side coverage, confirming the full blank-output lifecycle from generation to imprinting. The implementations are interoperable — the MUST is satisfied, and the divergences are in policy details (how much change, what to do with insufficient outputs) rather than protocol structure.
