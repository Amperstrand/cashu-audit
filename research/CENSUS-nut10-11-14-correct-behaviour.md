# Census: NUT-10/11/14 "correct behaviour" — issues, PRs, dev calls (internal)

*2026-09-09. Round-up for `issues/nut10-14-spending-conditions.md`. Internal
research only — nothing filed, nothing linked upstream (per 00-INDEX
etiquette). URLs are reference material, not engagement.*

## Timeline (dated, from nuts git history + issue/PR records)

| Date | Artifact | What it did |
|---|---|---|
| 2023-10-13 | nuts#40 (NUT-11 original) | Tag format: "arrays with **two or more strings**" |
| 2025-12-16 | nuts#320 (NUT-10 tag clarification) | Tags: "**ONE or more** strings"; adds `["pubkeys"]` (no values) as a **valid** example — **contradicts NUT-11's 2023 wording to this day** (d4) |
| 2026-01-08 | nuts#315 (new P2PK/HTLC rules) | NUT-14 hash-lock section: lowercase 64-char hex (producer rule) + byte-wise `must verify` equality (d5); new locktime/pathway rules |
| 2026-04-01 | nuts#358 opened (robwoodgate) | The two NUT-11 MUSTs (duplicate tags d2; n_sigs>pool d3), *following* already-merged impl alignment: nutshell#969, cdk#1880, cashu-ts#578 |
| 2026-04-17 | a1denvalu3 review on #358 | **The community's split-handling answer** (below) |
| 2026-05-14 | cdk#1966 | "num sig zero is invalid" — cdk-side enforcement of adjacent rule |
| 2026-05-18 | nutshell#1009 filed | Source issue: nut10_compatibility_checker shows nutshell 13–20/58 failures, **CDK 58/58** |
| 2026-06-09 | nuts#358 merged | MUSTs live on paper; **no vectors attached** |
| 2026-07-18 | callebtc edits #1008 branch | "nut10.py validates secret" (d1 strict SecretKind), "treat invalid locktime as permanent", "guard n_sigs", review-nits commit — **branch diverges from what #2252 had reviewed** |
| 2026-07-23 | cdk#2252 filed | Compares cdk vs the #1008 branch *as of May state* — the stale table we probed |
| 2026-08-03 | Kukks/DotNut#42 | **Third implementation implements the MUSTs** ("reject malformed secrets, compare keys by x-coordinate") — the spec-literal population is real |
| 2026-08-11 | nutshell#1008 merged | Full strictness lands on **main** (duplicate-tag, n_sigs-vs-pool, lowercase-hash validators — read directly on our `spectate/main`). **NOT in the published 0.20.3 image**: tag `0.20.3` is the Jul-22 version-bump commit (`1853902`), the image is its faithful build (FETCH_HEAD-verified), and `merge-base --is-ancestor 8e19619 0.20.3` → NO. 42 commits unreleased at audit time; measured preview (run 20260909-224356): the next image flips SEVEN cells — d2/d3/d4/d5 → REJECT and d6c/d7/d8 → ACCEPT (the rewrite also silently dropped hardening) — and matches the cdk#2252 table on all 8 divergences (the table was early, not wrong) |
| 2026-08-19 | nutshell#1126 (+ PR #1130, open) | #1008 changed witness error codes/messages; **cashu-ts integration suite breaks against nutshell main** — wallet-side conformance harness in action |
| 2026-09-09 | our probe | cdk-mintd/0.18.0 + Nutshell/0.20.3 measured matrix (reports/ab-p2pk-htlc-2026-09-09) |

## The load-bearing quote (correct-behaviour direction)

a1denvalu3 on nuts#358 (2026-04-17), "as per discussion" (i.e., a dev call):

> 1. The mint could treat malformed NUT-11 as anyone-can-spend
> 2. The wallets could reject malformed NUT-11.

This is **the same split our POSITION doc reached independently** for NUT-00
(duty-follows-issuance: mints honor what they signed; wallets are where
strictness lives). Neither #358's merged text nor either reference implements
this split — the MUST binds the *mint* to reject, which is the opposite half.

## Per-divergence "correct behaviour" verdict (evidence-weighted)

- **d1 unknown kind**: spec "may" (permissive). Community direction (a1denvalu3
  + NUT-10 Caution) favors mint-lenient = **cdk's reading is the community
  direction; nutshell 0.20.3's fail-closed is stricter than anyone asked for**
  (added by callebtc's Jul-18 "nut10.py validates secret", not present in the
  reviewed branch). Danger: future kinds (nuts#296 channels) brick at nutshell.
- **d2 duplicate tags / d3 n_sigs>pool**: MUST-reject exists (Jun 2026) but both
  references accept — **accidentally aligned with the a1denvalu3 split** (mint
  lenient), while DotNut#42 implements the letter. Resolve by amending the MUST
  to the split (mint→anyone-can-spend + wallet→reject) or shipping vectors;
  current state = third-impl bricking hazard (proven by DotNut).
- **d4 empty `["pubkeys"]`**: NUT-10 (Dec 2025) says valid; NUT-11 (2023) says
  invalid. Both impls follow NUT-10. Fix is a one-line nuts PR reconciling 11.md.
- **d5 uppercase hash**: producer-rule lowercase vs byte-wise equality — both
  impls take byte-equality. Defensible; needs one clarifying sentence.
- **d6 HTLC refund sigs-only witness**: NUT-14 Sender Pathway text ("providing
  signature(s)") supports nutshell; **cdk rejects the documented pathway** over
  witness-envelope shape + returns a misleading error (50000 "Secret is not a
  HTLC secret"). Community hasn't ruled; HTLCWitness.preimage optionality is
  unstated. Strongest candidate for a cdk fix.
- **d7 duplicate sigs / d8 witness-on-plain**: spec silent; both now reject
  (nutshell via #1008, cdk long-standing). Settled by convergence; fine.

## Dev calls

- Notes live in **cashubtc/cdk Discussions → "Dev calls" category** (posted
  by thesimplekid) — but the category **ends at Dev call 29 (2025-10-15)**;
  the call series moved off GitHub after that (community hub today:
  cashudevkit.org). So no cdk dev-call notes exist for the 2026 tightening
  window; the "Dev call 23" reference in cdk#2252 is a **number-coincidence
  autolink** to cdk discussion #1008 (Aug 2025), not evidence about
  #1008-the-PR.
- The a1denvalu3 "as per discussion" (Apr 2026) therefore refers to a
  discussion in the post-GitHub venue (cashudevkit/Telegram) — the ruling's
  *content* is preserved in the #358 review thread, which is the citable
  record. **Follow-up: locate the 2026 call notes on cashudevkit.org if
  they're published** (not done this pass).

## Wallet side (the next audit surface)

- **cashu-ts integration suite is run against real nutshell/cdk builds**
  (that's how #1126 was found) — the de-facto cross-impl conformance harness.
  Our conformance/scenarios share scenario names with
  SatsAndSports/nut10_compatibility_checker (58 cases) cited by #1009 — same
  test-space, three independent artifacts; consolidation candidate.
- cashu-ts#578 (P2PK hardening, merged 2026-04) is the wallet half of #358.
- Open wallet questions for d6: which witness shape does each wallet emit on
  HTLC refund spends (preimage-null vs omitted)? cashu-cf emits sigs-only
  (nutshell-aligned → **bricked at cdk mints today**); cashu-ts shape unverified.
  → extend ab_probe with a wallet-emission probe, or grep wallet libs.

## The SatsAndSports ecosystem (added 2026-09-09, second pass)

One contributor accounts for the channels proposal (nuts#296, active Aug
2026), the P2BK extension it needs (NUT-28, slot model `[data, ...pubkeys,
...refund]`), the reference implementation (`cashu_spilman_channels`,
cdk-spilman crate, own test mint), and the compatibility checker
(`nut10_compatibility_checker`, 58 scenarios, published results, same
naming scheme as our suite). Checker results (2026-05-18) pin two facts:

- **cdk 0.16.0 scored 58/58 including the sigs-only HTLC refund
  succeeding** — combined with our 0.18.0 REJECT, cdk's d6 regression
  window is 0.16.0→0.18.0 (the error string itself is ancient: 2024-04,
  `db14c117` "feat: NUT14").
- **Nutmix 0.4.0 over-accepts**: invalid HTLC SIG_ALL spends (signature-
  only, wrong preimage) "unexpectedly succeeded" — the only over-acceptance
  measured in this census, cross-validated by our July nutmix reference
  report. Fourth-implementation spread: DotNet stricter-than-MUST,
  Nutmix looser-than-MUST.

Also: cdk#1195 (SIG_ALL+refund fix, Oct 2025) was abandoned for #1212 —
cdk's refund semantics churned during channel development; and
audit.8333.space is the community mint auditor whose coverage gap
SatsAndSports explicitly named ("behave flawlessly with the auditor's
usages, but rug everybody when the user deviates").

Detail docs: `CHANNELS-nuts296-p2bk.md`, `WALLETS-spending-conditions.md`.

## Provenance notes

- Dates from `~/src/nuts` git history (`git log -S`, unshallowed this session).
- #1008's Jul-18 commit list explains the #2252 staleness mechanically.
- #1126 gives error-code-registry (issue #6) two fresh data points: code-0
  AssertionError leak pre-#1008; 11000 "no signatures in proof." folding
  absent-vs-malformed witness post-#1008.
