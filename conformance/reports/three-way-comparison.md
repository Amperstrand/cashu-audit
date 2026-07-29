# Three-Way Cross-Implementation Comparison

**Date**: 2026-07-29
**Suite**: 107 conformance scenarios across 17 NUT categories

## Results Summary

| Implementation | Version | Pass | Fail | Skip | NUTs Advertised |
|----------------|---------|------|------|------|-----------------|
| **cashu-cf** | Nutshell-CF/0.0.1 | **104** | **0** | 3 | 13 (4,5,7,8,9,10,11,12,14,19,20,23,29) |
| **CDK** | cdk-mintd/0.17.3 | ~60 | ~8 | ~39 | 14 (4,5,7,8,9,10,11,12,14,15,17,19,20,29) |
| **Nutshell** | Nutshell/0.20.0 | ~64 | ~33 | ~10 | 6 (4,5,7,8,9,11) |

## Key Findings

### cashu-cf Advantages
- ✅ **Best conformance**: 0 failures across 107 scenarios
- ✅ **NUT-04 accounting**: Only implementation with amount_paid/amount_issued/updated_at
- ✅ **Strictest validation**: Rejects invalid inputs (wrong keysets, wrong preimages, zero amounts)
- ✅ **NUT-23 BOLT11**: Only implementation advertising NUT-23

### CDK Advantages
- ✅ **Most NUTs**: 14 advertised (includes NUT-15 MPP, NUT-17 WebSocket)
- ✅ **V2 keysets**: Defaults to V2 keyset IDs (`use_keyset_v2 = true`)
- ✅ **NUT-12 DLEQ**: Full DLEQ proof support in responses

### CDK Gaps Found
- ❌ **NUT-04 accounting fields missing**: No amount_paid, amount_issued, updated_at
- ❌ **SIG_ALL output swap accepted**: Doesn't reject swapped output amounts (security gap)
- ❌ **HTLC locktime refund fails**: Returns "Secret is not a HTLC secret" error

### Nutshell Gaps Found
- ❌ **Wrong keysets accepted**: Allows proofs with incorrect keyset IDs (security)
- ❌ **Wrong HTLC preimages accepted**: 5 scenarios fail (validation gap)
- ❌ **Zero amount accepted**: Allows minting 0-sat quotes
- ❌ **No NUT-12/14/19/20/29**: Missing DLEQ, HTLC, cache, quote sigs, batch

## Cross-Implementation Divergences

| Feature | cashu-cf | CDK | Nutshell |
|---------|----------|-----|----------|
| NUT-04 accounting fields | ✅ | ❌ | ❌ |
| NUT-12 DLEQ proofs | ✅ | ✅ | ❌ |
| NUT-14 HTLC | ✅ | ✅ (with bugs) | ❌ |
| NUT-15 MPP | ❌ | ✅ | ❌ |
| NUT-17 WebSocket | ❌ | ✅ | ❌ |
| NUT-19 cache | ✅ | ✅ | ❌ |
| NUT-20 quote sigs | ✅ | ✅ | ❌ |
| NUT-23 BOLT11 method | ✅ | ❌ | ❌ |
| NUT-29 batch | ✅ | ✅ | ❌ |
| V2 keyset IDs | ❌ (V1) | ✅ (V2 default) | ✅ (V2) |
| Strict input validation | ✅ (strictest) | Medium | Lenient |
| UUID v7 quote IDs | ✅ | ❌ | ❌ |
| BOLT11 invoice format | Dummy (FakeWallet) | Dummy (FakeWallet) | Real BOLT11 |

## Conclusion

**cashu-cf is the most spec-compliant implementation** across the tested scenarios.
CDK has the broadest NUT coverage. Nutshell has the simplest implementation.

Each implementation has unique strengths:
- cashu-cf: Best validation, most complete NUT-04 accounting
- CDK: Most NUTs, V2 keysets, MPP + WebSocket support
- Nutshell: Real Lightning integration, simplest setup
