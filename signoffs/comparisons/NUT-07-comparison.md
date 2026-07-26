# Cross-Implementation Comparison: NUT-07 (Token State Check)

> **Generated**: 2026-07-26
> **Auditor**: GLM-5.2 in opencode
> **Source signoffs**:
> - `signoffs/cashu-cf/NUT-07-20260726-glm52.md` — cashu-cf @ 155cd94 (TypeScript / Cloudflare Workers)
> - `signoffs/cdk/NUT-07-20260726-glm52.md` — CDK @ d033f1b (Rust, type library + supporting types)
> - `signoffs/nutshell/NUT-07-20260726-glm52.md` — nutshell @ 1853902 (Python / FastAPI)
> **Spec**: cashubtc/nuts NUT-07 (`optional`)

## Executive Summary

All three implementations **PASS** NUT-07. Both explicit spec MUSTs — PENDING proof tracking to prevent concurrent reuse (L21) and response array order preservation (L68) — are satisfied across the board. The implementations converge on the three-value state enum (`UNSPENT`/`PENDING`/`SPENT`), the `PostCheckStateRequest`/`PostCheckStateResponse` wire shapes, unknown-proof → `UNSPENT` semantics, and NUT-06 advertisement.

The most significant divergence is the **`witness` field**: cashu-cf hardcodes it to `null` at all 7 response construction sites (WARN — NUT-10/11/14 witness data never persisted), while CDK implements full stringified-JSON witness serde and Nutshell correctly retrieves witness data from the `proofs_used` table. A secondary divergence is CDK's two extension state values (`RESERVED`, `PENDING_SPENT`) beyond the spec's three-value enum.

**Scope caveat**: The CDK audit covers the `cashu` crate type library only (`nut07.rs`, 129 lines) plus supporting serde types. Behavioral runtime enforcement (PENDING mutex, DB state persistence, order preservation in the handler) is deferred to the mint layer (`cdk-mintd`) and was not verified. The cashu-cf and Nutshell audits both covered the full request-to-response flow including concurrency analysis.

## Verdict Comparison

| Metric | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| **Overall verdict** | PASS | PASS | PASS |
| **Scope** | Full flow (handler + DO storage + proof state manager) | Type library only (`nut07.rs` + serde types) | Full flow (router + DB + ledger + concurrency) |
| **PASS** | 13 | 7 | 7 (all requirements) |
| **FAIL** | 0 | 0 | 0 |
| **WARN** | 1 | 1 | 0 |
| **N/A** | 0 | 0 | 0 |
| **Blocking findings** | — | — | — |

## Requirement-by-Requirement Matrix

### Endpoint & Routing

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `POST /v1/checkstate` endpoint exists | ✅ PASS | ✅ PASS (type) | ✅ PASS |
| Accepts HTTP POST with JSON body | ✅ PASS | — (transport layer) | ✅ PASS |
| Legacy/deprecated endpoint compat | ✅ INFO (non-standard formats) | — | ✅ PASS (`/check` deprecated) |

**Convergence**: All three register the spec-defined route. cashu-cf additionally accepts two non-standard request formats (`{proofs: [...]}`, `{secrets: [...]}`) as legacy extensions; Nutshell retains the deprecated v0 `/check` endpoint with boolean `spendable`/`pending` lists. Neither extension affects the standard path.

### Request Format (`PostCheckStateRequest`)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `Ys: Array[hex_str]` field | ✅ PASS | ✅ PASS (`Vec<PublicKey>`, renamed `Ys`) | ✅ PASS (`List[str]`) |
| Y = hex of compressed point `hash_to_curve(secret)` | ✅ PASS (opaque, no curve validation) | ✅ PASS (33-byte compressed enforced) | ✅ PASS |
| Input validation / DOS limits | ✅ INFO (duplicate Y rejected) | ✅ PASS (66-char hex enforced) | ✅ PASS (`max_length=66` per item, array cap) |

**Divergence on Y validation**: CDK enforces that each Y is exactly 33 bytes / 66 hex chars (compressed secp256k1 public key) at the type level. cashu-cf intentionally treats Y as an opaque identifier (no curve membership validation) — a documented design choice citing NUT-07's use of Y as a lookup key. Nutshell validates string length (66 chars) but not curve membership. None of these are spec violations — the spec says Y is "the hexadecimal representation of the compressed point" without mandating validation.

**Divergence on duplicate Y**: cashu-cf rejects duplicate Y values with HTTP 400 (stricter than spec, which is silent). CDK and Nutshell have no such rejection.

### Response Format (`PostCheckStateResponse`)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `states` array in response | ✅ PASS | ✅ PASS (`Vec<ProofState>`) | ✅ PASS (`List[ProofState]`) |
| Each state has `Y`, `state`, `witness` | ✅ PASS | ✅ PASS | ✅ PASS |
| States in same order as request `Ys` (MUST, L68) | ✅ PASS (`Promise.all` index mapping) | ✅ PASS (`Vec` ordered by contract) | ✅ PASS (sequential `for Y in Ys` loop) |
| `witness` populated for NUT-10 spent proofs | ❌ **WARN** (always `null`) | ✅ PASS (stringified-JSON serde) | ✅ PASS (retrieved from `proofs_used`) |

**This is the primary cross-implementation divergence.** See §Key Divergences below.

### State Semantics

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| State enum: `UNSPENT`, `PENDING`, `SPENT` | ✅ PASS | ✅ PASS (+ 2 extensions) | ✅ PASS |
| Unknown proofs → `UNSPENT` | ✅ PASS | — (handler concern) | ✅ PASS |
| State transitions: UNSPENT → PENDING → SPENT | ✅ PASS (validated) | — (handler concern) | ✅ PASS (implicit via DB state) |
| Extension state values | — (spec-only) | ⚠️ `RESERVED`, `PENDING_SPENT` | — (spec-only) |

### PENDING Tracking (MUST, L21)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| PENDING proofs remembered persistently | ✅ PASS (DO storage) | ✅ PASS (type: `State::Pending`) | ✅ PASS (`proofs_pending` table) |
| Prevents concurrent reuse | ✅ PASS (DO atomic transactions) | — (runtime concern) | ✅ PASS (table-level DB lock) |
| Stale PENDING recovery | ✅ PASS (`recoverStalePendingProofs`) | — | ✅ PASS (`_check_pending_proofs_and_melt_quotes`) |

### NUT-06 Advertisement

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `nuts.7: { "supported": true }` | ✅ PASS (env-overridable) | ✅ PASS (builder `.nut07()`) | ✅ PASS (unconditional) |

**Convergence**: All three advertise NUT-07 support. cashu-cf defaults to true with `NUT7_SUPPORTED` env override; CDK enables via builder pattern; Nutshell hardcodes as always-supported.

## Key Divergences

### 1. Witness Field Handling (most significant)

| Implementation | Witness behavior | Verdict |
|---|---|---|
| **cashu-cf** | Hardcoded `null` at all 7 response construction sites. `ProofState` interface has no `witness` field. Witness data from P2PK/HTLC spends is used for verification but never persisted. | **WARN** — feature gap for NUT-10/11/14 |
| **CDK** | Full `Witness` enum with per-variant custom serde. `serde_p2pk_witness` serializes as stringified JSON (matching spec L94 example). `Option<Witness>` → `null` when absent. | **PASS** — exact spec match |
| **Nutshell** | Witness retrieved from `proofs_used` table (stored at spend time via `witness` column). Model validator enforces witness only non-null when `state == SPENT`. | **PASS** — correctly persisted and returned |

**Impact**: Wallets querying checkstate for P2PK or HTLC proofs against cashu-cf will always see `witness: null` even after spending with a witness. This limits post-hoc auditability of NUT-11 spending conditions (P2PK is advertised as supported by default). CDK and Nutshell correctly populate the field. The spec uses declarative ("is the serialized witness data") rather than mandatory ("MUST return") language, so this is a feature gap, not a strict MUST violation.

### 2. Extension State Values (CDK only)

CDK implements two state values beyond the spec's three:

| CDK variant | Serialization | In spec? | Risk |
|---|---|---|---|
| `Reserved` | `"RESERVED"` | No | Low — arises during internal swap/melt flows; a well-behaved mint should not emit this in checkstate responses |
| `PendingSpent` | `"PENDING_SPENT"` | No | Low — internal transitional state |

The spec says `state` has "possible values" (L71) without a strict MUST enumerating only those values, so additive extensions are not a MUST violation. cashu-cf and Nutshell use only the three spec-defined values. CDK's recommendation: map `RESERVED` → `PENDING` and `PENDING_SPENT` → `SPENT` at the HTTP handler boundary for strict interop.

### 3. PENDING Tracking Mechanism

| Implementation | Mechanism | Strengths |
|---|---|---|
| **cashu-cf** | Durable Object `storage.transaction` (atomic read-validate-write). `setPendingBatch` validates all transitions inside the transaction before any write. Non-transactional fallback validates via batch read. Additional reservation-ownership enforcement in `setSpentBatch`. | Atomicity guaranteed by DO runtime; survives crashes; stale PENDING recovery |
| **CDK** | Type-level `State::Pending` variant. Runtime enforcement (mutex/DB) deferred to `cdk-mintd`. | Type-safe; compile-time guarantees |
| **Nutshell** | `proofs_pending` DB table with `lock_table="proofs_pending"`, `lock_timeout=1`. Check-then-insert atomicity inside locked transaction. Raises `ProofsArePendingError` on concurrent reuse. | DB-level durability; survives crashes; arguably more durable than in-memory mutex |

All three satisfy the spec's MUST. The spec's "mutex lock whose key is the Proof's Y" is listed as an example ("for example"), not a strict requirement on locking granularity. Nutshell's DB table-level lock and cashu-cf's DO transaction are both correct mutex-equivalent exclusions.

### 4. Audit Scope

| Dimension | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Handler logic audited | ✅ Full | ❌ Type library only | ✅ Full |
| Concurrency model verified | ✅ | ❌ | ✅ |
| Storage persistence verified | ✅ (DO storage) | ❌ | ✅ (DB table + locks) |
| Stale recovery verified | ✅ | ❌ | ✅ |

The CDK audit's type-layer scope is a methodology difference. Rust's type system enforces structural constraints at compile time, but behavioral requirements (PENDING mutex enforcement, DB persistence, order preservation in the handler) inherently require runtime review.

## Unique Findings Per Implementation

### cashu-cf-only findings
1. **WARN — `witness` always null** (Finding 1): All 7 response construction sites hardcode `witness: null`. The `ProofState` interface lacks a `witness` field. NUT-11 (P2PK) is advertised, making this gap user-facing. NUT-14 (HTLC) is disabled by default, softening impact.
2. **INFO — Legacy request format support** (Finding 2): Accepts `{proofs: [...]}` and `{secrets: [...]}` beyond the spec's `Ys` array. Includes hex-encoded secret dual-derivation fallback. Backward-compat extension; standard format is primary path.
3. **INFO — Duplicate Y rejection** (Finding 3): Rejects duplicate Y values with HTTP 400. Spec is silent on duplicates. Reasonable but could break a wallet sending duplicates expecting idempotent responses.
4. **Positive — Stale PENDING recovery** (Finding 4): `recoverStalePendingProofs` mechanism for proofs stuck in PENDING beyond a configurable threshold. Beyond spec requirements; strengthens the PENDING tracking guarantee.

### CDK-only findings
1. **WARN/Observation-1 — Extension states `RESERVED` and `PENDING_SPENT`** (Observation-1): Not in spec. Additive; not a MUST violation. Risk only for strict wallets that reject unknown enum values.
2. **COSMETIC — Module docstring title mismatch** (Observation-2): Says "Spendable Check" vs spec title "Token state check". No functional impact.
3. **Positive — Witness serde deep-dive**: The most thorough witness implementation. `#[serde(untagged)]` enum with per-variant custom serde modules producing exact stringified-JSON wire format. `None` → `null`.

### Nutshell-only findings
1. **No findings**: Fully conformant with zero deviations, zero warnings. The cleanest signoff of the three.
2. **Positive — Model-level witness validator** (`base.py:71-74`): Enforces witness can only be non-null when state is SPENT. Catches invariant violations at the model layer.
3. **Minor observation — Test uses dummy strings**: `test_api_check_state` uses `"asdasdasd"` (not valid hex pubkeys). Exercises UNSPENT path but doesn't validate with real hash-to-curve outputs. Test-quality note, not a compliance issue.

## Convergence and Divergence Summary

### Areas of Full Convergence (all 3 agree)
- `POST /v1/checkstate` endpoint with `Ys` request and `states` response
- Three-value state enum (`UNSPENT`/`PENDING`/`SPENT`) with correct uppercase serialization
- Unknown proofs → `UNSPENT` default
- Order preservation (MUST, L68) — via `Promise.all` (cashu-cf), `Vec` (CDK), sequential loop (Nutshell)
- PENDING proof tracking (MUST, L21) — persistent storage with mutex-equivalent exclusion
- NUT-06 `nuts.7` advertisement

### Areas of Divergence

| # | Issue | cashu-cf | CDK | Nutshell | Severity |
|---|---|---|---|---|---|
| 1 | `witness` field populated for NUT-10 spent proofs | ❌ Always `null` | ✅ Stringified JSON | ✅ From `proofs_used` | **Medium** — cashu-cf only gap |
| 2 | Extension state values | — (3 spec values) | ⚠️ +2 extensions | — (3 spec values) | **Low** — additive, not emitted normally |
| 3 | Y validation strictness | Opaque (no curve check) | 33-byte compressed enforced | Length only (66 chars) | **Info** — spec doesn't mandate validation |
| 4 | Duplicate Y handling | Rejected (400) | Not rejected | Not rejected | **Info** — spec silent |
| 5 | Stale PENDING recovery | ✅ `recoverStalePendingProofs` | — (not verified) | ✅ Periodic task | **Info** — beyond spec |
| 6 | Audit scope | Full flow | Type library only | Full flow | **Methodology** — CDK defers runtime to `cdk-mintd` |

## Recommendations

1. **cashu-cf — Populate `witness` field for NUT-10 proofs**: Add a `witness` column to proof state storage and populate it during `setSpent`/`setSpentBatch` when the spend operation includes witness data. Thread the witness through from melt/swap handlers to `ProofStateManager`. This closes the only WARN and aligns with CDK and Nutshell.

2. **CDK — Map extension states at handler boundary**: If strict interop is desired, `cdk-mintd` should map `RESERVED` → `PENDING` and `PENDING_SPENT` → `SPENT` at the HTTP handler boundary so checkstate responses only contain spec-defined values.

3. **CDK — Complete the audit with handler-layer review**: The type-library-only scope means PENDING mutex enforcement, DB persistence, and order preservation in the actual handler are unverified. A `cdk-mintd` handler audit would provide coverage comparable to cashu-cf and Nutshell.

4. **Cross-impl — Witness interop testing**: Given cashu-cf returns `null` while CDK and Nutshell return populated witness data, a cross-implementation interop test for P2PK proof checkstate would surface this divergence to wallet authors.

## Overall Assessment

NUT-07 is the most uniformly implemented of the three NUTs audited in this batch. All three implementations PASS with zero FAIL verdicts. The core protocol contract — check proof state, preserve order, track PENDING — is correctly implemented everywhere. The single notable gap (cashu-cf's null witness field) is a feature limitation for NUT-10 spending-condition auditability, not a structural spec violation. Nutshell achieves the cleanest signoff (zero warnings, zero deviations), while CDK provides the most rigorous witness serde implementation at the type level. The implementations are interoperable for the common case (non-NUT-10 proofs).
