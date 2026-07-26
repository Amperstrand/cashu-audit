# Cross-Implementation Comparison: NUT-05 (Melting Tokens)

> **Generated**: 2026-07-26
> **Auditor**: GLM-5.2 in opencode
> **Source signoffs**:
> - `signoffs/cashu-cf/NUT-05-20260726-glm52.md` — cashu-cf @ c1e3907 (TypeScript / Cloudflare Workers)
> - `signoffs/cdk/NUT-05-20260726-glm52.md` — CDK @ d033f1b (Rust, type layer only)
> - `signoffs/nutshell/NUT-05-20260726-glm52.md` — nutshell @ 1853902 (Python / FastAPI)
> **Spec**: cashubtc/nuts NUT-05

## Executive Summary

All three implementations **PASS** NUT-05, but with meaningful divergence in compliance depth. **cashu-cf is the only implementation with a blocking FAIL** (incomplete `prefer_async` response shape), while CDK and Nutshell are fully spec-compliant on the audited surfaces. The three implementations converge on core melt semantics (three-endpoint structure, UNPAID/PENDING/PAID state machine, proof validation before payment) but diverge on five surface details: quote ID format, the `method` response field, the `options` field in NUT-06 settings, expiry enforcement, and `MeltMethodSetting` serialization shape.

**Important scope caveat**: The CDK audit covers the `crates/cashu/src` type layer only — mint handler logic (`cdk-mintd`) was explicitly out of scope. Behavioral requirements (async dispatch, proof validation, fee enforcement) could not be verified for CDK. The cashu-cf and Nutshell audits both covered the full request-to-response flow.

## Verdict Comparison

| Metric | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| **Overall verdict** | PASS *(conditional)* | PASS | PASS |
| **Scope** | Full melt flow (3,443 LOC) | Type layer only (`nut05.rs` + `nut23.rs`) | Full melt flow (`ledger.py` + `router.py`) |
| **PASS** | 25 | 12 | 18 |
| **FAIL** | **1** | 0 | 0 |
| **WARN** | 5 | 5 | 2 |
| **N/A** | 0 | 0 | 2 |
| **Blocking findings** | prefer_async response missing `amount`/`unit` | — | — |

## Requirement-by-Requirement Matrix

### Endpoint Structure

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Three endpoints (quote request, quote check, melt) | ✅ PASS | ✅ PASS | ✅ PASS |
| Backward-compat / legacy aliases | ✅ PASS (extra aliases) | — (type layer) | ✅ PASS |
| `method` matches `[a-z0-9_-]+` | ✅ PASS | ✅ PASS ⚠️ | ✅ PASS |
| Dynamic `{method}` path parameter routing | ⚠️ WARN (hardcoded `bolt11`) | ✅ PASS (supports custom) | ℹ️ Only `bolt11` supported (design limitation) |

**Divergence**: CDK is the only implementation with generic `PaymentMethod` infrastructure supporting custom method paths. cashu-cf hardcodes `bolt11` routes but embeds fiat-rail methods (`upi`/`payto`/`spayd`) inside BOLT11 descriptions — an intentional architectural choice. Nutshell supports only `bolt11` (single-member `Method` enum).

**CDK nuance**: `is_valid_custom_method_name()` accepts ASCII uppercase (`[a-zA-Z0-9_-]`) which is more permissive than the spec's `[a-z0-9_-]+`. Mitigated because all construction paths lowercase before storage, so wire values are always compliant.

### Quote ID Format (spec L75: "UUID v7 with all 74 variable bits from a CSPRNG")

| Implementation | Format | Entropy | Spec-compliant? |
|---|---|---|---|
| **cashu-cf** | 32-char hex (128-bit `crypto.getRandomValues`) | 128 bits | ❌ **WARN** — not UUID v7 |
| **CDK** | `Uuid::now_v7()` (uuid crate) | 74 bits + 48-bit timestamp | ✅ PASS |
| **Nutshell** | Manual UUID v7 (`generate_uuid_v7()`) | 74 bits (12+62) + 48-bit timestamp | ✅ PASS |

**Divergence**: cashu-cf is the **only implementation that does not use UUID v7**. It generates a 128-bit random hex string, which provides *more* entropy than required but lacks the time-ordering and version/variant nibbles of UUID v7. The code comment acknowledges the spec requirement but the implementation doesn't match. Collision resistance is higher than UUID v7; the main loss is time-based sorting of quotes in storage. No interop issue — quote IDs are opaque to wallets.

**CDK compatibility note**: CDK's `QuoteId` enum accepts both `UUID(Uuid)` and `BASE64(String)` for parsing, explicitly to handle Nutshell's legacy base64 quote IDs. CDK mints always *generate* UUID v7.

### Melt Quote Response Fields (spec L59-70)

| Field | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `quote` | ✅ | ✅ | ✅ |
| `request` | ✅ | ⚠️ Optional (REVIEW marker) | ✅ |
| `amount` | ✅ | ✅ | ✅ |
| `unit` | ✅ | ⚠️ Optional (REVIEW marker) | ✅ |
| `fee_reserve` | ✅ | ⚠️ Non-optional (stricter) | ✅ |
| `method` | ❌ **WARN** — omitted | ✅ | ✅ |
| `state` | ✅ | ✅ | ✅ |
| `expiry` | ✅ | ✅ | ✅ |

**Divergence on `method`**: cashu-cf stores `method` on the internal `ExtendedMeltQuote` object but never includes it in any API response (quote creation, status check, or melt response). CDK and Nutshell both include it. Impact is low — all endpoints are under `/bolt11/` paths so clients can infer the method.

**Divergence on `request`/`unit` optionality**: CDK declares both as `Option<...>` with explicit REVIEW comments: *"This is now required in the spec, we should remove the option once all mints update."* This is tracked backward-compat debt for deserializing responses from older mints. cashu-cf and Nutshell always populate these fields.

### Async Processing (`prefer_async`)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `prefer_async` field parsed with default `false` | ✅ PASS | ✅ PASS | ✅ PASS |
| Validation before async response (spec L132) | ✅ PASS | — (type layer) | ✅ PASS |
| Async response: 200 OK + `state: "PENDING"` | ✅ PASS | ✅ PASS (type) | ✅ PASS |
| Async response includes `quote`/`amount`/`unit`/`expiry` (spec L152-161) | ❌ **FAIL** — missing `amount`/`unit` | ✅ PASS (type) | ✅ PASS |
| Ignore `prefer_async` if async unsupported | ✅ PASS | — (type layer) | N/A (always supports async) |

**The single blocking FAIL across all three audits**: cashu-cf's `prefer_async` response returns only `{quote, state, expiry}` — missing the `amount` and `unit` fields the spec explicitly requires (L152-161). This is a 3-line fix. Wallets that don't cache the original quote amount/unit would need a follow-up GET request.

**Nutshell** handles async cleanly: `_prepare_melt` performs full validation and atomically sets quote+proofs to PENDING, then spawns `asyncio.create_task` for background payment. The response always uses `PostMeltQuoteResponse.from_melt_quote()` which includes all fields.

**CDK** cannot verify behavioral async semantics from the type layer — this requires a separate `cdk-mintd` handler audit.

### Fee Handling

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `fee_reserve` covers routing + additional fees | ✅ PASS | ✅ PASS (type) | ✅ PASS |
| NUT-02 per-keyset input fee calculated | ✅ PASS | ✅ PASS (type) | ✅ PASS |
| NUT-08 change = overpaid after settlement | ✅ PASS | ✅ PASS (type) | ✅ PASS |

**Convergence**: All three implementations agree on fee semantics. cashu-cf has the most detailed fee breakdown (`computeMeltFeeReserve()` = backendFee + virtualRoutingFee + additionalFee + feeReserveBuffer) with extensive observability logging.

### Atomicity & Rollback

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Reserve proofs before payment | ✅ PASS | — (type layer) | ✅ PASS |
| Commit to SPENT after successful payment | ✅ PASS | — (type layer) | ✅ PASS |
| Rollback on failure (proofs→UNSPENT, quote→UNPAID) | ✅ PASS | — (type layer) | ✅ PASS |

**cashu-cf** has the most extensively documented three-phase commit (Prepare → Pay → Commit/Rollback) with a dedicated proof state machine (`setProofPendingBatch`, `commitProofPending`, `rollbackProofPending`).

**Nutshell** achieves atomicity via `verify_and_set_melt_quote_pending` DB write and a conservative failure mode: if `pay_invoice` returns FAILED/UNKNOWN but status check differs, it globally disables melt (`self.disable_melt = True`) rather than risk double-spending. A `_check_pending_proofs_and_melt_quotes` regular task provides crash recovery.

**CDK** atomicity is a handler-layer concern not verifiable from types.

### Expiry Enforcement (spec L80)

| Implementation | Enforced at quote creation? | Enforced at melt execution? |
|---|---|---|
| **cashu-cf** | ✅ | ✅ (timestamp comparison) |
| **CDK** | ✅ (type: `expiry: u64`) | — (handler concern) |
| **Nutshell** | ✅ | ❌ **WARN** — not checked in `_prepare_melt` |

**Divergence**: Nutshell's `mint()` method explicitly checks `quote.expiry < int(time.time())` (ledger.py:526-527), but `_prepare_melt` omits this check. External Lightning payments are indirectly protected (backend rejects expired invoices), but internal settlements (`melt_mint_settle_internally`) have no external time constraint, so an expired internal melt quote could theoretically be settled. cashu-cf correctly enforces expiry at both stages.

### NUT-06 `MeltMethodSetting` `options` Field (spec L259-268)

| Implementation | `options` field present? | Serialization |
|---|---|---|
| **cashu-cf** | Not separately audited | — |
| **CDK** | ⚠️ **WARN** — hoists `amountless` to top level | `{"method":"bolt11","unit":"sat","amountless":true}` (no `options` wrapper) |
| **Nutshell** | ⚠️ **WARN** — field missing from model | `{"method":"bolt11","unit":"sat",...}` (no `options` key) |

**Convergence on non-compliance**: Both CDK and Nutshell deviate from the spec's `options: <Object|null>` structure, but in different ways. CDK serializes `amountless` at the top level (ergonomic choice, dual-mode deserializer accepts both shapes). Nutshell omits the field entirely (would always be `null`, stripped by `response_model_exclude_none`). Neither has functional impact since no NUT defines method-specific melt options for bolt11.

## Unique Findings Per Implementation

### cashu-cf-only findings
1. **FAIL — prefer_async response shape** (Finding 1): The only blocking finding across all three audits. Missing `amount`/`unit` in async response. Tracked as ISSUE-017 follow-up.
2. **WARN — Quote ID not UUID v7** (Finding 2): 128-bit hex instead of UUID v7. More entropy, wrong format.
3. **WARN — `method` field omitted from all responses** (Finding 3): Stored internally but never serialized.
4. **Positive — correct `>=` operator**: Explicitly verified that the melt path does NOT have the ISSUE-023-style `===` bug found in NUT-04. Uses `validateAmountTotal(totalInputAmount, requiredAmount, '>=')`.

### CDK-only findings
1. **WARN — Method validation accepts uppercase**: `is_valid_custom_method_name()` uses `is_ascii_alphanumeric()` (matches `[A-Za-z0-9]`) vs spec's `[a-z0-9_-]+`. Mitigated by construction-path lowercasing.
2. **WARN — `fee_reserve` non-optional in bolt11 response**: Stricter than spec (spec says optional). Safe — no conforming mint should omit it.
3. **Note — `QuoteState` extension variants**: Adds `Unknown` and `Failed` beyond spec's 3 states. `Unknown` is the `#[default]` — safe default avoiding false state reports. Internal/DB only; handler must not emit non-spec states on the wire.
4. **Note — DLEQ stripping on construction**: `MeltRequest::new()` calls `inputs.without_dleqs()` — correctly strips DLEQ metadata before serialization. Correct behavior.

### Nutshell-only findings
1. **WARN — Expiry not enforced at melt execution** (Finding 1): `_prepare_melt` skips the expiry check that `mint()` performs.
2. **Internal melt optimization** (non-spec): `melt_mint_settle_internally` settles melts matching existing mint quotes without hitting Lightning. Sets internal fees to 0, validates match, updates both quotes atomically.
3. **Conservative payment-state failure handling**: On FAILED/UNKNOWN payment state mismatch, globally disables melt rather than risk double-spend. Sound but requires manual intervention to re-enable.
4. **Crash recovery**: `_check_pending_proofs_and_melt_quotes` periodic task re-checks PENDING quotes with backend — provides resilience against background task failures.

## Convergence and Divergence Summary

### Areas of Full Convergence (all 3 agree)
- Three-endpoint structure (quote request, quote check, melt execution)
- UNPAID/PENDING/PAID state machine with correct wire serialization
- Proof validation before payment (signature, keyset, unit, amount, spending conditions)
- NUT-02 per-keyset input fee calculation
- NUT-08 change outputs for overpaid amounts
- `prefer_async` defaults to `false` when omitted

### Areas of Divergence

| # | Issue | cashu-cf | CDK | Nutshell | Severity |
|---|---|---|---|---|---|
| 1 | Quote ID format | ❌ 128-bit hex | ✅ UUID v7 | ✅ UUID v7 | **Medium** — only cashu-cf deviates |
| 2 | `method` in response | ❌ Omitted | ✅ Present | ✅ Present | **Low** — inferable from URL |
| 3 | `prefer_async` response shape | ❌ Missing `amount`/`unit` | ✅ (type) | ✅ Complete | **Medium** — only cashu-cf deviates |
| 4 | Expiry enforcement at melt | ✅ Enforced | — (handler) | ❌ Not enforced | **Low** — backend protects externally |
| 5 | `MeltMethodSetting.options` | — | ⚠️ Top-level `amountless` | ⚠️ Field absent | **Info** — no functional impact |
| 6 | Dynamic `{method}` routing | ⚠️ Hardcoded | ✅ Custom supported | ℹ️ `bolt11` only | **Info** — design choices |

## Recommendations

1. **cashu-cf — Fix the blocking FAIL (Finding 1)**: Add `amount`, `unit`, and `fee_reserve` to the `prefer_async` response at `melt.ts:2833-2837`. This is a 3-line fix and the only blocking finding across all three audits. *(Tracked under ISSUE-017.)*

2. **cashu-cf — Align quote ID format**: Migrate `generateQuoteId()` from 128-bit random hex to UUID v7 to match CDK and Nutshell. The current format has more entropy but breaks time-based sorting and format compliance.

3. **cashu-cf — Add `method` to responses**: Include the `method` field (already stored on the quote object) in all melt quote responses for spec parity with CDK and Nutshell.

4. **Nutshell — Enforce expiry at melt execution**: Add `if melt_quote.expiry and melt_quote.expiry < int(time.time()): raise TransactionError("quote expired")` to `_prepare_melt`, mirroring the existing `mint()` check. Closes the internal-settlement expiry gap.

5. **CDK — Complete the audit**: The type-layer-only scope means behavioral requirements (async dispatch, proof validation, fee enforcement, atomicity) are unverified. A `cdk-mintd` handler audit is needed for full NUT-05 coverage comparable to cashu-cf and Nutshell.

6. **CDK & Nutshell — Consider `options` field alignment**: Both deviate from the spec's `options: <Object|null>` in `MeltMethodSetting`. Low priority — no functional impact today, but wallets expecting the wrapper may need null-coalescing.

7. **Cross-impl — Quote ID interop**: CDK already accommodates Nutshell's legacy base64 quote IDs via a `BASE64(String)` parse variant. If cashu-cf migrates to UUID v7, all three implementations will converge on a common generate format, simplifying interop testing.

## Audit Scope Comparison

| Dimension | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Lines of code reviewed | 3,443 (+ supporting) | ~1,000 (2 Rust files) | ~2,200 (6 Python files) |
| Handler logic audited | ✅ Full | ❌ Type layer only | ✅ Full |
| Behavioral requirements verified | ✅ | ❌ | ✅ |
| Atomicity/rollback verified | ✅ | ❌ | ✅ |
| Test coverage referenced | ✅ (ISSUE-023 cross-ref) | ✅ (unit tests cited) | ✅ (code paths traced) |

**Note**: The CDK audit's type-layer-only scope is a methodology difference, not a deficiency. Rust's type system enforces many constraints at compile time that TypeScript and Python handle at runtime. However, behavioral requirements (async dispatch, proof state transitions, fee enforcement) inherently require handler-layer review.
