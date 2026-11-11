# FINDINGS 2026-11-11 — coco (2.0/master) cannot mint from cashu-cf mints: check_mint_quote drops NUT-04 accounting fields

NUT row: NUT-04 (mint quote responses). Wallet: cashubtc/coco @ 2d6aa58
(master, post-#613; gate ships in v2.0.0 npm — tag containment verified).
Mint: testnut.cashu.exchange (cashu-cf). Method: live drill, wire captured.

## What happened (live, 2026-11-11)

Crash-drill harness (coco master + sqlite-bun adapter + logging proxy →
testnut): mint quote 21 sat created (FakeWallet auto-pays). testnut's
check endpoint reports `state: PAID`. coco polls it 6+ times over 30 s
and NEVER claims — no POST /v1/mint at all. Operation stays `pending`,
balance 0, log: "Mint quote is not sufficiently funded for operation",
claimableAmount 0.

## Root cause (both sides verified at source + wire)

1. cashu-cf check responses omit the accounting fields. Live wire
   (wire.jsonl, this dir): CREATE carries `amount_paid: 0`, CHECK
   returns exactly `{quote, request, amount, unit, state, expiry}` —
   no `amount_paid`, `amount_issued`, `updated_at`, ever. Source:
   src/mint/router.ts handleBatchCheckMintQuotes constructs the
   response field-by-field and drops them (refreshed path explicitly;
   default path same shape on the wire). Sibling /v1/mint/quotes
   pushes the raw quote object (fields included) — the stripping is
   check-path-only. NOTE: the ledger rule (ledger/rules.ts
   applyMintQuoteIssued, with the `amount_paid ?? amount` back-compat
   default) already exists on main — only the check serializer lags.
2. NUT-04 (current text, /root/src/NUTs/04.md): "Mints MUST include
   `amount_paid`, `amount_issued`, and `updated_at` in all mint quote
   responses." cashu-cf is the divergent arm.
3. coco 2.0.0+ claimability is accounting-based:
   models/MintQuoteClaimability.ts — `remoteAvailable = amountPaid −
   amountIssued`; state string is not consulted. A PAID quote with no
   accounting fields is permanently unclaimable. (File last touched
   e6ff94bb 2026-07-30, contained in v2.0.0 — so coco npm 2.0.0 is
   equally affected, not just master.)

## Matrix (create/check mint-quote field presence)

| Mint | amount_paid on CHECK | source of evidence |
|---|---|---|
| cashu-cf (testnut, live) | NO (create: yes) | wire.jsonl (this dir) |
| cdk 0.18.1/0.18.2 | YES (non-optional DTO) | git show v0.18.2 crates/cashu/src/nuts/nut04.rs (amount_paid/amount_issued/updated_at, mapped unconditionally) |
| nutshell 0.20.3/0.21.0 | fields exist (Optional, default 0) | upstream-cache nutshell cashu/core/base.py:408-409 |

Blast radius: coco-based wallets (2.0+) vs cashu-cf-family mints only.
cdk/ns mints unaffected.

## Impact on our lanes

- pecan/giftcard (cdk-mintd twins): NOT gated by this — cdk serves the
  fields. coco-master snapshot migration remains safe on this axis.
- wallet-zoo coco arm: the coco × cashu-cf cell (incl. testnut) is
  blocked until cf serves the fields; coco × cdk/ns cells fine.
- testnut certifier (certify_testnut.py legs driving coco): same block.
- cashu-cf: spec-divergence fix needed in OUR repo (issue filed).

## Fix shape (cashu-cf, owner-gated deploy)

- handleBatchCheckMintQuotes: include `amount_paid`, `amount_issued`,
  `updated_at` in BOTH response constructions, sourced from the stored
  quote with the existing rules.ts back-compat default
  (`amount_paid ?? amount`, `amount_issued ?? 0`, `updated_at ?? now`).
- Additive wire change (spec-conformance), but wire-visible: pre-deploy
  baseline already banked (wire.jsonl here = testnut's current check
  identity); re-run the drill post-deploy as the mechanical diff.
- Regression lock in battery scope asserting the three fields on both
  paths (paid-after-lookup and already-PAID).
- Check for characterization tests pinning the stripped shape before
  landing; re-pin in the same commit if any.

## Evidence (this directory)

- wire.jsonl — full drill wire log (create + 6× check, bodies verbatim)
- drill.ts, drill-proxy.ts — harness (proxy injects a reclaim
  interruption on swap#2; that leg never reached the mint because
  funding was blocked by this finding — recovery legs already proven
  offline in COCO-RECOVERY-BATTERY-2026-11-11.md)

## Status

Finding verified (wire + source both sides + spec text). cashu-cf issue
filed (see registry row). Registry row added. Tracker NUT-04 card sync
+ coverage recount queued (not done in this session).
