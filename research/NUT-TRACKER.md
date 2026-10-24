# NUT TRACKER — the systematic audit spine

One row per NUT. Every audit artifact in this repo maps to exactly one
row; every row names its gap. This file is the answer to "what have we
audited, what changed in the spec, and what's left."

Generated inputs (regenerate, don't hand-edit their data):

- **Spec history** — `research/SPEC-HISTORY/` (per-NUT commit timelines,
  cashubtc/NUTs @ 1363de4 2026-10-23) · regen: `python3
  tools/spec_history.py --refresh`
- **Mint NUT declarations (wire)** — `research/MINT-NUT-SUPPORT.md` +
  raw `/v1/info` JSON · regen: `python3 tools/nut_support.py
  --host-network` (ai-legion)
- **Venue map** — `research/DIVERGENCE-REGISTRY.md` (hand-maintained)

Axes per NUT:
- **History** — first/last spec change + commit count (from timelines)
- **Wire** — `/v1/info` declaration by ns/cdk/cf arms (see matrix)
- **Research** — dedicated findings docs (divergences/, issues/, research/)
- **Suite** — conformance scenarios (conformance/README.md coverage table)
- **Status** — `deep` (measured multi-version findings) · `partial`
  (single finding or suite-only) · `none` (no audit artifact)

## Master table

| NUT | Title | Spec status | First→last change | Cmts | Research | Suite | Status |
|---|---|---|---|---|---|---|---|
| 00 | Notation, Utilization, Terminology (+token formats) | mandatory | 2023-01-27→2026-10-23 | 31 | 19 | 0 | deep |
| 01 | Mint public key exchange | mandatory | 2023-01-27→2026-10-20 | 12 | 0 | 6 | partial |
| 02 | Keysets and fees | mandatory | 2023-01-27→2026-10-20 | 14 | 4 | 6 | deep |
| 03 | Swap tokens | mandatory | 2023-01-27→2026-10-20 | 13 | 0 | 3 | partial |
| 04 | Mint tokens | mandatory | 2023-01-27→2026-10-20 | 31 | 4 | 5 | partial |
| 05 | Melting tokens | mandatory | 2023-01-27→2026-10-20 | 32 | 5 | 3 | partial |
| 06 | Mint information | mandatory | 2023-01-27→2026-08-15 | 18 | 0 | 6 | partial |
| 07 | Token state check | optional | 2023-03-09→2026-10-20 | 17 | 4 | 2 | partial |
| 08 | Lightning fee return | optional | 2023-03-09→2026-10-20 | 20 | 3 | 6 | partial |
| 09 | Restore signatures | optional | 2023-04-05→2026-10-20 | 13 | 2 | 1 | partial |
| 10 | Spending conditions | optional | 2023-10-13→2026-10-20 | 12 | 13 | 0 | deep |
| 11 | Pay to Public Key (P2PK) | optional | 2023-10-13→2026-10-20 | 21 | 23 | 20 | deep |
| 12 | Offline ecash validation (DLEQ) | optional | 2023-11-05→2026-10-20 | 12 | 2 | 0 | partial |
| 13 | Deterministic secrets | optional | 2024-03-22→2026-10-20 | 13 | 0 | 3 | none |
| 14 | HTLCs | optional | 2024-04-24→2026-10-20 | 11 | 11 | 10 | deep |
| 15 | Partial multi-path payments | optional | 2024-04-24→2026-10-20 | 11 | 0 | 0 | none |
| 16 | Animated QR codes | optional | 2024-05-23→2026-10-20 | 3 | 0 | 0 | none |
| 17 | WebSockets | optional | 2024-06-26→2026-10-20 | 7 | 0 | 0 | none |
| 18 | Payment requests | optional | 2024-10-18→2026-10-20 | 10 | 1 | 2 | partial |
| 19 | Cached responses | optional | 2024-12-03→2026-10-20 | 3 | 0 | 1 | none |
| 20 | Signature on mint quote | optional | 2024-12-25→2026-10-20 | 14 | 5 | 4 | deep |
| 21 | Clear auth | optional | 2025-01-29→2026-10-20 | 3 | 0 | 0 | none |
| 22 | Blind auth | optional | 2025-01-29→2026-10-20 | 6 | 0 | 0 | none |
| 23 | BOLT11 method abstraction | optional | 2025-06-01→2026-10-20 | 6 | 0 | 0 | none |
| 24 | HTTP 402 | optional | 2025-06-26→2026-10-20 | 5 | 0 | 0 | none |
| 25 | BOLT12 | optional | 2025-08-28→2026-10-20 | 6 | 0 | 0 | none |
| 26 | Payment req Bech32m | optional | 2026-01-11→2026-10-20 | 5 | 0 | 2 | none |
| 27 | Nostr mint backup | optional | 2026-01-11→2026-10-20 | 3 | 0 | 0 | none |
| 28 | Pay-to-Blinded-Key (P2BK) | optional | 2026-02-16→2026-06-28 | 2 | 2 | 0 | partial |
| 29 | Batched minting | optional | 2026-03-09→2026-10-20 | 13 | 0 | 3 | none |
| 30 | Onchain payments | optional | 2026-05-20→2026-10-20 | 6 | 0 | 0 | none |

(Suite counts from `conformance/README.md`; research counts from the
2026-10-24 inventory — regenerate: see "Maintenance" below. "Research 0 +
suite 0" = unaudited.)

## Wire declarations (measured 2026-10-24, all 6 arms)

From `research/MINT-NUT-SUPPORT.md` / raw `mint-nut-support.json`:

- **NUT-06 `nuts` shape**: spec example and ALL 6 arms agree on an object
  with bare numeric keys (`{"4": {...}}`) — the older array-of-`"NUT-XX"`
  form is gone from the spec (last seen pre-#205/#425 era). No divergence.
- **Field-level forks inside `methods[]`** (the real declaration
  divergences): `method_name` — ns `"bolt11"`, cdk `"Bolt11"` (case
  fork), cashu-cf omits the field entirely; `min_amount`/`max_amount`
  present in cf + cdk, absent in ns. Spec example shows min/max but no
  `method_name` — extra fields are the fork, not omissions.
- **NUT-17 websocket commands**: ns declares 3, cdk declares 9, cashu-cf
  declares none (no NUT-17 entry at all).
- **NUT-19 caching**: cashu-cf + cdk declare `{}`; nutshell has no entry.
- **NUT-15 MPP**: only cdk declares (bolt11).
- **NUT-04/05 method surface**: cdk 4 methods (bolt11, bolt12, onchain,
  paypal — sat); ns 1 (bolt11:sat); cashu-cf bolt11 in 2 units
  (sat + usd — the only multi-unit arm).
- **Method-entry fields** (NUT-04 `methods[]` objects): `method_name`
  casing forks — ns `"bolt11"`, cdk `"Bolt11"`, cashu-cf omits the field;
  `min_amount`/`max_amount` present in cf + cdk, absent in ns.
- Retracted on verification: an earlier draft of this section claimed the
  spec documents `nuts` as an array — wrong; current NUT-06 example is
  the object form all arms ship (checked 06.md directly, 2026-10-24).

## Spec epochs — when behavior-defining changes landed

From the per-NUT timelines (dates = commit dates; PR in parens):

- **2023-01-27** — base NUT-00..06 minted. **2023-12-18** — "Cashu v1 —
  the Great Cleanup" (#55) reshapes 01/02/03/04/09/10.
- **2024-01** — NUT-07 checkstate v2 (`Y`-based) replaces the proof-list
  shape (#71, #93).
- **2024-04/05** — NUT-14 HTLC, NUT-15 MPP (#104, #103).
- **2024-06** — NUT-02 gains fees (#126); NUT-17 websockets (#98).
- **2024-10/12** — NUT-18 payment requests (#124); NUT-19 (#195);
  binary token serialization added then REMOVED within 13 days (#199 →
  #202, 2024-12).
- **2025** — NUT-21/22 auth (Jan #198); NUT-23 method abstraction (Jun
  #258); NUT-24 402 (Jun #239); NUT-25 bolt12 (Aug #259); **2025-08-20**
  NUT-11 SIG_ALL (#149); **2025-11-15** SIG_ALL message extended with
  `secret`+`C` / `amount`+`B_` (#302) — the nutshell 0.20.3/0.21.0
  format-flip boundary in our registry rows; 2025-11 prefer-async melt
  (#285).
- **2026-01** — *the big month*: **Keyset ID V2** (#182, touches 00/01/02/
  13/24/27); **NUT-11+14 "New P2PK/HTLC rules"** (#315, 2026-01-08 — the
  Sender Pathway text our d6/HTLC findings cite); NUT-26 bech32m (#294),
  NUT-27 (#267), NUT-21/22 matching rules (#334).
- **2026-02** — NUT-28 P2BK (#300).
- **2026-05/07** — onchain NUT-30 (#365); NUT-04/05 custom payment
  methods (#382, #374); quote-accounting alignment wave (#377 — touches
  04/05/20/23/25/29/30: `amount_paid`/`amount_issued`); NUT-20 quote
  signature HARDENING (#370/#384 breaking) + deterministic quote-lock
  derivation (#373); NUT-18 consolidation (#381); UUIDv7 recommendation
  (#383).
- **2026-08/09** — tightening wave: NUT-08 blank change outputs MUST be
  amount 0 (#426); NUT-06 max request length (#425); NUT-07 UNSPENT
  defined as absence (#424); NUT-03/05 unit consistency normative
  (#406); NUT-04 expiry = payment deadline (#427); **NUT-12 DLEQ
  completeness MUST** (#434-adjacent, 2026-09-11) and deterministic DLEQ
  nonce (#368); NUT-11 locktime==now defined (#440, 2026-09-14).

Audit relevance: an implementation released BEFORE an epoch cannot
conform to it — the version matrices (ns 0.20.3/0.21.0, cdk 0.18.1/0.18.2
— all released mid-2026, see `conformance/`) postdate every epoch except
the 2026-08/09 tightening wave, which is exactly where unenforced-fresh-
MUST findings should concentrate. That is the standing hunting ground.

## Per-NUT audit cards

### NUT-00 — deep
Hold: secret-encoding campaign (issues/nut00-secret-encoding.md,
POSITION-mint-leniency, AB-TEST-redemption-rules, registry row);
V1/V2/V4 token formats (FINDINGS-2026-10-22-keyset-ids-nut02-v4pool,
V4-token-URL violations); GONUTS divergence; amount-serialization issue.
Gap: no doc owns the **2026-02 conventions pass (#322)** delta; V4 token
family (multimint, tokenv4 encoding) findings live under other numbers.
Next: none urgent — registry rows 6b/pe-serde carry open work.

### NUT-01 — partial (suite-only)
Hold: suite info/keysets scenarios. Gap: Keyset ID V2 (#182) landed
2026-01-11 — **no finding measures V1↔V2 derivation acceptance across
arms** (related: registry's `final_expiry=0` noncanonical-id row proves
cdk verifies, nutshell doesn't). Next: V1-id/V2-id acceptance probe
(mint lists both? mint accepts outputs under a V1 id?).

### NUT-02 — deep
Hold: keyset-id formats (issues/nut02-keyset-id-formats.md), active-flag
semantics, final_expiry divergence (issues/keyset-final-expiry +
registry rows), FINDINGS-2026-10-22 (rotation identity, expiry).
Gap: fees block (#126, 2024-06) interacts with NUT-08 — covered there.
Next: expiry-enforcement registry row is owner-gated; nothing new.

### NUT-03 — partial (suite-only)
Hold: swap scenarios. Gap: **zero dedicated findings** for the mandatory
core path — unit-consistency #406 (2026-09-15) is fresh normative text;
no arm measured against it. Next: cross-unit swap rejection probe
(sat-keyset proofs + msat outputs etc.), error-identity asserted.

### NUT-04 — partial
Hold: accounting-fields pattern (divergences/NUT-04-ACCOUNTING...),
mint-retry idempotency fork (registry, measured 2026-10-23 —
shadow-proxy A6b). Gap: custom methods (#382) and `method` field (#378
solution, 2026-06-10) unmeasured; expiry-as-deadline (#427) unmeasured.
Next: quote `method` round-trip + unknown-method error identity.

### NUT-05 — partial
Hold: UUIDv7/method violations, blank-change-outputs issue (with NUT-08).
Gap: prefer_async (#339, 2026-02) — no arm measured; state-enum vs
deprecated `paid` field. Next: async-melt fork probe (ns vs cdk vs cf).

### NUT-06 — partial (suite-only)
Hold: info scenarios; wire matrix field forks (`method_name` casing,
min/max presence, 2026-10-24 — see "Wire declarations"). Gap:
max-request-length (#425, 2026-08-15) — nothing measures whether arms
enforce or even advertise it.
Next: `max_request_length` presence + enforcement probe.

### NUT-07 — partial
Hold: checkstate shape issue, witness-field violations (cashu-cf).
Gap: UNSPENT-definition #424 (2026-09-09) — PENDING-era semantics
per arm unmeasured. Next: pending-state probe (in-flight melt/swap →
checkstate → verdicts).

### NUT-08 — partial
Hold: fee-return scenarios, blank-change-outputs (index-pairing)
issue. Gap: amount-0-on-blank MUST (#426, 2026-08-23) — fresh;
no arm measured. Next: non-zero-amount blank-output acceptance probe.

### NUT-09 — partial (suite-only)
Hold: 1 restore scenario. Gap: restore semantics listed "not started"
in SPEC-AUDIT-FRAMEWORK dimensions (2026-09); still true.
Next: partial-batch restore (some outputs spent) verdict identity.

### NUT-10 — deep
Hold: cdk#2252 campaign (d1-d8 issues, MUST-GAP vectors, census,
alignment docs). Gap: tag-clarification #320 (2025-12-16) wording
vs measured leniency. Next: registry item-6 draft v3.1 staged — owner.

### NUT-11 — deep
Hold: 23 docs + 20 scenarios + registry rows (SIG_ALL family,
#1008/#1009/#1100/#1126 thread history).
Gap: locktime==now #440 (2026-09-14) — boundary-exact vectors
deliberately avoided (nuts#431 row: "no boundary-exact data").
Next: boundary probe if a venue opens; else parked.

### NUT-12 — partial
Hold: dleq-bypass experiment (registry row), CHANNELS-nuts296 census;
deterministic-nonce #368 + completeness MUST (2026-09-11) unmapped to
arms. Gap: cdk dual-gate divergence (registry D3) unfiled.
Next: nonce-derivation + all-or-nothing acceptance matrix.

### NUT-13 — none (suite 3 only)
Framework's own "not started" (2026-09) still true. 2026 churn:
HMAC-SHA256-only for v2 recovery (2026-03-24), P2PK standard
derivation (2026-01-19). Next: derivation-path fork probe
(ns vs cdk vs cf restore of the same mnemonic-derived secrets).

### NUT-14 — deep
Hold: d5/d6 issues, refund vectors, NUT14-REFUND-VECTORS results,
CDK-VS-NUTSHELL alignment. Gap: pubkey-less HTLC spend clarification
(2026-06-28) unmeasured. Next: preimage-only spend acceptance matrix.

### NUT-15 — none
MPP (#103 2024-05, msat spec 2025-03 #220). Zero artifacts. Wire
(2026-10-24): declared by cdk only — ns and cashu-cf have no entry.
Next: if MPP matters to any audited wallet, probe cdk's mpp quote path;
else park with the declaration fact recorded.

### NUT-16 — none
Animated QR — client-side; not a mint surface. Park (note in
wallet-audit contexts only).

### NUT-17 — none
WebSockets (state updates #98; bolt12 kinds #298 2025-10; UUIDv7
#383). Wire (2026-10-24): ns declares 3 commands, cdk 9, cashu-cf none
— declaration fork already measured, behavior not.
Next: subscription-event parity probe (quote state transitions vs
REST polling verdicts on the same quote id); cdk-only events (6 of 9)
are the likely wallet-compat fork.

### NUT-18 — partial
Hold: item-6 crossover findings (FINDINGS-2026-10-23). Gap:
consolidation #381 (2026-07-21) rewrote the NUT — our findings predate?
Verify against current text; decode scenarios exist.
Next: re-baseline item6 findings against post-#381 18.md.

### NUT-19 — none (suite 1)
ETag/caching. Scenario exists, no findings. Wire (2026-10-24): cashu-cf
+ cdk declare NUT-19 (`{}`); nutshell has no entry.
Next: cache-behavior divergence probe (conditional GET per arm).

### NUT-20 — deep
Hold: quote-sig violations, NUT20-MINT-AUTH divergence, deterministic
locking (#373). Gap: the #370/#384 breaking hardening (2026-06-07) —
version matrix of who signs what message; registry has no row.
Next: quote-signature message-derivation matrix across arms/versions.

### NUT-21/22 — none
Auth NUTs; matching rules #334 (2026-02), NUT-22 DLEQ-mandatory #222.
Zero artifacts. Next: only if an audited mint enables auth — check
wire matrix; else park.

### NUT-23/25 — none
Method abstraction (bolt11 #258) / bolt12 (#259). Wire (2026-10-24):
cdk arms advertise bolt12 (+onchain, +paypal) under NUT-04/05/29
methods; ns/cashu-cf advertise bolt11 only.
Next: method-discovery probe — quote under each advertised method
family, error identity on unsupported method+unit pairs.

### NUT-24 — none
HTTP 402cash. Zero artifacts. Park unless a TollGate venue opens.

### NUT-26 — none (suite 2)
Bech32m payment-request encoding. Next: round-trip decode parity
(ns/cdk/cf + cashu-ts) — cheap, fits the v4-pool harness.

### NUT-27 — none
Nostr backup. Wallet-side. Park.

### NUT-28 — partial
Hold: pe-serde registry row (cdk violation), CHANNELS census.
Spec is 2 commits old — youngest NUT. Gap: no acceptance matrix for
P2BK tokens across the three families beyond the pe-vector.
Next: extend v4-pool with P2BK lifecycle (mint→send→receive) per arm.

### NUT-29 — none (suite 3)
Batched minting; 13 commits of churn (quote-sig + UUIDv7 waves).
Gap: batch atomicity (partial failure semantics) unmeasured.
Next: partial-batch probe (some outputs invalid → whole batch rejected
or partial signatures?).

### NUT-30 — none
Onchain (2026-05). Newest method surface. Next: same as 23/25 probe.

## Priority queue (2026-10-24)

Ranked by (mandatory/fresh-MUST × unmeasured × fund-loss class):

1. NUT-03 unit-consistency #406 — mandatory core, 5 weeks old, zero data
2. NUT-06 max_request_length #425 + NUT-08 amount-0 #426 + NUT-07
   UNSPENT #424 — the 2026-08/09 tightening wave, all unmeasured
3. NUT-13 derivation fork — only "not started" with fund-loss potential
   (restore failures strand funds)
4. NUT-20 post-hardening signature matrix — breaking change, our deep
   area, no row
5. NUT-29 batch atomicity — fund-loss class (partial batch states)
6. NUT-17 websocket parity, NUT-04/05 method surface — medium
7. NUT-01 V1/V2 keyset-id acceptance — pairs with registry expiry rows

## Maintenance

- After any spec epoch lands upstream: `python3
  tools/spec_history.py --refresh` → diff `research/SPEC-HISTORY/` →
  update epochs section + affected cards + priority queue.
- After any arm release: `python3 tools/nut_support.py --host-network`
  → diff `research/MINT-NUT-SUPPORT.md`.
- Research/suite counts: `python3 tools/coverage_counts.py` (prints the
  table columns; paste-worthy). Re-count after adding findings.
- New findings must state their NUT row in the doc header — the tracker
  row links back.
