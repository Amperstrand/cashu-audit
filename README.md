# cashu-audit

Cross-implementation Cashu spec compliance audit framework.

## What this is

A neutral, implementation-agnostic framework for auditing Cashu implementations against the NUT specification. It covers three layers:

| Layer | What | Where it lives |
|---|---|---|
| **Layer 1** | greatspectations verbatim spec quotes in source code | In each implementation repo (`// NUT #NN:` comments) |
| **Layer 2** | Cross-implementation divergence database | Here (`divergences/`) |
| **Layer 3** | Reusable AI audit prompts + signed-off results | Here (`prompts/` + `signoffs/`) |

## Implementations covered

| Implementation | Language | Layer 1 status | Layer 3 audits |
|---|---|---|---|
| **cashu-cf** | TypeScript | 121 quotes, spec:check exit 0 | NUT-10/11/14 ✅ |
| **cashubtc/cdk** | Rust | Pending adoption | Pending |
| **cashubtc/nutshell** | Python | Pending adoption | Pending |
| **gonuts-tollgate** | Go | Pending adoption | Pending |

## Quick start

```bash
# Clone this repo alongside your Cashu implementation
git clone <this-repo> ../cashu-audit

# Adopt Layer 1 in your implementation:
cp ../cashu-audit/templates/specquotes.toml ./specquotes.toml
# Edit dir path to point at your nuts checkout
# Add // NUT #NN: <verbatim spec quote> comments in your source
# Run: spectate check --config specquotes.toml --comment-start '// ' --comment-continue '//' src/**/*.ts

# Run a Layer 3 AI audit:
# 1. Open prompts/NUT-10-11-14.md
# 2. Inject your implementation's source code
# 3. Run with your AI model of choice
# 4. Save output to signoffs/<your-impl>/NUT-10-11-14-YYYYMMDD-<model>.md
```

## Directory structure

```
cashu-audit/
├── prompts/           # Reusable AI audit prompt templates (Layer 3)
├── signoffs/          # Audit results, one per impl per NUT (Layer 3)
│   ├── cashu-cf/
│   ├── cdk/
│   └── nutshell/
├── divergences/       # Cross-impl behavior database (Layer 2)
├── templates/         # Adoption templates for new implementations
└── scripts/           # Tooling (run-audit, compare, etc.)
```

## How it works

1. **Each implementation** adopts greatspectations (Layer 1) by adding `// NUT #NN:` verbatim spec quotes in its source code, configured via `specquotes.toml`. CI runs `spectate check` to catch drift.

2. **This repo** maintains the cross-implementation divergence database (Layer 2) documenting where CDK, Nutshell, cashu-cf, and others disagree on behavior. Each divergence references the relevant NUT spec text and the implementations' respective behaviors.

3. **AI audit prompts** (Layer 3) are reusable templates that instruct an AI to review an implementation's code against the spec + divergences. The same prompt works against any implementation. Results are saved as signed-off artifacts.

## Origin

This framework was developed during the cashu-cf greatspectations trial (July 2026). The 3-layer architecture was validated on NUT-10/11/14 (spending conditions), surfacing ISSUE-023 (a real spec deviation caught within 10 minutes) and documenting 8 cross-implementation divergences from [CDK #2252](https://github.com/cashubtc/cdk/issues/2252).
