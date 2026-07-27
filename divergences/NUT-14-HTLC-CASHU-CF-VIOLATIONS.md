# NUT-14 HTLC Violations in cashu-cf (2026-07-27)

Source: LLM spec audit of cashu-cf against NUT-14 spec + Nutshell Python reference.
Full report: [NUT-14-result.md](../signoffs/cashu-cf/NUT-14-result-20260727.md)

## Summary

4 spec violations found. The most critical completely blocks the HTLC sender (refund) pathway.

## Violations

| # | Requirement | Spec | cashu-cf behavior | Severity |
|---|------------|------|-------------------|----------|
| 1 | Sender pathway: spend via refund after locktime | L67-71 | `asHTLCWitness()` requires preimage unconditionally — sender CANNOT spend | CRITICAL |
| 2 | Receiver pathway "ALWAYS available" | L63 | Locktime check short-circuits before preimage verification | HIGH |
| 3 | Hash comparison should use bytes | L90 | Uses string equality (fragile) | LOW |
| 4 | `secret.data` format validation | L48 | Only validates preimage, not hash lock format | LOW |

## Cross-implementation comparison

| Behavior | Nutshell (Python) | cashu-cf (TypeScript) |
|----------|-------------------|----------------------|
| Sender pathway after locktime | ✅ works (preimage optional) | ❌ BLOCKED (requires preimage) |
| Receiver pathway after locktime | ✅ always available | ❌ not checked |
| Preimage requirement | ✅ optional for refund | ❌ always required |

## Resolution

Filed as [ISSUE-031](https://github.com/Amperstrand/cashu-cf/blob/main/docs/issues/ISSUE-031-nut14-htlc-spec-violations.md).
Fix in progress (2026-07-27).
