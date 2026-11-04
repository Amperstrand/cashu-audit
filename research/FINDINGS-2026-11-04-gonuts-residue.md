# gonuts v0.16.0 residue — B1 wallet SIG_ALL melts, NUT-17, NUT-12, /v1/restore (2026-11-04)

Audit #68 item B, executed unattended 2026-11-04. Four sub-items:
**B1** wallet-side SIG_ALL melt production (the priority — code landed
as gonuts-tollgate PR #53), **B2** NUT-17 websocket coverage vs the
matrix, **B3** mint-side NUT-12 DLEQ issuance parity, **B4** /v1/restore
hardening review vs the tollgate #866 lineage.

## Arms (identity verified before any result was trusted, #40 rule)

| Arm | Identity (`/v1/info`) | Provenance | Port |
|---|---|---|---|
| gonuts (B1 branch) | `gonuts-sigall-branch / gonuts/0.4.0` | local build, `/root/src/gonuts-fix` @ `20f7e8a` (branch `fix/sigall-melt-wallet`, = main e3dfc63 = tag `v0.16.0` + the B1 commit), cmd/mint, FAKEBACKEND, INPUT_FEE_PPK=0 | 4430 |
| nutshell 0.21.0 | `Cashu mint / Nutshell/0.21.0` | docker `cashubtc/nutshell:0.21.0`, FakeWallet, `--network host` | 4440 |
| cdk 0.18.3 | `cdk-mintd/0.18.3` | docker `cashubtc/mintd:0.18.3`, fakewallet, `--network host`, fresh workdir + `config init` | 4442 |
| cdk 0.18.1 | `cdk-mintd/0.18.1` | docker `cashubtc/mintd:0.18.1`, fakewallet, `--network host`, fresh workdir + `config init` | 4446 |
| nutshell 0.20.3 | `Cashu mint / Nutshell/0.20.3` | docker `cashubtc/nutshell:0.20.3`, FakeWallet, `--network host` | 4444 |

cdk 0.18.2 (port 4448) was also booted for the four new matrix rows
only. All arms torn down after the run.

## B1 — wallet-side SIG_ALL melt production (LANDED: gonuts-tollgate PR #53)

The gap: since the #809 alignment (#48/#50) the gonuts MINT accepts
spec SIG_ALL melts — first-input witness over
`concat(secret_i‖C_i) ‖ concat(amount_j‖B_j) ‖ quote_id` — verified in
`MeltTokens` before the quote CAS. The gonuts WALLET never produced
that witness: melting any spending-condition token from a gonuts wallet
was impossible end-to-end (wire symptom pre-fix: `400 {"code":30001,
"detail":"invalid witness"}`).

The fix (`wallet/wallet.go` `Melt()`), mirroring the send paths
(`Receive`/`swapToTrusted`/`ReceiveHTLC`):

- **P2PK SIG_ALL** — `AddSigAllSignatureToFirstInput(inputs, blankOutputs,
  quoteId, key)`: the aggregate is computed over the exact
  `(inputs, outputs, quote id)` that go on the wire AND into the melt
  intent, so a `resumeOneMelt` crash-replay re-POSTs byte-identical
  bytes (the #497 replay invariant extended to melts — no re-derivation,
  no fresh counter range).
- **plain P2PK** — per-input signatures (`AddSignatureToInputs`), the
  same mirror `Receive` applies to swaps; the mint's per-proof
  `VerifyP2PKLockedProof` path now has a wallet that satisfies it.
- **refusals that used to strand inputs** — locks the wallet cannot sign
  (`cannot sign locked proofs`) and HTLC-locked proofs (the melt path
  carries no preimage) now refuse **locally**, releasing the
  pending-marked inputs back to spendable, instead of firing a doomed
  request and leaving the inputs pending.

HTLC SIG_ALL melts need a preimage-bearing entry point (`MeltHTLC`) —
flagged for an owner decision, not smuggled into this PR.

### Verification (local + wire)

- Unit (`wallet/sigall_melt_test.go::TestMeltSigAllWitnessShapeAndBinding`):
  witness shape (first input only, one schnorr sig, per-input witnesses
  cleared), binding (verifies over `SigAllMessage(inputs, outputs,
  quote_id)`; must NOT verify without the quote id, over another quote,
  or with an output dropped), and intent/request byte parity.
  **Mutation-verified three ways** — reverting the production signing,
  dropping the quote id from the signing aggregate, and dropping the
  outputs from the signing aggregate each fail both the unit test and
  the e2e (mint-side rejection path).
- Mint-level e2e (`TestMeltSigAllEndToEndRealMint`,
  `TestMeltPlainP2PKEndToEndRealMint`): production `mint.Mint` +
  FakeBackend behind `SetupMintServer`, wallet funded 63 sats, whole
  balance locked to its own key, melted 62+1 fee-reserve (nonzero
  reserve ⇒ blank outputs in the aggregate) → `PAID`.
- Gates: `go vet ./...`, `go test ./... -count=1` (13 packages),
  `go test ./mint/ -tags killtest` — all green.
- Wire: full conformance matrix on the branch — see the wire-run
  section; the pre-existing corpus is unchanged (116/116 green).

## B2 — NUT-17 websocket: coverage was zero; supported surface now covered; kinds diverge

The matrix had **no NUT-17 scenario at all** (README table has no
NUT-17 row). Added `conformance/scenarios/nut17_websocket.py` (3 rows,
all measured on five arms before committing):

| Row | gonuts | ns 0.20.3 | ns 0.21.0 | cdk 0.18.1 | cdk 0.18.3 |
|---|---|---|---|---|---|
| `ws_mint_quote_subscribe_initial_state` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ws_mint_quote_unsubscribe_ok` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ws_mint_quote_unknown_quote_rejected` | ✅ | ❌ | ❌ | ✅ | ✅ |

The nutshell row (subscribe for a nonexistent quote **acks OK** — no
pre-validation of filters — where gonuts and cdk answer a JSON-RPC
error) is seeded in `expected-fail-nutshell-0.20.3.json` +
`expected-fail-nutshell-0.21.0.json` so the Monday v2 lane stays
verdict-stable.

### Subscription-kind parity (probe-measured, `conformance/results/nut17-meltchange/probe-2026-11-04.json`)

| Kind | gonuts | ns .20.3/.21.0 | cdk .18.1/.18.3 |
|---|---|---|---|
| `bolt11_mint_quote` | ACK | ACK | ACK |
| `bolt11_melt_quote` | **ERR 1000 `invalid request method`** | ACK | ACK |
| `proof_state` | **ERR 1000** | ACK | ACK¹ |

¹ with a real curve point as the Y filter; a non-point hex string gets
`-32700 Parse error` from cdk (parse-time point validation).

gonuts supports 1 of 3 spec'd subscription kinds — the melt-quote kind
is dead code in `mint/websocket.go` (`case nut17.Bolt11MeltQuote:` is
commented out; the request falls to `default: invalid request method`)
and the proof-state case is commented out pending cashubtc/nuts#213.
Both reference families support all three. Wallet impact: a wallet
watching its melt via NUT-17 against a gonuts mint must poll instead.
Prior art: the proof-state gap is known upstream
(elnosh/gonuts#108, open); **no venue exists for the melt-quote kind**
(searched gonuts-tollgate + elnosh/gonuts issues and PRs 2026-11-04).
One latent bug noted while reading: `ProofStatesSubClient.Close()`
unsubscribes from `BOLT11_MELT_QUOTE_TOPIC` (wrong topic string) —
currently unreachable (the proof-state case is commented out), would
matter if #213 lands and the case is re-enabled as-is.

## B3 — NUT-12 DLEQ: attached everywhere gonuts signs — but the melt path signs nothing

Code survey: every mint-side signing path converges on
`signBlindedMessages`, which attaches a DLEQ proof to every signature
and persists `(e,s)` alongside `C_` (`blind_signatures` table):

| Path | Signs via `signBlindedMessages` | DLEQ |
|---|---|---|
| NUT-04 mint (incl. NUT-29 batch) | ✓ | ✓ |
| NUT-03 swap | ✓ | ✓ |
| NUT-09 restore | replays stored `(e,s)` | ✓ (wire-measured, new row below) |
| NUT-05 melt change | **never signs** | n/a |

New matrix row `dleq_proof_in_restore_response` (nut12_dleq.py): mint →
`POST /v1/restore` with the same `B_`s → replayed signatures carry
verifiable DLEQ. **PASS on all five arms** — restore-DLEQ parity holds.

### The gap underneath: gonuts never returns melt change at all

NUT-23: *"If the `outputs` field is included and there is excess from
the `fee_reserve`, the mint will respond with a `change` field
containing blind signatures for the overpaid amount."* In gonuts no
code path writes the response's `change` field — the server handler
constructs `PostMeltQuoteBolt11Response` without it and `MeltTokens`
never signs the request's outputs. Wire-measured (same probe capture,
8-sat inputs vs 2-sat invoice, blank outputs in the melt request):

| Arm | state | change |
|---|---|---|
| gonuts (branch) | PAID | **absent** — 6 sats overpayment silently consumed |
| ns 0.20.3 / 0.21.0 | PAID | returned (1 signed output) |
| cdk 0.18.1 / 0.18.3 | PAID | returned (1 signed output) |

Fund note for the TollGate deployment: the operator wallet melting
against gonuts mints (reseller mode) loses every overpaid fee-reserve
and rounding remainder; against cdk/nutshell mints the existing
wallet change-recovery (PR #33/#46 lineage) collects it. The gonuts
WALLET already handles returned change (`meltBolt11Response.Change` →
unblind → save), so the fix is mint-side: sign the request outputs for
the overpaid amount and return them — a monetary path (needs the #59
discipline: claim before sign, persist sigs before the Paid write).
Prior art: none (searched gonuts-tollgate + elnosh/gonuts issues and
PRs 2026-11-04; the open fork PR #46 is wallet-side recovery of change
other mints DO return). Registered in DIVERGENCE-REGISTRY.

## B4 — /v1/restore hardening vs the #866 lineage (read-only audit)

The #866 wallet fallback (fork PR #40) survives a refused swap replay
by asking `/v1/restore` for the journaled outputs. The gonuts endpoint
itself is sound for that purpose:

- Serves from the **persistent** sqlite `blind_signatures` store, not
  the in-memory NUT-19 cache — survives mint restart (the exact
  scenario #40's live test exercised against cdk).
- Returns signatures **with DLEQ** (wire-measured above) and in the
  request's order; the wallet realigns by `B_` anyway.
- Unauthenticated by design (NUT-09); enumeration is infeasible
  (`B_` values are random curve points, not sequential).

Two hardening findings:

1. **Swap-path persistence window (new, unreported).** `Swap` performs
   `AddPendingProofs` (claim) → sign → `SettleProofs` (pending→used, tx
   A) → `SaveBlindSignatures` (tx B) — **two transactions**. A mint
   crash between A and B spends the inputs without persisting the
   output signatures: restore then honestly returns nothing, the #866
   wallet fallback correctly refuses to guess (keeps the intent
   forever), and the value is recoverable only by the mint operator.
   The mint path does NOT have this window (the #59 saga discipline
   persists signatures before the Issued write; the recovery head
   replays them); cdk-mintd does not have it (swap state transitions
   are one DB transaction). Also two smaller windows exist between
   claim→sign→settle where a hard crash strands the inputs as mint-side
   `pending` with no reconciler (the melt quote path got one in #59;
   swap-claim orphans did not). Fix shape: persist blind signatures in
   the same transaction as `SettleProofs` (or before it), matching the
   mint path's ordering discipline.
2. **No array-size limits on restore (or swap/melt) requests.**
   `MintLimits` covers amounts/balance only; the only output bound in
   the tree is NUT-29's `BatchMaxOutputs=1000`. `/v1/restore` with a
   huge `outputs` array costs one indexed sqlite lookup per element —
   cheap DoS surface. cdk enforces `max_inputs`/`max_outputs` limits on
   transaction endpoints. A blanket body/array limit would match both
   the reference family and the NUT-06 `max_array_length` convention
   (nutshell advertises 1000).

## Wire-run: conformance matrix on the B1 branch (target 116/116 unchanged — met)

`conformance/reports/matrix-gonuts-sigall-melt-2026-11-04.md`
(identity-stamped `gonuts-sigall-branch / gonuts/0.4.0` @ 4430):

- **120 passed, 3 failed, 5 skipped (128 total)**. Every row that
  existed at the v0.16.0 tag (the 116-row corpus) is **still non-FAIL**
  — the 5 skips are pre-existing classes (invoice-description support,
  nonzero-ppk fee row, DLEQ-absent mint, 2 batch-cap rows — each an
  unmet precondition on this config, never silent). The 3 fails are all
  item A's post-tag `errid_*` rows — the documented gonuts
  error-identity divergences from
  FINDINGS-2026-11-04-error-identity.md (11002-vs-11005 underfunded,
  10002-vs-11003 outputs-already-signed, 11005-vs-11013 unit) —
  expected, unchanged, registry'd. This session's 4 new rows all PASS.
- The "116/116" target from the #68 body: interpreted as "every row
  non-FAIL at v0.16.0 stays non-FAIL" — met with zero corpus
  regressions.

## Verification honesty

- B1 mutation checks were run against the WORKING TREE mutations (sed
  of the one signing call), not a committed revert; each mutation was
  restored immediately and the suite re-run green after restore.
- The gonuts wire arm ran the B1 BRANCH build (provenance above); the
  matrix's melt scenarios sign manually probe-side, so the branch's
  wallet-side change is invisible to the matrix by construction — its
  evidence is the Go test suite (unit + real-mint e2e), not the wire
  run. The wire run's job here was regression (corpus unchanged).
- NUT-17 kind probes: the `proof_state` filter must be a REAL curve
  point for cdk (a non-point hex gets `-32700`); the first probe draft
  used a fake point and misread cdk as unsupported — corrected, the
  committed probe uses `hash_to_curve` of a fixed string.
- ns 0.21.0's melt-change cell initially read as no-change: its
  FakeWallet reserves 2 sats on a 2-sat invoice, so the 4-sat input
  set was underfunded (`needed: 5`); re-measured with 8-sat inputs →
  change returned. The committed probe sizes inputs to clear every
  arm's reserve.
- cdk 0.18.2 was measured only on the four new matrix rows (the
  lane-pinned surface where seeding matters), not the full corpus.
- No upstream issues/PRs filed; the three new gonuts-side facts
  (melt-quote kind, melt change absence, swap persistence window) are
  registered in DIVERGENCE-REGISTRY with prior-art searches noted.

## Rig notes for whoever runs next

- cdk-mintd 0.18.x config: the working shape is `[info]` (url/
  listen_host/listen_port/mnemonic=env:…) + `[database] engine=sqlite`
  + `[payment_backend] backend="fakewallet"` + `[onchain]
  onchain_backend="fakewallet"` + `[fake_wallet] supported_units=
  ["sat"]`; `config init --new-mint --file config.toml` must run in the
  same container invocation as the daemon (`cd /data && config init …
  && exec cdk-mintd`) — an init in a separate `--rm` container leaves
  a DB the daemon considers uninitialized. Working pattern is in this
  session's commands; `/root/ab-matrix/cdk-upgrade-ladder/config.toml`
  is the 0.18.0-era reference.
- gonuts-arm melt probes need INVOICES from a nutshell arm (mainnet
  prefix + payment_secret): gonuts FakeBackend invoices are signet
  (`lntbs…`) which cdk answers with a misleading `50000 Invalid payment
  method`.
- Host rule confirmed again: `--network host` arms work; the wedged
  docker0 bridge was not exercised (no bridge-mapped containers were
  needed).
