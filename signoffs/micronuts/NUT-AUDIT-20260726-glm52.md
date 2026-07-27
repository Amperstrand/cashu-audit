# NUT Compliance Audit: Micronuts (Embedded Cashu on STM32)

**Date:** 2026-07-26
**Auditor:** glm-5.1
**Branch:** `experiment/greatspectations-audit`
**Platform:** STM32F469I-Discovery (bare-metal Rust, `no_std`, Embassy async runtime)
**Spec source:** `/home/ubuntu/src/micronuts/nuts/00.md` through `05.md`

**Primary source files reviewed:**
- `micronuts-mint/src/mint_core.rs` — DemoMint state machine (540 lines)
- `micronuts-mint/src/keyset.rs` — DemoKeyset key generation (146 lines)
- `micronuts-mint/src/lib.rs` — Module declarations (31 lines)
- `host-mint-tool/src/mint.rs` — Standalone host-side mint tool (35 lines)
- `firmware/src/hardware_impl.rs` — STM32 hardware abstraction (346 lines)

**Supporting library files reviewed (`cashu-core-lite`):**
- `src/crypto.rs` — BDHKE primitives: `hash_to_curve`, `blind_message`, `sign_message`, `unblind_signature`, `verify_signature` (142 lines)
- `src/nuts/nut00.rs` — Core models: `BlindedMessage`, `BlindSignature`, `Proof`, `ErrorResponse`, `decompose_amount` (133 lines)
- `src/nuts/nut01.rs` — `KeyPair`, `KeySet`, `KeysResponse` (46 lines)
- `src/nuts/nut02.rs` — `KeysetInfo`, `KeysetsResponse`, `derive_keyset_id` (68 lines)
- `src/nuts/nut03.rs` — `SwapRequest`, `SwapResponse`
- `src/nuts/nut04.rs` — `MintQuoteRequest`, `MintQuoteResponse`, `MintRequest`, `MintResponse` (71 lines)
- `src/nuts/nut05.rs` — `MeltQuoteRequest`, `MeltQuoteResponse`, `MeltRequest`, `MeltResponse` (89 lines)
- `src/nuts/nut06.rs` — `MintInfo`, `NutSupport`, `ContactInfo` (55 lines)
- `src/nuts/nut07.rs` — `CheckStateRequest`, `ProofState`, `CheckStateResponse` (54 lines)
- `src/token.rs` — V4 token encode/decode (174 lines)

---

## Executive Summary

Micronuts implements a **functional but non-spec-compliant** Cashu mint core for a bare-metal embedded platform. The cryptographic primitives (BDHKE) are correct and match the NUT-00 specification exactly. However, the protocol layer has **five specification deviations** ranging from deprecated keyset ID format to missing mandatory response fields. These deviations stem from the project's explicit "demo shortcut" design philosophy — every gap is documented with an inline comment acknowledging the limitation.

### Verdict by NUT

| NUT | Title | Status | Verdict |
|-----|-------|--------|---------|
| NUT-00 | Cryptography and Models | mandatory | **PASS** (crypto) / **WARN** (models) |
| NUT-01 | Mint public keys | mandatory | **WARN** |
| NUT-02 | Keysets and fees | mandatory | **FAIL** (V1 keyset ID) |
| NUT-03 | Swap tokens | mandatory | **PASS** |
| NUT-04 | Mint tokens | mandatory | **FAIL** (3 deviations) |
| NUT-05 | Melt tokens | mandatory | **FAIL** (2 deviations) |
| NUT-06 | Mint info | mandatory | **WARN** |
| NUT-07 | Token state check | optional | **PASS** (session-scoped) |

### Greatspectations Quotes Audit

The codebase contains **7 inline spec quotes** (comment lines matching `// NUT #0X: ...`):

| # | File:Line | NUT | Quote | Implementation Status |
|---|-----------|-----|-------|----------------------|
| 1 | `mint_core.rs:107` | NUT-01 | MUST use compressed Secp256k1 public key format | **PASS** |
| 2 | `mint_core.rs:117` | NUT-02 | MUST have at least one active keyset | **PASS** |
| 3 | `mint_core.rs:206` | NUT-04 | MUST NOT issue ecash exceeding `amount_paid - amount_issued` | **FAIL** — strict equality enforced, no `amount_issued` tracking |
| 4 | `mint_core.rs:393` | NUT-02 | New outputs MUST be from active keysets only | **WARN** — keyset ID on output is silently ignored; amount-only lookup |
| 5 | `keyset.rs:70` | NUT-01 | MUST use compressed Secp256k1 public key format | **PASS** (duplicate of #1) |
| 6 | `keyset.rs:87` | NUT-02 | MUST have at least one active keyset | **PASS** (duplicate of #2) |
| 7 | `host-mint-tool/src/mint.rs:17` | NUT-01 | MUST use compressed Secp256k1 public key format | **PASS** (duplicate of #1) |

4 unique requirements, 3 duplicated. Of the 4 unique: 2 PASS, 1 FAIL, 1 WARN.

---

## Architectural Context

Micronuts is an **embedded platform** — a bare-metal Rust application running on an STM32F469I-Discovery board with no operating system, no HTTP server, and no filesystem. The following design decisions are inherent to the platform and are **not counted as spec violations**:

| Design Decision | Spec Expectation | Micronuts Reality | Classification |
|----------------|------------------|-------------------|----------------|
| Transport | HTTP REST API (`GET /v1/keys`, etc.) | Direct function calls + custom binary RPC over USB CDC ACM | Architectural — N/A for compliance |
| Serialization | JSON (human-readable) | CBOR via `minicbor` (binary, compact) | Architectural — N/A for compliance |
| State persistence | Durable (database/file) | In-memory only (lost on power cycle) | Acknowledged demo shortcut |
| Lightning backend | Real BOLT11 invoice generation/payment | Auto-paid dummy invoices | Acknowledged demo shortcut |
| Keyset count | Multiple keysets supported | Single hardcoded keyset | Platform constraint |

The audit evaluates **data model correctness** and **cryptographic protocol compliance** — the aspects that matter regardless of transport layer.

---

## NUT-00: Notation, Utilization, and Terminology (`mandatory`)

### What it implements

- **BDHKE cryptographic protocol** (`crypto.rs`): All five operations of the Blind Diffie-Hellman Key Exchange are correctly implemented:
  - `hash_to_curve(x)` → `Y`: Domain separator `b"Secp256k1_HashToCurve_Cashu_"` (28 bytes), u32 little-endian counter from 0
  - `blind_message(secret, r)` → `B_ = Y + rG`: Correct point addition
  - `sign_message(k, B_)` → `C_ = k * B_`: Correct scalar multiplication
  - `unblind_signature(C_, r, K)` → `C = C_ - rK`: Correct point subtraction
  - `verify_signature(x, C, k)` → `k * hash_to_curve(x) == C`: Correct verification
- **Core data models** (`nut00.rs`): `BlindedMessage`, `BlindSignature`, `Proof`, `ErrorResponse` — all structurally match spec field sets
- **Amount decomposition**: `decompose_amount()` implements power-of-two greedy split for denomination selection
- **V4 token codec** (`token.rs`): Partial V4 token encode/decode with `cashuB` and `crawB` prefix handling

### What it does NOT implement

- JSON wire serialization (uses CBOR with array-indexed fields, not CBOR map with string keys)
- V3 token format (deprecated by spec, reasonable omission)
- V4 token with spec-compliant CBOR map encoding (single-char string keys `m`, `u`, `d`, `t`, `i`, `p` — see Finding F-1)
- Short keyset ID (`s_id`) support in token format
- DLEQ proof fields in V4 token proof objects
- Witness field in V4 token proof objects
- Binary token `crawB` prefix for encode (only decode supports it)

### Requirement Checklist

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 00-MUST-1 | `hash_to_curve` MUST use domain separator `b"Secp256k1_HashToCurve_Cashu_"` | **PASS** | `crypto.rs:11` — exact 28-byte match |
| 00-MUST-2 | Counter MUST be uint32 little-endian, incremented from 0 | **PASS** | `crypto.rs:41-45` — `counter.to_le_bytes()`, range `0..u16::MAX` |
| 00-MUST-3 | Curve point MUST try `0x02` prefix first | **PASS** | `crypto.rs:49` — `arr[0] = 0x02` |
| 00-MUST-4 | Signing: `C_ = k * B_` | **PASS** | `crypto.rs:118-122` |
| 00-MUST-5 | Unblinding: `C = C_ - rK` | **PASS** | `crypto.rs:101-112` |
| 00-MUST-6 | Verification: `k * hash_to_curve(x) == C` | **PASS** | `crypto.rs:130-141` |
| 00-MUST-7 | BlindedMessage model: `{amount, id, B_}` | **PASS** | `nut00.rs:21-31` — fields present, correct types |
| 00-MUST-8 | BlindSignature model: `{amount, id, C_}` | **PASS** | `nut00.rs:38-48` |
| 00-MUST-9 | Proof model: `{amount, id, secret, C}` | **PASS** | `nut00.rs:55-68` |
| 00-MUST-10 | Error response: `{detail, code}` with HTTP 400 | **N-A** | `ErrorResponse` struct exists (`nut00.rs:72-77`); no HTTP layer on embedded |
| 00-MUST-11 | Token prefix `cashu` + version char | **PASS** (decode only) | `token.rs:151-156` — recognizes `cashuB` and `crawB` |
| 00-MUST-12 | V4 CBOR uses single-char map keys (`m`, `u`, `d`, `t`, `i`, `p`, `a`, `s`, `c`) | **FAIL** | See Finding F-1 |
| 00-MUST-13 | base64_urlsafe decode with/without padding | **PASS** | `token.rs:18-95` — custom decoder handles both |
| 00-MUST-14 | Receivers MUST ignore unknown fields | **N-A** | CBOR array encoding has no named fields to ignore |

### Finding F-1: V4 Token CBOR Encoding Incompatible with Standard (MEDIUM)

**Spec (NUT-00 §V4 tokens):** V4 tokens use CBOR map with single-character string keys (`m`, `u`, `d`, `t`, `i`, `p`, `a`, `s`, `c`). Proofs within `p` omit `id` (carried at group level).

**Reality (`token.rs`):** `TokenV4` uses `minicbor` with `#[n(0)]`, `#[n(1)]`, etc. which produces a **CBOR array** (index-based), not a CBOR map with string keys. The `Proof` struct in `token.rs:98-110` includes a `keyset_id` field (should be omitted at proof level in V4). The standard Cashu V4 CBOR map format uses keys like `"m"`, `"u"`, `"t"`, `"i"`, `"p"`, `"a"`, `"s"`, `"c"` — none of these are present.

**Impact:** A token encoded by micronuts cannot be decoded by Nutshell, CDK, cashu-ts, or any standard Cashu wallet, and vice versa. The `decode_token` function attempts base64url + CBOR decode but would fail on standard V4 tokens because `minicbor::decode` expects array-indexed fields, not map-keyed fields.

**Mitigation:** For same-device QR scanning (firmware scanning its own generated tokens), this works. For cross-wallet interoperability, it fails completely.

**Recommendation:** Use `minicbor` map encoding with string keys, or add a separate serde layer for standard V4 compatibility.

---

## NUT-01: Mint public keys (`mandatory`)

### What it implements

- `DemoMint::get_keys()` returns a `KeysResponse` containing the single active keyset
- Each key is a compressed secp256k1 public key (33 bytes, `0x02`/`0x03` prefix)
- Keys are mapped by denomination amount: `{1, 2, 4, 8, 16, 32, 64, 128}` sat
- Key derivation is deterministic from a fixed seed (SHA-256 chain)

### What it does NOT implement

- `active` field in keyset response (spec example includes it in `/v1/keys` response)
- `input_fee_ppk` field in keyset response (spec example includes it)
- `final_expiry` field in keyset response
- `GET /v1/keys/{keyset_id}` endpoint for specific keyset lookup
- Multiple keysets
- Key rotation

### Requirement Checklist

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 01-MUST-1 | Mint MUST use compressed Secp256k1 public key format | **PASS** | `keyset.rs:46` — `sk.public_key()` via k256 produces compressed format; `to_encoded_point(true)` at `mint_core.rs:88` |
| 01-MUST-2 | Each denomination MUST have its own keypair | **PASS** | `keyset.rs:36-48` — one keypair per amount in DENOMINATIONS |
| 01-MUST-3 | `GET /v1/keys` returns active keysets only | **PASS** | `mint_core.rs:108-112` — single keyset, always active |
| 01-MUST-4 | Response includes `active` field per keyset | **FAIL** | `KeySet` struct (`nut01.rs:29-39`) has no `active` field |
| 01-MUST-5 | Response includes `input_fee_ppk` field per keyset | **FAIL** | `KeySet` struct has no `input_fee_ppk` field |
| 01-MUST-6 | Response includes `final_expiry` field per keyset | **FAIL** | `KeySet` struct has no `final_expiry` field |
| 01-GET-1 | `GET /v1/keys/{keyset_id}` endpoint | **N-A** | Single keyset; non-HTTP transport |

### Finding F-2: KeysResponse Missing Mandatory Fields (MEDIUM)

**Spec (NUT-01 §Example response):** The `/v1/keys` response includes `active`, `input_fee_ppk`, and `final_expiry` alongside `id`, `unit`, and `keys` for each keyset.

**Reality:** The `KeySet` struct (`nut01.rs:29-39`) contains only `id: String`, `unit: String`, `keys: Vec<KeyPair>`. Three fields from the spec response are absent. A standard Cashu wallet parsing this response would be unable to determine if the keyset is active, what the input fee is, or when it expires.

**Note:** The `KeysetInfo` struct (from NUT-02's `/v1/keysets` response) does include `active` and `input_fee_ppk`. The gap is specifically in the `/v1/keys` response model.

---

## NUT-02: Keysets and fees (`mandatory`)

### What it implements

- `DemoMint::get_keysets()` returns a `KeysetsResponse` with keyset metadata
- `KeysetInfo` includes `id`, `unit`, `active` (always `true`), `input_fee_ppk` (always `0`)
- Keyset ID is derived from sorted compressed public keys via SHA-256
- Single keyset, always active

### What it does NOT implement

- V2 keyset ID format (uses deprecated V1)
- `final_expiry` field in `KeysetInfo`
- Multiple keysets
- Keyset rotation (activate/deactivate)
- Input fee calculation in transactions

### Requirement Checklist

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 02-MUST-1 | Mint MUST have at least one active keyset | **PASS** | `mint_core.rs:62` — `DemoKeyset::demo_default()` creates active keyset |
| 02-MUST-2 | New outputs MUST be from active keysets only | **WARN** | See Finding F-3 |
| 02-MUST-3 | Keyset ID derived per spec algorithm | **FAIL** | See Finding F-4 (V1 format, deprecated) |
| 02-MUST-4 | `input_fee_ppk` present (defaults to 0 if omitted) | **PASS** | `keyset.rs:94` — `input_fee_ppk: 0` |
| 02-MUST-5 | `final_expiry` field present (optional, MAY be null) | **FAIL** | `KeysetInfo` struct (`nut02.rs:19-33`) has no `final_expiry` field |
| 02-MUST-6 | Fee equation: `sum(inputs) - fees == sum(outputs)` | **PASS** | `mint_core.rs:344` — `input_sum != output_sum` with `fee_ppk=0` is correct |
| 02-GET-1 | `GET /v1/keysets` endpoint | **N-A** | Non-HTTP transport; function call `get_keysets()` provides equivalent data |
| 02-GET-2 | `GET /v1/keys/{keyset_id}` endpoint | **N-A** | Single keyset |

### Finding F-3: Output Keyset ID Not Validated (LOW)

**Spec (NUT-02 §Active keysets):** "new outputs (`BlindedMessages` and `BlindSignatures`) **MUST** be from `active` keysets only."

**Reality (`mint_core.rs:394-414`):** `sign_outputs()` looks up the secret key by **amount only** via `self.keyset.get_secret_key(output.amount)`. The output's `id` field (which specifies the requested keyset) is **never checked**. The `BlindSignature` returned always carries `self.keyset.id`, regardless of what keyset ID the client requested in the `BlindedMessage`.

**Impact:** If a client sends outputs with a wrong or inactive keyset ID, the mint will still sign them with the active keyset and return signatures stamped with the active keyset ID. In a single-keyset system this is harmless. In a multi-keyset system this would be a spec violation.

**Mitigation:** Single-keyset constraint makes this safe in practice.

### Finding F-4: Deprecated V1 Keyset ID Format (HIGH)

**Spec (NUT-02 §Keyset ID V2):** "Keyset IDs are 33 byte hex strings with a version byte (two hexadecimal characters). The currently used version byte is `01`." The V2 derivation algorithm includes the unit string, optional `input_fee_ppk`, and optional `final_expiry` in the preimage.

**Spec (NUT-02 §V1 Keysets):** "V1 keysets are 8 bytes long, including a version byte prefix `00`." — marked as **deprecated**.

**Reality (`nut02.rs:51-67`):** `derive_keyset_id()` implements the V1 algorithm:
1. Concatenates compressed public keys only (no unit, no fee, no expiry)
2. SHA-256 hashes the concatenation
3. Takes first **7 bytes** (14 hex chars)
4. Prepends `"00"` (V1 version byte)
5. Result: 16 hex characters (8 bytes)

Test assertion confirms this (`keyset.rs:125`): `assert!(ks1.id.starts_with("00"))` and `assert_eq!(ks1.id.len(), 16)`.

**Impact:** Standard Cashu wallets receiving this keyset ID would interpret it as a V1 (deprecated) keyset. V2-only wallets may reject it. The keyset ID does not bind the unit or fee information, making it impossible for wallets to verify keyset integrity per the V2 spec.

**Recommendation:** Implement `derive_keyset_id_v2()` including unit string, `input_fee_ppk`, and version byte `"01"` in the preimage.

---

## NUT-03: Swap tokens (`mandatory`)

### What it implements

- `DemoMint::post_swap()` implements the full swap operation:
  1. Verifies input proofs (signature check against mint keys)
  2. Checks input sum equals output sum (with fees = 0)
  3. Marks input proofs as spent (in-memory set)
  4. Signs new blinded outputs
  5. Returns blind signatures

### What it does NOT implement

- Fee-aware balance checking (assumes `input_fee_ppk = 0` always)
- Durable double-spend protection (spent set is in-memory only)
- Input keyset ID validation (same issue as F-3 — amount-only lookup)
- Spending condition verification (NUT-10/11/14 — not in scope)

### Requirement Checklist

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 03-MUST-1 | Swap: verify inputs, invalidate, sign outputs | **PASS** | `mint_core.rs:334-355` — full flow |
| 03-MUST-2 | `sum(inputs) - fees == sum(outputs)` | **PASS** | `mint_core.rs:344` — exact match with `fee_ppk=0` |
| 03-SHOULD-1 | Outputs ordered by amount ascending (privacy) | **N-A** | Client-side concern; mint does not enforce |
| 03-POST-1 | `POST /v1/swap` endpoint | **N-A** | Non-HTTP transport |

### Verdict: **PASS**

The swap implementation is correct for the demo's constraints (zero fees, single keyset, in-memory state). The core protocol — verify, invalidate, sign — is properly implemented.

---

## NUT-04: Mint tokens (`mandatory`)

### What it implements

- Two-step minting flow: `post_mint_quote()` → `post_mint()`
- Quote state machine: `UNPAID` → `PAID` → `ISSUED`
- Amount validation: rejects `amount == 0`
- Quote lookup: `get_mint_quote()` by quote ID
- Output sum verification against quoted amount
- Blind signature generation on paid quotes

### What it does NOT implement

- UUID v7 quote IDs (uses sequential counter hex)
- `amount_paid`, `amount_issued`, `updated_at` accounting fields
- `method` field in quote response
- `unit` field in quote response
- Partial minting (spec allows minting less than `amount_paid - amount_issued`)
- Payment method-specific endpoints (`POST /v1/mint/quote/{method}`)
- `description` and `pubkey` (NUT-20) optional fields
- Real Lightning invoice generation
- Quote expiry enforcement

### Requirement Checklist

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 04-MUST-1 | MUST NOT issue ecash exceeding `amount_paid - amount_issued` | **FAIL** | See Finding F-5 |
| 04-MUST-2 | Quote ID MUST be UUID v7 | **FAIL** | `mint_core.rs:79-81` — `format!("{:016x}", counter)` |
| 04-MUST-3 | Response MUST include `amount_paid`, `amount_issued`, `updated_at` | **FAIL** | `MintQuoteResponse` (`nut04.rs:35-52`) has none of these |
| 04-MUST-4 | Response MUST include `method` field | **FAIL** | Not present |
| 04-MUST-5 | Response MUST include `unit` field | **FAIL** | Not present |
| 04-MUST-6 | `amount_issued` MUST NOT exceed `amount_paid` | **N-A** | Neither field exists |
| 04-MUST-7 | Quote is unique, random, non-derivable from payment request | **WARN** | Sequential counter — predictable and non-random |
| 04-MUST-8 | Two-step flow: quote request, then mint execution | **PASS** | `post_mint_quote()` + `post_mint()` |
| 04-MUST-9 | Mint verifies payment before signing | **PASS** | `mint_core.rs:198-203` — checks `PAID` state |
| 04-MUST-10 | Mark quote as issued after minting | **PASS** | `mint_core.rs:216-218` — sets `ISSUED` state |
| 04-MUST-11 | Reject re-minting of already-issued quote | **PASS** | `mint_core.rs:199-201` — returns `QuoteAlreadyIssued` |

### Finding F-5: Strict Equality Prevents Partial Minting (MEDIUM)

**Spec (NUT-04 L83):** "Mints **MUST NOT** issue ecash whose total output amount exceeds `amount_paid - amount_issued`. If a wallet mints less than the currently mintable amount, `amount_issued` only increases by the amount that was issued."

**Reality (`mint_core.rs:207-209`):**
```rust
let output_sum: u64 = request.outputs.iter().map(|o| o.amount).sum();
if output_sum != quoted_amount {
    return Err(CashuError::AmountMismatch);
}
```

The code checks **strict equality** (`!=`), rejecting any request where outputs don't sum to exactly the quoted amount. The spec requires only that outputs don't **exceed** the mintable amount. Partial minting (minting some tokens now, more later from the same quote) is impossible because there is no `amount_issued` tracking.

The inline spec quote at line 206 correctly states the MUST NOT EXCEED requirement, but the implementation enforces equality instead.

**Impact:** A wallet cannot split a large mint quote into multiple smaller mint operations. For the embedded demo (auto-paid quotes, single mint), this is functionally equivalent. For spec compliance, it is a deviation.

### Finding F-6: Quote IDs Are Sequential, Not UUID v7 (HIGH)

**Spec (NUT-04 L72, L89):** "`quote` is the quote ID in UUIDv7 format." "quote **SHOULD** be UUID v7 with all 74 variable bits generated by a CSPRNG."

**Reality (`mint_core.rs:78-81`):**
```rust
fn next_quote_id(&mut self) -> String {
    self.quote_counter += 1;
    format!("{:016x}", self.quote_counter)
}
```

Quote IDs are sequential hex counters: `0000000000000001`, `0000000000000002`, etc. They are:
- Predictable (trivially guessable)
- Not UUID v7 format
- Not CSPRNG-generated
- Derivable without any secret knowledge

**Impact:** Any party who can observe or guess the quote ID can front-run the minting operation and steal tokens. The spec explicitly warns about this: "A third party who knows the `quote` ID can front-run and steal the tokens."

**Mitigation:** For an embedded demo with USB-only access (no network exposure), the attack surface is minimal. For any networked deployment, this would be critical.

---

## NUT-05: Melting tokens (`mandatory`)

### What it implements

- Two-step melting flow: `post_melt_quote()` → `post_melt()`
- Quote state machine: `UNPAID` → `PAID`
- Amount extraction from dummy invoice format (`lnbcdemo{N}sat1micronuts`)
- Input proof verification and amount checking
- Change output support (optional blinded outputs signed and returned)
- Dummy payment preimage generation

### What it does NOT implement

- UUID v7 quote IDs (same sequential counter as NUT-04)
- `method` field in quote response
- `unit` field in quote response
- `PENDING` state (goes directly `UNPAID` → `PAID`)
- `prefer_async` support
- Real Lightning payment execution
- Fee reserve calculation (always 0)
- Quote expiry enforcement

### Requirement Checklist

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 05-MUST-1 | Quote ID MUST be UUID v7 | **FAIL** | Same sequential counter as NUT-04 |
| 05-MUST-2 | Response MUST include `method` field | **FAIL** | `MeltQuoteResponse` (`nut05.rs:37-57`) has no `method` field |
| 05-MUST-3 | Response MUST include `unit` field | **FAIL** | Not present in response (only in request) |
| 05-MUST-4 | `state` enum: UNPAID, PENDING, PAID | **WARN** | `PENDING` state defined but never used; goes UNPAID → PAID directly |
| 05-MUST-5 | Input proofs MUST cover `amount + fee_reserve + fee` | **PASS** | `mint_core.rs:292-297` — checks `input_sum >= required_amount` |
| 05-MUST-6 | Change outputs signed and returned | **PASS** | `mint_core.rs:304-308` — optional outputs signed |
| 05-MUST-7 | Two-step flow: quote request, then melt execution | **PASS** | `post_melt_quote()` + `post_melt()` |
| 05-OPT-1 | `prefer_async` support | **N-A** | Synchronous only |

### Verdict: **FAIL** (2 mandatory field omissions + non-UUID quote IDs)

The melt flow logic is functionally correct for a demo, but the response model is missing mandatory fields (`method`, `unit`) and quote IDs are non-compliant.

---

## NUT-06: Mint info (`mandatory`)

> Note: NUT-06 spec (`06.md`) was not provided in the audit scope (00–05). Assessment based on code review against known NUT-06 requirements.

### What it implements

- `DemoMint::get_info()` returns a `MintInfo` with:
  - `name`: "Micronuts Demo Mint"
  - `pubkey`: First denomination key's public key (hex-encoded compressed point)
  - `version`: "micronuts-mint/0.1.0"
  - `description`: "In-memory demo Cashu mint for Micronuts development"
  - `contact`: Empty vector
  - `nuts.supported`: `[0, 1, 2, 3, 4, 5, 6, 7]`

### What it does NOT implement

- NUT-04/05 settings objects (method-unit pairs, min/max amounts, disabled flags)
- `description_long` field
- `motto` field
- Nested `nuts` object with per-NUT configuration
- Time-based fields (`time`, `tos_url`, `icon_url`)
- Extended contact info (only method + info)

### Finding F-7: NutSupport Lacks Per-NUT Settings (MEDIUM)

**Spec expectation (NUT-06):** The `nuts` field should contain nested settings for NUT-04 and NUT-05 specifying supported `method`-`unit` pairs, `min_amount`, `max_amount`, and `disabled` flags.

**Reality (`nut06.rs:51-54`):** `NutSupport` contains only `supported: Vec<u32>` — a flat list of NUT numbers. No per-NUT configuration is possible.

**Impact:** Standard wallets querying `/v1/info` cannot determine which payment methods or units the mint supports.

---

## NUT-07: Token state check (optional)

### What it implements

- `DemoMint::post_check_state()` accepts an array of Y values
- Computes `Y = hash_to_curve(secret)` for lookup (actually receives Y directly from client)
- Checks each Y against in-memory `spent_ys` set
- Returns `ProofState` with `y`, `state` (SPENT/UNSPENT), and `witness: None`

### What it does NOT implement

- Durable spent state (lost on restart — acknowledged demo shortcut)
- `PENDING` state (for in-flight HTLC transactions)
- `witness` field population (always `None`)
- Double-spend rejection (mark_spent silently allows re-marking)

### Requirement Checklist

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 07-MUST-1 | Accept Y values, return state | **PASS** | `mint_core.rs:362-385` |
| 07-MUST-2 | States: UNSPENT, SPENT, PENDING | **PASS** | UNSPENT and SPENT implemented; PENDING defined but unused |
| 07-OPT-1 | `witness` field for spending conditions | **N-A** | No spending conditions implemented |

### Verdict: **PASS** (session-scoped)

Correct for the demo's constraints. The spent-proof tracking is functional within a single session, which is the stated design goal.

---

## Cross-Cutting Findings

### F-8: Double-Spend Silently Allowed (MEDIUM)

**Location:** `mint_core.rs:452-463` (`mark_spent`)

```rust
// Demo shortcut: we allow double-spending for now (no error if already spent)
self.spent_ys.insert(y_hex);
```

The `mark_spent` function does not check whether a proof's Y value is already in the `spent_ys` set before inserting. A proof can be spent unlimited times within a session. The spec requires that once a secret is spent, it cannot be spent again.

**Impact:** Within a session, an attacker (or buggy wallet) can double-spend the same proofs in rapid succession before the spent set is checked. In practice, the swap/melt operations verify the proof signature but don't check the spent set **before** marking — they mark after verification without rejecting pre-spent proofs.

**Note:** `verify_proofs()` (`mint_core.rs:421-446`) checks cryptographic validity but does **not** check the spent set. Only `post_checkstate()` reads the spent set, and it's a read-only query, not a guard.

### F-9: Mint Pubkey Uses Wrong Key (LOW)

**Location:** `mint_core.rs:88`

```rust
let mint_pk = self.keyset.keys[0].2.to_encoded_point(true);
```

The mint's `pubkey` in `MintInfo` (NUT-06) is set to the **first denomination's** public key (the 1-sat key). In Cashu, the mint pubkey in NUT-06 should be a dedicated mint identity key, not a denomination key. Using a denomination key conflates the mint identity with a specific denomination.

**Impact:** Low. The field is informational. No security impact since all keys are derived from the same seed.

### F-10: host-mint-tool Is a Separate Simpler Implementation (INFO)

**Location:** `host-mint-tool/src/mint.rs`

The `host-mint-tool` crate contains a **separate, simpler** `DemoMint` struct with a single keypair (no denominations). It duplicates the NUT-01 spec quote but implements a different signing flow. This appears to be an earlier prototype that was superseded by the `micronuts-mint` crate. The two implementations are not connected.

---

## Findings Summary

| ID | Severity | NUT | Title | Spec-Quoted? |
|----|----------|-----|-------|-------------|
| F-1 | MEDIUM | NUT-00 | V4 token CBOR encoding incompatible with standard (array vs map) | No |
| F-2 | MEDIUM | NUT-01 | KeysResponse missing `active`, `input_fee_ppk`, `final_expiry` fields | No |
| F-3 | LOW | NUT-02 | Output keyset ID silently ignored; amount-only key lookup | Yes (quote #4) |
| F-4 | **HIGH** | NUT-02 | Deprecated V1 keyset ID format (`00` prefix, 8 bytes) | No |
| F-5 | MEDIUM | NUT-04 | Strict equality prevents partial minting | Yes (quote #3) |
| F-6 | **HIGH** | NUT-04 | Sequential quote IDs, not UUID v7 / CSPRNG | No |
| F-7 | MEDIUM | NUT-06 | NutSupport lacks per-NUT settings objects | No |
| F-8 | MEDIUM | NUT-07 | Double-spend silently allowed (no pre-check in verify_proofs) | No |
| F-9 | LOW | NUT-06 | Mint pubkey uses denomination key instead of identity key | No |
| F-10 | INFO | — | host-mint-tool is a divergent prototype | No |

---

## Spec Coverage Map

| NUT | Spec Status | Implementation | Coverage |
|-----|------------|----------------|----------|
| NUT-00 | mandatory | Crypto: full. Models: present. Token V4: proprietary codec. | 80% |
| NUT-01 | mandatory | Core key exchange: correct. Response model: 3 fields missing. | 60% |
| NUT-02 | mandatory | Keyset metadata: partial. ID derivation: V1 deprecated. Fees: hardcoded 0. | 50% |
| NUT-03 | mandatory | Swap operation: correct. Fee handling: N/A (zero fee). | 95% |
| NUT-04 | mandatory | Mint flow: correct. Quote model: 4 mandatory fields missing. Partial mint: blocked. | 45% |
| NUT-05 | mandatory | Melt flow: correct. Quote model: 2 mandatory fields missing. Async: N/A. | 55% |
| NUT-06 | mandatory | Basic info: present. NUT settings: flat list, no per-NUT config. | 50% |
| NUT-07 | optional | Check state: session-scoped correct. Witness: N/A. | 85% |
| NUT-08+ | optional | Not implemented | 0% |

---

## Recommendations (Priority Order)

1. **F-4 (HIGH):** Implement V2 keyset ID derivation. The V1 format is deprecated and will be rejected by V2-only wallets.
2. **F-6 (HIGH):** Replace sequential quote IDs with UUID v7 generated from the hardware RNG (`Rng` peripheral is available per `hardware_impl.rs:294-308`).
3. **F-5 (MEDIUM):** Change `output_sum != quoted_amount` to `output_sum > mintable_amount` and track `amount_issued` per quote.
4. **F-2 (MEDIUM):** Add `active`, `input_fee_ppk`, `final_expiry` to the `KeySet` struct.
5. **F-1 (MEDIUM):** Use CBOR map encoding with string keys for V4 token compatibility, or document micronuts as a closed-loop system.
6. **F-8 (MEDIUM):** Add spent-check in `verify_proofs()` before accepting inputs in swap/melt operations.
7. **F-3 (LOW):** Validate output `id` field matches active keyset before signing.
8. **F-7 (MEDIUM):** Add NUT-04/05 settings objects to `NutSupport` for `/v1/info` completeness.

---

## Conclusion

Micronuts demonstrates a **working Cashu mint core** on bare-metal STM32 hardware — a significant engineering achievement. The BDHKE cryptographic protocol (NUT-00) is implemented correctly and matches the specification exactly. The swap operation (NUT-03) and check-state (NUT-07) are functionally complete for session-scoped use.

However, the protocol layer has **two HIGH-severity deviations** that would break interoperability with standard Cashu wallets: the deprecated V1 keyset ID format (F-4) and non-random sequential quote IDs (F-6). Five additional MEDIUM findings represent missing response fields and logic deviations from quoted spec requirements.

For the stated purpose — an embedded demo wallet on STM32F469I-Discovery with USB serial transport and no network exposure — these deviations are acceptable. For any deployment requiring cross-wallet interoperability, F-1, F-2, F-4, F-5, and F-6 would need to be resolved.

The greatspectations quote at `mint_core.rs:206` is particularly notable: it correctly quotes the NUT-04 requirement ("MUST NOT issue ecash whose total output amount exceeds `amount_paid - amount_issued`") but the implementation on the very next line enforces strict equality instead. This is the clearest case of a quoted requirement not matching its implementation.
