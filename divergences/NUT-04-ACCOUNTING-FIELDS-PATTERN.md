# NUT-04 Accounting Fields: Cross-Implementation Pattern Analysis

> **Date**: 2026-07-27
> **Analyst**: GLM-5.2 in opencode
> **Scope**: 5 Cashu implementations
> **Finding**: NUT-04 accounting fields (`amount_paid`, `amount_issued`, `updated_at`) are the most widespread spec compliance gap across the Cashu ecosystem.

## The Spec Requirement

NUT-04 (line 81):
> Mints **MUST** include `amount_paid`, `amount_issued`, and `updated_at` in all mint quote responses. `amount_paid` and `amount_issued` **MUST** be non-negative integers, and `amount_issued` **MUST NOT** exceed `amount_paid`.

NUT-04 (line 83):
> Mints **MUST NOT** issue ecash whose total output amount exceeds `amount_paid - amount_issued`.

NUT-04 (line 85):
> Mints **MUST** update `updated_at` whenever `amount_paid` or `amount_issued` changes.

These three fields enable **partial minting** — a wallet can mint less than the full quote amount across multiple calls, tracking how much has been issued so far.

## Cross-Implementation Status

| Implementation | Fields present? | Validation correct? | Partial mint supported? | Severity |
|---|---|---|---|---|
| **cashu-cf** | ✅ All 3 present | ✅ Fixed (ISSUE-023: `<=` not `===`) | ✅ Yes | **Fixed** |
| **CDK** v0.17.3 | ⚠️ Via `extra` flatten | ✅ Correct | ✅ Yes | Low (design choice) |
| **Nutshell** | ✅ All 3 present | ✅ Correct | ✅ Yes | None |
| **gonuts-tollgate** | ❌ **Completely absent** | ❌ N/A | ❌ No | **Critical** |
| **micronuts** | ❌ Not implemented (embedded) | N/A | N/A | N/A |

## The Pattern

3 of 4 full implementations had (or still have) NUT-04 accounting field issues:

### cashu-cf (FIXED — ISSUE-023)
- **Was**: Fields present in response but validation used `===` (strict equality) instead of `<=` (partial mint)
- **Root cause**: Stale code path from January 2026 (commit `e565c2d8` by `amperstand`) that predated the accounting fields
- **Found by**: greatspectations — the `// NUT #04:` quote at the validation line mechanically surfaced the mismatch
- **Fixed**: Commit `a754f9a` — changed `validateAmountTotal(totalOutputAmount, q.amount, '===')` to `validateAmountTotal(totalOutputAmount, currentlyMintable, '<=')`

### CDK v0.17.3 (ACCEPTABLE)
- **Is**: Fields present via `extra: serde_json::Value` flatten (not explicit struct fields)
- **Design choice**: CDK uses a flexible `extra` map for forward-compatible fields. The fields ARE in responses but not as typed struct members.
- **Impact**: Low — the data is correct on the wire, just not type-safe in code
- **Status**: No fix needed — intentional extensibility design

### gonuts-tollgate (CRITICAL — ISSUE #3 on cashu-audit)
- **Is**: Fields completely absent from `MintQuoteResponse` struct and all response construction points
- **Root cause**: The Go struct was defined before NUT-04 added the accounting fields requirement. Never updated.
- **Impact**: Critical — wallets relying on these fields for partial-mint accounting break against gonuts mints
- **Status**: Being fixed in this session

### Why This Pattern Matters

NUT-04's accounting fields were added relatively recently to the spec. Implementations that were written before the fields became mandatory tend to lag behind. The pattern is:

1. **Spec evolves**: NUT-04 adds `amount_paid`/`amount_issued`/`updated_at` requirements
2. **Reference impl (Nutshell) updates**: Nutshell adds the fields correctly
3. **Other impls lag**: cashu-cf has stale validation, CDK uses flexible-but-untyped approach, gonuts completely misses the update
4. **greatspectations catches it**: The `// NUT #04:` verbatim quote at the response construction point makes the absence visible

## Recommendation for the Cashu Community

1. **Wallet developers**: Don't assume `amount_paid`/`amount_issued` are present — handle their absence gracefully
2. **Mint developers**: Audit your mint quote response structs against NUT-04 L81. If the fields aren't there, add them.
3. **Spec process**: When adding mandatory fields to an existing NUT, consider a spec-rotation mechanism to signal the breaking change (like NUT-02 keyset version bumps)
4. **Adopt greatspectations**: The NUT-04 accounting quotes at the response construction point would have caught this in all 3 implementations at PR review time

## greatspectations as Preventive Measure

The greatspectations quote that catches this:

```
// NUT #04: Mints **MUST** include `amount_paid`, `amount_issued`, and `updated_at` in all mint quote responses.
```

When placed above the struct/response construction, this quote makes the absence mechanically visible. `spectate check` would fail if the quote is present but the code below it doesn't include the fields — wait, actually spectate only checks that the quote TEXT matches the spec, not that the CODE implements it. The human reviewer sees the quote above code that lacks the fields, which is the audit value.

**This is the key insight from the post-quote audits**: greatspectations doesn't mechanically verify code behavior — it creates a human-visible anchor point where a reviewer (human or AI) can immediately see "the spec says MUST include these fields, but the struct doesn't have them." That visibility is the value.
