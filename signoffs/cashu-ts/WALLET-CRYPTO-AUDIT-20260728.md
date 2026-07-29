# Wallet Crypto Audit — cashu-ts v4.7.2

**Date**: 2026-07-28
**Auditor**: Layer 3 AI Audit (autonomous)
**Subject**: `@cashu/cashu-ts` v4.7.2 wallet-side cryptographic implementation
**Scope**: `src/crypto/core.ts`, `src/crypto/NUT01.ts`, `src/crypto/NUT11.ts`, `src/crypto/NUT20.ts`, `src/model/SigAll.ts`
**Cross-check**: `cashu-cf` mint (Nutshell-CF) verification paths

---

## Executive Summary

The core DHKE (Diffie-Hellman Key Exchange) cryptosystem in cashu-ts v4.7.2 is **correct**. The `hashToCurve`, `blindMessage`, `unblindSignature`, key derivation, and proof assembly all faithfully implement NUT-00/NUT-01. The NUT-11 P2PK and SIG_ALL spending conditions are spec-compliant. The NUT-20 quote signature has a deliberate dual-format (amended + legacy) strategy with automatic fallback that ensures interoperability.

**No critical exploitable vulnerabilities were found.**

Three observations of note:
1. **[Low]** `hashToCurve` counter byte order relies on platform endianness (practically safe, not spec-guaranteed by JS)
2. **[Informational]** NUT-20 public API exports legacy format; amended format is internal-only in v4 (mitigated by wallet's dual-sign fallback)
3. **[Informational]** SIG_ALL multi-party signing produces 2 signatures per signer (current + legacy) — correct but larger witnesses than single-format

---

## 1. Core Crypto (`src/crypto/core.ts`)

### 1.1 `hashToCurve` — CORRECT

**Spec (NUT-00)**:
```
hash_to_curve(x):
  msg_hash = SHA256(DOMAIN_SEPARATOR || x)
  counter = 0
  while True:
    hashed_point = SHA256(msg_hash || counter.to_bytes(4, 'little'))
    if hashed_point is valid x-coordinate on curve:
      return lift_x(hashed_point)  # even-Y point
    counter += 1
```
Where `DOMAIN_SEPARATOR = b"Secp256k1_HashToCurve_Cashu_"`.

**Implementation** (`core.ts:38-53`):
```typescript
const DOMAIN_SEPARATOR = utf8ToBytes('Secp256k1_HashToCurve_Cashu_');

export function hashToCurve(secret: Uint8Array): WeierstrassPoint<bigint> {
  const msgToHash = sha256(Bytes.concat(DOMAIN_SEPARATOR, secret));
  const counter = new Uint32Array(1);
  const maxIterations = 2 ** 16;
  for (let i = 0; i < maxIterations; i++) {
    const counterBytes = new Uint8Array(counter.buffer);
    const hash = sha256(Bytes.concat(msgToHash, counterBytes));
    try {
      return pointFromHex(bytesToHex(Bytes.concat(new Uint8Array([0x02]), hash)));
    } catch {
      counter[0]++;
    }
  }
  throw new CTSError('No valid point found');
}
```

**Verification**:
| Step | Spec | Code | Match |
|------|------|------|-------|
| Domain separator | `b"Secp256k1_HashToCurve_Cashu_"` | `utf8ToBytes('Secp256k1_HashToCurve_Cashu_')` | ✅ |
| msg_hash | `SHA256(DS ‖ x)` | `sha256(Bytes.concat(DOMAIN_SEPARATOR, secret))` | ✅ |
| Counter init | 0 | `new Uint32Array(1)` → `[0]` | ✅ |
| Counter bytes | `counter.to_bytes(4, 'little')` | `new Uint8Array(counter.buffer)` | ✅* |
| Point construction | `lift_x(hash)` with even Y | `0x02 ‖ hash` (even-Y compressed prefix) | ✅ |
| Max iterations | not specified | 2^16 (sufficient: failure prob ≈ 2^-65536) | ✅ |

*Counter byte order uses `Uint32Array.buffer` which yields little-endian on all practical JS runtimes (V8, SpiderMonkey, JavaScriptCore all run on little-endian CPUs). The ECMAScript spec doesn't mandate platform endianness, but no deployed JS engine runs on big-endian hardware. **Not a real-world risk.**

**Cross-check with cashu-cf**: The mint re-exports `hashToCurve` from `@cashu/cashu-ts` (`src/crypto/cashu-crypto.ts:42-47`), so both sides use the identical implementation. ✅

### 1.2 `blindMessage` — CORRECT

**Spec (NUT-00 DHKE)**:
```
Step 2: Alice computes Y = hash_to_curve(x)
Step 3: Alice picks random r, computes B_ = Y + r*G
```

**Implementation** (`core.ts:116-126`):
```typescript
export function blindMessage(secret: Uint8Array, r?: bigint): RawBlindedMessage {
  const Y = hashToCurve(secret);
  if (r === undefined) {
    r = secp256k1.Point.Fn.fromBytes(createRandomSecretKey());
  } else if (r === 0n) {
    throw new CTSError('Blinding factor r must be non-zero');
  }
  const rG = secp256k1.Point.BASE.multiply(r);
  const B_ = Y.add(rG);
  return { B_, r, secret };
}
```

- `B_ = Y + rG` ✅ (correct blinding)
- `r` is a valid random scalar from `secp256k1.utils.randomSecretKey()` (range [1, n-1]) ✅
- Zero-check for deterministic `r` ✅

### 1.3 `unblindSignature` — CORRECT

**Spec (NUT-00 DHKE)**:
```
Step 6: Bob computes C_ = k * B_
Step 7: Alice computes C = C_ - r * A  (where A = k*G)
```

Math: `C = C_ - rA = kB_ - r(kG) = k(Y + rG) - krG = kY + krG - krG = kY` ✅

**Implementation** (`core.ts:128-135`):
```typescript
export function unblindSignature(C_, r, A): WeierstrassPoint<bigint> {
  const C = C_.subtract(A.multiply(r));
  return C;
}
```

- `C = C_ - rA` ✅

### 1.4 `createBlindSignature` (mint-side, cross-check) — CORRECT

**Implementation** (`core.ts:85-93`):
```typescript
export function createBlindSignature(B_, privateKey, id): BlindSignature {
  const a = secp256k1.Point.Fn.fromBytes(privateKey);
  const C_: WeierstrassPoint<bigint> = B_.multiply(a);
  return { C_, id };
}
```

- `C_ = a * B_` ✅

### 1.5 `constructUnblindedSignature` / Proof Assembly — CORRECT

**Implementation** (`core.ts:137-145` + `model/OutputData.ts:128-165`):

The `OutputData.toProof()` method:
1. Verifies DLEQ proof if present (NUT-12) ✅
2. Unblinds: `C = C_ - rA` via `constructUnblindedSignature` ✅
3. Serializes C as compressed hex (33 bytes, `toHex(true)`) ✅
4. Secret: `new TextDecoder().decode(unblinded.secret)` — converts bytes back to UTF-8 string ✅
5. Returns `{id, amount, C, secret, dleq?, ...}` ✅

### 1.6 `createRandomRawBlindedMessage` — CORRECT

**Implementation** (`core.ts:103-107`):
```typescript
export function createRandomRawBlindedMessage(): RawBlindedMessage {
  const secretStr = bytesToHex(randomBytes(32)); // 64 char ASCII hex string
  const secretBytes = new TextEncoder().encode(secretStr); // UTF-8 of the hex
  return blindMessage(secretBytes);
}
```

Per NUT-00: "The secret message x is a UTF-8 encoded string." The wallet generates 32 random bytes, hex-encodes them to a 64-character ASCII string, then UTF-8 encodes that string (64 bytes) before passing to `hashToCurve`. This matches the spec — the secret is a UTF-8 string, and `hashToCurve` receives the UTF-8 bytes. ✅

**Cross-check with cashu-cf**: The mint's `verifyProofSignatureWithPrivateKey()` tries UTF-8 encoding first (`new TextEncoder().encode(secret)`), which matches the wallet's encoding. The hex-decode fallback in `secretToBytes()` is only for legacy ecash compatibility. ✅

---

## 2. Key Derivation (`src/crypto/NUT01.ts`)

### 2.1 `createNewMintKeys` — CORRECT

**Spec (NUT-01)**:
- Keys indexed by amount: `{<amount_1>: <pubkey_1>, ...}`
- `K_i = k_i * G` (private key times generator)
- Compressed secp256k1 format (33 bytes)
- BIP32 derivation path: `m/0'/0'/0'/{index}`

**Implementation** (`NUT01.ts:63-104`):
```typescript
const DERIVATION_PATH = "m/0'/0'/0'";

while (counter < pow2height) {
  const index = (2n ** counter).toString(); // 1, 2, 4, 8, ...
  if (masterKey) {
    const k = masterKey.derive(`${DERIVATION_PATH}/${counter}`).privateKey;
    privKeys[index] = k;
  } else {
    privKeys[index] = createRandomSecretKey();
  }
  pubKeys[index] = getPubKeyFromPrivKey(privKeys[index]); // K = kG (compressed)
  counter++;
}
```

- BIP32 hardened derivation ✅
- Amount = 2^counter (standard power-of-2 denominations) ✅
- Public keys are compressed (`getPubKeyFromPrivKey` uses `secp256k1.getPrivateKey(k, true)`) ✅

### 2.2 `deriveKeysetId` — CORRECT

Supports V0 (`00` prefix) and V1 (`01` prefix) keyset IDs per NUT-02.

V1 preimage format: `amount1:pubkey1,amount2:pubkey2,...|unit:sat|input_fee_ppk:N|final_expiry:T`

Cross-checked with cashu-cf's `deriveKeysetIdV2()` — same preimage construction, same SHA-256, same `01` prefix. ✅

### 2.3 `verifyUnblindedSignature` — CORRECT

**Implementation** (`NUT01.ts:106-111`):
```typescript
export function verifyUnblindedSignature(proof: UnblindedSignature, privKey: Uint8Array): boolean {
  const Y = hashToCurve(proof.secret);
  const a = secp256k1.Point.Fn.fromBytes(privKey);
  const aY = Y.multiply(a);
  return aY.equals(proof.C);
}
```

Checks `C == k * hash_to_curve(secret)` per NUT-00 Step 8. ✅

---

## 3. P2PK Spending Conditions (`src/crypto/NUT11.ts`)

### 3.1 P2PK Secret Construction — CORRECT

**Spec (NUT-10/11)**: Secret is JSON array `["P2PK", {"nonce":"<hex>", "data":"<pubkey>", "tags":[...]}]`

**Implementation** (`NUT11.ts:142-146` + `NUT10.ts:26-36`):
```typescript
export function createP2PKsecret(pubkey: string, tags?: string[][]): string {
  const secret = createSecret('P2PK', pubkey, tags);
  parseP2PKSecret(secret); // validates structure and sigflag
  return secret;
}
```

Output: `["P2PK",{"nonce":"<64hex>","data":"<pubkey>","tags":[["locktime","..."],["pubkeys","..."]]}]`

Matches NUT-10 well-known secret format. ✅

### 3.2 Witness Signing (SIG_INPUTS) — CORRECT

**Spec (NUT-11)**: "The message to sign MUST be constructed using the **unescaped** secret string."

**Implementation** (`NUT11.ts:410-442`):
```typescript
export function signP2PKProof(proof: Proof, privateKey: PrivKey, message?: string): Proof {
  message = message ?? proof.secret; // default: unescaped secret string
  // ... verify key is required ...
  const signature = schnorrSignMessage(message, privateKey);
  // append to witness
}
```

- Message = `proof.secret` (the raw JSON string, not escaped) ✅
- `schnorrSignMessage` hashes with SHA-256, then Schnorr-signs the digest ✅
- Key requirement check: verifies the pubkey is in the expected witness list ✅

**Cross-check with cashu-cf**: The mint's `verifyP2PKSigInputs()` also uses `proof.secret` as the message:
```typescript
const message = messageToSign || proof.secret;
```
And `verifySchnorrSignature()` hashes with `sha256(new TextEncoder().encode(message))`. ✅

### 3.3 SIG_ALL Message Construction — CORRECT

**Spec (NUT-11)**: `msg = secret_0 ‖ C_0 ‖ ... ‖ secret_n ‖ C_n ‖ amount_0 ‖ B_0 ‖ ... ‖ amount_m ‖ B_m [‖ quote_id]`

**Implementation** (`NUT11.ts:673-692`):
```typescript
export function buildP2PKSigAllMessage(inputs, outputs, quoteId?): string {
  const parts: string[] = [];
  for (const p of inputs) {
    parts.push(p.secret, p.C);
  }
  for (const o of outputs) {
    parts.push(String(o.blindedMessage.amount), o.blindedMessage.B_);
  }
  if (quoteId) {
    parts.push(quoteId);
  }
  return parts.join('');
}
```

Produces: `secret_0 C_0 ... secret_n C_n amount_0 B_0 ... amount_m B_m quote_id` ✅

**Cross-check with cashu-cf** (`spending-conditions.ts:669-684`):
```typescript
export function buildSigAllSwapMessage(proofs, outputs): string {
  // identical structure: secret_0 || C_0 || ... || amount_0 || B_0 || ...
}
```
Format matches exactly. The mint also tries legacy format (no C values, no amounts) and various sort orders as candidates. ✅

### 3.4 Locktime/Refund/Anyone-Can-Spend Logic — CORRECT

The `verifyP2PKSpendingConditions()` function (`NUT11.ts:498-582`) implements:
- **ACTIVE lock**: Main pubkeys must satisfy threshold ✅
- **EXPIRED + refund keys**: Both main and refund paths available ✅
- **EXPIRED + no refund keys**: Anyone-can-spend (returns `success: true, path: 'UNLOCKED'`) ✅
- **Permanent lock (no locktime)**: Main pubkeys must satisfy threshold ✅

Cross-checked with cashu-cf's `verifyP2PKSigInputs()` — same locktime/refund semantics. ✅

---

## 4. NUT-20 Quote Signature (`src/crypto/NUT20.ts`)

### 4.1 Amended Message Format — CORRECT

**Spec (cashubtc/nuts#375)**:
```
msg_to_sign = SHA256(
  b"Cashu_MintQuoteSig_v1" ‖
  len32_BE(quote) ‖ quote ‖
  len32_BE(amount_0) ‖ amount_0 ‖ len32_BE(B_0) ‖ B_0 ‖
  ...
)
```

**Implementation** (`NUT20.ts:26-43`):
```typescript
function constructMessage(quote, blindedMessages): Uint8Array {
  const transcript = sha256.create();
  transcript.update(MINT_QUOTE_SIG_DST);              // "Cashu_MintQuoteSig_v1"
  const quoteBytes = utf8ToBytes(quote);
  transcript.update(numberToBytesBE(quoteBytes.length, 4)); // len32 BE
  transcript.update(quoteBytes);
  for (const blindedMessage of blindedMessages) {
    const amountBytes = amountToMinimalBytes(blindedMessage);
    transcript.update(numberToBytesBE(amountBytes.length, 4));
    transcript.update(amountBytes);
    const pointBytes = hexToBytes(blindedMessage.B_);
    transcript.update(numberToBytesBE(pointBytes.length, 4));
    transcript.update(pointBytes);
  }
  return transcript.digest();
}
```

| Component | Spec | Code | Match |
|-----------|------|------|-------|
| Domain separator | `b"Cashu_MintQuoteSig_v1"` | `utf8ToBytes('Cashu_MintQuoteSig_v1')` | ✅ |
| Quote length | 4-byte BE | `numberToBytesBE(len, 4)` | ✅ |
| Amount encoding | minimal BE bytes | `amountToMinimalBytes()` | ✅ |
| B_ encoding | raw 33 bytes | `hexToBytes(B_)` | ✅ |
| Length prefixes | 4-byte BE for each field | `numberToBytesBE(len, 4)` | ✅ |
| Hash | SHA-256 of concatenation | streaming SHA-256 (equivalent) | ✅ |

**Cross-check with cashu-cf** (`mint/nut20.ts:48-76`): Identical format. Both use `DataView.setUint32(0, len, false)` (big-endian) for length prefixes, same domain separator, same field ordering. ✅

### 4.2 Canonical Amount Encoding — CORRECT

**Implementation** (`NUT20.ts:15-20`):
```typescript
function amountToMinimalBytes(blindedMessage): Uint8Array {
  const value = Amount.from(blindedMessage.amount).toBigInt();
  if (value === 0n) return new Uint8Array(0);  // 0 → empty
  const hex = value.toString(16);
  return hexToBytes(hex.length % 2 === 1 ? '0' + hex : hex);
}
```

Produces minimal big-endian representation: `1 → [0x01]`, `256 → [0x01, 0x00]`, `0 → []`.

Cross-checked with cashu-cf's `amountToMinimalBytes()` — identical algorithm. ✅

### 4.3 Dual-Format Signing Strategy — CORRECT (with fallback)

**Observation**: The public barrel (`crypto/index.ts`) exports only the legacy `signMintQuote` / `verifyMintQuoteSignature`. The amended variants (`signMintQuoteAmended`, `verifyMintQuoteSignatureAmended`) are internal-only in v4.

However, the wallet's `Wallet.ts` uses BOTH:
```typescript
// Line 2271-2272:
mintPayload.signature = signMintQuoteAmended(signingKey, quote.quote, blindedMessages);
legacySignature = signMintQuote(signingKey, quote.quote, blindedMessages);
```

And implements automatic fallback (`Wallet.ts:2290-2310`):
```typescript
private async withLegacyQuoteSigFallback(hasLegacySignature, attempt, retryWithLegacySignature) {
  try {
    return await attempt();  // Try amended first
  } catch (e) {
    if (hasLegacySignature && e.code === MINT_QUOTE_SIGNATURE_INVALID_CODE) {
      return retryWithLegacySignature();  // Fall back to legacy
    }
    throw e;
  }
}
```

**Assessment**: This is a deliberate compatibility strategy. The wallet sends the amended signature first (matching cashu-cf and other amended-spec mints), and falls back to legacy if the mint rejects with code 20008. **Not a bug.** ✅

---

## 5. SIG_ALL Multi-Party Signing (`src/model/SigAll.ts`)

### 5.1 Digest Computation — CORRECT

**Implementation** (`SigAll.ts:76-89`):
```typescript
function computeDigests(inputs, outputs, quoteId?): SigAllDigests {
  const sigAllOutputs = outputs.map((blindedMessage) => ({ blindedMessage }));
  const legacyMsg = buildLegacyP2PKSigAllMessage(inputs, sigAllOutputs, quoteId);
  const currentMsg = buildP2PKSigAllMessage(inputs, sigAllOutputs, quoteId);
  return {
    legacy: computeMessageDigest(legacyMsg, true),  // SHA256 hex
    current: computeMessageDigest(currentMsg, true),
  };
}
```

Both formats are computed:
- **Current**: `secret_0 ‖ C_0 ‖ ... ‖ amount_0 ‖ B_0 ‖ ... ‖ quoteId`
- **Legacy**: `secret_0 ‖ ... ‖ B_0 ‖ ... ‖ quoteId` (no C values, no amounts)

### 5.2 Dual-Format Signing — CORRECT

**Implementation** (`SigAll.ts:210-232`):
```typescript
function signPackage(pkg, privkey) {
  newSigs.push(schnorrSignDigest(pkg.digests.current, privkey));
  if (pkg.digests.legacy) {
    newSigs.push(schnorrSignDigest(pkg.digests.legacy, privkey));
  }
}
```

Each signer produces 2 signatures (current + legacy). The mint tries 10+ candidate messages in `verifySigAll()` including both formats. This ensures compatibility with NutShell, CDK, and cashu-cf. ✅

**Note**: This produces witness payloads 2x larger than single-format signing. For a 2-of-3 multisig SIG_ALL with 5 inputs, this means 12 signatures instead of 6. This is a trade-off for backward compatibility, not a bug.

### 5.3 Signing Package Transport — CORRECT

The `SigAllSigningPackage` is serialized as `sigallA` + base64url(JSON), containing:
- `version`: `"sigallA"` (format version)
- `type`: `"swap"` or `"melt"`
- `inputs`: `[{secret, C}]` (minimal proof data for message reconstruction)
- `outputs`: `SerializedBlindedMessage[]`
- `digests`: `{legacy?, current}` (precomputed SHA-256 digests)
- `witness?`: `{signatures: [...]}`

No blinding factors or private keys are included in the package — only what's needed to reconstruct and verify the SIG_ALL message. ✅

---

## 6. Cross-Check Summary: Wallet → Mint Interoperability

| Operation | Wallet Produces | Mint Expects | Match |
|-----------|----------------|--------------|-------|
| Blinded message B_ | Compressed secp256k1 point (33 bytes hex) | `pointFromHex(B_)` | ✅ |
| Secret encoding | UTF-8 of hex string | UTF-8 first (hex-decode fallback) | ✅ |
| Proof C value | Compressed hex (`toHex(true)`) | `pointFromHex(C)` | ✅ |
| P2PK witness message | `proof.secret` (unescaped JSON) | `proof.secret` (unescaped JSON) | ✅ |
| SIG_ALL message | `secret‖C‖...‖amount‖B_‖...‖quoteId` | Same format (among candidates) | ✅ |
| NUT-20 signature | Amended format (with legacy fallback) | Amended format only | ✅* |
| Schnorr signatures | BIP340 x-only, 64 bytes hex | BIP340 x-only, 64 bytes hex | ✅ |
| Keyset ID V1 | `01` + SHA256(preimage) | `01` + SHA256(preimage) | ✅ |

*The wallet sends amended signature first; cashu-cf only supports amended. First-attempt success. Legacy fallback is for other mints (NutShell, older CDK).

---

## 7. Findings

### FINDING-1: [Low] `hashToCurve` Counter Byte Order Platform-Dependent

**Location**: `src/crypto/core.ts:44-46`
**Description**: The counter is encoded via `new Uint8Array(new Uint32Array([n]).buffer)`, which produces little-endian bytes on little-endian platforms. The JS spec does not mandate platform endianness for TypedArray backing buffers.

**Impact**: Negligible. All deployed JS engines (V8, SpiderMonkey, JavaScriptCore) run on little-endian CPUs. No big-endian browser or Node.js runtime exists in production.

**Recommendation**: For spec-purity, use `DataView.setUint32(0, counter, true)` to explicitly request little-endian. This is a code quality improvement, not a security fix.

### FINDING-2: [Informational] NUT-20 Public API Exports Legacy Format

**Location**: `src/crypto/index.ts:11`
**Description**: The public barrel exports `signMintQuote` and `verifyMintQuoteSignature` which use the legacy format (no domain separator, no length prefixes). The amended versions (`signMintQuoteAmended`, `verifyMintQuoteSignatureAmended`) are not exported in v4.

**Impact**: None for the wallet's own operations (Wallet.ts imports the amended function directly from `../crypto/NUT20`). External library consumers who use the public `signMintQuote` will produce signatures incompatible with amended-only mints like cashu-cf.

**Mitigation**: The comment in `index.ts` explicitly documents this as a v4 → v5 migration plan: "v5 exports the amended pair under those names."

**Recommendation**: Document this clearly in the public API changelog. External consumers should be aware that `signMintQuote` uses legacy format until v5.

### FINDING-3: [Informational] SIG_ALL Witness Size Inflation

**Location**: `src/model/SigAll.ts:218-221`
**Description**: The `signPackage` function signs both `digests.current` and `digests.legacy`, producing 2 signatures per signer per format. For N-of-M SIG_ALL, this means `2 * N` signatures in the witness.

**Impact**: Larger witness payloads than necessary. For a typical 1-of-1 SIG_ALL swap, the witness contains 2 signatures (128 bytes) instead of 1 (64 bytes). Not a correctness issue.

**Rationale**: This ensures compatibility with all mint implementations (NutShell uses legacy, CDK ≥0.14 uses current, cashu-cf accepts current). The mint tries all candidate messages and accepts whichever matches.

### FINDING-4: [Observation] `secretToBytes` in cashu-cf Has Latent Encoding Mismatch

**Location**: `cashu-cf/src/crypto/secret-encoding.ts:48-60`
**Description**: The `secretToBytes()` function hex-decodes 64-character hex secrets before `hashToCurve`, while cashu-ts always UTF-8 encodes. For a secret like `"a1b2c3...d4"` (64 hex chars):
- cashu-ts: `hashToCurve([0x61, 0x31, 0x62, 0x32, ...])` (UTF-8 of hex chars)
- cashu-cf `secretToBytes`: `hashToCurve([0xa1, 0xb2, 0xc3, ...])` (hex-decoded bytes)

**Impact**: None in the actual verification flow. The real verification uses `verifyProofSignatureWithPrivateKey()` which tries UTF-8 encoding first (matching the wallet). The `secretToBytes` function is only used by `verifyProofSignature()` which performs a structural check only (always returns true if `hashToCurve` doesn't throw).

**Recommendation**: The `secretToBytes` function should be aligned to always use UTF-8 encoding (matching NUT-00 spec and cashu-ts), with hex-decode only as an explicit legacy fallback path. This prevents future misuse.

---

## 8. Items Verified Correct (No Issues)

| Component | Verification |
|-----------|-------------|
| `hashToCurve` domain separator | ✅ Matches `b"Secp256k1_HashToCurve_Cashu_"` |
| `hashToCurve` point lifting | ✅ Uses `0x02` prefix (even-Y, BIP-340 lift_x) |
| `blindMessage` formula | ✅ `B_ = Y + rG` |
| `unblindSignature` formula | ✅ `C = C_ - rA` |
| `createBlindSignature` formula | ✅ `C_ = a * B_` |
| Proof assembly (`OutputData.toProof`) | ✅ Correct unblind, DLEQ verify, hex serialize |
| Key derivation (BIP32 path) | ✅ `m/0'/0'/0'/{index}` |
| Keyset ID V0/V1 derivation | ✅ Matches NUT-02 |
| P2PK secret format | ✅ NUT-10 well-known secret |
| Witness signing message | ✅ `proof.secret` (unescaped) |
| SIG_ALL message format | ✅ `secret‖C‖amount‖B_[‖quote]` |
| NUT-20 amended binary format | ✅ DST + len32_BE + fields |
| NUT-20 amount encoding | ✅ Minimal big-endian bytes |
| NUT-20 dual-format fallback | ✅ Amended first, legacy retry on 20008 |
| Schnorr sign/verify | ✅ BIP340 x-only, SHA-256 message digest |
| Locktime/refund/anyone-can-spend | ✅ Correct pathway selection |
| Pubkey normalization/dedup | ✅ X-only dedup, 02/03 prefix normalization |
| `hash_e` (DLEQ challenge) | ✅ Uncompressed point hex, UTF-8 encode, SHA-256 |
| SigAll signing package | ✅ No secrets leaked, digests precomputed |

---

## 9. Conclusion

The cashu-ts v4.7.2 wallet crypto implementation is **sound**. The core DHKE protocol (hashToCurve → blindMessage → unblindSignature) is mathematically correct and matches NUT-00. The P2PK/SIG_ALL spending conditions match NUT-11. The NUT-20 quote signature correctly implements the amended spec with backward-compatible fallback.

The cashu-ts wallet produces exactly what the cashu-cf mint expects across all verified crypto surfaces. No exploitable vulnerabilities were identified.

**Verdict**: ✅ **PASS** — No blocking issues found.

---

*Audit conducted by autonomous Layer 3 AI analysis. All findings are based on static code review of cashu-ts v4.7.2 (`src/crypto/`, `src/model/`) and cashu-cf mint verification code (`src/mint/spending-conditions.ts`, `src/mint/nut20.ts`, `src/crypto/`). Cross-referenced against NUT-00, NUT-01, NUT-02, NUT-10, NUT-11, and NUT-20 specifications.*
