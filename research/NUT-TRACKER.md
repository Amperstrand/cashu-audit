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
| 00 | Notation, Utilization, Terminology (+token formats) | mandatory | 2023-01-27→2026-10-23 | 31 | 20 | 0 | deep |
| 01 | Mint public key exchange | mandatory | 2023-01-27→2026-10-20 | 12 | 0 | 6 | partial |
| 02 | Keysets and fees | mandatory | 2023-01-27→2026-10-20 | 14 | 7 | 6 | deep |
| 03 | Swap tokens | mandatory | 2023-01-27→2026-10-20 | 13 | 5 | 5 | partial |
| 04 | Mint tokens | mandatory | 2023-01-27→2026-10-20 | 31 | 4 | 5 | partial |
| 05 | Melting tokens | mandatory | 2023-01-27→2026-10-20 | 32 | 5 | 3 | partial |
| 06 | Mint information | mandatory | 2023-01-27→2026-08-15 | 18 | 6 | 6 | partial |
| 07 | Token state check | optional | 2023-03-09→2026-10-20 | 17 | 6 | 2 | partial |
| 08 | Lightning fee return | optional | 2023-03-09→2026-10-20 | 20 | 6 | 6 | partial |
| 09 | Restore signatures | optional | 2023-04-05→2026-10-20 | 13 | 2 | 1 | partial |
| 10 | Spending conditions | optional | 2023-10-13→2026-10-20 | 12 | 15 | 0 | deep |
| 11 | Pay to Public Key (P2PK) | optional | 2023-10-13→2026-10-20 | 21 | 25 | 20 | deep |
| 12 | Offline ecash validation (DLEQ) | optional | 2023-11-05→2026-10-20 | 12 | 2 | 0 | partial |
| 13 | Deterministic secrets | optional | 2024-03-22→2026-10-20 | 13 | 3 | 3 | partial |
| 14 | HTLCs | optional | 2024-04-24→2026-10-20 | 11 | 12 | 10 | deep |
| 15 | Partial multi-path payments | optional | 2024-04-24→2026-10-20 | 11 | 0 | 0 | none |
| 16 | Animated QR codes | optional | 2024-05-23→2026-10-20 | 3 | 0 | 0 | none |
| 17 | WebSockets | optional | 2024-06-26→2026-10-20 | 7 | 0 | 0 | none |
| 18 | Payment requests | optional | 2024-10-18→2026-10-20 | 10 | 1 | 2 | partial |
| 19 | Cached responses | optional | 2024-12-03→2026-10-20 | 3 | 3 | 3 | deep |
| 20 | Signature on mint quote | optional | 2024-12-25→2026-10-20 | 14 | 9 | 4 | deep |
| 21 | Clear auth | optional | 2025-01-29→2026-10-20 | 3 | 0 | 0 | none |
| 22 | Blind auth | optional | 2025-01-29→2026-10-20 | 6 | 0 | 0 | none |
| 23 | BOLT11 method abstraction | optional | 2025-06-01→2026-10-20 | 6 | 0 | 0 | none |
| 24 | HTTP 402 | optional | 2025-06-26→2026-10-20 | 5 | 0 | 0 | none |
| 25 | BOLT12 | optional | 2025-08-28→2026-10-20 | 6 | 0 | 0 | none |
| 26 | Payment req Bech32m | optional | 2026-01-11→2026-10-20 | 5 | 1 | 2 | none |
| 27 | Nostr mint backup | optional | 2026-01-11→2026-10-20 | 3 | 0 | 0 | none |
| 28 | Pay-to-Blinded-Key (P2BK) | optional | 2026-02-16→2026-06-28 | 2 | 2 | 0 | partial |
| 29 | Batched minting | optional | 2026-03-09→2026-10-20 | 13 | 3 | 3 | partial |
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

**Pre-staged audit plan: `research/V3-READINESS.md`** (readiness doc
with the merge-day sequence, probe battery, and pre-staged BLS12-381
tooling — py_ecc installed and pairing-verified 2026-10-25).

- **nuts#443 "NUT-10: Nutroot secrets (v3 keysets)"** (open, cont. #421,
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

### NUT-03 — partial (unit consistency + keyless-amount matrix 2026-10-25)
Hold: suite swap scenarios; unit probe (FINDINGS-nut03-units.md):
testnut enforces #406 on swap (all violation shapes rejected; usd
lifecycle green; mint-vs-swap identities differ 12001/14005).
**Keyless-amount family matrix** (FINDINGS-keyless.md +
divergences/CASHU-CF-KEYLESS-AMOUNT-SIGNING-2026-10-25.md): **cf SIGNS
outputs whose amount has no keyset key and then REFUSES its own proof
at redemption ("No public key found for amount 63") — sign/verify path
asymmetry, stranded funds on the issuing mint** (cf fix queued, item
#3); cdk rejects 12001 "Unknown Keyset" (misleading, safe); ns
crash-rejects `detail:"N"` (F5 class, third instance). Melt
change-output caps: cf handles 1001 (melt path clean — the swap-path
SQLite leak is swap-specific); cdk 11015/1000.
Gap: ns/cdk multi-unit arms; cf balanced beyond-keyset-max leg.
NOTE 2026-10-25: two-unit cdk arm attempted (supported_units
["sat","usd"] fake-wallet TOML): config-init OK but mintd exits
silently at boot (no logs) — needs per-unit backend config research;
not a one-line change.

### NUT-04 — partial
Hold: accounting-fields pattern (divergences/NUT-04-ACCOUNTING...),
mint-retry idempotency fork (registry, measured 2026-10-23 —
shadow-proxy A6b); cdk-mintd duplicate-outputs ERROR IDENTITY bug
(divergences/2026-10-29-cdk-mintd-duplicate-outputs-error-identity.md,
measured 2026-10-29 with two same-seed wallets: the issue path maps
the blind-signature UNIQUE violation to InvoiceAlreadyPaid instead of
NUT-19 11003 — wallets roll the derivation counter back and brick
permanently; with 11003 they walk past the burn in N attempts. Fix on
Amperstrand/cdk fix/duplicate-outputs-error-identity; upstream filing
owner-gated. Completes the error-identity picture the A6b row started:
nutshell refuses duplicates with the CORRECT 11003; cdk replays
identical re-sends but mis-identifies fresh collisions).
Gap: custom methods (#382) and `method` field (#378
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

### NUT-06 — partial (cap landscape ~complete)
Hold: info scenarios; wire field forks; **per-endpoint cap landscape
measured 2026-10-25** (FINDINGS-arraycaps.md + FINDINGS-nut29-caps.md):
cf mint-out 100 / swap-in 100 (source) / swap-out NONE (SQLite error
leaks as the cap — candidate cf fix) / batch-Q 50 / checkstate 1000;
ns 1000 everywhere (pydantic); cdk 1000 everywhere EXCEPT batch-Q 100
(advertises 1000 — the one dishonest advertisement). Error-registry
pattern: cf+cdk adopt spec codes (11014/11015/11016/11017/20008);
ns pydantic 422s bypass.
Gap: exact cf swap-input wire confirmation; melt-path caps.
Next: melt outputs cap (cheapest remaining cell).

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
Hold: dleq-bypass evidence REDACTED to private/ (2026-10-27, undisclosed security finding); CHANNELS-nuts296 census;
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

### NUT-19 — deep (replay matrix complete 2026-10-25)
Hold: **full 3×3 replay-caching matrix measured**
(experiments/fresh-must-wave/FINDINGS-nut19.md): cf and cdk return
byte-identical cached 200s on mint + swap + melt replays; nutshell
rejects all three (11003 / 11001 / 20006). Declaration correlates
with behavior (ns absent, cf/cdk `{}`) but NO arm advertises its
cached_endpoints list — the info params under-advertise everywhere.
Quote-create remains non-idempotent on all arms (2026-10-24 datum).
Bonus: ns `detail:"N"` opaque-crash class extends to plain swaps
(keyless output amount); keyset denomination ranges diverge (cf 2^17
max vs ns 2^63 — wallet splitting must consult the keyset).
Gap: ttl behavior (does the cache expire?); replay of PARTIALLY
failed requests.

### NUT-20 — deep (lock path + batch locked-mint COMPLETE 2026-10-25)
Hold: quote-sig violations, NUT20-MINT-AUTH divergence, deterministic
locking (#373); lock-path probes (FINDINGS-nut20.md): pubkey-locked
quotes work on all arms; **20008 converged**; third-party post-#370
x-only BIP340 signatures accepted everywhere; quotes survive sig
rejections. **Batch locked-mint (FINDINGS-nut20batch.md): converged**
— signatures [sig, null] array → 200 on all arms; omitted → 20008 on
all arms. L5 fork (spurious sig on UNLOCKED quote: ns/cf ignore, cdk
rejects). 20.md's example signature decorative (verifies under no
format). Version-stable: 0.20.3/0.18.1 identical identities on lock +
keyless paths.
Gap: none on the lock path — audit complete.

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

### NUT-29 — partial (measured 2026-10-25; caps + error-registry data)
Hold: batch atomicity probes (experiments/fresh-must-wave/
FINDINGS-nut29.md): **atomicity HOLDS on all three families** — no
partial signatures on any failure leg; rejected batches do not burn
paid quotes (cf same-quote retry after a 500 → 200). Caps probe
(FINDINGS-nut29-caps.md): **batch-quote caps are 50 (cf) / 100 (cdk) /
1000 (ns)** — cdk ADVERTISES 1000 but enforces 100 (11017): the
advertisement-vs-enforcement gap is cdk's, not cf's. Error-registry
pattern: 11016/11017/20008 all spec-listed and converged on cf+cdk;
ns's pydantic 422s bypass the registry (framework-vs-handler layer —
sharpens the error-drift narrative). Warts: cf 500-crash on malformed
B_ (candidate cf fix); cdk "Unknown quote" for empty batch; check-order
divergence; testnut quote stays PAID after batch issuance.
Gap: bolt12/onchain batch legs; NUT-20 locked-batch signatures array
(measured 2026-10-26: converged — FINDINGS-nut20batch.md). Version
drift 2026-10-26: the 11017 length-first batch cap landed EXACTLY at
cdk 0.18.1 (0.17.6/0.17.7/0.18.0 = existence-first, no length cap)
— see COMPAT-LEDGER.md change points.

### NUT-30 — none
Onchain (2026-05). Newest method surface. Next: same as 23/25 probe.

## Priority queue (re-ranked 2026-10-29 against wire-verified state)

Closed since the 10-25 ranking: cf keyless-amount fix DEPLOYED to
testnut (wire-verified 10-29: 64→[63,1] rejected — note the deployed
identity is 11001-fee-flavored, not the branch's 14005); NUT-20
batch locked-mint converged; COMPAT-LEDGER matrix complete incl.
checkstate retraction (cdk 1000/1000 on all arms 0.17.6–0.18.2);
dleq-bypass disclosed via security email (owner-gated trail);
testnut≡local-main post-deploy certified. Remaining, ranked:

1. **Keyset-rotation rung** (tollgate #818 repro): mint under
   keyset A, rotate, verify old proofs still swap + wallet-facing
   error identities. No driver exists yet — build on the upgrade-
   ladder harness.
2. **Locktime-0 pool vector** (cashu-ts #1324; 4.13.0 re-touches
   NUT-11 — still zero spend-path vectors in the pool).
3. cashu-cf fix residue (verify-then-close): batch B_ 500-crash →
   clean 4xx; swap-outputs SQLite leak → cap + clean error;
   interop-lab hardcoded /Users/macbook python path.
4. NUT-07 UNSPENT/PENDING legs (needs a holding invoice backend —
   candidate for the kali-live box when reachable).
5. NUT-12 DLEQ completeness acceptance matrix.
6. Multi-unit cdk arm (blocked: mintd exits silently with usd in
   supported_units — per-unit backend config research).
7. v3 (#443 still OPEN as of 2026-10-29) — V3-READINESS.md sequence;
   the watch fires when it merges.

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
