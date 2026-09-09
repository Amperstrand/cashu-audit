# Issue drafts — spec confusions & project traps (2026-09-08)

One fileable draft per confusion. Each argues: why a developer **or LLM**
gets confused, the lesson, and the improvement. Venue rule: full reasoning
stays in this repo (`research/`); the filed issue gets ~15 lines + links.

Status: DRAFTS — nothing filed upstream. Owner decides per-item venue
(cashubtc/nuts, cashubtc/cdk, cashubtc/cashu-ts, cashubtc/cashu.me, or
internal). Filing etiquette: one issue per repo, link the audit bundle.

| # | Draft | Venue candidate | Priority |
|---|---|---|---|
| 1 | nut00-secret-encoding.md | cashubtc/nuts (+ cdk, cashu-ts) | HIGH — campaign subject |
| 2 | nut00-hash-algorithm-versioning.md | cashubtc/nuts | HIGH — live rot |
| 3 | nut05-blank-change-outputs.md | cashubtc/nuts | HIGH — production incident exists |
| 4 | amount-json-serialization.md | cashubtc/nuts | MEDIUM |
| 5 | nut07-checkstate-shape.md | cashubtc/nuts | MEDIUM |
| 6 | error-code-registry.md | cashubtc/nuts | MEDIUM |
| 7 | nut02-keyset-id-formats.md | cashubtc/nuts | MEDIUM |
| 8 | keyset-active-flag-semantics.md | cashubtc/nuts | LOW |
| 9 | interrupted-operation-recovery.md | cashubtc/nuts | HIGH — biggest underspecified area |
| 10 | cdk-config-split.md | cashubtc/cdk | MEDIUM — we debugged it live |

Source inventory: `research/CONFUSIONS-spec-and-projects-2026-09-08.md`.
Position & evidence: `research/POSITION-mint-leniency-and-spec-silence.md`,
`research/INCIDENTS-unspendable-ecash-census.md`.
