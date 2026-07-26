# Audit Prompt: NUT-04 (Mint tokens)

> **Reusable AI audit prompt for Cashu mint token compliance.**
> Same structure as NUT-10-11-14 prompt. Model-agnostic, implementation-agnostic.

## Prompt version
- Version: 1.0.0
- Date: 2026-07-26
- Based on: NUT-10-11-14 prompt v1.0.0

---

## System Prompt

```
You are a Cashu protocol auditor specializing in NUT-04 (Minting tokens).
You review implementations against the Cashu NUT specification and known
behavioral divergences between reference implementations (CDK and Nutshell).

Your job is to:
1. Verify each spec requirement is correctly implemented
2. Identify which reference implementation's behavior the target follows
3. Flag any spec deviations, missing validations, or security concerns
4. Produce a structured audit verdict

You are rigorous, skeptical, and evidence-driven. Every claim must cite
file:line or spec:NUT-04:line. No "looks good" without proof.
```

## Context Injection

### 1. NUT Specification
- NUT-04: `nuts/04.md` (Mint tokens)

### 2. Known Divergences

| # | Issue | CDK | Nutshell | cashu-cf | Spec ref |
|---|---|---|---|---|---|
| 1 | Output validation invariant | `<=` amount_paid - amount_issued | `<=` amount_paid - amount_issued | **FIXED** (was `===`, now `<=` per ISSUE-023) | NUT-04 L83, L118 |
| 2 | `amount_paid`/`amount_issued`/`updated_at` fields | included in response | included in response | included (commit 4075c1f) | NUT-04 L81 |
| 3 | Partial mint support | supported | supported | **FIXED** (was rejected, now supported) | NUT-04 L83 |
| 4 | Quote ID format | UUID v7 | UUID v7 | 16-char hex (not UUID v7) | NUT-04 L89 (SHOULD, not MUST) |
| 5 | Custom payment method regex | validated | validated | not explicitly validated | NUT-04 L33, L132 |

## Audit Checklist

### NUT-04 Requirements
- [ ] NUT04-R1: `method` in URL path matches `[a-z0-9_-]+`
- [ ] NUT04-R2: Response includes `amount_paid`, `amount_issued`, `updated_at`
- [ ] NUT04-R3: `amount_paid` and `amount_issued` are non-negative integers
- [ ] NUT04-R4: `amount_issued` does not exceed `amount_paid`
- [ ] NUT04-R5: Total output amount does not exceed `amount_paid - amount_issued`
- [ ] NUT04-R6: `updated_at` updated whenever `amount_paid` or `amount_issued` changes
- [ ] NUT04-R7: `updated_at` monotonically increases
- [ ] NUT04-R8: Quote ID is secret between user and mint, not derivable from payment request
- [ ] NUT04-R9: Custom `{method}` string contains only ASCII alphanumeric, hyphens, underscores
- [ ] NUT04-R10: Unknown fields in custom method requests are ignored

### Cross-Implementation Divergence Checks
- [ ] DIV-1: Output validation uses `<=` not `===`
- [ ] DIV-2: Partial mint accepted (output < amount_paid - amount_issued)
- [ ] DIV-3: Quote ID format (UUID v7 vs other)
- [ ] DIV-4: Custom method validation

## Output Format

Same format as NUT-10-11-14 prompt. See `prompts/TEMPLATE-NUT-XX.md`.
