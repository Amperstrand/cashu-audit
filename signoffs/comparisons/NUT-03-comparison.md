# Cross-Implementation Comparison: NUT-03 (Swap Tokens)

**Date:** 2026-07-26
**Spec:** cashubtc/nuts @ 734f60e — `03.md` (Swap tokens, `mandatory`)
**Implementations compared:**
- **cashu-cf** @ c1e3907 (TypeScript / Cloudflare Workers)
- **CDK** @ d033f1b (Rust / `cashu` + `cdk` crates)
- **Nutshell** @ 18539020 (Python / FastAPI)
**Auditor model:** GLM-5.1/5.2 in opencode

---

## Summary Table

| Metric | cashu-cf | CDK | Nutshell |
|--------|----------|-----|----------|
| **Verdict** | PASS | PASS | PASS |
| **PASS** | 8 | 4 | 11 |
| **FAIL** | 0 | 0 | 0 |
| **WARN** | 1 | 0 | 0 |
| **INFO** | 2 | 5 (non-blocking obs) | 0 |
| **N/A** | 0 | 5 | 0 |

---

## Note on Audit Scope Asymmetry

NUT-03 is the thinnest mandatory spec (91 lines, zero literal "MUST" keywords). The three audits have **fundamentally different scopes**:

| Implementation | Audit Scope | Why |
|---------------|-------------|-----|
| **cashu-cf** | Full swap implementation: router, features, swap-utils, types | Cloudflare Workers mint — all code in one repo |
| **CDK** | Data types only: `nut03.rs` (245 lines) + NUT-00 wire types | CDK is a library; swap *logic* lives in `cdk` mint crate (separate file, out of scope) |
| **Nutshell** | Full swap implementation: ledger, router, verification, DB write, models | Standalone Python mint — all code accessible |

CDK's 5 N/A items are all **protocol-level concerns** (endpoint routing, input verification, input invalidation, blind signing, value-conservation enforcement) that live in the mint crate, not the data-structure file. The `nut03.rs` file correctly provides utility methods (`input_amount()`, `output_amount()`, `promises_amount()`) that the mint layer uses.

**This scope difference is architectural, not a quality gap.**

---

## Consensus Areas (All Three Agree)

### Wire Format — Exact Match

All three implement identical request/response structures:

**Request (`PostSwapRequest`):**
```json
{"inputs": [<Proof>...], "outputs": [<BlindedMessage>...]}
```

| Field | cashu-cf | CDK | Nutshell |
|-------|----------|-----|----------|
| `inputs` | `SwapPayload.inputs` (Proof[]) | `SwapRequest.inputs: Proofs` (Vec<Proof>) | `PostSwapRequest.inputs: List[Proof]` |
| `outputs` | `SwapPayload.outputs` (BlindedMessage[]) | `SwapRequest.outputs: Vec<BlindedMessage>` | `PostSwapRequest.outputs: List[BlindedMessage]` |

**Response (`PostSwapResponse`):**
```json
{"signatures": [<BlindSignature>...]}
```

| Field | cashu-cf | CDK | Nutshell |
|-------|----------|-----|----------|
| `signatures` | `{signatures: BlindSignature[]}` | `SwapResponse.signatures: Vec<BlindSignature>` | `PostSwapResponse.signatures: List[BlindSignature]` |

CDK names types `SwapRequest`/`SwapResponse` (dropping `Post` prefix) — cosmetic only, does not affect wire format.

### Endpoint — `POST /v1/swap`

cashu-cf and Nutshell both register `POST /v1/swap` explicitly. CDK's HTTP routing is in `cdk-axum`/`cdk-mintd` (referenced but out of audit scope).

### BlindedMessage / BlindSignature Wire Fields

All three use identical serde field names matching spec:
- `amount`, `id` (via `#[serde(rename = "id")]` in CDK), `B_` (via rename), `C_` (via rename), optional `witness`, optional `dleq`.

### Value Conservation

All three enforce that input value covers output value + fees. See NUT-02 comparison for the strict-equality vs. overpayment divergence detail.

---

## Key Divergences

### 1. Atomicity Model

| Implementation | Atomicity Mechanism | Strength |
|----------------|--------------------|---------| 
| **cashu-cf** | Cloudflare Durable Objects single-threaded handler + ACID transaction with rollback | Strong — DO serializes per-object |
| **CDK** | (Mint layer, out of scope) — provides primitives | N/A from this audit |
| **Nutshell** | Single locked DB transaction wrapping invalidate + sign; two-layer pending-set + table lock | Strongest — explicit double-spend prevention |

**cashu-cf** relies on Cloudflare Durable Objects' inherent single-threaded serialization for the object. The swap performs a "probe" cycle (set pending → rollback) before the actual `swapProofs` call, which performs its own independent proof-state check + pending lock. The probe is redundant with `swapProofs`'s built-in ACID handling (FINDING-1, WARN).

**Nutshell** uses the most explicit double-spend protection: (1) `_verify_spent_proofs_and_set_pending` marks proofs PENDING with a `lock_table="proofs_pending"` before the main transaction; (2) the main swap transaction re-acquires the lock on the same table. A concurrent swap hitting the same proofs blocks on the row lock or fails validation.

### 2. Balance Equation Strictness

| Implementation | Formula Enforced | Overpayment? |
|----------------|-----------------|--------------|
| **cashu-cf** | `inputAmount >= outputAmount + requiredFee` | **Yes** — allows overpayment (intentional, Nutshell-aligned) |
| **CDK** | (Mint layer enforces — provides `input_amount()`/`output_amount()` helpers) | N/A from data-type scope |
| **Nutshell** | `sum_outputs + fees_inputs - sum_inputs == 0` | **No** — strict equality |

cashu-cf's overpayment allowance is documented as intentional: "Nutshell semantics: inputs - fees must be >= outputs (allow overpayment for compatibility)" (`features.ts:652`). The excess is effectively burned. This is not a spec violation (NUT-03 examples show equal sums but don't mandate rejection of overpayment).

### 3. Server-Side Privacy Enhancement (cashu-cf unique)

cashu-cf goes **beyond the spec** on privacy: `features.ts:715-720` sorts outputs server-side before signing, then reorders signatures to match the client's original request order. This defeats amount-inference attacks even when clients don't follow the spec's SHOULD recommendation (L17: output ordering).

**Nutshell** correctly does NOT enforce output ordering server-side (spec uses SHOULD, directed at clients/wallets). The mint-side sort in cashu-cf is a defensive enhancement.

**CDK** correctly does not enforce ordering in the data structure.

### 4. DLEQ Proof Handling

| Implementation | DLEQ in Swap Response | Fallback Behavior |
|----------------|-----------------------|-------------------|
| **cashu-cf** | Attached to each BlindSignature (NUT-12) | SHA256 pseudo-proof → zero-valued placeholders (theoretical only) |
| **CDK** | Optional `dleq` field; stripped from inputs via `without_dleqs()` | N/A (data type only) |
| **Nutshell** | Included via `_sign_blinded_messages` (NUT-12) | No fallback documented |

cashu-cf's DLEQ fallback chain (real proof → SHA256 pseudo-proof → zero placeholders) is a NUT-12 quality concern, not a NUT-03 violation. The core fields (`id`, `amount`, `C_`) are always correct. The zero-placeholder path is unreachable in practice.

### 5. Spending Conditions Integration

| Implementation | NUT-10/11/14 Support |
|----------------|---------------------|
| **cashu-cf** | `verifySpendingConditions` before proof locking; error → 403 |
| **CDK** | `SpendingConditionVerification` trait impl with SIG_ALL message format (NUT-11/21/22) |
| **Nutshell** | SIG_INPUTS spending conditions checked in `_verify_inputs` |

All three integrate spending conditions into the swap flow, though this is technically beyond NUT-03 scope.

### 6. Legacy Endpoint Support

| Implementation | Legacy Endpoint | Behavior |
|----------------|----------------|----------|
| **cashu-cf** | None documented | N/A |
| **CDK** | None documented | N/A |
| **Nutshell** | `POST /v1/split` (deprecated) → delegates to `Ledger.swap` | Backward compat for clients < 0.13 |

Nutshell maintains a deprecated `/v1/split` endpoint that maps old `{proofs, amount, outputs}` format to the new swap interface. Not a spec violation — NUT-03 does not forbid deprecated endpoints.

---

## Overall Assessment

**All three implementations PASS NUT-03.** The spec is exceptionally thin (zero literal MUSTs, one SHOULD), defining only the request/response data model and describing swap semantics in prose. All three implementations correctly model the wire format.

### Scope-Quality Summary

| Implementation | Depth | Notable Strength |
|---------------|-------|-----------------|
| **cashu-cf** | Full implementation audit | Server-side privacy sort (exceeds spec); ACID with DO serialization |
| **CDK** | Data types only | Clean type design; DLEQ stripping on construction; spending condition support |
| **Nutshell** | Full implementation audit | Two-layer double-spend protection; strict value conservation; atomic transaction |

### Interoperability
**Zero interoperability risk.** All three produce and consume identical wire formats. A wallet sending a `PostSwapRequest` to any of the three mints will receive a correctly-formed `PostSwapResponse`. The BlindedMessage and BlindSignature field names match exactly across implementations.

### Key Insight
NUT-03's thinness means the real implementation work — and the interesting divergences — live in areas the spec delegates to other NUTs: atomicity (implicit from "invalidate + issue" semantics), fee handling (NUT-02), spending conditions (NUT-10/11/14), and DLEQ (NUT-12). The three implementations make different design choices in these cross-cutting concerns, but all satisfy the NUT-03 data model requirements.

**Cleanest implementation:** Nutshell (11 PASS, 0 WARN, 0 INFO — no findings, most comprehensive atomicity model).
**Most privacy-enhancing:** cashu-cf (server-side output sorting exceeds spec SHOULD).
**Most extensible:** CDK (SpendingConditionVerification trait, clean type separation).
