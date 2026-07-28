# Security Audit: cashu-cf

**Date**: 2026-07-28
**Auditor**: Automated security review (Sisyphus-Junior)
**Commit**: ea5b657
**Scope**: ISSUE-041 (private key leak in logs), ISSUE-042 (raw error messages), input validation gaps

---

## Executive Summary

| Severity | Count | Summary |
|----------|-------|---------|
| **HIGH** | 2 | Private key fragment in logs; full raw error messages leaked to clients |
| **MEDIUM** | 5 | Stack trace logging; inconsistent error format; missing request body size limits; verbose proof diagnostics leaked; Lightning invoice logging |
| **LOW** | 6 | Signing debug logging; duplicate console.error patterns; missing negative-amount checks in verification.ts; invoice prefix logging; unvalidated Y format in checkstate; health endpoint error leak |
| **INFO** | 3 | NUT-00 format inconsistency; debug endpoint in production path; key fingerprint logging |

**Overall Assessment**: The codebase has a solid error-handling framework (`error-handling.ts`) with proper Cashu error codes, but multiple catch blocks bypass it by injecting raw `error.message` strings into client-facing HTTP responses. The private key leak (ISSUE-041) is config-gated but still a clear policy violation. Input validation is generally strong but has gaps in verification.ts and checkstate.

---

## FINDING-1: Private Key Prefix Leaked in Logs (ISSUE-041)

**Severity**: HIGH
**File**: `src/mint/router.ts:214`
**CVSS**: 3.7 (Low exploitability, config-gated, but principle violation)

### Description

When `MINT_LOG_SIGNING_DETAILS=true`, the signing path logs the first 20 hex characters (10 bytes) of the 32-byte secp256k1 private key to Cloudflare Workers observability:

```typescript
// src/mint/router.ts:213-214
const privKeyHex = bytesToHex(privateKey);
logSigning(`[router.signBlindedMessagesWithTracking] ✅ Private key derived: ${privKeyHex.substring(0, 20)}... (length: ${privKeyHex.length})`);
```

This leaks 10 of 32 bytes of the derived per-denomination private key. While 22 bytes (176 bits) of entropy remain unknown, this violates the fundamental principle of never logging cryptographic secrets. The README explicitly states "Private keys are derived on-demand, not persisted in storage" — partially logging them undermines this guarantee.

### Impact

- **Config-gated**: Only triggers when operator sets `MINT_LOG_SIGNING_DETAILS=true` (defaults to off)
- **Partial exposure**: 10 of 32 bytes leaked; computationally infeasible to brute-force the remaining 176 bits
- **Observability access**: Anyone with Cloudflare Workers Logs access can view these
- **Log retention**: Cloudflare Workers logs may be retained for extended periods

### Evidence

The `logSigning` function is defined at line 171:
```typescript
const logSigning = (...args: any[]) => {
  if (logSigningDetails) console.log(JSON.stringify({message: 'signing_debug', args: String(args)}));
};
```

### Additional Signing Details Leaked

Lines 199, 208-210, 216, 223, 240 also log keyset IDs, amounts, and signature IDs when this flag is enabled. While not as sensitive as the private key, these provide excessive operational detail.

### Fix

```typescript
// Replace privKeyHex logging with hash-based redaction:
logSigning(`[router] Private key derived: [REDACTED, sha256=${await sha256(privKeyHex)}] length=${privKeyHex.length}`);
```

---

## FINDING-2: Raw Internal Error Messages Leaked to Clients (ISSUE-042)

**Severity**: HIGH
**Files**: `src/api/mint.ts:508,1467`, `src/api/melt.ts:1091,3417,3453`
**CVSS**: 5.3 (Network-based, information disclosure)

### Description

Multiple API catch blocks inject raw `error.message` strings directly into HTTP response bodies sent to clients. These messages can contain:
- Internal file paths
- Library names and versions (fingerprinting)
- SQL query fragments
- Configuration details
- Stack trace fragments

### Evidence — 5 confirmed instances:

**1. `src/api/mint.ts:508`** — Mint quote creation:
```typescript
const errorResponse = CommonErrors.internalError(`Failed to create mint quote: ${errorMessage}`);
```
Client sees: `{"error":"internal_error","detail":"Failed to create mint quote: <raw error>"}`

**2. `src/api/mint.ts:1467`** — Mint token operation:
```typescript
return CommonErrors.internalError(`Failed to mint tokens: ${errorMessage}`);
```

**3. `src/api/melt.ts:3417`** — Melt token operation (inner catch):
```typescript
return await finalize(CommonErrors.internalError(`Melt operation failed: ${errorMessage}`), 'error', {...});
```

**4. `src/api/melt.ts:3453`** — Melt token operation (outer catch):
```typescript
return await finalize(CommonErrors.internalError(`Melt operation failed: ${errorMessage}`), 'error', {...});
```

**5. `src/api/melt.ts:1091`** — Melt quote creation:
```typescript
const res = CommonErrors.invalidRequest(err.message);  // Raw error message as 400 detail
```
This is especially problematic: any internal exception gets mapped to a 400 "invalid_request" with the raw error message, potentially confusing clients and leaking internals.

### Impact

Attackers performing reconnaissance can:
1. Fingerprint libraries by error message patterns
2. Identify infrastructure (SQL engines, crypto libraries)
3. Map error conditions and input validation boundaries
4. Discover internal paths and module structure

### Fix

```typescript
// Log internally with full detail:
error('Mint quote failed', { error: errorMessage, stack: errorStack });

// Return generic message to client:
return CommonErrors.internalError('Failed to create mint quote');
```

---

## FINDING-3: Stack Trace Fragments Logged to Observability

**Severity**: MEDIUM
**File**: `src/api/mint.ts:494,503`, `src/mint/router.ts:311-315,512-516`

### Description

Stack traces are logged to Cloudflare Workers observability with 500-char truncation:

```typescript
// src/api/mint.ts:494
const errorStack = err instanceof Error ? err.stack : undefined;
// ...
// src/api/mint.ts:503
errorStack: errorStack?.substring(0, 500), // Truncate stack for logging
```

```typescript
// src/mint/router.ts:512-516
obsError('Mint quote router error', {
  errorType: error instanceof Error ? error.constructor.name : 'UnknownError',
  errorMessage: error instanceof Error ? error.message : String(error),
  errorStack: error instanceof Error ? error.stack  // Full stack, no truncation
});
```

### Impact

- Stack traces in observability may reveal file paths, internal module names
- Not directly exposed to clients (only to operators with log access)
- Router.ts does NOT truncate the stack (unlike mint.ts)

### Fix

Consistently truncate or omit stack traces in production. Consider `error.stack?.split('\n')[0]` to log only the first frame.

---

## FINDING-4: Inconsistent Error Response Format (NUT-00 Non-Compliance)

**Severity**: MEDIUM
**Files**: `src/utils/error-handling.ts`, `src/core/errors.ts`

### Description

The codebase has **two conflicting error response formats**:

**Format A** (`src/utils/error-handling.ts` — used by most API handlers):
```json
{"error": "internal_error", "detail": "...", "code": 10000}
```

**Format B** (`src/core/errors.ts` — NUT-00 spec compliant):
```json
{"detail": "...", "code": 10000}
```

NUT-00 specifies the error format as `{"detail": "message", "code": <number>}`. The `error` field in Format A is a non-standard addition. While most endpoints use Format A (via `CommonErrors`), `createErrorResponse` from `core/errors.ts` uses Format B.

### Evidence

`src/core/errors.ts:197-203`:
```typescript
export function createErrorResponse(error: unknown, headers: HeadersInit = {}): Response {
  const body = formatErrorResponse(error);  // {detail, code}
  // ...
}
```

`src/utils/error-handling.ts:116-142`:
```typescript
export function createStandardErrorResponse(status, error, detail?, code?): Response {
  const body: CashuErrorResponse = { error, ...(detail && { detail }), ...(code && { code }) };
  // ...
}
```

### Impact

Wallets strictly following NUT-00 may not parse the `error` field, missing the error classification. The `detail` field is sometimes omitted (when falsy), making errors opaque.

### Fix

Align both paths to the NUT-00 format: `{"detail": "...", "code": <number>}`. The `error` string field can be kept as an extension, but `detail` should always be present.

---

## FINDING-5: Missing Request Body Size Limits

**Severity**: MEDIUM
**Files**: All API handlers using `parseJson()`

### Description

API handlers parse request bodies via `parseJson()` without enforcing a maximum body size. A malicious client could send an oversized JSON payload to:
- Exhaust Cloudflare Workers memory (128MB limit)
- Create a Denial of Service condition
- Trigger expensive array operations on huge arrays

### Evidence

`src/api/mint.ts:144`:
```typescript
const parsed = await parseJson<MintQuotePayload>(request);
```

While `validateArray` enforces count limits (e.g., `maxMintOutputs`), there is no check on the total request body size before parsing. Cloudflare Workers has built-in body size limits (100MB for free tier), but this is far too generous for Cashu API endpoints.

### Impact

- Memory exhaustion DoS
- CPU time exhaustion (parsing + validating large payloads)

### Fix

Check `request.headers.get('content-length')` before parsing, or use `request.text()` with a size limit before `JSON.parse()`.

---

## FINDING-6: Verbose Proof Diagnostic Information Leaked in Error Responses

**Severity**: MEDIUM
**File**: `src/api/melt.ts:1958-1997`

### Description

When proof signature verification fails, the error response includes extensive diagnostic information:

```typescript
// src/api/melt.ts:1959-1972
const diagInfo = {
  amount: input.amount,
  keysetId: id,
  secret: String(input.secret).substring(0, 20) + '...',  // Proof secret prefix!
  secretLength: String(input.secret).length,
  C: C.substring(0, 20) + '...',  // Signature prefix!
  cLength: C.length,
  pubKeyHex: pubKeyHex.substring(0, 20) + '...',  // Public key prefix!
  pubKeyLength: pubKeyHex.length,
  hasDLEQ: !!dleq,
  resolvedUnit: resolvedUnit,
  quoteUnit: quote.unit,
  resolvedBy: resolvedBy
};
```

```typescript
// src/api/melt.ts:1995-1997
return createStandardErrorResponse(400, 'invalid_proof', 
  `Invalid proof signature at index ${i}. Debug: keysetId=${id}, unit=${resolvedUnit}, amount=${amount}${diagStr}`, 
  CashuErrorCodes.INVALID_PROOF);
```

### Impact

- Proof secret prefixes (20 chars) leak partial secret data — secrets are used to derive proof Y values
- Public key prefixes leak keyset structure
- Internal resolution state (`resolvedBy`, `resolvedUnit`) leaks operational details
- This is a debugging aid that should be production-gated

### Fix

Return a generic "Invalid proof signature" message. Log diagnostics internally only.

---

## FINDING-7: Lightning Invoice Logged in Observability

**Severity**: LOW
**File**: `src/mint/verification.ts:272,282`

### Description

The verification module logs full Lightning invoice strings:

```typescript
// src/mint/verification.ts:272
globalThis.LOG?.error?.('INVALID_LIGHTNING_INVOICE_FORMAT', {
  invoice,  // Full invoice string!
  context: 'mint-verification',
}) || console.error(JSON.stringify({ message: 'Invalid Lightning invoice format', invoice, context: 'mint-verification' }));

// src/mint/verification.ts:282
globalThis.LOG?.info?.('LIGHTNING_INVOICE_FORMAT_VERIFIED', {
  invoice,  // Full invoice string on success too!
  context: 'mint-verification',
})
```

### Impact

BOLT11 invoices contain payment hashes, amounts, and descriptions that could be sensitive. Logging them to observability creates a data retention concern.

### Fix

Log only the invoice prefix (`invoice.slice(0, 24) + '...'`) as done elsewhere in the codebase (e.g., `melt.ts`).

---

## FINDING-8: `MINT_LOG_SIGNING_DETAILS` Debug Logging Surface

**Severity**: LOW
**File**: `src/mint/router.ts:96-98,170-173`

### Description

The `MINT_LOG_SIGNING_DETAILS` flag enables verbose signing diagnostics including keyset IDs, amounts, and signature metadata. This is a debugging surface that, if accidentally enabled in production, exposes operational details.

```typescript
// src/mint/router.ts:96-98
private shouldLogSigningDetails(): boolean {
  return String(String(this.context.env?.MINT_LOG_SIGNING_DETAILS ?? '')).toLowerCase() === 'true';
}
```

### Impact

Low — defaults to disabled. But no guard prevents enabling it in production environments.

### Fix

Consider environment-gating (only allow in `local` or `testnut` environments).

---

## FINDING-9: Console.error Fallback Pattern Leaks Error Messages

**Severity**: LOW
**Files**: `src/mint/verification.ts` (23 instances), `src/api/melt.ts`, `src/api/checkstate.ts`

### Description

The verification module uses a dual-logging pattern:

```typescript
globalThis.LOG?.error?.('CODE', { data }) || console.error(JSON.stringify({ data }));
```

When `globalThis.LOG` is not configured (e.g., in some test or edge environments), the `console.error` fallback fires, logging raw data to Workers observability. This is acceptable for internal logging but the pattern means error messages from catch blocks flow through unfiltered.

### Impact

Low — internal only, but means error messages are present in logs in plaintext.

---

## FINDING-10: Input Validation Gaps in verification.ts

**Severity**: LOW
**File**: `src/mint/verification.ts:93,177-204`

### Description

**Gap 1 — Non-power-of-2 amounts in `verifyProofAmounts`:**
The method validates amounts against a hardcoded denomination list:
```typescript
const validDenominations = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536];
```
This is capped at 65536 (2^16), but keysets support `max_order` up to 18 (2^18 = 262144). Amounts between 65536 and 262144 would be incorrectly rejected.

**Gap 2 — Missing negative amount check in `_verifyOutputs`:**
```typescript
if (output.amount <= 0) {
  throw new CashuError(0, `Invalid output amount: ${output.amount}`);
}
```
This includes the raw amount in the error message. While `<= 0` catches negatives, the error leaks the exact invalid value.

**Gap 3 — `verifyMeltOperation` treats proofs as `string[]` but accesses `.amount`:**
```typescript
async verifyMeltOperation(proofs: string[], amount: number, feeRate: number) {
  // ...
  const totalAmount = proofs.reduce((sum, proof) => sum + (proof as any).amount || 0, 0);
```
Type mismatch — `proofs` is typed as `string[]` but treated as objects. This method appears unused but is a latent bug.

### Impact

Low — the main validation paths in `api/mint.ts` and `api/melt.ts` have their own robust validation. These gaps exist in the `LedgerVerification` class which appears to be partially used.

### Fix

1. Make `validDenominations` dynamic based on keyset `max_order`
2. Remove amount from error message: `'Invalid output amount'`
3. Fix type signature of `verifyMeltOperation`

---

## FINDING-11: Checkstate Y Values Not Format-Validated (Standard Path)

**Severity**: LOW
**File**: `src/api/checkstate.ts:122-125,272`

### Description

In the standard NUT-07 path (direct `Ys` array), Y values are passed directly to `proofStateManager.getProofState(Y)` without format validation:

```typescript
// src/api/checkstate.ts:122-125
if ('Ys' in parsed && Array.isArray(parsed.Ys)) {
  Ys = parsed.Ys;
}
// ...
// Line 272:
const stateEnum = await proofStateManager.getProofState(Y);
```

The legacy paths (proofs/secrets) validate via `looksLikeCompressedPointHex()`, but the standard `Ys` path does not. Malformed Y values are passed to the storage layer, which may handle them inconsistently.

### Impact

Low — storage layer likely returns UNSPENT for unknown values, but unvalidated input reaching storage is poor hygiene.

### Fix

Validate Y format in the standard path:
```typescript
if (!looksLikeCompressedPointHex(Y)) {
  return CommonErrors.invalidRequest('Invalid Y format');
}
```

---

## FINDING-12: Health Endpoint Leaks Error Messages

**Severity**: LOW
**File**: `src/api/health.ts:125,157,195,234`

### Description

Health check endpoints return raw error messages in response bodies:

```typescript
// src/api/health.ts:125
error: error instanceof Error ? error.message : 'Unknown error'
// Returns: {"status":"error","error":"<raw message>"}

// src/api/health.ts:195
return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Unknown error' }), {...});
```

### Impact

Low — health endpoints typically aren't exposed to external clients, but if publicly accessible, they leak internal error details (database errors, connection failures, etc.).

### Fix

Return generic health status: `{"status":"unhealthy"}` without the raw error.

---

## FINDING-13: Debug Endpoint Exposed in Router

**Severity**: INFO
**File**: `src/mint/router.ts:104-144`

### Description

A debug endpoint `POST /v1/debug/melt-payload` exists that logs incoming proof data:

```typescript
async debugMeltPayload(request: Request): Promise<Response> {
  // Logs proof secrets, C values, amounts to observability
  CloudflareLogger.logDebug('debug_melt_first_proof', 'debug_endpoint', {
    proof: { secret: body.inputs[0].secret, C: body.inputs[0].C, ... }
  });
```

### Impact

Informational — depends on whether this route is registered in production. If accessible, it logs proof secrets to observability and reveals endpoint existence.

### Recommendation

Verify this route is not registered in production environments.

---

## FINDING-14: Keyset Fingerprint Logging

**Severity**: INFO
**File**: `src/api/admin-statistics.ts:145,528-532`

### Description

Admin statistics compute a SHA-256 fingerprint of `MINT_PRIVATE_KEY`:

```typescript
// Line 528-532
if (!env?.MINT_PRIVATE_KEY) { ... }
const masterKey = String(env.MINT_PRIVATE_KEY);
// Used to derive expected keysets for comparison
```

The fingerprint is described as "first 16 hex chars of SHA-256" which is safe (cannot reverse to the key). This is informational — the admin endpoint is access-controlled.

---

## Positive Findings

1. **Strong error code framework**: `CashuErrorCodes` in `error-handling.ts` is well-structured and aligned with NUT error code specifications
2. **Proper CashuError hierarchy**: `core/errors.ts` provides spec-compliant error classes with correct codes
3. **Private key provider pattern**: `CashuMintSigner` correctly uses a provider function for on-demand key derivation rather than storing keys
4. **Input validation utilities**: `validation.ts` provides solid reusable validators (`validateArray`, `validateProofStructure`, `validateBlindedMessage`)
5. **Amount validation**: `validateAmount`, `validateMaxOperationAmount`, `validateMinOperationAmount` properly enforce bounds
6. **Duplicate detection**: `checkDuplicateSecrets`, `checkDuplicateYs`, `checkDuplicateBlindingFactors` prevent replay attacks
7. **Max operation limits**: `MAX_OPERATION_AMOUNT`, `MAX_MINT_OUTPUTS`, `MAX_SWAP_INPUTS` provide DoS protection
8. **No private key persistence**: Keys are derived via HMAC-SHA256 from master key, never stored in databases

---

## Recommendations

### Immediate (P1)
1. **FINDING-1**: Remove private key prefix from signing debug logs
2. **FINDING-2**: Strip raw error messages from all 5 client-facing catch blocks
3. **FINDING-6**: Remove proof diagnostic info from melt error responses

### Short-term (P2)
4. **FINDING-4**: Standardize on NUT-00 error format (`{detail, code}`)
5. **FINDING-5**: Add request body size limits (recommend 1MB max)
6. **FINDING-3**: Consistently truncate stack traces in observability
7. **FINDING-7**: Truncate Lightning invoices in all log calls

### Long-term (P3)
8. **FINDING-10**: Fix verification.ts denomination list and type mismatches
9. **FINDING-11**: Validate Y format in checkstate standard path
10. **FINDING-13**: Ensure debug endpoint is not production-accessible
11. **FINDING-8**: Environment-gate `MINT_LOG_SIGNING_DETAILS`

---

## Audit Methodology

1. Read all API handler files (`mint.ts`, `melt.ts`, `checkstate.ts`, `keys.ts`)
2. Read error handling infrastructure (`error-handling.ts`, `error.ts`, `core/errors.ts`)
3. Read signing infrastructure (`cashu-signer.ts`, `mint/router.ts`)
4. Read verification layer (`mint/verification.ts`)
5. Read validation utilities (`validation.ts`)
6. Searched for patterns: `privateKey`, `console.log`, `error.message`, `error.stack`, `MINT_LOG_SIGNING`
7. Cross-referenced ISSUE-041 and ISSUE-042 issue files
8. Compared error response format against NUT-00 specification

---

## Sign-off

This audit covers the specified scope at commit ea5b657. Findings are based on static code analysis. Runtime verification of exploitability was not performed for this audit.

**Next steps**: Address FINDING-1 and FINDING-2 immediately as they map to tracked issues ISSUE-041 and ISSUE-042.
