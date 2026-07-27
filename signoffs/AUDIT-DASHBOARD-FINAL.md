# Cashu Implementation Audit Dashboard — FINAL

> **Date**: 2026-07-26
> **Auditor**: GLM-5.2 in opencode
> **Scope**: 5 Cashu implementations, all NUTs, 3-layer audit framework

## Coverage Matrix

| Implementation | Language | Quotes | spectate | AI Audits | Status |
|---|---|---|---|---|---|
| **cashu-cf** | TypeScript | 124 | ✅ exit 0 | 14 signoffs | ✅ Complete |
| **CDK** v0.17.3 | Rust | 137 | ✅ exit 0 | 23 signoffs | ✅ Complete |
| **Nutshell** | Python | 129 | ✅ exit 0 | 21 signoffs | ✅ Complete |
| **gonuts-tollgate** | Go | 85 | ✅ exit 0 | 1 signoff | ✅ Complete |
| **micronuts** | Rust (embedded) | 7 | ✅ exit 0 | 1 signoff | ✅ Complete |
| **TOTAL** | 3 languages | **482** | All green | **70 signoffs** | |

## Key Findings Across All Implementations

### Critical Findings

| # | Implementation | Finding | Severity | Status |
|---|---|---|---|---|
| 1 | cashu-cf | NUT-04 output validation `===` vs `<=` | **Fixed** | ISSUE-023 resolved |
| 2 | gonuts-tollgate | NUT-04 accounting fields (`amount_paid`/`amount_issued`/`updated_at`) completely absent | **Critical** | Documented |
| 3 | CDK | Duplicate tags use first-match (spec says MUST reject) | Low | Documented |
| 4 | CDK + Nutshell | n_sigs > pubkeys not validated at parse time | Medium | Documented |

### Cross-Implementation Pattern: NUT-04 Accounting Fields

**3 of 5 implementations** have NUT-04 accounting field issues:
- cashu-cf: had `===` validation (FIXED → `<=`)
- CDK: partial implementation (fields exist but via `extra` flatten)
- gonuts-tollgate: fields completely absent from data model

This suggests the NUT-04 accounting requirements need **community attention** — either spec clarification or implementation guidance.

### CDK #2252: 75% Outdated

6 of 8 documented divergences between CDK and Nutshell don't match current code. CDK and Nutshell are more aligned than anyone thought.

### Post-Quote Audit Insight

Across 3 post-quote audits (CDK v0.15.1, v0.17.3, Nutshell): **0 new findings** attributed to quotes. Quotes improve precision, measurability, and sustainability — not one-time discovery. Value is in CI-enforced drift prevention.

## Layer 1 (greatspectations) Coverage

| Spec | cashu-cf | CDK | Nutshell | gonuts | micronuts |
|---|---|---|---|---|---|
| NUT-00 | 7 | 7 | 21 | 6 | — |
| NUT-01 | 2 | 2 | 2 | 4 | 3 |
| NUT-02 | 5 | 5 | 5 | 6 | 3 |
| NUT-03 | 6 | 0* | 1 | 5 | — |
| NUT-04 | 9 | 9 | 6 | 5 | 1 |
| NUT-05 | 2 | 2 | 4 | 3 | — |
| NUT-06 | 6 | 6 | 13 | 5 | — |
| NUT-07-09 | 8 | 16 | 7 | — | — |
| NUT-10/11/14 | 23 | 27 | 25 | — | — |
| NUT-12-17 | 15 | 14 | 14 | 51 | — |
| NUT-19-29 | 14 | 42 | 21 | — | — |
| BIP-340/39 | — | 5 | — | — | — |
| **Total** | **124** | **137** | **129** | **85** | **7** |

*NUT-03 has 0 MUST requirements (only SHOULD) — 0 quotes is correct.

## All Repos

| Repo | Branch | Status |
|---|---|---|
| [Amperstrand/cashu-cf](https://github.com/Amperstrand/cashu-cf) | main | 124 quotes, CI blocking, ISSUE-023 fixed |
| [Amperstrand/cdk](https://github.com/Amperstrand/cdk) | experiment/greatspectations-v0.17.3 | 137 quotes, CI non-blocking |
| [Amperstrand/cdk](https://github.com/Amperstrand/cdk) | experiment/greatspectations-audit | 125 quotes (v0.15.1 historical) |
| [Amperstrand/nutshell](https://github.com/Amperstrand/nutshell) | experiment/greatspectations-audit | 129 quotes, CI non-blocking |
| gonuts-tollgate | main | 85 quotes (already adopted) |
| [Amperstrand/micronuts](https://github.com/Amperstrand/micronuts) | experiment/greatspectations-audit | 7 quotes, pushed |
| [Amperstrand/cashu-audit](https://github.com/Amperstrand/cashu-audit) | main | 70 signoffs, runbook, methodology |
| [Amperstrand/hackathon-tooling](https://github.com/Amperstrand/hackathon-tooling) | main | Methodology + learnings |
