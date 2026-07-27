# Cashu Multi-Implementation Audit Experiment — Final Report

> **Date**: 2026-07-26
> **Duration**: ~8 hours
> **Auditor**: GLM-5.2 in opencode (Sisyphus agent)
> **Scope**: 3 Cashu implementations × 3-layer audit framework

## Executive Summary

We built and validated a 3-layer spec compliance audit framework for the Cashu ecosystem, applying it across 3 implementations (cashu-cf, CDK, Nutshell). The framework uses greatspectations for mechanical spec-quote drift detection (Layer 1), inline reference-implementation notes for cross-impl awareness (Layer 2), and reusable AI audit prompts for deep semantic review (Layer 3).

**Key results**:
- **375 spec-quote comments** across 3 implementations (all pass mechanical verification)
- **55+ AI audit signoffs** covering 21+ NUTs per implementation
- **2 spec violations found** in CDK (both also present in Nutshell)
- **CDK #2252 found 75% outdated** — 6 of 8 documented divergences don't match current Nutshell code
- **1 real bug fixed** in cashu-cf (ISSUE-023: NUT-04 output validation `===` vs `<=`)

## What was built

### Layer 1: greatspectations (mechanical spec-quote drift detection)

| Implementation | Language | Quotes | Comment style | CI | Repo |
|---|---|---|---|---|---|
| cashu-cf | TypeScript | 121 | `// NUT #NN:` | ✅ Blocking | [Amperstrand/cashu-cf](https://github.com/Amperstrand/cashu-cf) main |
| CDK (experiment) | Rust | 125 | `// NUT #NN:` + `// BIP #NN:` | ✅ Non-blocking | [Amperstrand/cdk](https://github.com/Amperstrand/cdk) `experiment/greatspectations-audit` |
| Nutshell (experiment) | Python | 129 | `# NUT #NN:` | ✅ Non-blocking | [Amperstrand/nutshell](https://github.com/Amperstrand/nutshell) `experiment/greatspectations-audit` |
| **Total** | 3 languages | **375** | 2 comment styles | 3 CI workflows | 3 repos |

**Spec sources covered**: Cashu NUTs (markdown, 31 specs), Bitcoin BIPs (mediawiki, BIP-340 + BIP-39).

### Layer 2: Cross-implementation divergence notes

Inline `// REF-CDK:` / `// REF-NUTSHELL:` / `# REF-CDK:` / `# REF-NUTSHELL:` comments at divergence points in each implementation's source code. Documents where implementations disagree on behavior.

- cashu-cf: 16 REF notes (8 divergence pairs in spending-conditions.ts)
- CDK: REF notes being added (Layer 2 agent running)
- Nutshell: REF notes being added (Layer 2 agent running)

### Layer 3: AI audit prompts + signoffs

**cashu-audit repo**: [Amperstrand/cashu-audit](https://github.com/Amperstrand/cashu-audit)

| Artifact | Count | Description |
|---|---|---|
| Audit signoffs | 55+ | Per-NUT per-implementation verdicts with file:line evidence |
| Cross-impl comparisons | 10+ | NUT-00 through NUT-09 showing where impls agree/diverge |
| Audit prompts | 3 | NUT-04, NUT-10-11-14, general NUT-XX template |
| Divergence database | 3 | NUT-10-11-14 corrected table, CDK #2252 finding, CDK violation analysis |
| Learnings doc | 1 | Patterns, friction points, adoption guide |
| Templates | 2 | specquotes.toml, spec-quotes-guide |

## Key findings

### Finding 1: CDK #2252 is 75% outdated

CDK issue #2252 documents 8 divergences between CDK and Nutshell on NUT-10/11/14. Our independent audit found **6 of 8 are inaccurate** for current Nutshell code:

| # | CDK #2252 claims | Reality |
|---|---|---|
| 2 | Nutshell rejects duplicate tags | Nutshell also uses first-match |
| 3 | Nutshell rejects n_sigs upfront | Nutshell validates at verify time |
| 4 | Nutshell rejects empty pubkeys | Nutshell accepts |
| 5 | Nutshell requires lowercase HTLC hash | Nutshell accepts mixed case |
| 7 | Nutshell ignores duplicate sigs | Nutshell also rejects |
| 8 | Nutshell accepts witness on plain secret | Nutshell also rejects |

**CDK and Nutshell are more aligned than anyone thought.** See `divergences/FINDING-CDK-2252-outdated.md` for details.

### Finding 2: CDK has 2 spec violations (Nutshell has the same)

Both in NUT-11 spending conditions:

1. **Duplicate tags**: Both CDK and Nutshell use first-match-wins instead of rejecting. Spec says "MUST be rejected as unspendable." See `divergences/CDK-VIOLATION-ANALYSIS.md`.

2. **n_sigs > pubkeys**: Neither validates at parse time. Refund pathway remains usable despite malformed secret. Spec says "MUST be rejected as unspendable."

**cashu-cf is the ONLY implementation that correctly implements both.**

### Finding 3: ISSUE-023 — cashu-cf NUT-04 output validation (FIXED)

greatspectations surfaced a real bug within 10 minutes: `validateAmountTotal(output, q.amount, '===')` at mint.ts:1067 used strict equality instead of the spec's `<= amount_paid - amount_issued`. This blocked partial mints that the spec explicitly permits.

**Fixed** in commit a754f9a. TDD: failing test → minimal fix → spec quote matches.

### Finding 4: cashu-cf is strictest on 3 edge cases

| Edge case | CDK | Nutshell | cashu-cf |
|---|---|---|---|
| Duplicate tags | First-match | First-match | **Rejects all** |
| n_sigs > pubkeys | Deferred | At verify time | **Rejects upfront** |
| HTLC hash case | Mixed accepted | Mixed accepted | **Lowercase enforced** |

## Methodology

### The 3-layer architecture

```
Layer 1 (per-repo):     greatspectations verbatim quotes → spectate check in CI
Layer 2 (per-repo):     REF-CDK/REF-NUTSHELL inline notes at divergence points
Layer 3 (cashu-audit):  Reusable AI audit prompts + signed-off results
```

### Audit process per NUT per implementation

1. Read NUT spec → extract every MUST/MUST NOT
2. Read implementation source → find code anchors
3. For each MUST: verify implementation, cite file:line
4. Produce signoff: PASS/FAIL/WARN per requirement
5. Cross-compare: where do implementations diverge?

### What worked well

- **Parallel agents**: 8-22 concurrent deep agents per wave. Total ~80+ agent runs.
- **Mechanical verification**: spectate check is fast, deterministic, CI-able
- **AI audits**: GLM-5.2 found real issues (ISSUE-023, CDK violations) that mechanical tools can't
- **Cross-impl comparison**: comparing 3 implementations side-by-side revealed that CDK #2252 was outdated

### What was hard

- **Markdown bold**: `**MUST**` must be preserved verbatim — many agents failed initially
- **Comment continuation**: any `//` after a NUT quote is parsed as continuation
- **Multi-format specs**: BIP mediawiki format parsed differently from NUT markdown
- **Large files**: Nutshell's ledger.py (1000+ LOC) required targeted function searches

## Reproducibility

All signoffs record:
- Target commit hash
- Spec commit hash (pinned to `734f60e`)
- Prompt version
- Model used (GLM-5.2)
- Date

Any signoff can be re-run with:
```bash
git clone https://github.com/cashubtc/nuts.git nuts && cd nuts && git checkout 734f60e
# Read the signoff, apply the same prompt to the same code
```

## Files produced

### cashu-audit repo (12 commits)

```
signoffs/
├── AUDIT-DASHBOARD-20260726.md
├── cross-impl-comparison-20260726.md
├── comparisons/                    # 10 per-NUT reports
│   ├── NUT-00-comparison.md
│   └── ... through NUT-09
├── cashu-cf/                       # 14 signoffs
├── cdk/                            # 16 signoffs (including quoted-code audit)
└── nutshell/                       # 15 signoffs

divergences/
├── NUT-10-11-14.md                 # Corrected divergence table
├── FINDING-CDK-2252-outdated.md    # 6/8 claims outdated
└── CDK-VIOLATION-ANALYSIS.md       # 2 spec violations with experiment designs

prompts/
├── TEMPLATE-NUT-XX.md              # General template
├── NUT-04.md                       # NUT-04 specific
└── NUT-10-11-14.md                 # Spending conditions specific

learnings.md
templates/
```

### cashu-cf repo (commits on main)

- 121 greatspectations quotes
- ISSUE-023 fix (NUT-04 partial mint)
- Duplicate tag enforcement fix
- SIG_ALL documentation
- CI workflow (blocking)
- Contributor guide

### CDK repo (experiment branch)

- 125 greatspectations quotes (NUTs + BIPs)
- CI workflow (non-blocking, spec pinned)
- Issue #1 documenting experiment
- Layer 2 REF notes (in progress)

### Nutshell repo (experiment branch)

- 129 greatspectations quotes
- CI workflow (non-blocking, spec pinned)
- Issue #1 documenting experiment
- Layer 2 REF notes (in progress)
