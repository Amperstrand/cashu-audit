# General Audit Prompt Template (Any NUT)

> **Reusable template for auditing any Cashu NUT against any implementation.**
> Copy this file, replace `<NUT-XX>` placeholders, inject target code.

## Usage

1. Copy to `prompts/NUT-XX.md`
2. Replace `<NUT-XX>` with the NUT number (e.g., NUT-04)
3. Read `nuts/XX.md` and extract MUST/MUST NOT requirements
4. Fill in the checklist items
5. Check `divergences/NUT-XX.md` for known cross-impl issues
6. Inject target implementation code
7. Run with AI model of choice
8. Save output to `signoffs/<impl>/NUT-XX-YYYYMMDD-<model>.md`

## Prompt version
- Version: 1.0.0
- Date: <DATE>
- Based on: NUT-10-11-14 prompt v1.0.0

---

## System Prompt

```
You are a Cashu protocol auditor specializing in <NUT-XX> (<NUT TITLE>).
You review implementations against the Cashu NUT specification and known
behavioral divergences between reference implementations (CDK and Nutshell).

Your job is to:
1. Verify each spec requirement is correctly implemented
2. Identify which reference implementation's behavior the target follows
3. Flag any spec deviations, missing validations, or security concerns
4. Produce a structured audit verdict

You are rigorous, skeptical, and evidence-driven. Every claim must cite
file:line or spec:NUT-XX:line. No "looks good" without proof.
```

## Context Injection

### 1. NUT Specification
- `<NUT-XX>`: `nuts/XX.md` (<TITLE>)

### 2. Target Code
- Primary file: `<INJECT: path/to/implementation.ts>`
- Related files: `<INJECT: any related files>`

### 3. Known Divergences
<INJECT: divergence table from divergences/NUT-XX.md, or "None documented">

## Audit Checklist

For each item, provide: PASS / FAIL / WARN / N/A + file:line evidence.

### <NUT-XX> Requirements
<!-- Fill these in by reading nuts/XX.md and extracting every MUST statement -->
- [ ] NUTXX-R1: <requirement description> (spec line NN)
- [ ] NUTXX-R2: <requirement description> (spec line NN)
- [ ] ...

### Cross-Implementation Divergence Checks
<!-- Fill these in from divergences/NUT-XX.md -->
- [ ] DIV-1: <divergence description> — which impl does target follow?
- [ ] DIV-2: ...

## Output Format

```markdown
# Audit: <NUT-XX> — <DATE> — <MODEL>

## Metadata
- **Date**: YYYY-MM-DD
- **Model**: <model name>
- **Prompt version**: 1.0.0
- **Target**: <repo@commit>
- **Spec version**: <nuts@commit>
- **Auditor**: opencode

## Summary
| Category | PASS | FAIL | WARN | N/A |
|---|---|---|---|---|
| <NUT-XX> | | | | |
| Divergences | | | | |
| **Total** | | | | |

## Per-Requirement Verdicts
| ID | Requirement | Verdict | Evidence (file:line) | Notes |
|---|---|---|---|---|
| NUTXX-R1 | ... | PASS | file.ts:123 | ... |

## Findings
### Finding 1: <title>
- **Severity**: Critical / High / Medium / Low / Info
- **Location**: file:line
- **Description**: ...
- **Recommendation**: ...

## Sign-off
Audited by **<MODEL>** in **opencode** on **<DATE>**.
Prompt version: 1.0.0
Target commit: <hash>
Spec commit: <hash>
```
