# FINDINGS 2026-10-23 — agenda #43 item 6: multi-mint V3, DLEQ handling, NUT-18 crossover

Tracking: DLEQ bypass = audit #55 (fund-safety, owner-gated filing).

Night sessions 2026-10-22/23; companion to
FINDINGS-2026-10-22-keyset-ids-nut02-v4pool.md (items 1–4). Evidence
classes: `live` (local docker nutshell 0.21.0 arms, deterministic
keys, FakeWallet; cdk-cli debug build @ 715d0bd0 = 0.18.2 features;
cashu-ts 4.11.0 + 5.0.0-rc.9 vitest harness), `src` (cited lines),
`spec` (cashubtc/nuts @ 2026-10-22). Full transcripts:
`private/RESEARCH-2026-10-21-agenda.md` (item 6 sections). All
candidate filings are owner-gated; nothing posted.

## 6a. Multi-mint V3 tokens — unreceivable across the reference ecosystem; two implementation bugs

Token: two real 2-proof sends from two local arms merged into one
spec-legal V3 shape (full 66-hex ids, memo, unit sat).

| Consumer | Verdict | Identity |
|---|---|---|
| cdk-cli 0.18.2 | reject | `Error: Unsupported token` |
| Nutshell 0.21.0 wallet | reject | `Exception: TokenV3 must contain proofs from only one mint.` |
| cashu-ts 4.11.0 / 5.0.0-rc.9 | reject | `CTSError: Multi entry token are not supported` |

Triage:
- cdk's parse SUCCEEDS (single-entry control parses to the trust
  gate); the rejection is `Token::mint_url()`
  (nut00/token.rs:103-114) returning the GENERIC `UnsupportedToken`
  for `mint_urls.len() != 1` — shadowing the dedicated
  `MultiMintTokenNotSupported` (wallet/receive/mod.rs:80).
  Error-identity class.
- **Nutshell's multi-mint fallback is dead code**:
  `deserialize_token_from_string` (wallet/helpers.py:109-113) catches
  `except ValueError`, but `TokenV4.from_tokenv3` raises a PLAIN
  `Exception` (core/base.py:1409) — the fallback meant to route
  multi-mint tokens to the mint-looping `redeem_TokenV3`
  (helpers.py:37-76) never fires. One-word fix (`except Exception`)
  restores intended behavior.
- cashu-ts rejects intentionally at decode (core.ts:453-455 / :485).

Impact: senders of multi-mint V3 (a shape Nutshell wallets can emit
via multi-mint send flows) strand funds against every reference
wallet. Registry row staged.

## 6b. DLEQ handling — live mixed-proof verification bypass in Nutshell 0.21.0

Setup: 3 real proofs, garbage DLEQ (constant 32-byte hex e/s/r) at
designated positions.

| Consumer | [no-dleq, garbage, no-dleq] | [garbage] alone | [garbage first] |
|---|---|---|---|
| Nutshell wallet receive | **Received 5 sat — garbage NEVER verified** | `Exception: DLEQ proof invalid.` | `Exception: DLEQ proof invalid.` |
| cdk-cli 0.18.2 (--allow-untrusted) | `Error: Invalid DLEQ proof` | same class | same class |
| cashu-ts 4.11 / rc.9 | reject (per-proof loop) | reject | reject |

**Runnable repro + independent confirmation (2026-10-23): `experiments/dleq-bypass-nutshell/`** — fresh arm, fresh wallets: received-with-garbage vs control-rejected.

Root cause (src cashu/wallet/wallet.py:998-1002):
`verify_proofs_dleq` iterates `for proof in proofs: if not
proof.dleq: return` — **`return` where `continue` belongs**: the
first dleq-less proof aborts verification for the whole list. Gates
receive/redeem (wallet.py:722) and minting (wallet.py:1077). NUT-12
threat model: a malicious mint can pair an honest-looking first
proof with invalid-dleq followers that are never checked.
Order-dependent, clean live repro; registry row + issue text staged.

Adjacent source facts:
- **cdk ships two disagreeing DLEQ gates**: receive saga is
  verify-if-present per proof (receive/saga/mod.rs:148-156); public
  `Wallet::verify_token_dleq` (wallet/mod.rs:1051) REQUIRES dleq on
  every proof (`Proof::verify_dleq` `None → MissingDleqProof`,
  nut12.rs:230). API consumers of the latter reject every
  dleq-less (e.g. Nutshell-minted) token — the cdk#1331 class
  persists at API level in 0.18.2.
- **cashu-ts 5.0.0-rc.9 flipped `hasValidDleq`'s `require` default
  true→false** (wallet receive is verify-if-present in both versions
  via `verifyDleqIfPresent`) — a library-API break: bare
  `hasValidDleq(p, ks)` calls silently change meaning on upgrade.
- cashu-ts `getDecodedToken(tok, [])` structurally cannot decode V2
  tokens: the empty-keyset-list guard (core.ts:819-822) fires before
  id-length discrimination, even for full 66-hex ids.
- cashu-ts 5.0.0-rc.9 full-pool run (18 vectors, 2026-10-23):
  verdict parity 18/18 with 4.11.0, but the two type-error rejections
  (text-`i`, text-`c`) lost their wrapped CTSError messages — raw
  `expected Uint8Array, got type=string` surfaces instead
  (error-identity regression; verdicts unchanged).
- Nutshell 0.20.3 full-pool run (17 runnable V4 vectors, 2026-10-23):
  verdict parity 17/17 with 0.21.0 — the lenient-parse/silent-coercion
  class (text-`i` → 16 garbage bytes; empty-`t`; mixed-unit accepted)
  predates 0.21.0 and is not a new regression. `pe` on 0.20.3 decodes
  as an ignored unknown field (predates NUT-28 capture).

## 6c. NUT-07 startup cost (cdk#2631) — sequential saga recovery, unfixed in 0.18.2

cdk#2631 (OPEN, read 2026-10-23): long-lived wallets accumulate one
`wallet_sagas` row per send; startup `recover_incomplete_sagas` does
one sequential NUT-07 round-trip per saga (~4.3k rows → 10+ min
startup). Source-verified in 0.18.2: wallet/recovery.rs:409 plain
`for saga in sagas { resume_*.await }` — no concurrency, no
batching, though NUT-07 accepts an array of Ys per request (one/few
POSTs could drain all pending proofs). We stay silent upstream (no
new fact beyond the issue text); folded a recovery-under-load shape
into the staged 07-test.md proposal.

## NUT-18 crossover — payloads inherit the V3 id ambiguity and the 6b bypass

- Payment REQUESTs (creqA CBOR / NUT-26 bech32m) carry no token; the
  crossover surface is `PaymentRequestPayload` JSON
  `{id, memo, mint, unit, proofs: Array<Proof>}` — **V3-shaped JSON
  proofs** ("see NUT-00"), so the short-vs-full id ambiguity applies
  with no resolution layer: cdk's payload parses `Proofs` with
  full-`Id` serde (nut18/payment_request.rs:307-316) — a naive copy
  of cdk's own native V3 SHORT spelling fails to parse; cashu-ts
  takes plain-string ids (lenient). Second spec-unpinned surface
  (fold into the staged 00-tests contribution).
- V4 tokens never ride in payloads (JSON only) — "V4↔PR crossover"
  resolves to nil for V4, real for V3 semantics.
- 18.md:103 makes the PAYEE responsible for checking incoming DLEQ —
  exactly the check Nutshell implements bypassably (6b): a NUT-18
  receiver on nutshell follows the spec's instruction with a
  bypassable verification path.

## Owner decision queue (owner-gated; briefs in
`private/DECISION-BRIEFS-2026-10-22-w0p2.md`, D1–D6)

1. D1: nutshell mixed-DLEQ bypass — file? (issue text staged:
   `private/UPSTREAM-nutshell-dleq-bypass.md`)
2. D2: multi-mint V3 dead fallback — file? (issue text staged:
   `private/UPSTREAM-nutshell-multimint-fallback.md`)
3. D3: cdk dual dleq gates — pair with the pe-serde filing?
4. D5: fold payload-spelling into the 00-tests contribution.
5. Registry rows 6–8 (landed in this commit with this doc).
