# NUT-20 Quote Signature Format Violations in cashu-cf (2026-07-27)

Source: LLM spec audit of cashu-cf against NUT-20 spec + Nutshell Python reference.
Full report: docs/audits/results/NUT-20-result.md

## Summary

The quote signature verification uses the **wrong message format**. This silently breaks
NUT-20 locked quotes — signatures from spec-compliant wallets are rejected.

## Violation

| # | Requirement | Spec | cashu-cf behavior | Severity |
|---|------------|------|-------------------|----------|
| 1 | Message aggregation format | L110-123: `b"Cashu_MintQuoteSig_v1" \|\| len32(quote) \|\| quote \|\| len32(amount_i) \|\| amount_i \|\| len32(B_i) \|\| B_i` | Naive string concat: `quote + B_.join('')` | **CRITICAL** |

### What's Wrong

1. ❌ No domain separator `b"Cashu_MintQuoteSig_v1"`
2. ❌ No `len32()` 4-byte big-endian length prefixes
3. ❌ No `amount_i` values in the message
4. ❌ `B_i` values are hex-encoded UTF-8 strings, not raw decoded bytes

### Affected Files

- `src/mint/nut20.ts` — `verifyMintQuote()` (line 69)
- `src/mint/verification.ts:119` — duplicated incorrect format

## Cross-implementation Comparison

| Implementation | Domain separator | Length prefixes | Amounts | Raw B_ bytes |
|---------------|-----------------|-----------------|---------|-------------|
| Nutshell (Python) | ✅ | ✅ | ✅ | ✅ |
| CDK (Rust) | ✅ | ✅ | ✅ | ✅ |
| cashu-cf (TS) | ❌ | ❌ | ❌ | ❌ |

## Resolution

Filed as [ISSUE-033](https://github.com/Amperstrand/cashu-cf/blob/main/docs/issues/ISSUE-033-nut20-quote-signature-format.md) (P0).
