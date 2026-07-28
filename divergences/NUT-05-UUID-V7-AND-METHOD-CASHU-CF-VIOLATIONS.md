# NUT-05 UUID v7 + Method Field Violations in cashu-cf (2026-07-27)

Source: LLM spec audit of cashu-cf against NUT-05 spec + Nutshell Python reference.
Full report: docs/audits/results/NUT-05-result.md

## Summary

Two interop violations: quote IDs are random hex instead of UUID v7, and melt
quote responses omit the `method` field.

## Violations

| # | Requirement | Spec | cashu-cf behavior | Severity |
|---|------------|------|-------------------|----------|
| 1 | Quote IDs MUST be UUID v7 | L61,75: time-ordered with version/variant bits | 32-char random hex (no dashes, no version, no timestamp) | HIGH |
| 2 | Melt response MUST include `method` | L66, 23.md:167 | Value known but never serialized | HIGH |

## Cross-implementation Comparison

| Behavior | Nutshell (Python) | cashu-cf (TypeScript) |
|----------|-------------------|----------------------|
| Quote ID format | ✅ UUID v7 | ❌ random hex |
| Melt response `method` | ✅ always serialized | ❌ omitted |

## Resolution

Filed as [ISSUE-034](https://github.com/Amperstrand/cashu-cf/blob/main/docs/issues/ISSUE-034-nut05-uuid-v7-and-method-field.md) (P1).
✅ **Fixed** (commit `c1cb6a2`, 2026-07-27).
