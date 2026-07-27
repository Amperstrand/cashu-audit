# NUT-07 Witness Field Violation in cashu-cf (2026-07-27)

Source: LLM spec audit of cashu-cf against NUT-07 spec.
Full report: docs/audits/results/NUT-07-result.md

## Summary

The `witness` field in checkstate responses is always `null`, even for spent proofs
with NUT-10 spending conditions.

## Violation

| # | Requirement | Spec | cashu-cf behavior | Severity |
|---|------------|------|-------------------|----------|
| 1 | `witness` returns serialized witness data | L72 | Always `null` (hardcoded in all 4 response paths) | MEDIUM |

## Resolution

Filed as [ISSUE-035](https://github.com/Amperstrand/cashu-cf/blob/main/docs/issues/ISSUE-035-nut07-witness-field-checkstate.md) (P2).
