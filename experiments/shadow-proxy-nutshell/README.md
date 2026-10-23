# shadow-proxy-nutshell — cashu-cf as a Diffy proxy over Nutshell 0.20.3

The owner-directed topology: **cashu-cf runs AS the proxy** (its own
`SHADOW_MODE` worker, ISSUE-095 architecture) in front of a local
Nutshell mint; Nutshell is authoritative for clients; cashu-cf computes
in parallel and emits `SHADOW_DIFF` telemetry. The study instrument then
compares BOTH implementations' own answers endpoint-by-endpoint —
extending the miniflare-spend-matrix to a two-implementation comparative
audit.

## Topology

```
                 ┌──────────────────────────────┐
 scenarios ─────►│ cashu-cf SHADOW worker        │──► Nutshell 0.20.3 :8737
 (proxy-study)   │  (miniflare, SHADOW_MODE)     │    (FakeWallet, authoritative)
                 │   ├ passthrough (client sees) │
                 │   └ local compute → SHADOW_DIFF
                 └──────────────────────────────┘
 scenarios ─────► cashu-cf PLAIN worker (miniflare)  ← cashu-cf's own answers
```

## Bring-up

```
bash setup-nutshell.sh &          # nutshell 0.20.3 FakeWallet on :8737
node proxy-study.mjs              # runs the corpus, writes study-out/
```

cashu-cf side: bundle via `wrangler deploy --dry-run --outdir
.tmp-wrangler-build --name miniflare-test --env ''` (CASHU_CF_ROOT).

## FROZEN PREDICTIONS (2026-10-22, pre-run)

cashu-cf identities are LOCKED from the miniflare-spend-matrix (9/9).
Nutshell predictions from the divergence-registry record (0.20.3 = the
#1008 error-handling rewrite release).

| # | Scenario | cashu-cf (locked) | Nutshell 0.20.3 (prediction) |
|---|---|---|---|
| R4 | GET /v1/keys/{bogus} | 400 | 400 family |
| R5 | POST /v1/checkstate malformed Y | 200 UNSPENT (ISSUE-096 semantics) | 422 (strict curve parse — CDK-parity class) |
| H1 | mint: quote→PAID→mint→unblind verify | 200 + verifiable proofs | 200 + verifiable proofs (cross-wallet: cashu-ts primitives) |
| A1 | swap forged off-curve C | 400 `invalid_request`/14005 detail `Proof verification failed at index 0` | non-200, "Token not verified"-family detail |
| A2 | swap same proof twice | 400 `duplicate_proof`/14008 (ISSUE-126 fix) | non-200 — dedup family UNKNOWN (characterize) |
| A3 | swap P2PK witness-less | 403/30006-family (spending condition) | non-200, 11000-family `no witness in proof` |
| A4 | melt SIG_ALL witness over wrong message | 403/30006 `SIG_ALL verification failed` | non-200, 11000-family |
| A5 | melt HTLC no-witness | 403/30006 `No witness in proof` | non-200, 11000-family (hashlock demands preimage) |
| A6 | mint replay: same outputs on consumed quote | 200 + IDENTICAL signature (restore path) | non-200 "outputs already signed"-family OR 200 replay — characterize |

Read-endpoint shape diffs (info/keys/keysets) are EXPECTED to diverge
(identity/metadata/config: fees ppk 0 vs 100, max_order, v1 vs v2 ids) —
catalogued, not filed as defects.

## Results (2026-10-22/23, cashu-cf branch-stack bundle, nutshell 0.20.3)

**Locked table (error-identity assertions; two full runs + fix-iterations
per the probe-bug log):**

| # | cashu-cf | nutshell 0.20.3 |
|---|---|---|
| R4 keys/{bogus} | **404** `not_found`/10000 | **400** `keyset not found`/12001 |
| R5 checkstate malformed-Y | 200 `UNSPENT` | 200 `UNSPENT` (prediction WRONG: ns is NOT the strict-422 one — that's CDK; ns matches cf) |
| H1 mint + NUT-12 DLEQ cross-verify | `true` | `true` (cashu-ts primitives verify both mints' blind signatures) |
| A1 swap forged off-curve C | 400 `invalid_request`/14005 | 400/10001 `proofs could not be verified` |
| A2 swap duplicate proof | 400 `duplicate_proof`/14008 | 400/11007 `Duplicate inputs provided` |
| A3 swap P2PK witness-less | 403/30006 | 400/**code 0** `Witness is missing for p2pk signature` |
| A4 melt SIG_ALL wrong-message | 403/30006 | 400/11000 `no witness in proof.` |
| A5 melt HTLC no-witness | 403/30006 | 400/**code 0** `Witness is missing for htlc preimage` |
| A6b mint replay same-outputs | **200 + byte-identical signature** (restore path) | **400/11003 `outputs already signed`** |

Route surface (discovered en route): nutshell 0.20.3 serves melt ONLY at
`POST /v1/melt/bolt11`; cashu-cf serves BOTH `/v1/melt` and
`/v1/melt/bolt11` (alias retained). cashu-ts v4 calls the modern route.

**Findings classification:**
- **F1 (registry)**: retry/idempotency fork — A6b. A wallet that times out
  and re-POSTs an identical mint request gets 200+same signatures on
  cashu-cf but 400 `outputs already signed` on nutshell. Neither behavior
  is NUT-mandated; the fork silently forks wallet retry logic.
- **F2 (catalogue)**: error-identity map — every rejection above differs
  in (status, code, detail) across the two mints; nutshell emits code 0
  on two P2PK/HTLC paths (not a NUT-registered code).
- **F3 (catalogue)**: unknown-keyset status fork — 404 vs 400 on
  /v1/keys/{id}; CDK is 400 (ISSUE-095 parity evidence) → cashu-cf is the
  outlier among the three.
- **F4 (resolved non-issue)**: malformed-Y checkstate — cashu-cf and
  nutshell BOTH answer 200/UNSPENT; CDK's 422 is the strict outlier.

Proxy telemetry: `SHADOW_DIFF` events captured per run (info shape 14
diffs; keys full-mode diff — keysets differ by design); passthrough +
`x-shadow-mode: active` + `x-shadow-local-quote` correlation verified.

Probe-bug log (per method): melt route name (cf-alias assumption) → the
404s in run 1 were the ROUTE finding, not mint behavior; DLEQ arg order
(dleq first, hex→bytes) → run-3 `true` on both; R5 prediction corrected
by evidence.
