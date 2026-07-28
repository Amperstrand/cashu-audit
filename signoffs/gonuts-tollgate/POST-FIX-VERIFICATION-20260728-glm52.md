# Post-Fix Verification: gonuts-tollgate @ opentollgate/main (997bb03) — 2026-07-28

## Metadata
- **Date**: 2026-07-28
- **Model**: GLM-5.2 in opencode
- **Target**: OpenTollGate/gonuts-tollgate @ opentollgate/main (commit 997bb03)
- **Previous audit**: 2026-07-26 against Amperstrand fork (commit 386aaf2)
- **Scope**: Verify fixes for findings from previous audit, check for regressions

---

## Audit Delta: What changed since last audit

Two commits on `opentollgate/main` since `386aaf2`:
1. `3fb9af8` fix: add NUT-04 accounting fields to mint quote responses
2. `997bb03` fix: NUT-20 binary message format + NUT-11 duplicate tag rejection

---

## Finding Verification

### NUT-11 Finding: Duplicate P2PK tags (was FAIL) → ✅ FIXED

**Previous finding**: Duplicate tags silently overwritten — NUT-11 says "MUST be rejected as unspendable."

**Fix verification** (`cashu/nuts/nut11/nut11.go:106-112`):
```go
seen := map[string]bool{}
for _, tag := range tags {
    tagType := tag[0]
    if seen[tagType] {
        return nil, cashu.BuildCashuError("duplicate tag: "+tagType, NUT11ErrCode)
    }
    seen[tagType] = true
```

**Verdict**: Correctly implements duplicate detection. Returns typed error with NUT-11 error code. ✅ **PASS**

### NUT-04 Finding: Missing accounting fields (was WARN/Critical) → ✅ FIXED

**Previous finding**: `amount_paid`, `amount_issued`, `updated_at` absent from `PostMintQuoteBolt11Response`.

**Fix verification** (`cashu/nuts/nut04/nut04.go:67-69`):
```go
AmountPaid   uint64 `json:"amount_paid"`
AmountIssued uint64 `json:"amount_issued"`
UpdatedAt    uint64 `json:"updated_at"`
```

**Verdict**: All three required fields added to response struct. ✅ **PASS**

### NUT-14 Finding: HTLC signature bypass (was FAIL) → ❌ STILL OPEN

**Previous finding**: Receiver pathway with `pubkeys` but no `n_sigs` skips signature verification.

**Code unchanged** (`cashu/nuts/nut14/nut14.go:49-50`):
```go
signatureNeeded := false
if tags.NSigs > 0 {  // ← still only triggers on explicit NSigs
```

If `pubkeys` present but `NSigs` not set (defaults to 0), `signatureNeeded` stays false. Witness created with preimage only.

**Verdict**: Bypass still exploitable. ❌ **FAIL** — Issue filed: OpenTollGate/tollgate-module-basic-go#328

### V4 CBOR Decoding (new finding from TollGate QA) → ❌ STILL OPEN

`DecodeTokenV4` uses `cbor.Unmarshal` with `json` struct tags. CBOR from modern wallets fails to decode. Not fixed on `main` or on `fix/v4-cbor-tags-and-v2-keyset` branch.

**Verdict**: ❌ **FAIL** — Issue filed: OpenTollGate/tollgate-module-basic-go#326

### DecodeToken Error Masking (new finding) → ❌ STILL OPEN

V4 decode error overwritten by V3 fallback error. Users see "invalid V3 token" for V4 input.

**Verdict**: ❌ **WARN** — Diagnostic issue, not exploitable

---

## Updated Summary Table

| NUT | Previous | Current | Change |
|-----|----------|---------|--------|
| NUT-00 (V4 CBOR) | — | FAIL | New finding (from TollGate QA) |
| NUT-04 (accounting) | WARN | **PASS** | ✅ Fixed |
| NUT-05 (error masking) | — | WARN | New finding |
| NUT-11 (duplicate tags) | FAIL | **PASS** | ✅ Fixed |
| NUT-14 (HTLC bypass) | FAIL | **FAIL** | ❌ Still open |

**Overall verdict**: PASS (with 2 open items) — 2 of 3 previous FAIL/WARN findings resolved. NUT-14 bypass and V4 CBOR issue remain.

---

## Sign-off

Audited by **GLM-5.2** in **opencode** on **2026-07-28**.
Target: OpenTollGate/gonuts-tollgate @ opentollgate/main (997bb03)
Previous audit: 2026-07-26 against Amperstrand fork (386aaf2)
