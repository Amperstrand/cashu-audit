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
| 11 | nut10-14-spending-conditions.md (umbrella) | cashubtc/cdk#2252 (comment) + cashubtc/nuts | HIGH — both refs violate NUT-11 MUSTs; 2 bricking divergences survive (measured 2026-09-09) |
| 12 | nut10-d1-unknown-kind-secrets.md | — (KNOWN: cdk#2252 item 1) | reference-only |
| 13 | nut11-d2-duplicate-tags-must-unenforced.md | cashubtc/nuts (amend #358 to split handling + vectors) | HIGH — NOVEL: converged-on-violation |
| 14 | nut11-d3-nsigs-exceeds-pubkeys-must-unenforced.md | cashubtc/nuts (bundle with #13) | HIGH — NOVEL: converged-on-violation |
| 15 | nut10-d4-empty-pubkeys-tag-spec-contradiction.md | cashubtc/nuts (one-line 11.md fix) | MEDIUM — NOVEL: intra-spec contradiction |
| 16 | nut14-d5-hash-hex-case.md | — (fold into future nuts PR) | LOW — PARTIAL: converged, spec tension |
| 17 | nut14-d6-htlc-refund-witness-shape.md | cashubtc/cdk (fix or error text) + nuts (preimage optionality) | HIGH — PARTIAL: live bricking + misleading error |
| 18 | nut11-d7-duplicate-signatures.md | — (re-diverging at next release — measured preview 2026-09-09) | reference-only |
| 19 | nut11-d8-witness-on-plain-secret.md | — (re-diverging at next release — measured preview 2026-09-09) | reference-only |

Source inventory: `research/CONFUSIONS-spec-and-projects-2026-09-08.md`.
Position & evidence: `research/POSITION-mint-leniency-and-spec-silence.md`,
`research/INCIDENTS-unspendable-ecash-census.md`.
