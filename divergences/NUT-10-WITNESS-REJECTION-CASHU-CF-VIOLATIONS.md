# NUT-10 Witness on Regular Proof Violation in cashu-cf (2026-07-27)

Source: LLM spec audit of cashu-cf against NUT-10 spec + Nutshell Python reference.
Full report: docs/audits/results/NUT-10-result.md

## Summary

Witness data on non-conditioned (regular) proofs is silently accepted instead of
being rejected. Nutshell explicitly rejects this as defense-in-depth.

## Violation

| # | Requirement | Spec | cashu-cf behavior | Severity |
|---|------------|------|-------------------|----------|
| 1 | Witness on regular proof rejected | NUT-00/NUT-10 implicit | Silently accepted (early return without witness check) | MEDIUM |

## Cross-implementation Comparison

| Behavior | Nutshell (Python) | cashu-cf (TypeScript) |
|----------|-------------------|----------------------|
| Witness on regular proof | ❌ rejects with error | ✅ silently accepts |

## Resolution

Filed as [ISSUE-036](https://github.com/Amperstrand/cashu-cf/blob/main/docs/issues/ISSUE-036-nut10-witness-on-regular-proof.md) (P2).
✅ **Fixed** (2026-07-28).
