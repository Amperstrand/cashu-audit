# Unified Coverage Gap Analysis

> **Date**: 2026-07-27
> **Tool**: `spectate coverage --all-sections`
> **Scope**: 5 Cashu implementations

## Summary

| Implementation | Language | Quotes | Coverage Gaps | Coverage % |
|---|---|---|---|---|
| **cashu-cf** | TypeScript | 124 | 0 | 100% |
| **CDK** v0.17.3 | Rust | 137 | 0 | 100% |
| **Nutshell** | Python | 129 | 0 | 100% |
| **gonuts-tollgate** | Go | 85 | 219 | ~60% |
| **micronuts** | Rust (embedded) | 7 | 35 | ~15% |

## Interpretation

- **cashu-cf, CDK, Nutshell**: Coverage gaps = 0 means all spec text within the scanned NUT files is covered by at least one quote. This doesn't mean every MUST is quoted — it means every section of the spec markdown has at least one quote referencing text within it.
- **gonuts-tollgate**: 219 uncovered lines indicates significant spec text with no corresponding code quotes. This is expected — gonuts has fewer NUTs quoted (85 quotes vs 124-137 for the top 3).
- **micronuts**: 35 uncovered lines is expected for an embedded implementation with only 7 quotes covering 3 NUTs.

## What "coverage gap" means

A coverage gap is a line of spec markdown text that has NO `// NUT #NN:` (or `# NUT #NN:`) quote in any scanned source file that matches text within that section. Gaps fall into categories:

1. **Unimplemented NUTs**: spec text for NUTs the implementation doesn't support (correctly uncovered)
2. **Informative text**: examples, diagrams, non-normative explanations (acceptable to leave uncovered)
3. **Missing quotes**: the implementation DOES handle the requirement but no quote was added (actionable gap)

## Actionable gaps

For gonuts-tollgate (219 gaps), the main actionable categories:
- NUT-04 accounting fields (being fixed)
- NUT-05 melt quote response format
- NUT-19 cache implementation details
- NUT-20 quote signature details

For micronuts (35 gaps), most are NUTs not implemented on embedded platform — not actionable.
