# gonuts NUT-08 melt change — fixed on branch `fix/nut08-melt-change` (PR #54) (2026-11-05)

Follow-up to FINDINGS-2026-11-04-gonuts-residue §B3 (audit #68): the
"gonuts mint never returns melt change" divergence is fixed on
OpenTollGate/gonuts-tollgate PR #54
(`fix/nut08-melt-change`, branch off main `e3dfc63` = v0.16.0). Wire
evidence: `conformance/reports/matrix-gonuts-nut08-melt-change-20261105-031804.md`.

## What landed (the short version)

- **Mint**: blank outputs validated before the quote claim (keyset/B_
  checks; **amounts ignored** per NUT-08 "Bob MUST ignore it"),
  journaled (`melt_change_outputs`, migration 000011) before the
  payment attempt; on settlement the overpay
  `inputs − input fees − invoice amount − fee actually spent` is split
  into keyset denominations, imprinted on the blanks in request order,
  signed (DLEQ) and persisted **before** the Paid write (#59
  discipline). Poll-path reconciler signs change from the journal; a
  PAID quote re-POSTed with identical outputs answers idempotently
  from stored signatures (past the NUT-19 cache TTL and across
  restarts — the #497 invariant, mint side); quote-state responses
  carry the stored change; info declares nut 8 supported.
- **Fee truth**: `PaymentStatus.FeeSpent/FeeSpentKnown` — CLN reports
  `amount_sent − amount`; the FakeBackend reports 0; **a backend that
  cannot report keeps its whole reserve** (LND today) — never return an
  unaccounted fee.
- **Wallet**: `constructMeltChangeProofs` — mint-assigned amounts legal
  only at the NUT-08 boundary; signature *i* answers blank *i* at the
  same keyset; no more signatures than blanks; denominations only;
  total ≤ the wallet's own overpay; DLEQ verified; counters never
  rewound. The pre-existing resume tail mis-passed the full blank set
  into the swap-strict constructor (a latent bug for partial change) —
  fixed by the same seam.
- FakeBackend `FeeReserveSats` knob (default 0); `cmd/mint`
  `MINT_FAKE_FEE_RESERVE`.

## Wire verification (identity-verified at run start, #40 rule)

Arms: gonuts branch build @ 4432 (`gonuts-nut08-branch / gonuts/0.4.0`,
`.env` in CWD, FAKEBACKEND, `MINT_FAKE_FEE_RESERVE=2`), branch-build
oracle @ 4434, **gonuts origin/main build @ 4436** (same knobs — the
divergence arm), nutshell 0.21.0 + cdk 0.18.3 docker arms (host
network) with separate same-family oracles.

New scenario family `melt_change` (2 rows, committed):

| Row | gonuts branch | gonuts main | ns 0.21.0 | cdk 0.18.3 |
|---|---|---|---|---|
| `melt_change_returned_for_overpay` | ✅ 14 sats (full overpay) | ❌ no change | ✅ 12 sats | ✅ 13 sats |
| `melt_change_omitted_without_outputs` | ✅ | ✅ | ✅ | ✅ |

The exact change differs per arm because the reference FakeWallets
spend different actual fees (ns 2, cdk 1, gonuts fake 0) — the row
asserts the NUT-08 range `total − amount − reserve ≤ change ≤ total −
amount`, which is the spec-stable invariant; the gonuts exact math
(fake spends 0 → full overpay returns) is covered by the Go unit
tests. Change proofs were unblinded and re-spent (swap) on every arm.

Full registry on the branch: 129 rows, 3 FAIL — exactly the three
pre-existing registry'd error-identity divergences
(FINDINGS-2026-11-04-error-identity: 11002/11005, 10002/11003,
11005/11013), unchanged from the v0.16.0 corpus. Zero regressions.

## The wire run earned its keep

The first cut of the fix **rejected nonzero amounts on melt blank
outputs** ("Alice MUST set amount 0" read as a MUST-enforce). The
corpus immediately went red on five `melt_p2pk*`/`melt_htlc*` rows —
rows that PASS on nutshell 0.21.0 and cdk 0.18.3 (v2 baselines) and
encode the house scenario pattern of sending real amounts on melt
outputs. Spec re-read: NUT-08 also says "**Bob MUST ignore it**,
imprinting the amount himself" — accepting and ignoring is the
conformant behavior. Fixed before the PR opened; regression test
`TestMeltChangeIgnoresNonzeroBlankAmounts` pins it.

## Rig notes for whoever runs next

- The gonuts arm needs THREE instances for melt-change evidence: the
  target (with the reserve knob), an invoice oracle (foreign invoices
  force the real payment path — the target's own FakeBackend invoices
  settle internally, which zeroes the reserve), and a main build for
  the divergence column.
- Docker reference arms need SEPARATE oracle containers (a FakeWallet
  auto-settles its own invoices → `20006 Invoice already paid` when
  the oracle is the same instance).
- `cmd/mint` builds need CGO (go-sqlite3); a `CGO_ENABLED=0` build
  fails at "go-sqlite3 requires cgo".
- Mutation-verified four ways on the branch: dropping the Succeeded-
  branch assignment, the poll-path assignment, the wallet keyset/index
  binding, and the wallet overpay ceiling each fail their tests.
