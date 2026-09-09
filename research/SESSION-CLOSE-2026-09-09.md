# Session close-out — 2026-09-08/09

## What we started with
A stuck 59,942-sat payment on mint.minibits.cash from a receipt.cash
backup file pulled off a phone via ADB.

## What we ended with

### Understanding
- Proved the NUT-00 secret-encoding trap end-to-end (entropy vs utf8-of-string)
- Proved the hash-algorithm divergence between cdk and nutshell
- Proved recovery is impossible for the encoding species (17 variants tested)
- Audited the entire ecosystem (9 implementations)
- Found the same trap live in our own mint (cashu-cf)
- Researched the community history (3 silent softforks, no signaling)
- Counted the removal cost: 4 lines of verify() logic, 39 executable lines total

### Code (all on Amperstrand forks, nothing filed upstream)
| Branch | What | Tested |
|---|---|---|
| cdk `legacy-three-modes` | allow/observe/rugpull per keyset | 3 modes x 3 derivations, live |
| cdk `nut00-legacy-v0.18.0` | algorithm-legacy honor (backport) | A/B arm 5, matches nutshell |
| cdk `nut00-per-keyset-leniency` | encoding-legacy honor + sensor | 22/22 unit + e2e on 0.17.6/0.18 |
| cashu-ts `secret-encoding-guard` | string-first API + guard + vectors | 6/6 vitest |
| nuts `nut00-secret-encoding-vectors` | MUST wording + vectors + negative | aligned with cdk/nutshell/nucula tests |
| nucula `crypto-test-string-secret-vectors` | test blind-spot fix | pattern-matched to house style |
| cashu-audit `nut00-secret-encoding-audit` | everything below | pushed |

### cashu-audit additions (all on nut00-secret-encoding-audit branch)
- **Scenario module** `nut00_secret_encoding.py` (3 permanent conformance probes)
- **A/B probe** `ab_probe.py` (3-derivation, 4-arm, frozen-prediction)
- **Filtered runner** `run_filtered.py` (full matrix, per-scenario timeout, JSON)
- **Demo** `demo-bug.mjs` (one-minute end-to-end, docker + node)
- **Vectors** `reference-vectors/nut00-secret-encoding.json` (7/7 cross-validated)
- **Divergence filing** for cashu-cf dual-encoding leniency
- **Position doc** — duty-follows-issuance, keyset grandfathering, signaling
- **Incident census** — 7 genus incidents with real sats
- **Confusion inventory** — 9 spec + 6 project-level traps (personally hit)
- **Issue drafts** — 10 fileable, each with confusion/lesson/improvement
- **Retrospective** — 14 own-failure inventory + 10 what-worked + internalized rules
- **A/B test** — 4 arms + fix arm, 12/12 frozen predictions confirmed
- **Community pitch** — forward-looking spec-gap framing (for owner's use)
- **Framework** — reusable spec-audit methodology + audit dimensions
- **Error-UX analysis** — cashu.me error chain + proposed human message
- **Sequence doc** — master plan with phases and decision ledger

### lightning-playground addition
- `docs/LLM-CONFUSIONS-2026-09-08-cashu.md` — 8 generalizable failure
  classes (L1-L8), each earned by an actual mistake

## Open items (for future sessions)
1. **59,942 sats** — refund email to minibits still needs sending (drafted)
2. **Nostr post** — drafted, awaiting owner approval
3. **Upstream issues** — 10 drafts ready, awaiting owner decision
4. **P2PK/HTLC audit** — cdk#2252 documents 8 divergences; framework ready
5. **BLS migration monitoring** — PR #999 introduces v3 keysets; same
   governance questions will arise
6. **cashu.me error-UX** — issue draft ready (owner reviews before filing)
7. **Spec MUST + vectors PR** — branch ready (owner reviews before filing)

## Environment state at close
- **ai-legion**: cleaned (no mints, no docker, cdk build preserved)
- **laptop**: all worktrees committed and pushed; no stray processes
- **local docker**: all test containers removed
- **testnut**: restored to main code (verified)
- **credentials**: used existing `cf-cashu-cf-deploy` token (nothing new minted)
