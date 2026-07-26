# Learnings & Patterns from the cashu-cf Audit Pilot

Lessons from adopting greatspectations + 3-layer audit on cashu-cf (July 2026). Captured so other implementations can adopt faster.

## Layer 1: greatspectations adoption

### What worked
- **Tool is production-ready**: 121 quotes across 18 NUTs, all passing `spectate check`. Zero false positives after initial learning curve.
- **Catches real bugs fast**: ISSUE-023 (`===` vs `<=`) surfaced within 10 minutes of the first quote. The 48KB human-written NUT-04 review had missed it.
- **Co-exists with legacy comments**: Existing `// NUT-XX:` paraphrases are silently ignored (lack `#id`). New `// NUT #XX:` verbatim style is additive.
- **CI integration is trivial**: 5-line GitHub Actions workflow, pinned to greatspectations v0.1.1.
- **Coverage mode is actionable**: `spectate coverage --all-sections` shows which spec text isn't covered by any quote — useful for finding gaps.

### Friction points
1. **Markdown bold must be preserved verbatim**: `**MUST**` not `MUST`. Developers reading rendered docs will forget asterisks. **Mitigation**: documented in `spec-quotes.md` contributor guide.
2. **Continuation-line parsing**: any `//` comment after a `// NUT #NN:` quote is parsed as a continuation (appended to quote text). **Rule**: place NUT quotes LAST before code, with no other `//` comments between.
3. **Section-header comments trigger parse errors**: `// NUT-04 errors (spec)` (no colon after NUT-04) fails parsing. **Rule**: reword to `// Errors (NUT-04, spec)` — move NUT reference out of prefix position.
4. **Code blocks in spec can't be quoted**: whitespace collapse destroys indentation inside ```` ``` ```` blocks. **Rule**: quote prose only, never code examples.

### Patterns for new implementations

**Adoption checklist:**
1. Clone cashubtc/nuts to `../nuts` (or `nuts/` subdir)
2. Install greatspectations: `pip install git+https://github.com/rustyrussell/greatspectations.git`
3. Copy `templates/specquotes.toml` to your repo root
4. Add `spec:check` and `spec:coverage` npm scripts (or equivalent)
5. Copy `.github/workflows/spec-quote-drift.yml` for CI
6. Start with mandatory NUTs (00-06): ~5-10 quotes each, ~1h total
7. Expand to optional NUTs you implement

**Per-NUT workflow:**
1. Read `nuts/NN.md` spec
2. Identify MUST/MUST NOT statements (grep for `**MUST**`)
3. For each: find the implementing code, add `// NUT #NN: <verbatim quote>` comment
4. Run `spec:check` — fix any markdown-bold or continuation issues
5. Run `spec:coverage --all-sections` — triage remaining gaps
6. Document findings (drift? deviation? missing implementation?)

## Layer 2: Reference implementation notes

### Pattern: inline `// REF-CDK:` / `// REF-NUTSHELL:` comments

```
// REF-CDK: <behavior description>
// REF-NUTSHELL: <behavior description>
// NUT #NN: <verbatim spec quote>
<code that implements this behavior>
```

**Order matters**: REF comments BEFORE NUT quote (to avoid continuation parsing).

**When to add REF notes:**
- When a known divergence exists (check `divergences/NUT-XX.md`)
- When the code handles an edge case differently from the spec's primary path
- When the code has a compatibility hack (e.g., cashu-cf's 10 SIG_ALL message variants)

## Layer 3: AI audit prompts

### What makes a good audit prompt

1. **Structured checklist**: per-requirement items with binary PASS/FAIL/WARN verdicts
2. **Evidence requirement**: every verdict must cite `file:line`
3. **Cross-impl awareness**: include the divergence table so the auditor knows what to look for
4. **Model-agnostic**: no model-specific instructions; just the spec, the code, and the checklist
5. **Reproducible sign-off**: prompt version + hash + target commit + spec commit recorded in output

### Prompt structure that worked

```
## System Prompt (role definition)
## Context Injection (spec text, target code, divergence table)
## Audit Checklist (per-requirement items)
## Output Format (structured markdown with metadata header)
## Notes for Iteration (how to adapt for other impls/models)
```

### Findings from GLM-5.2 audit of cashu-cf

- **Speed**: ~3 minutes to audit 880 LOC of spending conditions against 15 MUST requirements + 8 divergence checks
- **Accuracy**: 23/23 verdicts correct (verified by human spot-check). No false positives or negatives.
- **Depth**: Found 2 non-blocking warnings (partial duplicate tag enforcement, SIG_ALL compat hack) that a mechanical tool couldn't surface
- **Limitation**: can't run the code — verdicts are based on reading, not execution. Runtime testing is complementary.

## General patterns

### The "drift exposure" pattern
The most valuable use of greatspectations is NOT finding existing bugs — it's PREVENTING future drift. The CI gate ensures that any future code change that contradicts a `// NUT #NN:` quote will fail the build.

### The "AI as auditor" pattern
AI audits are point-in-time snapshots. They're valid as of the audited commit. Any code change after the audit invalidates the signoff for changed files. Re-run after significant changes.

### The "cross-impl divergence database" pattern
The divergence database is the highest-value artifact for the Cashu community. It enables:
- Wallet developers to test against multiple mint behaviors
- Mint operators to understand compatibility implications
- Spec authors to clarify ambiguous requirements
- New implementations to make informed behavioral choices
