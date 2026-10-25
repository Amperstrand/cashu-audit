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
| 02 | Keysets and fees | mandatory | 2023-01-27→2026-10-20 | 14 | 5 | 6 | deep |
| 03 | Swap tokens | mandatory | 2023-01-27→2026-10-20 | 13 | 1 | 3 | partial |
| 04 | Mint tokens | mandatory | 2023-01-27→2026-10-20 | 31 | 3 | 5 | partial |
| 05 | Melting tokens | mandatory | 2023-01-27→2026-10-20 | 32 | 5 | 3 | partial |
| 06 | Mint information | mandatory | 2023-01-27→2026-08-15 | 18 | 4 | 6 | partial |
| 07 | Token state check | optional | 2023-03-09→2026-10-20 | 17 | 6 | 2 | partial |
| 08 | Lightning fee return | optional | 2023-03-09→2026-10-20 | 20 | 6 | 6 | partial |
| 09 | Restore signatures | optional | 2023-04-05→2026-10-20 | 13 | 2 | 1 | partial |
| 10 | Spending conditions | optional | 2023-10-13→2026-10-20 | 12 | 14 | 0 | deep |
| 11 | Pay to Public Key (P2PK) | optional | 2023-10-13→2026-10-20 | 21 | 25 | 20 | deep |
| 12 | Offline ecash validation (DLEQ) | optional | 2023-11-05→2026-10-20 | 12 | 2 | 0 | partial |
| 13 | Deterministic secrets | optional | 2024-03-22→2026-10-20 | 13 | 3 | 3 | partial |
| 14 | HTLCs | optional | 2024-04-24→2026-10-20 | 11 | 12 | 10 | deep |
| 15 | Partial multi-path payments | optional | 2024-04-24→2026-10-20 | 11 | 0 | 0 | none |
| 16 | Animated QR codes | optional | 2024-05-23→2026-10-20 | 3 | 0 | 0 | none |
| 17 | WebSockets | optional | 2024-06-26→2026-10-20 | 7 | 0 | 0 | none |
| 18 | Payment requests | optional | 2024-10-18→2026-10-20 | 10 | 1 | 2 | partial |
| 19 | Cached responses | optional | 2024-12-03→2026-10-20 | 3 | 1 | 1 | none |
| 20 | Signature on mint quote | optional | 2024-12-25→2026-10-20 | 14 | 6 | 4 | deep |
| 21 | Clear auth | optional | 2025-01-29→2026-10-20 | 3 | 0 | 0 | none |
| 22 | Blind auth | optional | 2025-01-29→2026-10-20 | 6 | 0 | 0 | none |
| 23 | BOLT11 method abstraction | optional | 2025-06-01→2026-10-20 | 6 | 0 | 0 | none |
| 24 | HTTP 402 | optional | 2025-06-26→2026-10-20 | 5 | 0 | 0 | none |
| 25 | BOLT12 | optional | 2025-08-28→2026-10-20 | 6 | 0 | 0 | none |
| 26 | Payment req Bech32m | optional | 2026-01-11→2026-10-20 | 5 | 1 | 2 | none |
| 27 | Nostr mint backup | optional | 2026-01-11→2026-10-20 | 3 | 0 | 0 | none |
| 28 | Pay-to-Blinded-Key (P2BK) | optional | 2026-02-16→2026-06-28 | 2 | 2 | 0 | partial |
| 29 | Batched minting | optional | 2026-03-09→2026-10-20 | 13 | 3 | 3 | none |
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
- **max_array_length** (#425): ns 0.20.3 ABSENT; ns 0.21.0 + cdk 1000;
  cashu-cf **50** — but ALL arms enforce **1000** on checkstate (cf's
  advertisement wrong by 20x; corrected same-day after the 60-Y probe
  was shown to be under the real limit; see divergences/
  NUT-06-MAX-ARRAY-LENGTH-2026-10-24.md + fresh-must-wave FINDINGS).
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

### In flight upstream (unmerged — the next epoch, watch for it)

- **nuts#443 "NUT-10: Nutroot secrets (v3 keysets)"** (open, cont. #421):
  the v3 protocol — v3 keysets (NUT-02), taproot-style locking
  (tweak/internal key/leaves, NUT-10 as the leaf registry), v3 secrets +
  transaction transcript + key-path witness moved into NUT-00, v3 mint
  quotes ALWAYS LOCKED (NUT-04), checkstate returns witnesses (NUT-07),
  v3 derivation incl. NUMS/leaf/quote-lock keys (NUT-13), P2BK in
  payment requests (NUT-18/24/26/28). cdk already builds against it
  (cdk#2607 Nutroot, cdk#2674 v3 seed vectors). Adjacent: nuts#460
  (NUT-09/13 restore lookup), nuts#371 (BLS12-381 in NUT-00).
  When #443 merges the watch regenerates SPEC-HISTORY and this section
  must be rewritten as an epoch; the v3 surface (locking, locked quotes,
  new derivation) is the next big interop audit target — start the
  coverage matrix the day it lands.

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

### NUT-03 — partial
Hold: suite swap scenarios; fresh-must unit probe 2026-10-24
(experiments/fresh-must-wave/): unsupported-unit quotes rejected by all
arms — error identity forks cf 11005 (self-describing message) vs
ns-0.20.3 10000 vs ns-0.21.0/cdk 11013, incl. **intra-ns code drift
10000→11013** (silent, wallets keying codes fork across ns versions).
Gap: cross-unit swap (sat inputs + usd outputs) unmeasured — needs
two-unit lifecycle. Next: mixed-unit swap probe on testnut (only
multi-unit arm).

### NUT-04 — partial
Hold: accounting-fields pattern (divergences/NUT-04-ACCOUNTING...),
mint-retry idempotency fork (registry, measured 2026-10-23 —
shadow-proxy A6b). Gap: custom methods (#382) and `method` field (#378
solution, 2026-06-10) unmeasured; expiry-as-deadline (#427) unmeasured.
Next: quote `method` round-trip + unknown-method error identity.

### NUT-05 — partial
Hold: UUIDv7/method violations, blank-change-outputs issue (with NUT-08);
prefer_async probe 2026-10-24 (fresh-must-wave): accepted 200 by all 6
arms, echoed by NONE; quote fee_reserve forks cf/ns 10 vs cdk 20 on the
same invoice; quote ids UUIDv7-shaped everywhere (#383 adopted).
Gap: async-melt BEHAVIOR (does a paid async melt return PENDING vs
PAID) unmeasured — quote layer only. Next: async-melt lifecycle probe
(invoice-oracle pattern).

### NUT-06 — partial
Hold: info scenarios; wire matrix field forks (`method_name` casing,
min/max presence, 2026-10-24 — see "Wire declarations"); max_array_length
finding COMPLETE 2026-10-24 (divergences/NUT-06-MAX-ARRAY-LENGTH-2026-10-24.md,
corrected same day): **all 5 arms enforce 1000** on checkstate — cf
ADVERTISES 50 (wrong by 20x), ns-0.20.3 enforces without advertising;
error identity 3-way fork (14005 / bare-422 / 11014).
Gap: swap/melt array paths (same 1000? per-endpoint?) unmeasured.
Next: array-limit probe on swap outputs (fund-relevant path).

### NUT-07 — partial
Hold: checkstate shape issue, witness-field violations (cashu-cf);
fresh-must-wave side finding 2026-10-24: **cdk curve-validates Ys at
checkstate** (422 "malformed public key" on non-point hex) — cf/ns
accept arbitrary hex; ns accepts ONLY the Ys shape (outputs-shape →
422), cf accepts Ys/proofs/secrets.
Gap: UNSPENT-definition #424 (2026-09-09) — PENDING-era semantics per
arm unmeasured. Next: pending-state probe (in-flight melt → checkstate
→ verdicts).

### NUT-08 — partial
Hold: fee-return scenarios, blank-change-outputs issue (index-pairing);
fresh-must melt probes 2026-10-24 (experiments/fresh-must-wave/
FINDINGS-nut08.md): **perfect three-family convergence** — declared
change amounts ignored (outputs=[1,1,1] melt PAID everywhere; #426
amount-0 unenforced mint-side), mint re-decomposes change over the
offered output slots ([32,16] for 2 slots, [32,16,2] for 3), response
field `change` spec-conformant everywhere. Explains the Amethyst #3847
class directly. **Leg C: slot-count truncation CONFIRMED** — true
change 50 (32+16+2, three denominations) in 2 slots returns [32,16]=48;
the mint silently KEEPS the remainder that doesn't fit the offered
power-of-2 slots (both families). **Leg D: fee ledger EXACT** — no
hidden per-input or fixed fees (2/4/8 inputs identical, gap 0 on ns);
testnut charged 2 vs quoted reserve 1 (F7-class rounding); the earlier
"~16 unaccounted" was my probe's dict-key bug, retracted in
FINDINGS-nut08.
Next: wallet-side consequence audit — which deployed wallets hardcode
change-output counts (pairs with WALLETS-spending-conditions.md).

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

### NUT-13 — partial (intent-researched, claim corrected)
Hold: intent research 2026-10-25 (research/NUT13-INTENT-RESEARCH-2026-10-25.md):
**the cross-family-restore claim is RETRACTED** — cdk's 0x01-slot
`SecretKey::derive` is dead code (zero callers; pre-spec prototype);
cdk's shipped P2PK keys follow the spec path `m/129373'/10'`
(wallet/p2pk.rs) and quote-lock `129373'/20'` (nut20.rs), matching
cashu-ts. BIP32-vs-KDF was deliberately settled upstream (#331 won,
merged 2026-07-30 on production grounds). Real gaps: nutshell ships NO
deterministic P2PK/quote-lock derivation; spec V2 step-3 wording is
ambiguous (casualty: one dead-API mislabel). Upstream: nothing meets
the bar; hold unless a v2-vectors PR opens.
Next: only the nutshell-missing-derivation datum — candidate note if a
nutshell NUT-13 issue/PR opens.

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

### NUT-19 — partial
Hold: fresh-must-wave probe 2026-10-24: declaring arms (cf, cdk) carry
**`{}` params — no cached_endpoints, no ttl advertised**; ns doesn't
declare. Identical melt-quote POST twice → NEW quote id on every arm
(quote-create non-idempotent everywhere; extends the registry's
retry-fork row). Side observation: no arm sends ETag; cf sends
Cache-Control max-age=600.
Gap: true NUT-19 replay (byte-identical /v1/swap, /v1/mint/bolt11,
/v1/melt/bolt11) — needs real blind outputs; queued.
Next: replay probe on cached endpoints via the must-gap driver.

### NUT-20 — deep
Hold: quote-sig violations, NUT20-MINT-AUTH divergence, deterministic
locking (#373). Wire datum 2026-10-24 (fresh-must artifacts): all 5
arms DECLARE NUT-20 `supported: true` yet no quote response carries a
`sig` field in default config — declaration is capability-speak;
signing presumably needs the lock/auth path exercised.
Gap: the #370/#384 breaking hardening (2026-06-07) — version matrix of
who signs what message; lock-path behavior unmeasured on any arm.
Next: quote-lock request path per arm (20.md request shape), then the
signature-message derivation matrix across arms/versions.

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

### NUT-29 — partial (measured 2026-10-25)
Hold: batch atomicity probes (experiments/fresh-must-wave/
FINDINGS-nut29.md): **atomicity HOLDS on all three families** — no
partial signatures on any failure leg; rejected batches do not burn
paid quotes (cf same-quote retry after a 500 → 200). Error-code
**11016 converged** on all arms (spec-fresh text adopted everywhere —
counter-example to the drift pattern). Warts: cf 500-crash on
malformed B_ (batch saga lacks point pre-validation — candidate cf fix,
owner-gated, pairs with the max_array_length fix); cdk "Unknown quote"
50000 for an EMPTY batch (misleading); check-order divergence
(dup-outputs vs unknown-quote first); testnut leaves quote state PAID
after successful batch issuance.
Gap: bolt12/onchain batch legs unmeasured (bolt11-only here); NUT-20
locked-batch signatures (the `signatures` array path) unmeasured —
overlaps the NUT-20 lock probe.

### NUT-30 — none
Onchain (2026-05). Newest method surface. Next: same as 23/25 probe.

## Priority queue (updated 2026-10-24 after the fresh-must wave)

Ranked by (mandatory/fresh-MUST × unmeasured × fund-loss class):

1. NUT-08 amount-0-on-blank-outputs #426 + NUT-07 UNSPENT #424 — the
   remaining unmeasured tightening-wave items (melt-lifecycle class,
   invoice-oracle pattern)
2. NUT-13 derivation fork — only "not started" with fund-loss potential
   (restore failures strand funds)
3. NUT-20 post-hardening signature matrix — breaking change, our deep
   area, no row
4. NUT-29 batch atomicity — fund-loss class (partial batch states)
5. NUT-19 true replay on cached endpoints (swap/mint/melt byte-identical
   re-POST) — extends 2026-10-24 quote-create data
6. NUT-03 mixed-unit swap lifecycle on testnut (quote layer done
   2026-10-24)
7. NUT-06 array limit on swap/melt paths (checkstate done)
8. NUT-17 websocket parity, NUT-04/05 method surface — medium
9. NUT-01 V1/V2 keyset-id acceptance — pairs with registry expiry rows

## Maintenance

The watch runs it for you — **twice, on two hosts** (state is committed
in `research/upstream-state.json`, so the hosts coordinate through the
repo and a change caught by one is never double-digested):

- hub: cron `47 5 * * *` local → `tools/upstream-watch-cron.sh` in
  /root/src/cashu-audit (log `/root/upstream-watch.log`)
- ai-legion-small: cron `7 7 * * *` UTC → dedicated clone
  `~/src/cashu-audit-watch` (log `~/upstream-watch.log`; NUTs clone
  auto-created at `~/src/NUTs`; gh auth = Amperstrand)

Each run checks NUTs HEAD + latest cdk/nutshell releases; on movement it
regenerates timelines, emits a release digest
(`research/releases/<project>-<version>.md`), appends
`research/UPSTREAM-WATCH.md`, commits + pushes. A `CHANGE:` line in
either log means: read the digest, then update the tracker epoch/card
rows it names. Manual digest for a version the watch hasn't seen (e.g.
adding a new pinned arm):

    python3 tools/release_digest.py --project cdk --version v0.18.2

The wrapper is location-independent (derives the repo from its own
path, `$HOME`-based caches, auto-clones NUTs) — any host is one
`git clone` + one crontab line away. It never resets a dirty tree
(lane WIP is logged and skipped).

After any arm release: `python3 tools/nut_support.py --host-network`
→ diff `research/MINT-NUT-SUPPORT.md`. Research/suite counts:
`python3 tools/coverage_counts.py` (prints the table columns;
paste-worthy). Re-count after adding findings. New findings must state
their NUT row in the doc header — the tracker row links back.
