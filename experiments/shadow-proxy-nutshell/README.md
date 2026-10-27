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

## Post-study action (2026-10-23)

F3 resolved cashu-cf-side: branch `fix/keys-unknown-id-400-alignment`
(e99a11e) — /v1/keys/{unknown} now 400, characterization-locked. The
divergence closes on merge+deploy; re-run this study to confirm
three-way 400 alignment (ns / cdk / cf).

## Run 4 extension (2026-10-23): A7 + fee/denomination catalogue

- **A7 (locked)**: fee-aware valid swap → both mints 200, burned Y reads
  SPENT via /v1/checkstate (ISSUE-067 class holds on both). NUT-02 fee
  math agrees: ceil(ppk/1000) per input.
- **F5 (catalogue)**: nutshell 0.20.3 default keyset ppk=100 + strict
  balance enforcement — `400/11000 "inputs (8) - fees (1) vs outputs (8)
  are not balanced."` cashu-cf study config ppk=0 (same rule, different
  config). Wallets must read keyset fees before building swap outputs.
- **F6 (catalogue)**: nutshell rejects a single NON-DENOMINATION output
  (amount 7) with the OPAQUE `400 code 0 detail:"7"` — the #1008
  open-question class ("reject and log? what error?"), now measured on
  the plain-swap path too. cashu-cf splits refund amounts across
  available blank outputs (imprintSplitAmounts) instead.

## Version matrix: nutshell 0.20.3 vs 0.21.0 (2026-10-23, same corpus)

| # | ns 0.20.3 | ns 0.21.0 | drift |
|---|---|---|---|
| A3 swap P2PK witness-less | 400/**code 0** `Witness is missing for p2pk signature` | 400/**11000** `no signatures in proof.` | opaque code-0 → proper NUT code (#1008 error-wave) |
| A5 melt HTLC no-witness | 400/**code 0** `Witness is missing for htlc preimage` | 400/**11000** `no HTLC preimage provided` | same fix |
| A1, A2, A4, A6b, A7, R4, R5, H1 | — | — | **unchanged** (identities stable across the release) |

Corollary: the retry fork (A6b) and all shared-rejection identity forks
persist on 0.21.0 — the F1 registry row is version-stable. The 0.20.3
code-0 paths we catalogued in F2 were fixed upstream in 0.21.0, confirming
they were defects, not semantics. cashu-cf R4 on this run = 400 (the
alignment branch bundle) — the unknown-keyset fork is closed on the wire;
three-way 400 alignment achieved modulo wording.

## Run 5 (2026-10-23): corpus-wide proxy faithfulness + happy melt (A8)

- **Proxy-faithfulness: 4/4** — R4/R5/A1/A2 sent through
  cashu-cf-as-proxy AND direct to nutshell: byte-identical status+body on
  every wrapped scenario. The "cashu-cf is the proxy for nutshell" claim
  is now corpus-backed, not single-endpoint sanity.
- **A8 (locked)**: happy melt on both — cashu-cf PAID, fee_reserve 1,
  change 3 (= inputs−amount−reserve, exactly); nutshell PAID, change 2.
- **F7 (catalogue)**: nutshell quoted `fee_reserve: 0` yet charged 2 sats
  (fakewallet policy: 1% + 2000 msat min) — actual fee EXCEEDED the
  quoted reserve, and the change output was imprinted down to the
  post-fee value. cashu-cf clamps the effective fee to the quoted
  reserve (`min(actual, feeReserve)`, settle.ts). Durable datum: the
  reserve-clamp semantic differs; ns fee_reserve is a lower bound, cf's
  is a bound. Wallets cannot rely on fee_reserve as a hard cap on ns.

## Three-way run (2026-10-24): CDK 0.18.1 as the third leg

cdk-mintd 0.18.1 (fakewallet, :8739, binary at /root/.cargo-target/release/
cdk-mintd — 3-min build via CARGO_TARGET_DIR) behind the SAME proxy
instrument: proxy-faithful **4/4 against CDK as well**.

| # | cashu-cf | nutshell 0.20.3 | CDK 0.18.1 |
|---|---|---|---|
| R4 keys/{bogus} | 404/10000 (→400 branch queued) | 400/12001 | **400** |
| R5 malformed-Y | 200 UNSPENT | 200 UNSPENT | **422** (strict outlier) |
| A1 forged-C swap | 400/14005 | 400/10001 | 400/10001 `Token not verified` |
| A2 duplicate swap | 400/14008 `duplicate_proof` | 400/11007 | 400/**11007** `Duplicate Inputs` (cdk≡ns code) |
| A3 P2PK witness-less | 403/30006 | 400/11000 | 400/**20008** witness-required |
| A4 SIG_ALL wrong-msg | 403/30006 | 400/11000 | 400/**20008** |
| A5 HTLC no-witness | 403/30006 `No witness in proof` | 400/11000 `no HTLC preimage provided` | 400/**50000 `Secret is not a HTLC secret`** — MISATTRIBUTED LABEL: cdk source (nut14/mod.rs:158-164) reuses IncorrectSecretKind for the NO-WITNESS branch; the secret WAS parsed as HTLC (kind check passed at :141). All three reject; cdk's message points at the wrong thing (the #1008 'what error?' class) |
| A6b mint replay | **200 + identical sig** | 400/11003 | **200 + identical sig** |
| A7 fee-aware swap | 200 SPENT | 200 SPENT | 200 SPENT (ppk 0) |
| A8 happy melt | PAID, reserve 1, change 3 (clamp) | PAID (reserve 0, charged 2) | PAID, reserve 1, **change 4** (refunds actual: fee 0 → 4 back) |

**F1 RESHARPENED**: the mint-retry idempotency fork is **nutshell vs
{cashu-cf, CDK}** — both 200-with-identical-signature; nutshell alone
rejects (400/11003). cashu-cf is ecosystem-majority; the registry row's
owner-venue calculus shifts (nutshell-side observation, not a cf gap).
**Fee semantics triad**: cf clamps effective fee to the quoted reserve;
cdk refunds per actual (reserve 1, actual 0 → full 4 back); ns charged
above its own quote (0→2). Three legitimately different NUT-05
fee-refund policies — wallets see three different change amounts for
identical melts.

## NUT-14 positive path (2026-10-24): three-way HTLC unlock

Complement to the A5 rejection locks — melt WITH the correct preimage
witness: **PAID on all three** (cashu-cf, nutshell 0.20.3, CDK 0.18.1).
Wire-shape datum en route: nutshell REQUIRES the witness as a JSON
STRING (object form → 422 pydantic `inputs.0.witness` validation error);
cashu-cf accepts both forms (stringifies objects itself); cdk verified
with the string form. HTLC secret shape: hash-in-data
(cashu-ts-canonical) recognized by all three (cf. corrected A5).

## NUT-11 positive path (2026-10-24): three-way P2PK unlock

Mint P2PK (SIG_INPUTS, n_sigs 1) conditioned proof on each mint, witness
produced by **cashu-ts's own `signP2PKProof`** (the canonical wallet
form): **PAID on all three** (cashu-cf, nutshell 0.20.3, CDK 0.18.1).
Witness wire form: JSON-string `{signatures:[schnorr-hex]}` (same
string-form rule as HTLC; ns requires string). Helper note: it returns
the SIGNED PROOF — extract `.witness`.

**Spending-condition matrix status (three-way):** P2PK ✓reject ✓unlock ·
HTLC ✓reject ✓unlock · SIG_ALL ✓reject (A4) ✗unlock — the one open
cell; positive SIG_ALL needs per-mint message-format handling (the
documented 0.20.3 format flip + cdk divergence = the format minefield;
highest-effort, deferred).

## SIG_ALL positive path (2026-10-24): the matrix completes

The "format minefield" dissolved under source-reading + empirics: the
canonical melt SIG_ALL message is **identical across all three**
implementations — `concat(secret_i‖C_i) ‖ quoteId` (ns appends quote at
conditions.py:134; cf's primary candidate + buildSigAllMeltMessage; cdk
accepted it first-try). Signature = schnorr over **sha256(message)**
(cf hashes at spending-conditions.ts:361 — signing the raw utf8 bytes
fails everywhere). **PAID on all three.**

**Spending-condition matrix FINAL (three-way):**

| Condition | Rejection | Unlock |
|---|---|---|
| P2PK (SIG_INPUTS) | ✓ | ✓ PAID ×3 |
| HTLC | ✓ | ✓ PAID ×3 |
| SIG_ALL | ✓ | ✓ PAID ×3 |

Every cell locked across cashu-cf, nutshell 0.20.3, CDK 0.18.1 —
rejection identities + unlock paths + the two wire rules (witness as
JSON string; SIG_ALL message = canonical concat + quoteId, schnorr over
sha256).
