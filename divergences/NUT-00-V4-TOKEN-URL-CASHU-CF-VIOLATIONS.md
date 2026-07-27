# NUT-00 V4 Token URL Trailing Slash Violation in cashu-cf (2026-07-27)

Source: LLM spec audit of cashu-cf against NUT-00 spec.
Full report: docs/audits/results/NUT-00-result.md

## Summary

V4 token mint URLs are not normalized — trailing slashes are not stripped.

## Violation

| # | Requirement | Spec | cashu-cf behavior | Severity |
|---|------------|------|-------------------|----------|
| 1 | Mint URL MUST strip trailing slashes | L281 | No normalization performed | LOW |

## Resolution

Filed as [ISSUE-037](https://github.com/Amperstrand/cashu-cf/blob/main/docs/issues/ISSUE-037-nut00-v4-token-url-trailing-slash.md) (P2).
