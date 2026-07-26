# Cross-Implementation Comparison: NUT-09 (Restore Signatures)

> **Generated**: 2026-07-26
> **Auditor**: GLM-5.2 in opencode
> **Source signoffs**:
> - `signoffs/cashu-cf/NUT-09-20260726-glm52.md` — cashu-cf @ 155cd94 (TypeScript / Cloudflare Workers)
> - `signoffs/cdk/NUT-09-20260726-glm52.md` — CDK @ d033f1b (Rust, wire types + mint handler)
> - `signoffs/nutshell/NUT-09-20260726-glm52.md` — nutshell @ 1853902 (Python / FastAPI)
> **Spec**: cashubtc/nuts NUT-09 (`optional`, used by NUT-13 wallet backup)

## Executive Summary

All three implementations **PASS** NUT-09. All seven normative requirements — store on every issuance, respond only if previously signed, include `amount` + `id` in restored signatures, request/response shapes, same-length index-correlated arrays, and NUT-06 advertisement — are satisfied across the board. The implementations converge on the `POST /v1/restore` endpoint structure, the `{outputs, signatures}` response shape, and the index-correlation invariant enforced by paired push/append in the restore loop.

The most significant divergence is **CDK's silent skipping of expired-keyset signatures** during restore — a condition the spec does not state, with medium recovery impact for NUT-13 wallet backup scenarios where a keyset expires between backup and restore. A secondary concern is **cashu-cf's `mockSignFn`** in the melt-quote DO path, which persists cryptographically invalid signatures into the restore index, defeating NUT-09's recovery purpose for that subset of outputs (though this is a functional bug outside the NUT-09 spec surface, not a spec-shape violation).

**Scope note**: All three audits covered behavioral handler logic (not just types). CDK's audit uniquely covers both the `nut09.rs` wire types and the `cdk` mint handler (`mint/mod.rs:1252-1349`). cashu-cf covers the full handler + `BlindedMessageTracker` storage layer. Nutshell covers the full ledger + DB layer.

## Verdict Comparison

| Metric | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| **Overall verdict** | PASS | PASS | PASS |
| **Scope** | Full (handler + tracker + DO storage + SQL dual-write) | Wire types + mint handler (`nut09.rs` + `mint/mod.rs`) | Full (ledger + router + DB + migrations) |
| **PASS** | 7 | 7 | 7 |
| **FAIL** | 0 | 0 | 0 |
| **WARN** | 4 | 1 | 1 |
| **N/A** | 0 | 0 | 0 |
| **Blocking findings** | — | — | — |

## Requirement-by-Requirement Matrix

### Storage Invariant (L11: "must store … every time they issue a BlindSignature")

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Store BlindedMessage + BlindSignature on every issuance | ✅ PASS | ✅ PASS | ✅ PASS |
| Issuance paths covered | Swap, Mint (2), Melt change, DO router | Mint (2), Swap, Melt change | Mint (single + batch), Swap, Melt change |
| Store-before-sign enforcement | ✅ Atomic batch (`storagePutBatch`) | ✅ `add_blind_signatures` on all paths | ✅ `ValueError` if row doesn't exist |
| Storage key | `blindedMessage:{B_}` + `nut09:{sha256(id\|amount\|B_)}` | `blinded_secret` (B_) | `b_` (UNIQUE constraint) |

**Convergence**: All three store on every issuance path. Nutshell uniquely enforces the store-before-sign invariant at runtime via a `ValueError` in `update_blinded_message_signature` if the placeholder row doesn't exist — the strongest enforcement. cashu-cf uses a dual-key scheme (primary dedup + stable restore index). CDK keys by `blinded_secret` (the B_ point).

### Restore Matching (L11: "only respond … if they have previously signed")

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Return signature only for previously-signed messages | ✅ PASS | ✅ PASS (with WARN-1) | ✅ PASS |
| Unknown messages silently skipped | ✅ PASS | ✅ PASS | ✅ PASS |
| Expired keysets skipped | — (no such gate) | ⚠️ **WARN** — silently dropped | — (no such gate) |
| Lookup query | `nut09:` key → `blindedMessage:` fallback | `get_blind_signatures` by `B_` | `WHERE b_ = :b_ AND c_ IS NOT NULL` |

**Divergence**: See §Key Divergences — Expired Keyset Handling below.

### Response Fields (L11: "contains the `amount` and the keyset `id`")

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `amount` present in restored signature | ✅ PASS | ✅ PASS (non-optional `Amount`) | ✅ PASS (`amount` column) |
| `id` (keyset id) present | ✅ PASS | ✅ PASS (non-optional `Id`) | ✅ PASS (`id` column) |

**Convergence**: All three guarantee `amount` and `id` are present in restored signatures. CDK enforces this at the type level (non-optional fields). cashu-cf and Nutshell enforce via the stored object shape.

### Request/Response Shape (L13-36)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `POST /v1/restore` with `{outputs: [...]}` | ✅ PASS | ✅ PASS | ✅ PASS |
| Response `{outputs: [...], signatures: [...]}` | ✅ PASS | ✅ PASS | ✅ PASS |
| Request size limit / DOS guard | ✅ `getMaxRestoreOutputs` | ✅ `max_outputs` limit | ✅ `mint_max_request_length` |

**Convergence**: All three match the spec wire format exactly. All three implement DOS guards (unspecified by the spec but sane for an unauthenticated DB-lookup endpoint).

### Index Correlation (L38: same length, `outputs[i]` ↔ `signatures[i]`)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| Length equality guaranteed | ✅ PASS (paired push) | ✅ PASS (paired push) | ✅ PASS (paired append) |
| Index correspondence | ✅ PASS (same loop iteration) | ✅ PASS (same loop iteration) | ✅ PASS (same `if` branch) |
| Request-order preservation | — (by construction) | ✅ **Stronger** (explicitly verified, `Error::Internal` on violation) | — (by construction) |

**Divergence**: CDK is the only implementation that **explicitly verifies** response outputs preserve the request's relative order (via a `position_map` built at loop start), turning any ordering bug into a hard `Error::Internal` rather than silent mis-pairing. This is stronger than the spec requires (which only mandates `outputs[i] ↔ signatures[i]` correspondence, not request-order preservation). cashu-cf and Nutshell preserve order by construction (loop iteration) but do not explicitly verify it.

### NUT-06 Advertisement (L40-49)

| Requirement | cashu-cf | CDK | Nutshell |
|---|---|---|---|
| `nuts.9: { "supported": true }` | ✅ PASS (env-overridable) | ✅ PASS (builder `.nut09()`) | ✅ PASS (unconditional) |

**Convergence**: All three advertise NUT-09 support.

## Key Divergences

### 1. Expired Keyset Handling (CDK only — medium recovery impact)

| Implementation | Behavior for expired-keyset signatures | Spec alignment |
|---|---|---|
| **cashu-cf** | No expiry gate; returns previously-signed signatures regardless of keyset status | ✅ Matches spec (single condition: "previously signed") |
| **CDK** | Silently skips entries where `keyset.is_expired()` → `continue` with `debug!` log | ⚠️ **WARN** — adds condition not in spec |
| **Nutshell** | No expiry gate; returns previously-signed signatures regardless of keyset status | ✅ Matches spec |

**Impact**: For NUT-13 wallet-backup recovery, a keyset that expires between backup and restore means CDK those tokens become unrestorable even though the mint holds the signature. The spec's recovery guarantee ("recover … by requesting from the mint to reissue the blind signatures") no longer holds for expired keysets on CDK mints. The wallet sees the output silently disappear with no signal that expiration (rather than "never signed") caused the omission. Whether this is acceptable depends on mint policy (expired keysets may have unloaded keys), but it is a strict-text deviation.

**Mitigating factor**: CDK's NUT-01 keysets remain queryable for expired keysets, so the data to unblind exists. CDK could restore expired-keyset signatures if keys are still loaded.

### 2. Melt Change Signature Validity (cashu-cf — functional bug)

| Implementation | Melt change signatures stored for restore | Valid? |
|---|---|---|
| **cashu-cf (primary melt path)** | ✅ Real signing via `signFn` | ✅ Valid |
| **cashu-cf (melt-quote DO 2PC path)** | ❌ `mockSignFn`: `C_: "sig_{B_}"` placeholder | ❌ **Cryptographically invalid** |
| **CDK** | Real signing via `process_melt_change` | ✅ Valid |
| **Nutshell** | Real signing via `_sign_blinded_messages` | ✅ Valid |

**Impact**: cashu-cf's melt-quote DO path (used for async settlement) stores fake `C_` values (`"sig_…"`) into the NUT-09 restore index via `tracker.signWithTracking(outputsToSign, mockSignFn)`. A wallet that later restores one of these outputs via `POST /v1/restore` receives a structurally-valid-but-cryptographically-invalid signature. This defeats the NUT-09 recovery guarantee for melt change outputs on this code path.

**Scope check**: This is the melt-quote DO's 2PC commit path. The comment at L456 ("in production this will use real private keys") confirms this is a placeholder. NUT-09 MUSTs M1-M3 are technically satisfied (store happened, signature exists, has amount+id), but the *purpose* of NUT-09 (recover a usable Proof) is violated. This is a functional bug, not a spec-shape violation.

### 3. Storage Model

| Implementation | Storage architecture | Key design | Strengths |
|---|---|---|---|
| **cashu-cf** | DO storage (KV) + optional SQLite dual-write + write-through cache | Dual: `blindedMessage:{B_}` (dedup) + `nut09:{sha256(id\|amount\|B_)}` (stable restore) | Legacy fallback; cache avoids storage round-trips; SQL migration path |
| **CDK** | DB backend (SQLite/Redb/PostgreSQL) via `add_blind_signatures` | `blinded_secret` (B_) | Clean separation; multi-backend; DB-result-length assertion |
| **Nutshell** | SQLite/PostgreSQL `promises` table | `b_` with `UNIQUE` constraint | Store-placeholder-then-update model; runtime existence check; `UNIQUE` prevents duplicates |

**Analysis**: cashu-cf's dual-key scheme is the most sophisticated — the stable restore key (`nut09:{sha256(...)}`) decouples restore from dedup strategy, so future changes to dedup cannot break restore. Nutshell's two-phase store-placeholder-then-update model enforces the store-before-sign invariant at runtime (ValueError if row doesn't exist). CDK's multi-backend approach provides flexibility but delegates transactional durability to the backend.

### 4. Test Coverage

| Implementation | Dedicated NUT-09 tests | Coverage |
|---|---|---|
| **cashu-cf** | ❌ **WARN** — zero matches for `restore`, `NUT.?09`, `getStoredSignature`, `storeSignedOutputs` | None — no regression protection |
| **CDK** | ✅ Unit test (`nut09.rs`) + integration test (`test_blind_signature_order.rs`) | Wire type round-trip; DB ordering preservation |
| **Nutshell** | ✅ Implicit via integration tests (swap/melt flows that exercise restore) | End-to-end but not NUT-09-specific |

**Divergence**: cashu-cf is the only implementation with zero dedicated NUT-09 tests. The index-correlation invariant (M6) and the "only-if-previously-signed" gate (M2) are subtle and could regress silently during refactors without test protection. Medium risk.

### 5. Restore Integrity Verification (Nutshell bonus)

| Implementation | Integrity check on restored signatures |
|---|---|
| **cashu-cf** | None beyond storage lookup |
| **CDK** | DB-result-length assertion (defensive invariant) |
| **Nutshell** | ✅ DLEQ regeneration + signature re-derivation + `C_` match assertion |

**Divergence**: Nutshell uniquely regenerates a NUT-12 DLEQ proof for each restored signature AND re-derives the signature (`b_dhke.step2_bob`) to assert `C_.format().hex() == promise.C_`. This guards against a corrupted/tampered `promises.c_` column — strictly stronger than the spec demands. Raises `TransactionError("restored signature does not match promise")` on mismatch.

### 6. Authentication Gate (CDK optional)

| Implementation | Auth on restore endpoint |
|---|---|
| **cashu-cf** | Unauthenticated (spec says nothing about auth) |
| **CDK** | Optionally gated behind NUT-21 (Clear Auth) when mint has auth configured |
| **Nutshell** | Unauthenticated (spec says nothing about auth) |

**Note**: NUT-09 specifies no authentication. CDK's optional NUT-21 integration is a non-spec defensive measure — the endpoint is auth-gated only when the mint has auth configured. For mints with auth disabled, restore is open as the spec assumes. No NUT-09 violation.

## Unique Findings Per Implementation

### cashu-cf-only findings
1. **WARN — Melt change DO stores fake signatures** (`mockSignFn`): `C_: "sig_{B_}"` placeholders persisted to restore index. Defeats NUT-09 recovery for melt change outputs on the DO 2PC path. Functional bug outside spec surface.
2. **WARN — Duplicate `handleRestore` implementation**: Live handler in `router.ts`; dead handler in `api/restore.ts` (unreferenced, references absent `ctx.observability`). Maintenance hazard.
3. **WARN — No dedicated NUT-09 tests**: Zero spec test matches. Index-correlation and only-if-signed invariants have no regression protection.
4. **WARN — Non-standard `promises` field in dead handler**: `api/restore.ts` returns `{outputs, signatures, promises}` — `promises` not in spec. Dead code; no runtime impact.
5. **Positive — Stable restore key**: `nut09:{sha256(id|amount|B_)}` decouples restore from dedup. Sound design.
6. **Positive — Legacy fallback**: `getStoredSignature` falls back to `blindedMessage:{B_}` for pre-migration entries. Backward compatible.
7. **Positive — SQL dual-write**: Best-effort migration to `nut09_index` table; KV remains source of truth.
8. **Positive — Defensive count check**: `storeSignedOutputs` throws before any write on `outputs.length !== signatures.length`.

### CDK-only findings
1. **WARN — Expired keysets silently skipped** (WARN-1): Restore skips entries where `keyset.is_expired()`. Condition not in spec. Medium recovery impact for NUT-13.
2. **Positive — Order-preservation verification**: Explicitly verifies response outputs preserve request relative order via `position_map`. Stronger than spec. Turns ordering bugs into hard `Error::Internal`.
3. **Positive — DoS guard**: `max_outputs` limit on restore requests. Sane abuse-mitigation for unauthenticated DB-lookup amplification.
4. **Positive — DB-result-length assertion**: Asserts `blinded_signatures.len() == output_len` after DB lookup. Pins backend contract.
5. **Positive — NUT-21 optional auth**: Restore endpoint auth-gated when mint has auth configured. Non-spec defensive measure.

### Nutshell-only findings
1. **WARN — Restore endpoint registered unconditionally** (W1): No config switch to disable NUT-09 independently of advertisement. Internally consistent (always advertised) but coupled. No spec violation.
2. **Positive — Store-before-sign runtime enforcement**: `update_blinded_message_signature` raises `ValueError` if the blinded-message row doesn't exist. Strongest store-before-sign guarantee of the three.
3. **Positive — DLEQ + signature re-derivation on restore**: Regenerates DLEQ proof, re-derives signature, asserts `C_` match. Guards against corrupted/tampered storage. Strictly stronger than spec.
4. **Positive — `UNIQUE(b_)` constraint**: DB-level guarantee that a given blinded message is stored at most once.
5. **Positive — Deprecated v0 route**: `/restore` (no `/v1/` prefix) for legacy clients, delegating to same `ledger.restore()`.

## Convergence and Divergence Summary

### Areas of Full Convergence (all 3 agree)
- `POST /v1/restore` with `{outputs: [...]}` request and `{outputs, signatures}` response
- Store BlindedMessage + BlindSignature on every issuance path (mint, swap, melt change)
- Return signature only for previously-signed messages; silently skip unknown
- `amount` and `id` present in every restored signature
- Same-length, index-correlated arrays (paired push/append in restore loop)
- NUT-06 `nuts.9` advertisement
- DOS guard on request size (unspecified by spec but universally implemented)

### Areas of Divergence

| # | Issue | cashu-cf | CDK | Nutshell | Severity |
|---|---|---|---|---|---|
| 1 | Expired keyset signatures skipped | — (no gate) | ⚠️ Silently dropped | — (no gate) | **Medium** — recovery impact for NUT-13 |
| 2 | Melt change signature validity | ❌ `mockSignFn` on DO path | ✅ Real signing | ✅ Real signing | **Medium** — functional bug, cashu-cf DO path only |
| 3 | Request-order preservation verified | — (by construction) | ✅ Explicitly verified | — (by construction) | **Info** — CDK stricter than spec |
| 4 | Restore integrity check | None | DB-length assertion | ✅ DLEQ + C_ re-derivation | **Info** — Nutshell strongest |
| 5 | Store-before-sign enforcement | Atomic batch | All paths covered | ✅ Runtime `ValueError` | **Info** — Nutshell strongest |
| 6 | Dedicated NUT-09 tests | ❌ Zero | ✅ Unit + integration | ✅ Implicit | **Low** — cashu-cf gap |
| 7 | Optional auth gate | Unauthenticated | NUT-21 (optional) | Unauthenticated | **Info** — CDK defensive |
| 8 | Storage key scheme | Dual-key (dedup + stable) | B_ | b_ (UNIQUE) | **Info** — design choices |

## Recommendations

1. **CDK — Document or revise expired-keyset skip policy**: Either (a) document as explicit CDK policy in user-facing docs so wallet authors know restore is best-effort for expired keysets, or (b) restore expired-keyset signatures anyway if keys are still loaded (NUT-01 keysets remain queryable). At minimum, consider whether silent dropping vs. an explicit signal is the right UX for NUT-13 recovery.

2. **cashu-cf — Replace `mockSignFn` with real signing**: The melt-quote DO 2PC path (`melt-quote-do.ts:214,457`) must use real blind-signing with the mint's derived private keys, not `C_: "sig_{B_}"` placeholders. This is a functional bug that defeats NUT-09 recovery for melt change outputs. File as a separate issue if confirmed live.

3. **cashu-cf — Add dedicated NUT-09 spec tests**: Write tests that (a) mint a token, (b) call `/v1/restore` with original outputs and assert signatures match, (c) call with never-signed outputs and assert empty arrays, (d) assert `outputs.length === signatures.length`. The index-correlation and only-if-signed invariants need regression protection.

4. **cashu-cf — Remove dead duplicate handler**: Delete `src/api/restore.ts` or consolidate to a single shared handler. The dead handler references absent `ctx.observability` and adds a non-standard `promises` field.

5. **Nutshell — Consider configurable NUT-09 disable**: The restore endpoint is registered unconditionally. Adding a guard on `is_nut_supported(RESTORE_NUT)` would allow independent disabling without editing `features.py`. Low priority — cosmetic coupling.

6. **Cross-impl — NUT-13 recovery interop test**: Given CDK's expired-keyset skip and cashu-cf's mock-signature bug, a cross-implementation NUT-13 backup→restore interop test would surface these issues to wallet authors. Specifically: backup tokens, wait for keyset expiry (CDK) or trigger async melt (cashu-cf), then restore and verify all signatures are cryptographically valid.

## Overall Assessment

NUT-09 is correctly implemented across all three codebases at the spec-compliance level — all seven normative requirements are satisfied with zero FAIL verdicts. The implementations share a common architecture (store on issuance, lookup on restore, paired push for index correlation) with meaningful variation in enforcement depth. Nutshell provides the strongest integrity guarantees (runtime store-before-sign enforcement + DLEQ/C_ re-derivation on restore), CDK provides the strongest ordering guarantees (explicit request-order verification), and cashu-cf provides the most sophisticated storage design (dual-key scheme + SQL dual-write) but has the most open issues (mock signatures on DO path, zero tests, dead code).

The two findings with real-world impact are: (1) CDK's expired-keyset silent skip, which breaks NUT-13 recovery for expired keysets, and (2) cashu-cf's `mockSignFn`, which produces worthless restore signatures for melt change outputs on the DO path. Neither is a spec-shape violation, but both defeat the user-facing purpose of NUT-09 for affected code paths. The implementations are interoperable for the common case (active keysets, primary melt path), but wallet authors building NUT-13 backup/restore should be aware of these edge-case behaviors.
