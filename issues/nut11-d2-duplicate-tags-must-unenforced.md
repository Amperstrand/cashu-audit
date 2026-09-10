# d2 — Duplicate NUT-11 tags: both references now violate the MUST

**Status:** INTERNAL RESEARCH (overview build, 2026-09-09). Nothing filed.
**Upstream novelty:** NOVEL — the *divergence* was known (cdk#2252 item 2);
the **converged-on-violation state** (both references accept what a merged
MUST says to reject, while a third implementation enforces it) is untracked
anywhere. This is our strongest filing candidate — one comment on cdk#2252
or one nuts follow-up, owner's call.

## What we found (measured 2026-09-09)

A secret with two `n_sigs` tags (`[["n_sigs","1"],["n_sigs","2"]]`, 1 valid
signature provided — satisfies the first-tag reading) spends at BOTH
cdk-mintd/0.18.0 and Nutshell 0.20.3 (first occurrence wins in both).
NUT-11 (since nuts#358, 2026-06-09) says: tags appear "exactly **ONCE** …
the P2PK secret is malformed and the Proof **MUST** be rejected as
unspendable." Both references violate a printed MUST. Kukks/DotNut#42
implements it — so a token both references accept is bricked at a DotNut
mint. Money whose validity is mint-dependent, by spec letter.

## How we tested

- Probe cell `d2_duplicate_tags_first_wins` (raw JSON secret builder — the
  house `build_p2pk_secret` cannot express malformed shapes by design).
- Same arms/lifecycle/evidence as d1; stable ×2. Full detail:
  `conformance/reports/ab-p2pk-htlc-2026-09-09.{json,log}`.

## Community discussion (summary)

- nuts#358 (robwoodgate, opened 2026-04-01, merged 2026-06-09) added the
  MUST, *following* already-merged implementation alignment on pubkey
  dedup (nutshell#969, cdk#1880, cashu-ts#578). No vectors were attached.
- The pivotal review exchange (a1denvalu3, 2026-04-17): "As per discussion,
  we could enforce split handling: 1. The mint could treat malformed NUT-11
  as anyone-can-spend 2. The wallets could reject malformed NUT-11." —
  i.e., the discussion's direction was mint-lenient/wallet-strict, but the
  merged text binds the *mint* to reject. Neither half shipped.
- cdk#2252 item 2 documented cdk=first-wins vs nutshell-branch=rejected;
  the rejected half was dropped before merge (review-nits commit path).

## Historic context

- 2023-10: original NUT-11 has no duplicate-tag rule.
- 2026-04→06: #358 adds the MUST (paper only).
- 2026-07-23: cdk#2252 still records a divergence.
- 2026-08-03: DotNut#42 implements the MUST (third-impl population live).
- 2026-08-11: #1008 merges lenient; both references now aligned on violation.
- 2026-09-09: our probe measures both-accept.

## Links (internal reference; no upstream engagement)

- cashubtc/nuts#358 — the MUST + the a1denvalu3 split-handling exchange
- cashubtc/cdk#2252 (item 2) — prior state, reference-only
- Kukks/DotNut#42 — spec-literal enforcement
- cashubtc/nutshell#1008 — the convergence event
- Dev calls: category ends Oct 2025; the "as per discussion" ruling is
  embedded in the #358 thread. Census:
  `research/CENSUS-nut10-11-14-correct-behaviour.md`.

## Release-train update (2026-09-09, measured + source-read)

The both-violate state is a **release snapshot, not a steady state**.
nutshell-main carries the #1008 strict validators (`_validate_tags`
rejects duplicate supported tags — read directly on `spectate/main`), but
**42 commits were unreleased** at audit time: tag `0.20.3` is the Jul-22
version-bump commit (`1853902`) and the published image is a faithful
build of that tag (its `/app/.git/FETCH_HEAD` records the tag checkout;
#1008 merged Aug 11, three weeks later — `merge-base --is-ancestor` → NO).
The **next nutshell image flips this cell to REJECT for every operator at
once** (scheduled softfork-by-release), leaving cdk the lone lenient
reference. The weekly matrix's floating `:latest` arm watches for exactly
this; the `ab-matrix:nutshell-main` git arm previews it pre-release.

## Direction (our read)

The spec text and the community direction diverged at merge time — and
nutshell-main choosing enforcement (above) settles the direction against
pure mint-leniency. Refined amendment (2026-09-09, delay-mode pass):
keep the MUST, add **"…or honor with a mandatory delay under keysets
issued before the implementation's enforcement date"** — strict for new
keysets, delay-honor for legacy (the delay surfaces affected wallets
without confiscating; the drain curve is the retirement signal), plus
negative vectors for both halves and wallet-side rejection at
construction (the a1denvalu3 half). Full mechanism:
`private/THINKING-delay-mode.md` (not upstream).
