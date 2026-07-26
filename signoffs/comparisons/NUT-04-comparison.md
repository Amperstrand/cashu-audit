# Cross-Implementation Comparison: NUT-04 (Minting Tokens)

> **Generated**: 2026-07-26
> **Auditor**: GLM-5.2 in opencode
> **Source signoffs**:
> - `signoffs/cashu-cf/NUT-04-20260726-glm52.md` — cashu-cf @ c1e3907 (TypeScript / Cloudflare Workers)
> - `signoffs/cdk/NUT-04-20260726-glm52.md` — CDK @ d033f1b (Rust, full stack)
> - `signoffs/nutshell/NUT-04-20260726-glm52.md` — nutshell @ 1853902 (Python / FastAPI)
> **Spec**: cashubtc/nuts NUT-04 @ 734f60e

## Executive Summary

All three implementations **PASS** NUT-04 with zero blocking FAILs — a cleaner outcome than the NUT-05 comparison (where cashu-cf had a blocking `prefer_async` FAIL). All three converge on core minting semantics: three-endpoint structure, accounting-field responses, UUID-quality quote IDs, and over-issuance prevention. The implementations diverge most sharply on **partial minting** (CDK fully supports it, Nutshell actively rejects it, cashu-cf accepts it in validation but breaks it in lifecycle), **quote ID secrecy** (cashu-cf embeds the quote ID in the invoice description, weakening the front-running protection the spec mandates), and **`updated_at` monotonicity** (only CDK achieves strict sub-second monotonicity).

Unlike the NUT-05 audit where CDK was type-layer-only, **all three NUT-04 audits covered full handler logic** — CDK's audit spanned 10 files across the type layer, domain model, enforcement logic, database layer, HTTP routing, and database test suite. This makes cross-implementation behavioral comparison fully valid.

## Verdict Comparison

| Metric | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| **Overall verdict** | PASS | PASS | PASS |
| **Scope** | Full mint flow (1496 LOC + supporting) | Full stack (10 files: types → domain → enforcement → DB → routing → tests) | Full mint flow (~965 LOC across 11 files) |
| **PASS** | 7 | 15 | 17 |
| **FAIL** | 0 | 0 | 0 |
| **WARN** | 5 | 3 | 3 |
| **N/A** | 2 | 0 | 1 |
| **Blocking findings** | — | — | — |

**Note on PASS count variation**: The raw counts are not directly comparable because each audit decomposed requirements at different granularities (cashu-cf: 10 requirements + 4 divergences; CDK: 14 MUST + 1 SHOULD + 3 design observations; Nutshell: 12 MUSTs + 1 SHOULD + 5 semantic checks). The normalized compliance picture is: all three satisfy every NUT-04 MUST on the audited surfaces.

## Requirement-by-Requirement Matrix

### Endpoint Structure

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Three endpoints (quote request, quote check, mint) | ✅ PASS | ✅ PASS | ✅ PASS |
| `method` matches `[a-z0-9_-]+` (spec L33) | ✅ PASS | ✅ PASS | ✅ PASS |
| Dynamic `{method}` path parameter routing | ⚠️ Hardcoded `bolt11` | ✅ Custom methods supported | ℹ️ Only `bolt11` (N/A) |
| Custom method name validation (spec L132) | N/A (no custom methods) | ✅ PASS (`is_valid_custom_method_name`) | N/A (no custom methods) |
| Ignore unrecognized fields (spec L142) | ✅ PASS | ✅ PASS (explicit `IgnoredAny` + serde defaults) | ✅ PASS (Pydantic `extra='ignore'`) |

**Divergence**: CDK is the only implementation with generic custom payment method infrastructure. `is_valid_custom_method_name()` validates ASCII alphanumeric/hyphen/underscore at route registration (`cdk-axum/custom_router.rs:67-77`), and custom method responses include all required accounting fields (`MintQuoteCustomResponse`). cashu-cf and Nutshell both hardcode `bolt11` routes with no dynamic method dispatch — functional for bolt11, but the custom method feature is absent.

### Accounting Fields in Responses (spec L81)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `amount_paid` present | ✅ PASS | ✅ PASS | ✅ PASS |
| `amount_issued` present | ✅ PASS | ✅ PASS | ✅ PASS |
| `updated_at` present | ✅ PASS | ✅ PASS | ✅ PASS |
| `amount_paid`/`amount_issued` non-negative integers | ✅ PASS | ✅ PASS (u64 type-level guarantee) | ✅ PASS |
| `amount_issued` ≤ `amount_paid` | ✅ PASS (trivially — `amount_issued` always 0) | ✅ PASS (`OverIssue` error at domain model) | ✅ PASS (state setter invariant) |

**Convergence**: All three implementations include the three accounting fields in all mint quote responses. CDK's type system (`Amount<U = ()>` wrapping `u64`) makes negative values unrepresentable at compile time — the strongest guarantee. Nutshell enforces the invariant via the state setter (`base.py:646-659`), which only ever sets `amount_paid`/`amount_issued` to `0` or the positive quote amount.

**Key divergence on `amount_issued` tracking**: cashu-cf **always returns `amount_issued: 0`** in every response — the value is never persisted or incremented. CDK and Nutshell both track `amount_issued` to reflect actual issuance. This means cashu-cf cannot signal to wallets that a partial mint has occurred (relevant for multi-pass minting — see Partial Minting below).

### Output Amount Validation (spec L83, L118)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Total output ≤ `amount_paid - amount_issued` | ✅ PASS (`<=`, post-ISSUE-023 fix) | ✅ PASS (`<=` via `amount_mintable()`) | ✅ PASS (`==`, stricter than spec) |
| Over-issuance prevented | ✅ PASS | ✅ PASS (domain-level `OverIssue` error) | ✅ PASS |

**Critical divergence — the validation operator**:

| Implementation | Operator | Spec compliance | Behavior |
|---|---|---|---|
| **cashu-cf** | `<=` (`validateAmountTotal(..., '<=')`) | ✅ Spec-compliant | Accepts partial and full mints (validation allows output < mintable) |
| **CDK** | `<=` (`amount_mintable()` subtraction + `TransactionUnbalanced` error) | ✅ Spec-compliant | Accepts partial and full mints; tracks `amount_issued` incrementally |
| **Nutshell** | `==` (`sum_amount_outputs == quote.amount`) | ⚠️ Stricter than spec | **Rejects** partial mints — requires exact amount match |

cashu-cf's `<=` operator is the result of the **ISSUE-023 fix** (changed from `===` to `<=`), explicitly documented at `mint.ts:1067-1073`. This was the known bug that this audit cycle was partly designed to verify.

Nutshell's strict equality is **safe** (cannot over-issue) but **functionally limiting** — it blocks the partial-mint use case described in spec L83: "If a wallet mints less than the currently mintable amount, `amount_issued` only increases by the amount that was issued." The Nutshell audit explicitly notes this is not a MUST violation (the spec uses descriptive language, not "MUST support partial minting").

### `updated_at` Semantics (spec L85)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Updated when `amount_paid`/`amount_issued` changes | ❌ **WARN** — recomputed from wall clock on every response, never persisted | ✅ PASS (SQL `UPDATE ... SET updated_at = CASE ...`) | ✅ PASS (`_set_mint_quote_state` sets `updated_at = int(time.time())` on every transition) |
| Monotonically increases (strict, sub-second) | ❌ **WARN** — 1-second resolution, not strictly increasing | ✅ PASS (SQL CASE: `current_time > updated_at + 1 ? current_time : updated_at + 1`) | ❌ **WARN** — 1-second resolution, not strictly increasing |

**This is the area of greatest three-way divergence:**

**CDK** is the only implementation achieving strict sub-second monotonicity. Its SQL `CASE WHEN :current_time > updated_at + 1 THEN :current_time ELSE updated_at + 1 END` expression guarantees that two updates in the same second always produce incrementing values (`updated_at + 1`). This is backed by a generic database test suite (`database/mint/test/mint.rs:1190-1327`) that validates the behavior across all DB backends.

**Nutshell** persists `updated_at` correctly (set on every state transition in `_set_mint_quote_state`), but uses `int(time.time())` with 1-second resolution. Two transitions within the same wall-clock second produce identical values. The audit notes this is practically harmless because Lightning payment confirmation introduces seconds-to-minutes latency, making same-second transitions unlikely.

**cashu-cf** has the weakest implementation: `updated_at` is **never persisted** — it is recomputed as `nowSec()` (wall clock) on every response. A GET status check at T1 returns `updated_at=T1`; another GET at T2>T1 returns `updated_at=T2` even if nothing changed. The field does not reflect when accounting values changed; it reflects when the response was generated. Additionally, like Nutshell, it uses 1-second resolution without strict monotonicity.

**Impact assessment**: cashu-cf's approach is functionally safe for wallet staleness checks (wall clock only increases, so `updated_at` never goes backwards), but it fails to signal meaningful accounting changes. Nutshell's approach is correct in principle but lacks sub-second precision. CDK's approach is fully spec-compliant.

### Quote ID Security (spec L89)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `quote` MUST remain secret | ⚠️ **WARN** — embedded in invoice description | ✅ PASS | ✅ PASS |
| `quote` MUST NOT be derivable from payment request | ✅ PASS (not derived) ⚠️ (but embedded) | ✅ PASS | ✅ PASS |
| `quote` SHOULD be UUID v7 (spec L89) | ❌ **WARN** — 32-char hex (128-bit CSPRNG) | ✅ PASS (`Uuid::now_v7()`) | ✅ PASS (`generate_uuid_v7()`) |

**The most significant security divergence**: cashu-cf embeds the full 32-character quote ID in the BOLT11 invoice description field as `` `quote ${quoteId}` `` (`mint.ts:341`). The BOLT11 payment request is self-contained — anyone who decodes it can read the description field and extract the quote ID. This directly enables the front-running attack the spec warns about at L89: "A third party who knows the `quote` ID can front-run and steal the tokens."

This is classified as **Medium severity** in the cashu-cf audit — the highest severity finding across all three NUT-04 audits. Mitigations exist (custom description replaces the quote ID; NUT-20 pubkey locks prevent unauthorized minting), but the default code path is vulnerable. A stale code comment at `mint.ts:339` claims "Use short 16-character quote ID only" but the code embeds the full 32-char ID.

CDK and Nutshell both generate quote IDs completely independent of the payment request and never embed them in invoice metadata.

**Quote ID format**: cashu-cf is the only implementation not using UUID v7. Its 128-bit random hex provides *more* entropy than UUID v7's 74 variable bits, but lacks time-ordering and version/variant nibbles. This is the same divergence pattern seen in the NUT-05 comparison.

### Mint Execution Response (spec L120-128)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Response is `{ "signatures": [...] }` | ✅ PASS | ✅ PASS (`MintResponse { signatures: Vec<BlindSignature> }`) | ✅ PASS |
| No extra fields in mint response | ✅ PASS | ✅ PASS | ✅ PASS |

**Full convergence**: All three implementations return exactly `{ "signatures": [...] }` from the mint execution endpoint, matching spec L122-128.

## Partial Minting — The Three-Way Split

The starkest behavioral divergence across the three implementations is their handling of partial mints (minting less than `amount_paid - amount_issued` in a single request):

| Implementation | Validation accepts partial? | `amount_issued` tracked? | Multi-pass lifecycle? | Verdict |
|---|---|---|---|---|
| **CDK** | ✅ `<=` | ✅ Incremental (`add_issuance` with `OverIssue` guard) | ✅ Quote stays mintable until `amount_issued >= amount_paid` | **Fully supported** |
| **cashu-cf** | ✅ `<=` (post-ISSUE-023) | ❌ Always `0` | ❌ `finalizeMintQuoteIssued` sets `ISSUED`/`consumed` after first mint | **Validation allows, lifecycle breaks** |
| **Nutshell** | ❌ `==` (strict equality) | N/A (full amount only) | ❌ Rejected at validation | **Not supported (stricter than spec)** |

**CDK** is the reference implementation for partial minting: `MintQuote::add_issuance()` increments `amount_issued` and guards against over-issuance (`if new_amount_issued > self.amount_paid { return Err(OverIssue) }`). A wallet can mint 50 of 100 sats, then return to mint the remaining 50.

**cashu-cf** has an incomplete partial-mint implementation. The ISSUE-023 fix correctly changed the validation from `===` to `<=`, allowing partial mint amounts. However, the downstream lifecycle was not updated: `finalizeMintQuoteIssued` unconditionally sets `state = ISSUED` and `consumed = true` after any mint, without incrementing `amount_issued`. A wallet that mints 50 of 100 sats cannot return for the remaining 50 — the quote is fully consumed. This is tracked as a low-severity finding since no known wallet uses multi-pass partial minting today.

**Nutshell** explicitly rejects partial mints with strict equality (`sum_amount_outputs == quote.amount`). The state setter jumps `amount_issued` from `0` to the full quote amount in one step. This is safe but blocks the partial-mint use case. The Nutshell audit notes this is not a MUST violation.

## Unique Findings Per Implementation

### cashu-cf-only findings
1. **WARN (Medium) — Quote ID embedded in invoice description** (Finding 1): The full 32-char quote ID is embedded in the BOLT11 description as `"quote <quoteId>"`. Anyone decoding the payment request can extract the quote ID and front-run the mint. Stale comment claims only 16 chars are used. Mitigated by custom descriptions and NUT-20 pubkey locks.
2. **WARN (Low) — `updated_at` not persisted** (Finding 2): Recomputed as wall-clock time on every response. Does not reflect when accounting values changed. Functionally safe but semantically incorrect.
3. **WARN (Low) — `updated_at` lacks sub-second monotonicity** (Finding 3): `nowSec()` has 1-second resolution; same-second updates produce identical values.
4. **WARN (Low) — Partial-mint lifecycle incomplete** (Finding 4): ISSUE-023 fixed validation (`<=`) but finalization always marks quote as fully consumed. `amount_issued` never incremented.
5. **INFO — Quote ID not UUID v7** (Finding 5): 32-char hex from CSPRNG (128 bits). More entropy than UUID v7's 74 bits, but wrong format. Low priority (SHOULD, not MUST).
6. **Positive — ISSUE-023 fix confirmed**: `mint.ts:1067-1073` verified using `<=` operator. The `===` bug is resolved in production code.

### CDK-only findings
1. **WARN (Info) — Legacy `state` field retained** (Finding 1): `MintQuoteBolt11Response` includes a `state: QuoteState` field removed from the current spec. Redundant with accounting fields but harmless (spec L142: unrecognized fields must be ignored). `MintQuoteCustomResponse` correctly omits it.
2. **WARN (Info) — `unit`/`amount` are `Option<>`** (Finding 2): Spec shows `unit` as required; CDK declares both as `Option<>` with REVIEW comments acknowledging they should be non-optional. Wire format is always correct (builders always set `Some(...)`); only affects deserialization tolerance.
3. **WARN (Low) — `updated_at` monotonicity at SQL layer only** (Finding 3): The CASE-statement guarantee is in the SQL implementation. The domain model's `add_payment`/`add_issuance` do not update `updated_at` themselves — they rely on the database layer. Non-SQL backends must replicate independently. Mitigated by the generic test suite validating all backends.
4. **Positive — Domain-level over-issuance prevention**: `MintQuote::add_issuance()` returns `OverIssue` error before any signature is generated — defense-in-depth beyond HTTP-layer validation.
5. **Positive — Explicit unknown-field handling**: `MintMethodSettings` visitor uses `serde::de::IgnoredAny` to explicitly skip unknown keys. `MintQuoteCustomRequest` uses `#[serde(flatten)]` to capture method-specific extras.

### Nutshell-only findings
1. **WARN — `updated_at` not strictly monotonic within same second** (N04-M7): `int(time.time())` has 1-second resolution. Same-second transitions produce identical values. Practically harmless due to Lightning payment latency.
2. **WARN — Partial minting not supported** (`==` validation): Strict equality blocks the partial-mint use case. Stricter than spec, not a MUST violation.
3. **WARN — No custom payment method support**: Only `bolt11` via hardcoded routes. Feature absence, not a violation.
4. **Positive — Batch mint (NUT-29)**: `mint_batch()` and `POST /v1/mint/bolt11/batch` extend NUT-04 for multi-quote atomic minting. Uses sorted quote IDs for deterministic lock ordering to prevent deadlocks. Unique to Nutshell.
5. **Positive — Row-lock concurrency control**: `_set_mint_quote_pending` acquires a DB row lock; concurrent mint attempts block, then see PENDING state and raise `TransactionError`. Clean race-condition prevention.
6. **Positive — Wallet-side stale-response handling**: `MintQuote.check_stale_and_from_resp_wallet` implements the wallet-side MUSTs (rejects responses with lower `updated_at`, `amount_paid`, or `amount_issued`). Uses strict `<` comparisons.

## Convergence and Divergence Summary

### Areas of Full Convergence (all 3 agree)
- Three-endpoint structure (quote request, quote check, mint execution)
- All responses include `amount_paid`, `amount_issued`, `updated_at`
- `amount_paid`/`amount_issued` are non-negative integers
- `amount_issued` ≤ `amount_paid` invariant enforced
- Over-issuance prevented (output cannot exceed mintable amount)
- Mint execution response is exactly `{ "signatures": [...] }`
- Unrecognized fields silently ignored
- Quote ID not cryptographically derivable from payment request (generation is independent)
- `method` string `bolt11` matches `[a-z0-9_-]+`

### Areas of Divergence

| # | Issue | cashu-cf | CDK | Nutshell | Severity |
|---|---|---|---|---|---|
| 1 | Quote ID embedded in invoice | ❌ Full ID in description | ✅ Not embedded | ✅ Not embedded | **Medium** — front-running risk |
| 2 | Partial mint support | ⚠️ Validation allows, lifecycle breaks | ✅ Fully supported | ❌ Rejected (`==`) | **Low** — no known wallet uses it |
| 3 | `updated_at` persistence | ❌ Recomputed from wall clock | ✅ Persisted via SQL CASE | ✅ Persisted on state transitions | **Low** — staleness check still safe |
| 4 | `updated_at` strict monotonicity | ❌ 1s resolution | ✅ Sub-second (SQL CASE) | ❌ 1s resolution | **Low** — practical impact minimal |
| 5 | Quote ID format | ❌ 128-bit hex | ✅ UUID v7 | ✅ UUID v7 | **Info** — SHOULD, not MUST |
| 6 | `amount_issued` tracking | ❌ Always `0` | ✅ Incremental | ✅ Full-amount steps | **Low** — signals partial mint state |
| 7 | Custom method support | ℹ️ `bolt11` only | ✅ Validated custom methods | ℹ️ `bolt11` only | **Info** — design choices |
| 8 | Output validation operator | `<=` (spec-compliant) | `<=` (spec-compliant) | `==` (stricter) | **Info** — both safe |

## Recommendations

1. **cashu-cf — Fix quote ID embedding (Finding 1, Medium)**: Stop embedding the full quote ID in the BOLT11 invoice description. Use an opaque lookup identifier for sibling-mint detection, or hash the quote ID before embedding. This is the highest-severity finding across all three NUT-04 audits — it directly enables the front-running theft the spec warns about. Mitigated when NUT-20 pubkey locks are used, but the default code path is vulnerable. *(Also fix the stale comment at `mint.ts:339`.)*

2. **cashu-cf — Persist `updated_at` on the quote record**: Store `updated_at` when `amount_paid` or `amount_issued` changes (in `updateMintQuote`, `finalizeMintQuoteIssued`). Return the stored value in responses rather than recomputing from wall clock. This aligns with CDK and Nutshell behavior.

3. **cashu-cf — Complete partial-mint lifecycle or revert to `==`**: The ISSUE-023 fix correctly changed validation to `<=`, but the downstream lifecycle still marks the quote as fully consumed after one mint. Either (a) persist `amount_issued` incrementally and only set `ISSUED` when `amount_issued >= amount_paid` (matching CDK), or (b) revert to `==` (matching Nutshell) if multi-pass minting is not a goal. The current state — validation allows it but lifecycle breaks it — is the worst of both options.

4. **cashu-cf — Migrate quote ID to UUID v7**: Align with CDK and Nutshell. The 128-bit hex provides more entropy but breaks time-based sorting and format compliance. This is the same recommendation as in the NUT-05 comparison.

5. **Nutshell — Consider supporting partial minting**: The strict `==` validation blocks the partial-mint use case described in spec L83. If multi-pass minting is desired, change to `<=` and implement incremental `amount_issued` tracking. Not urgent — no known wallet uses it today, and the current behavior is safe.

6. **CDK — Remove legacy `state` field from BOLT11 response**: `MintQuoteBolt11Response` still includes `state: QuoteState` which was removed from the spec. While spec-compliant (unrecognized fields must be ignored), retaining it encourages wallets to depend on `state` rather than migrating to the accounting model. Low priority.

7. **CDK — Make `unit`/`amount` non-optional in BOLT11 response**: The REVIEW comments acknowledge these should be non-optional per the current spec. Removing the `Option<>` wrapper once all known mints are updated would close the type-safety gap.

8. **Cross-impl — Partial minting interop**: If partial minting becomes a wallet expectation, all three implementations should converge on the same semantics. CDK's incremental `amount_issued` tracking with `OverIssue` domain-level guard is the reference design. cashu-cf and Nutshell would need lifecycle changes to support it.

## Audit Scope Comparison

| Dimension | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Lines of code reviewed | 1496 + supporting (6 files) | ~3000+ (10 files) | ~965 (11 files) |
| Handler logic audited | ✅ Full | ✅ Full | ✅ Full |
| Domain model audited | ✅ (`crud.ts`) | ✅ (`cdk-common/mint.rs`) | ✅ (`base.py`, `ledger.py`) |
| Database layer audited | ✅ (`crud.ts`) | ✅ (`cdk-sql-common/mint/quotes.rs`) | ✅ (`db/write.py`) |
| HTTP routing audited | ✅ (`mint-routes.ts`) | ✅ (`cdk-axum/custom_router.rs`) | ✅ (`router.py`) |
| Test coverage referenced | ✅ (ISSUE-023 cross-ref) | ✅ (unit tests + DB monotonicity tests cited) | ✅ (code paths traced, empirical verification) |
| Behavioral requirements verified | ✅ | ✅ | ✅ |

**Note**: Unlike the NUT-05 audit where CDK was type-layer-only, all three NUT-04 audits covered full handler logic. CDK's audit was the most broad in file count (10 files), explicitly reviewing the type layer, domain model, enforcement logic, database layer, HTTP routing, and database test suite. This makes the cross-implementation behavioral comparison in this report fully valid — no "handler concern" caveats are needed.
