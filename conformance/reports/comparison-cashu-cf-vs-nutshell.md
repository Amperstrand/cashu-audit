# Cross-Implementation Comparison: cashu-cf vs Nutshell

**Date**: 2026-07-28
**cashu-cf**: testnut.cashu.exchange (Nutshell-CF/0.0.1)
**Nutshell**: localhost:3338 (Nutshell/0.20.0, FakeWallet)

## Summary

| Metric | cashu-cf | Nutshell |
|--------|----------|----------|
| **Pass** | 97 | ~64 |
| **Fail** | 0 | ~33 |
| **Skip** | 3 | ~3 |
| **Pass Rate** | 100% | ~66% |

## Key Divergences

### 1. Input Validation (cashu-cf stricter)
- **Wrong keyset proofs**: cashu-cf rejects ❌, Nutshell accepts ✅ (SECURITY)
- **Zero-amount mint quotes**: cashu-cf rejects ❌, Nutshell accepts ✅
- **Wrong HTLC preimages**: cashu-cf rejects ❌, Nutshell accepts ✅ (in some paths)

### 2. NUT Coverage (cashu-cf broader)
| NUT | cashu-cf | Nutshell |
|-----|----------|----------|
| NUT-12 (DLEQ) | ✅ | ❌ Not in response |
| NUT-14 (HTLC) | ✅ | ✅ (but lenient validation) |
| NUT-19 (Cache) | ✅ | ❌ Not advertised |
| NUT-20 (Quote Sig) | ✅ | ❌ Not supported |
| NUT-29 (Batch) | ✅ | ❌ Not supported |

### 3. SIG_ALL Message Format
- **cashu-cf**: Uses 10 candidate message formats for backward compatibility
- **Nutshell**: Uses legacy format (secrets + B_ only)
- Both accept each other's signatures when formats overlap

### 4. Quote Accounting
- **cashu-cf**: UUID v7 IDs, amount_paid/amount_issued/updated_at fields
- **Nutshell**: Random hex IDs (pre-V7), missing accounting fields in this version

### 5. NUT-09 Restore
- **cashu-cf**: Works (returns stored signatures)
- **Nutshell**: Returns 404 on restore endpoint

## Conclusions

cashu-cf is **more spec-compliant** than Nutshell 0.20.0 in:
- Input validation (stricter, more secure)
- NUT coverage (6 additional NUTs)
- Accounting fields (NUT-04 compliance)
- Error handling

Nutshell has **advantages** in:
- Simplicity (fewer endpoints to maintain)
- Real BOLT11 invoice support (vs cashu-cf's FakeWallet dummy invoices)
