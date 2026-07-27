# Release Audit Runbook: Cashu Implementation Spec Compliance

> **Purpose**: Step-by-step process for auditing a Cashu implementation release against the NUT spec using greatspectations + AI prompts. Designed to be repeatable across releases and implementations.

## Prerequisites

```bash
# Clone the audit framework
git clone https://github.com/Amperstrand/cashu-audit

# Clone the implementation to audit (e.g., CDK)
git clone https://github.com/cashubtc/cdk
cd cdk

# Clone the Cashu spec
git clone https://github.com/cashubtc/nuts

# Install greatspectations
pip install git+https://github.com/rustyrussell/greatspectations.git
```

## Step 1: Prepare the fork

```bash
# Add Amperstrand remote
git remote add amperstrand git@github.com:Amperstrand/<repo>.git

# Fast-forward fork main to upstream
git fetch origin
git push amperstrand main

# Create experiment branch from release tag
git checkout -b experiment/greatspectations-v<VERSION> v<VERSION>
```

## Step 2: Configure greatspectations

Create `specquotes.toml` at repo root:

**For Rust/TypeScript** (`//` comments):
```toml
[sources.NUT]
format = "markdown"
dir = "nuts"
pattern = "{id:02d}.md"

# CLI flags needed: --comment-start '// ' --comment-continue '//'
```

**For Python** (`#` comments):
```toml
[sources.NUT]
format = "markdown"
dir = "nuts"
pattern = "{id:02d}.md"

# No CLI flags needed — '#' is the default
```

Add to `.gitignore`:
```
nuts/
bips/
.coverage
```

## Step 3: Add spec-quote comments (Layer 1)

For each NUT the implementation covers:
1. Read `nuts/NN.md` spec
2. Read the implementation source file
3. Extract every `**MUST**` / `**MUST NOT**` requirement
4. Add verbatim quote at the implementing code location

### Comment format

```
// NUT #04: Mints **MUST** include `amount_paid`, `amount_issued`...
```

### Critical authoring rules (learned the hard way)

1. **Preserve `**MUST**` bold markers** — copy from raw markdown, not rendered docs
2. **Preserve backticks** around code spans
3. **Place quote LAST before code** — no `//` comments after it (parsed as continuation)
4. **Use `NUT #NN:` not `NUT-NN:`** — the `#` is required by the parser
5. **Avoid `// NUT-XX <text>` without colon** — triggers parse error

### Parallel agent pattern

Fire one agent per NUT group:
```
task(category="deep", prompt="Read nuts/NN.md + source file. Add // NUT #NN: <verbatim> quotes...")
```

7-8 agents in parallel completes in ~5-10 minutes.

## Step 4: Verify

```bash
# All quotes match spec
spectate check --config specquotes.toml --comment-start '// ' --comment-continue '//' \
  -k crates/cashu/src/nuts/*.rs crates/cashu/src/nuts/*/*.rs
# Must exit 0

# Coverage gaps
spectate check --config specquotes.toml --comment-start '// ' --comment-continue '//' \
  --coverage .coverage -k crates/cashu/src/nuts/*.rs crates/cashu/src/nuts/*/*.rs
spectate coverage --config specquotes.toml --coverage .coverage --all-sections
```

## Step 5: Wire CI

Create `.github/workflows/spec-quote-drift.yml`:
- Non-blocking (`continue-on-error: true`) during experiment
- Pin NUT spec to specific commit
- Pin greatspectations to v0.1.1 (`433e1f2`)
- Upload coverage artifact

## Step 6: Run AI audit (Layer 3)

Use the cashu-audit prompts:

```bash
# Per-NUT audit
# Read: nuts/NN.md + implementation source + cashu-audit/prompts/TEMPLATE-NUT-XX.md
# Produce: signoffs/<impl>/NUT-NN-YYYYMMDD-<model>.md
```

Fire one Oracle/deep agent per NUT with the prompt template. Each produces a signoff with PASS/FAIL/WARN verdicts.

## Step 7: Document results

1. Save signoffs to `cashu-audit/signoffs/<impl>/`
2. Create cross-impl comparison if auditing multiple implementations
3. File any findings as issues on `cashu-audit` (not upstream)
4. Update audit dashboard

## Step 8: Push

```bash
git push amperstrand experiment/greatspectations-v<VERSION>
```

## Time estimates

| Step | Time | Parallelizable? |
|---|---|---|
| Fork setup | 2 min | No |
| Config | 2 min | No |
| Spec-quote comments | 10-30 min | Yes (7-8 agents) |
| Verification | 1 min | No |
| CI wiring | 5 min | No |
| AI audit | 15-30 min | Yes (per NUT) |
| Documentation | 10 min | No |
| **Total** | **~45-75 min** | |

## Re-running for a new release

1. `git checkout main && git pull origin`
2. `git checkout -b experiment/greatspectations-v<NEW_VERSION> v<NEW_VERSION>`
3. Cherry-pick specquotes.toml + CI from previous experiment branch
4. Fire agents to add/update quotes (diff against previous version to find changes)
5. Run AI audit
6. Compare with previous release's signoffs — what changed?

## Checklist

- [ ] Fork fast-forwarded to upstream
- [ ] Experiment branch created from release tag
- [ ] specquotes.toml configured
- [ ] NUT specs cloned locally
- [ ] Spec-quote comments added for all implemented NUTs
- [ ] `spectate check` exits 0
- [ ] CI workflow created
- [ ] AI audit signoffs produced
- [ ] Results documented in cashu-audit
- [ ] Branch pushed to Amperstrand fork
