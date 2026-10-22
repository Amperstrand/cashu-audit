# miniflare-spend-matrix — local adversarial spend-path battery (real bundle, real DOs)

Runs the cashu-cf worker (wrangler dry-run bundle + Durable Objects) in
miniflare@5 (constructor shape: `workers[].config`, `resourcePersistencePath`)
and drives ADVERSARIAL + RACE inputs at the spend endpoints through raw fetch.
Zero live exposure — no deploy, no real funds, FakeWallet backend.

Complements the live-mint probes (this is the same wire surface as
`melt-input-verification-probe.mjs`, but free, in-process, and pre-deploy):
run it before every melt/swap-path change lands, not only after deploys).

## Setup

- `CASHU_CF_ROOT` (default `~/src/cashu-cf`) must have a fresh
  `.tmp-wrangler-build/` (`npx wrangler deploy --dry-run --outdir
  .tmp-wrangler-build --name miniflare-test --env ''`) and `node_modules`
  (miniflare@5.20260831.0-alpha, @cashu/cashu-ts v4).
- Driver: `node matrix.mjs` — prints per-scenario verdicts, exit 1 on any
  FAIL. Raw transcript per scenario in `out/matrix-<ts>.log` (tee'd).

## FROZEN PREDICTIONS (written 2026-10-22, BEFORE the first run)

Per audit method: a surprising FAIL is a probe bug until proven otherwise.
First run = characterization of exact error identities; the PREDICT-LOCK
column is tightened to the observed identity immediately after and re-runs
must match it exactly (error-identity assertions, never any-4xx-is-pass).

| # | Scenario | Prediction (frozen) | Lock (exact identity, post-first-run) |
|---|---|---|---|
| S1 | swap: forged off-curve C (`02`+`ab`*32) | non-200, point/proof-reject family | 400 `invalid_request`/14005, detail `Proof verification failed at index 0` (swap's legacy shape; 30003 is melt-only) |
| S2 | swap: ON-CURVE but wrong-signature C (random valid point, real keyset id) | 400 invalid_proof-family (signature check fires — the subtle one) | identical to S1 — signature verification fires pre-claim |
| S3 | melt: P2PK SIG_ALL with schnorr witness over the WRONG message (no quote_id binding) | 403 spending_condition_not_met / 30006 | 403/30006, detail `SIG_ALL verification failed: no candidate message verified` |
| S4 | race: N=16 concurrent identical swaps, same real proof | exactly ONE 200; all others non-200 double-spend family; no double issuance | exactly 1×200; losers 400/30001; one distinct signature set |
| S5 | NUT-08 accounting: melt 4 of an 8-proof, fee_reserve 1 | 200 PAID; change present; inputs−amount−fee_reserve ≤ change_sum ≤ inputs−amount (never-red) | change_sum=3 with two blanks (refund 8−4−1); dust-truncation caveat below |
| S6 | race: N=16 concurrent identical MELTs, same real proof + same quote | exactly ONE 200 state=PAID (single preimage); every other response non-200 (double-spend / quote-claimed family) | PAID=1/16, one preimage, losers 403/10005 |
| S7 | checkstate after a successful swap: Y of the burned input | POST /v1/checkstate → state SPENT (ISSUE-067 class — burned proofs must not read UNSPENT) | 200, state=SPENT |
| S8 | swap with the SAME proof listed twice in inputs | non-200 rejection, duplicate-proof family (saga map reserves 14008); no signatures issued | 400 `duplicate_proof`/14008 (cashu-cf 33c681e, ISSUE-126) |
| S9 (frozen 2026-10-22, pre-run) | mint replay: re-POST /v1/mint/bolt11 with the SAME outputs on an exhausted quote | 400 quote-already-issued family (20002 per cashu-cf error registry); no second issuance | **prediction WRONG** — same-outputs replay is 200-with-IDENTICAL-signatures by design (restore/idempotency path, deterministic k·B_, value-neutral). Locked as two cases: S9a same outputs → 200 + identical sigs; S9b different outputs on consumed quote → 400/20002 |
| S10 (frozen 2026-10-22, pre-run) | melt: HTLC (NUT-14) conditioned proof, NO preimage witness | 403 spending_condition_not_met family (30006) | 403/30006, detail `No witness in proof` |

Control (runs first, must be green or everything above is noise):
mint→quote→PAID→mintProofs through cashu-ts v4 wallet.

## cashu-ts v4 transport gotchas baked into this driver

(ported to `learnings.md` 2026-10-22 — these bite every probe script)

1. `new Wallet(url, { customRequest })` SILENTLY DROPS the transport — v4
   forwards only `authProvider`/`logger` to its internal Mint. Wire it as
   `new Wallet(new Mint(url, { customRequest }), { unit })`.
2. v4 request bodies carry `BigInt`/`Amount` value objects — serialize with
   a bigint→Number replacer at the boundary; and v4 MUTATES parsed response
   objects in place (Amount instances appear inside objects you captured).

## Results

2026-10-22, cashu-cf main@d912252 pre-fix + branch `33c681e` post-fix
(bundle `wrangler deploy --dry-run`), miniflare@5.20260831.0-alpha:

**Pre-fix: 8/9 — S8 FAILED with the amplification finding (below).**
**Post-fix (cashu-cf 33c681e, ISSUE-126): 9/9 PASS** — see
`out/matrix-postfix.log` for the locked run.

| # | Locked identity (error-identity assertions) |
|---|---|
| S1 | 400 `invalid_request`/14005, detail `Proof verification failed at index 0: Invalid proof signature at index 0` (swap path's legacy shape — 30003 is the MELT path's code) |
| S2 | identical to S1 — the signature check fires for on-curve-but-unsigned C too |
| S3 | 403 `spending_condition_not_met`/30006, detail `SIG_ALL verification failed: no candidate message verified` |
| S4 | exactly 1×200 of N=16; losers 400/30001; one distinct signature set (no double issuance) |
| S5 | 200 PAID, change_sum=3 with two blank outputs (refund = 8−4−1); settle.ts dust-truncates refund parts beyond the supplied blanks (logged `melt change truncated`) — one blank + refund 3 returns 2 (denominations [2,1]). Client-supply enough blanks or lose dust. |
| S6 | exactly 1×16 PAID, one preimage; losers 403/10005 |
| S7 | 200, state=SPENT for the swap-burned Y |
| S8 | 400 `duplicate_proof`/14008 (post-fix; see incident) |

## INCIDENT 2026-10-22 — S8 pre-fix: swap duplicate-input amplification (cashu-cf ISSUE-126)

Frozen prediction said "duplicate rejected"; the run returned **200 with
1 signature** (probe passed on a technicality — the identity regex
matched nothing and the check failed correctly). Characterization per
method (probe-bug-first ruled out):

- `repro-amplify.mjs`: one 8-sat proof listed twice, outputs [8,8] →
  **200 with 16 sats of signatures**; checkstate of the input Y → SPENT
  (burned ONCE).
- `repro-liquidate.mjs`: the amplified signatures unblind and **swap back
  normally — 8 became 16 liquid**. Repeatable → unbounded unbacked issuance.
- `repro-melt-duplicate.mjs`: the melt path REJECTED the same attack
  (`400 duplicate_proof/14008`) — only swap lacked the check.

Reported to cashu-cf same session; fixed in cashu-cf `33c681e`
(shared `proof-dedup` primitive on both spend paths, swap identity
aligned to melt's 14008). Wire re-verified: `out/matrix-postfix.log` 9/9.

## Probe-bug log (per method, fixed before trusting)

- empty swap outputs → pre-validation 400 (S1/S2 first run)
- melt's 30003 wrongly frozen for swap (swap identity is 14005)
- single blank output → dust truncation misread as overcharge (S5)
- S8 first check passed a 200 through a family regex — tightened to
  exact error-identity assertions (this is why identity, not family)

## Run 2026-10-22 (final): 12/12 PASS — S9a/S9b/S10 added

- S9 prediction error (documented per method): same-outputs mint replay is
  NOT quote-exhaustion abuse — it returns the IDENTICAL signature via the
  restore/idempotency path (deterministic k·B_, value-neutral). The
  re-issuance abuse case is different-outputs-on-consumed-quote → 400/20002.
  Both now locked.
- S10: HTLC (NUT-14) witness-less melt locked at 403/30006
  `No witness in proof` (completes the spending-condition trio with S3's
  SIG_ALL).
