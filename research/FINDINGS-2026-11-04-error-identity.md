# Error-Identity Matrix — spec codes × 4 implementations (2026-11-04)

Audit #68 item A. Every error code/shape the Cashu NUTs define (NUT-00
envelope + `nuts/error_codes.md`), against what four implementations
actually emit on the wire for the same malformed-shaped requests.

**Arms (identity captured at run start, #40 rule):**

| Arm | Identity (`/v1/info` version) | Provenance |
|---|---|---|
| gonuts v0.16.0 | `gonuts/0.4.0` | local build, `/root/src/gonuts-fix` @ `d0fd3b0` (zero content diff vs tag `v0.16.0`), FakeBackend, :4460 |
| nutshell 0.21.0 | `Nutshell/0.21.0` | docker `cashubtc/nutshell:0.21.0`, FakeWallet, :4462 |
| cdk 0.18.1 | `cdk-mintd/0.18.1` | docker `cashubtc/mintd:0.18.1`, fakewallet, :4464 |
| cashu-cf | `Nutshell-CF/0.0.1` (testnut) | deployed `https://testnut.cashu.exchange`; local source `cashu-cf@6cd249e` re-verified via `experiments/miniflare-spend-matrix` (12/12 PASS incl. error locks) |

Also verified for seed accuracy: nutshell 0.20.3, cdk 0.18.2, cdk
0.18.3 (see "Version deltas"). Raw captures:
`conformance/results/error-identity/*.json` (probe battery:
`conformance/error_identity_probe.py`, frozen predictions in header).
Scenario verdicts: `conformance/scenarios/nut00_error_identity.py`.

## Spec inventory (cashubtc/nuts `error_codes.md` + NUT-00)

Envelope (NUT-00 §"Errors"): HTTP **400** + `{"detail": <string>,
"code": <int>}`. Codes: **10001** proof verification failed;
**11001–11017** transaction classes (spent/pending/signed-outputs/
pending-outputs/unbalanced/limit/dup-inputs/dup-outputs/multi-unit/
unit-mismatch/amountless/amount-mismatch/unit-unsupported/max-inputs/
max-outputs/dup-quote-ids/max-batch); **12001–12003** keyset unknown/
inactive/expired; **20001–20009** quote classes (unpaid/issued/minting-
disabled/LN-failed/pending/invoice-paid/expired/mint-sig-invalid/
pubkey-required); **30001–30002** NUT-21 clear auth; **31001–31004**
NUT-22 blind auth. NUT-19 mandates cached-endpoint replay semantics but
assigns no error code; NUT-11 witness/condition failures have **no
assigned code** (measured below as the widest divergence field).

## Wire matrix (same request → four answers)

| Failure class (spec) | Spec | gonuts v0.16.0 | cdk 0.18.1 | nutshell 0.21.0 | cashu-cf (testnut) |
|---|---|---|---|---|---|
| P01 unknown keyset in swap | 12001 | ✅ 12001 | ✅ 12001 | ❌ **11000** `keyset id unknown.` | ❌ **14005** |
| P02 duplicate inputs | 11007 | ✅ 11007 | ✅ 11007 | ✅ 11007 | ❌ **14008** |
| P04 underfunded swap | 11005 | ❌ **11002** | ✅ 11005 | ❌ **11000** `input amounts (8) less than output amounts (16).` | ❌ **11001**@400 `available for fees (-8)` |
| P05 spent proofs | 11001 | ✅ 11001 | ✅ 11001 | ✅ 11001 | ❌ **30001**@400 |
| P06 fresh inputs + already-signed outputs | 11003 | ❌ **10002** | ❌ **11008** `Duplicate outputs` | ✅ 11003 | ❌ **200 + identical sigs** (restore path, no error) |
| P07 forged C (valid keyset) | 10001 | ❌ **10000/10003**¹ | ❌ **422 + non-NUT text**² | ❌ **code 0** `public key could not be parsed` | ❌ **14005** `Proof verification failed at index 0` |
| P08 non-hex C | NUT envelope | ✅ 10000 `{detail,code}` | ❌ **422 + non-NUT text**² | ✅ code 0 `{detail,code}` | ✅ 14005 `{error,detail,code}`³ |
| P09 mint quote unit `usd` | 11013 | ❌ **11005** | ✅ 11013 | ✅ 11013 | ❌ **200 — quote created, unit ignored**⁴ |
| P10 mint quote amount 0 | 400+envelope | ❌ **20010** (non-spec) | ✅ 11006 `between 1 and 500000` | ❌ **422 pydantic array** (non-NUT) | ✅ 11006 `positive integer` |
| P11 mint w/ bogus quote id | (none assigned) | ❌ **20009** `quote does not exist`⁵ | ❌ **50000** | ❌ **code 0** `quote not found` | ❌ **404 + 14005** |
| P12 P2PK wrong witness | (none assigned) | ❌ **30001** `not enough valid signatures`⁶ | ⚠️ **20008** `P2PK spend conditions are not met`⁷ | ⚠️ **11000** `signature threshold not met` | ❌ **30006@403** |
| P13 HTLC wrong preimage | (none assigned) | ❌ **30004** `Invalid preimage for HTLC`⁶ | ❌ **50000** `Preimage does not match` | ⚠️ 11000 `HTLC preimage does not match` | ❌ **30006@403** |
| P14 melt quote non-BOLT11 | 400+envelope | ❌ **20009** `invalid invoice`⁵ | ❌ **50000** `Invalid payment method` | ⚠️ code 0 `Bech32 string is not valid` | ✅ 14005 |
| P15 exact swap replay (NUT-19) | cached 200 | ✅ 200 byte-identical sigs | ✅ 200 byte-identical sigs | ❌ 400 11001 `proofs already spent` | ✅ 200 identical sigs |

¹ payload-dependent: unparseable point → 10000 `invalid public key`;
   parseable-but-wrong point → 10003 `invalid proof` (both non-spec;
   spec 10001).
² axum `JsonRejection` plain-text body — a `{code,detail}` parser gets
   nothing; HTTP 422 not 400.
³ envelope carries an extra `error` field and duplicates `code` in a
   response header (super-set of NUT-00; noted, not fatal).
⁴ testnut keysets are `sat`-only, yet `unit:"usd"` returns a sat invoice
   — the mint-quote path ignores `unit` entirely (no rejection at all).
⁵ gonuts collapses all melt/quote lookup failures onto 20009, which the
   spec assigns to NUT-20 "pubkey required for mint quote" — a wallet
   branching on 20009 misdiagnoses.
⁶ gonuts' spending-condition codes 30001 (NUT-11) / 30004 (NUT-14)
   predate the spec's NUT-21/22 allocation of the 3xxxx range —
   **gonuts 30001 ≠ spec 30001 ≠ cashu-cf 30001** (three meanings:
   witness failure / clear-auth-required / token-spent).
⁷ cdk maps *all* NUT-11 failures (and NUT-20 quote-sig failures) onto
   20008 (`map_nut11_error`, cdk-common/src/error.rs) — the spec's 20008
   is the NUT-20 mint-quote signature; stretching it to swap witnesses
   is defensible-but-unilateral. Registry-vs-wire: cdk's wire
   BlindedMessageAlreadySigned case (11003) was NOT reachable in P06 —
   the cross-request duplicate-output check (11008) fires first.

## Static registry facts (source-level, cross-checked with wire)

- **gonuts** (`cashu/cashu.go` + `cashu/nuts/nut11,14`): hybrid legacy
  scheme — 10000 general, 10002 outputs-signed, 10003 invalid-proof,
  10004 secret-too-long, plus spec-aligned 11001/11006/11007/11008/
  11016/12001/12002/20001–20008, plus own 11002 (insufficient amount —
  collides with spec "pending"), 11003 (payment method — collides with
  spec "outputs already signed"), 11005 (unit — collides with spec "not
  balanced"), 20009 (generic melt-quote — collides with spec NUT-20),
  20010 (zero-amount, non-spec), 30001 (NUT-11) / 30004 (NUT-14)
  spending conditions. `ProofPendingErr` reuses **11001** — spent and pending
  are indistinguishable to a gonuts wallet. Missing entirely: 11004,
  11009–11015, 11017, 12003, 20007.
- **cdk** (`cdk-common/src/error.rs`): complete spec table incl.
  11014/11015/11017/12003/20007/30001-2/31001-4, plus `Unknown(50000)`
  internal family (on the wire for unknown-quote, bad-preimage,
  non-bolt11) and serde-level 422s that bypass the envelope.
- **nutshell** (`core/errors.py`): complete spec table, but the swap
  path raises bare `TransactionError` (11000) for keyset-unknown and
  unbalanced (typed classes 12001/11005 exist and are never raised
  there); `SecretTooLong`/`WitnessTooLong` → 11000; an untyped
  `CashuError` family surfaces as **code 0** (forged C, quote-not-found,
  bech32 parse); 11014/11015 (max inputs/outputs) not defined.
- **cashu-cf**: three registries. `src/core/errors.ts` is fully
  spec-aligned (used by mint-quote endpoints); `src/utils/error-
  handling.ts` `CashuErrorCodes`/`CommonErrors` (melt/swap paths)
  invents 14005/14008, re-maps spent→30001, pending→30002, invalid-
  proof→30003, insufficient→30004@402, spending-condition→30006@403,
  witness→30007, HTLC→30008 (30008 measured NOT emitted — 30006 is),
  unit→11005, invoice-already-paid→40003 (spec 20006), lightning→40001;
  `src/config/constants.ts` `ERROR_CODES` is a **dead** fourth registry
  (zero references) with yet another mapping. Same mint, same NUT range,
  two live meanings + one dead one.

## Version deltas (measured)

- nutshell 0.20.3 → 0.21.0: unsupported-unit fixed 10000 → 11013.
- cdk 0.18.1 → 0.18.3: no change on any row above.
- cashu-cf local (`6cd249e`) vs deployed testnut: no change on any row
  above (miniflare locks S1/S3/S4/S8/S9/S10 all re-verified PASS).
- nutshell 0.22.0 (released 2026-11-03, per the repo's upstream-watch):
  no docker image published as of this run — not probeable; the 0.21.0
  rows above are the latest wire-measured.

## What was and wasn't verified

- **Identity-verified**: all four arms via `/v1/info` at run start
  (headers in each capture); gonuts tree equality vs tag `v0.16.0`
  (`git diff v0.16.0 HEAD` empty).
- **Wire-verified**: every matrix cell above is a live response, not a
  static guess; envelope key-sets recorded in the JSON captures.
- **Static-only (not wire-probed)**: pending-proofs identities (11002
  spec meaning) — needs an in-flight melt to stage; keyset-inactive
  (12002) and keyset-expired (12003) — needs a rotated keyset arm;
  NUT-21/22 auth codes (30001/30002/31001-4 as spec'd) — no auth-enabled
  arm. These rows rest on source analysis only and are marked ⚠️ in
  registry facts, not in the wire matrix.
- **Mutation-checked**: the scenario suite's red cells were each
  observed live (per-arm runs above); no scenario passes vacuously —
  cdk's two FAILs and cashu-cf's six FAILs are the suite failing on
  real divergences, and the seed rows document exactly those cells.

## Convergence targets (what a wallet can rely on today)

Only three identities are identical across all four implementations on
the wire: duplicate-inputs is *rejected* (code agrees only gonuts/cdk/
nutshell: 11007; cf 14008), spent-proofs is rejected (11001 except cf
30001 — so not even that), and every arm rejects the P2PK wrong-witness
spend with a reasoned detail. **No numeric error code in the probed set
is emitted identically by all four implementations.** The practically
parseable subset: 400+`{detail,code}` envelope (gonuts, nutshell, cf
superset) with cdk's 422 serde escapes as the outlier class.

## UPDATE 2026-11-07 — gonuts arm fixed on branch (PR #55)

The gonuts column's hybrid scheme is fixed on
`OpenTollGate/gonuts-tollgate` branch `fix/error-identity`
([PR #55](https://github.com/OpenTollGate/gonuts-tollgate/pull/55), off
main `e3dfc63` = v0.16.0). Wire-verified on the branch arm
(`conformance/results/error-identity/gonuts-errid-branch-*.json`;
identity `gonuts/0.4.0` checked at run start; full-matrix reports
`conformance/reports/matrix-gonuts-fix-error-identity-2026-11-07.md` +
same-day pristine-main baseline):

- **Spec-aligned**: P04 underfunded 11002→**11005**; P06 outputs-signed
  10002→**11003**; P09 unit 11005→**11013**; P07 forged-C 10003→**10001**
  (and the parse-luck 10000s — P08 non-hex C now also 10001, killing the
  payload-dependent identity); P10 zero-amount 20010→**11006**; pending
  proofs de-conflated from spent (11001→**11002** — spent and pending
  are distinguishable for the first time).
- **Vacated spec blocks**: the spec-unassigned classes moved to a
  documented private 41xxx block outside every spec-allocated range —
  41001 payment-method (was 11003), 41002 quote-not-exist (was 20009 =
  NUT-20), 41003 melt-quote request validation incl. invalid invoice
  (was 20009), 41004 melt-quote-exists (was 20009), 41011 NUT-11
  witness (was 30001 = NUT-21 clear-auth), 41014 NUT-14 HTLC (was
  30004). Details unchanged on every path.
- **Unaffected**: P01 12001, P02 11007, P05 11001 as before; NUT-19
  exact-replay still 200 byte-identical (P15).
- **Scenario suite**: nut00_error_identity family **8/8** on the branch
  (was 5/8); 130-row matrix row-by-row identical to the pristine-main
  baseline except exactly the 3 errid rows clearing. Mutation-checked
  both sides: the Go fence (revert UnitErrCode →
  TestErrorCodesMatchSpecTable/Values red) and the rig (rebuilt mutant
  mint → exactly errid_mint_quote_unit_unsupported_code_11013 red, other
  7 green).
- The other three arms' columns are unchanged (cdk 6/8, nutshell 6/8,
  cashu-cf 2/8 on this family); with gonuts green the family's first
  fully-spec-aligned arm exists, and the P04/P05/P06/P01/P02 identities
  now agree gonuts↔cdk on codes.

## UPDATE 2026-11-07 (ii) — cashu-cf arm fixed on branch (PR #116)

The cashu-cf column is fixed on `Amperstrand/cashu-cf` branch
`fix/error-identity-audit68`
([PR #116](https://github.com/Amperstrand/cashu-cf/pull/116), ISSUE-148,
off main `2e3c5cf9` — which already carries ISSUE-138 phases 1+2, so the
branch starts from 3/8 locally, not the audit snapshot's 2/8).
Wire-verified on a local `wrangler dev` FakeWallet arm shaped like the
deployed testnut (`ENABLE_USD_BACKEND=true` overlay, sat-only keysets;
identity `Nutshell-CF/0.0.1` checked at run start; capture
`conformance/results/error-identity/cashucf-errid-local-20261107-*.json`;
report `conformance/reports/matrix-cashucf-fix-error-identity-2026-11-07.md`):

- **Spec-aligned**: P01 unknown keyset 14005→**12001**; P04 underfunded
  10000 (audit: 11001)→**11005**; P05 spent 14005-on-the-live-path (the
  T1-locked `setPendingBatch` wrapper hid the ProofStateError from the
  router's instanceof branch; audit measured 30001 pre-phase-1)→**11001**;
  P06 fresh-inputs+signed-outputs 200-restore-replay→**400/11003** with
  the restore now gated on inputs-consumed (retry/concurrent-duplicate
  replay unchanged; inputs provably not burned — cashu-cf spend-matrix
  S13b); P09 unit-usd 200-sat-invoice→**400/11013** by validating the
  quote unit against ACTIVE KEYSETS, not just `ENABLE_USD_BACKEND` (the
  deployed testnut's flag-on/keysets-sat-only mismatch is ISSUE-014's
  class; ISSUE-148 documents the tension and the config-side follow-up
  instead of silently deciding). Bonus same-class alignment: P07/P08
  forged/non-hex C 14005→**10001** (envelope shape unchanged).
- **Unaffected**: P02 11007 and P15 exact-replay 200 byte-identical
  (NUT-19 cache, untouched); detail messages and legacy `error` slugs
  frozen everywhere (characterization suites green unmodified).
- **Scenario suite**: nut00_error_identity family **8/8** on the branch
  (pristine-main same-env baseline **3/8**); full 130-row suite run on
  BOTH arms — row-identical except exactly the five errid rows clearing
  (the baseline arm is the mutation-check red side). Cashu-cf-side locks:
  spend-matrix 18/18 (S1/S2 re-locked to 10001; new S11–S14), unit
  families for every changed verdict.
- Fleet score after gonuts PR #55 + this PR: **two arms fully green on
  the errid family** (gonuts, cashu-cf); cdk 6/8 and nutshell 6/8 remain
  (cdk's P07/P08 422-serde escape class; nutshell's P01/P04 bare-11000
  class). Post-deploy re-verification of the DEPLOYED testnut arm is
  queued in cashu-cf ISSUE-148 (Open Question).

## Addendum 2026-11-07 (overnight battery, fresh-capture confirmation + 4 new vectors)

Independent re-run of the battery (private/error-identity/battery.py,
24 vectors) against gonuts @ `24d9da8` (the remediation branch, post
`fix(mint): error-identity alignment`), cdk-mintd 0.18.2, nutshell
0.21.0 — all captured identities match the matrix above and the
matrix-gonuts-fix-2026-11-07 run row-for-row (fresh reproduction of
the fixed 11003/11005/11006/11013/41xxx identities on the branch).
Raw rows: `private/error-identity/rows-*.json`.

Four vectors outside the original battery (three-way fresh rows):

| Vector | gonuts @24d9da8 | cdk 0.18.2 | nutshell 0.21.0 |
|---|---|---|---|
| checkstate/empty `{"Ys":[]}` | **connection closed, no HTTP response** (crash-class; cf. STREAM-STALL #32) | 400 `50000` `Empty IN clause for placeholder: ys` | **200, empty states** |
| GET /v1/keys/{unknown 66-hex} | 400 `12001` unknown keyset | 400 **no code** (`Invalid URL: NUT02: ID length invalid…`) | 400 `12001` keyset not found |
| swap oversized `B_` (64B hex) | 400 `10001` invalid proof | **422 deserialize-layer** | 400 `10001` proofs could not be verified |
| melt/quote unsupported unit | 400 `11013` | **400 `50000` Invalid payment method** | 400 **code 0** `'xxx'` |

New divergence notes (owner-gated registry candidates):
- **gonuts empty-`Ys` connection-close** is a liveness class (no
  response at all) — distinct from cdk's clean 400 and nutshell's
  permissive 200-empty; three-way split on a spec-underspecified edge.
- cdk emits **no `code`** on `/v1/keys/{id}` URL-level rejections
  (detail string only) — the NUT-00 envelope {code,detail} is not
  maintained on that path.
- melt-quote unit-unsupported: gonuts 11013 (spec-aligned) vs cdk
  50000 (unspec'd catch-all) vs nutshell code-0 — same fork shape as
  P09 but on the melt side; cashu-cf row TBD (needs the testnut leg).

### Addendum 2 (2026-11-07 evening): melt-quote-unit cf cell + the ⚠️ keyset-state rows measured

- **melt-quote/unsupported-unit — four-way, no two alike**: gonuts
  `11013` (spec) / cdk `50000` / nutshell `code 0` / **cashu-cf
  (testnut, Nutshell-CF/0.0.1) `400 14005` "Only sat and usd units
  are supported"**. Same fork shape as P09 on the melt side; garbage
  invoice re-confirmed `14005` (matches P14).
- **12002 inactive-keyset output — CONVERGENT row**: cdk 0.18.2
  `400 12002 "Inactive Keyset"` · nutshell 0.21.0 `400 12002
  "keyset is inactive, cannot sign messages"` · gonuts@24d9da8
  `400 12002 "requested signature from inactive keyset"` (staged via
  `mint-cli rotatekeyset`, admin socket). All three spec-aligned with
  distinct detail strings.
- **12003 expired-keyset — three-way split, one structural absence**:
  cdk `400 12003 "Keyset has expired"` (spec-aligned) · nutshell
  **`200` — signs; no expiry enforcement** (wire-confirmed Oct-2026
  finding) · **gonuts: structurally N/A** — no `ExpiredKeyset` code /
  no `final_expiry` concept anywhere in `cashu/cashu.go` · cashu-cf:
  not constructible today (no keyset in testnut `/v1/keysets` carries
  `final_expiry`; all null). Raw rows:
  `private/error-identity/rows-addendum2.json`.
