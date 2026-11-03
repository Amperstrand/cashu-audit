# Shadow-matrix regen — gonuts arm current (2026-11-04)

Audit #68 item C. The locked three-way matrix
(`experiments/shadow-proxy-nutshell/README.md`, evidence 2026-10-22..24)
was re-run with the **gonuts arm at v0.16.0** — the tag that carries the
#59 fix train (melt/mint CAS, SIG_ALL spec alignment on P2PK+HTLC, NUT-19
melt replay, quote hygiene). Instrument: the same reusable runner
(`tools/cashu-shadow`), same corpus, plus a supplementary A4 probe for the
SIG_ALL **rejection** cell (the corpus only carries the unlock row).

**Headline: the SIG_ALL row is green everywhere.** Unlock = PAID on all
four arms (canonical message `concat(secret_i‖C_i) ‖ quoteId`, schnorr
over sha256); rejection = enforced on all four arms for genuinely-wrong
messages. The v0.15.0 gonuts failure family ("not enough valid
signatures" on every SIG_ALL melt, 2026-10-28 run's 28-failure grade B)
is closed on the wire.

## Arms (identity verified before any result was trusted, #40 rule)

| Arm | Identity (`/v1/info`) | Provenance | Port |
|---|---|---|---|
| gonuts v0.16.0 | `gonuts/0.4.0` | local build, `/root/src/gonuts-fix` @ `d0fd3b0` (zero content diff vs tag `v0.16.0` = commit `e3dfc63`), cmd/mint, FAKEBACKEND, INPUT_FEE_PPK=0 | 4470 |
| cashu-cf | `Nutshell-CF/0.0.1`¹ | miniflare bundle built 2026-11-04 00:26 from `/root/src/cashu-cf` @ `6cd249e` (clean tree; same bundle shape verified 12/12 by the item-A session) | in-proc |
| nutshell 0.20.3 | `Nutshell/0.20.3` | docker `cashubtc/nutshell:0.20.3`, FakeWallet, `--network host` | 4472 |
| cdk 0.18.1 | `cdk-mintd/0.18.1` | docker `cashubtc/mintd:0.18.1`, fakewallet, `--network host`, fresh workdir + `config init` | 4474 |

¹ cashu-cf's local build reports the same version string shape as
deployed testnut; its provenance is by build, not by a distinct version
field. The A4 probe asserts the other three arms' `/v1/info` strings
before probing and aborts on mismatch.

Runs: `tools/cashu-shadow/out/shadow-2026-11-03T23-48-10-386Z.*`
(cf↔gonuts), `…23-48-30-252Z.*` (cf↔ns), `…23-49-05-348Z.*` (cf↔cdk),
`out/sigall-a4-rejection-2026-11-03T23-50-32-233Z.json` (A4, 3 wrong-
message variants × 4 arms). Configs: `config.cf-gonuts.json`,
`config.cf-ns-regen.json`, `config.cf-cdk-regen.json`; probe:
`sigall-a4-reject.mjs`.

## Regenerated four-way matrix

| # | Scenario | cashu-cf | nutshell 0.20.3 | cdk 0.18.1 | **gonuts v0.16.0** |
|---|---|---|---|---|---|
| R4 keys/{bogus} | 400 `not_found` | 400 **12001** | 400 (bare) | 400 **12001** | ✅ 400/12001 `unknown keyset` |
| R5 checkstate malformed-Y | 200 UNSPENT | 200 UNSPENT | 422 (strict outlier) | ✅ 200 UNSPENT |
| H1 mint + DLEQ verify | 200 `true` | 200 `true` | 200 `true` | ✅ **200 `true`** |
| A1 swap forged off-curve C | 400/14005 | 400/10001 | 400/10001 | ⚠️ 400/**10003** `invalid proof`² |
| A2 swap duplicate proof | 400/14008 | 400/11007 | 400/11007 | ⚠️ 400/**11007** (≡ ns/cdk code) |
| A3 swap P2PK witness-less | 403/30006 | 400/code 0 | 400/20008 | ⚠️ 400/**30001** `invalid witness`³ |
| A6b mint replay same-outputs | 200 + identical sig | 400/11003 | 200 + identical sig | ✅ **200 + byte-identical sigs** |
| A7 fee-aware swap → SPENT | 200 (ppk 0) | 200 (ppk 100) | 200 (ppk 0) | ✅ 200 SPENT (ppk 0) |
| A8 happy melt | PAID | PAID | PAID | ✅ PAID |
| A8 HTLC unlock | PAID | PAID | PAID | ✅ PAID |
| **SIG_ALL unlock (canonical)** | PAID | PAID | PAID | ✅ **PAID** |
| **A4 SIG_ALL rejection** (garbage suffix / quote-first) | 403/30006 `no candidate message verified` | 400/11000 `signature threshold not met` | 400/20008 | ✅ **400/30001 `not enough valid signatures`** |

² parseable-but-wrong point → 10003 (unparseable → 10000) — the known
gonuts payload-dependent pair; spec says 10001. See
FINDINGS-2026-11-04-error-identity P07.
³ gonuts' NUT-11 witness-fail code — the triple-booked 30001 (gonuts
witness-fail ≠ spec clear-auth ≠ cashu-cf token-spent), same doc P12.

Reference-arm drift: **NONE** — every cf/ns/cdk cell above reproduces the
locked 2026-10-22..24 table byte-for-byte on status+code+detail-shape.

## Verdicts and catalogue deltas

1. **SIG_ALL green everywhere (the item-C acceptance question).**
   Rejection ✓ ×4, unlock ✓ ×4. Error identities still fork four ways
   (30006 / 11000 / 20008 / 30001) — consistent with the error-identity
   matrix; the *behavior* is now uniform even where the codes are not.
2. **A6b forks 3-vs-1**: gonuts replay-caches the mint with
   byte-identical signatures, joining cashu-cf + cdk; nutshell alone
   rejects (400/11003). Extends the F1 registry row to a fourth arm.
3. **H1 DLEQ: gonuts v0.16.0 emits NUT-12 DLEQ that verifies via
   cashu-ts `verifyDLEQProof`** — wire-measured here for the first time
   (the locked matrix never had a gonuts H1 cell; #68 B(3) asked). Not
   yet checked: DLEQ on *every* denomination / under swap re-signing —
   single-denomination evidence only.
4. **R4 converges on status**: all four answer 400; gonuts' code 12001
   matches nutshell exactly.
5. **cf legacy-lenience, wire-captured on the melt path**: a SIG_ALL
   witness over the legacy pre-0.20.3 message (no quoteId) **SPENDS on
   cashu-cf (200)** while ns/cdk/gonuts all reject it. This is the
   documented deliberate compat window (UPSTREAM-AUDIT 2026-10 §3.22,
   "10 encodings / 3 sort orders") — first wire capture of the legacy
   form succeeding on a *melt*, and a durable interop datum: a wallet
   emitting legacy messages can silently spend against cf but not
   against the other three.

## What was and wasn't verified

- **Wire-verified**: every cell above is a live response from this
  run; captures listed above (identities stamped in the A4 JSON; corpus
  identities verified at bring-up against the same processes, no
  restarts between).
- **Not re-run**: nutshell 0.21.0 arm (locked version-matrix rows
  already establish 0.20.3 ≡ 0.21.0 on this corpus, and item A
  re-verified the 0.21.0 error rows yesterday); cdk 0.18.2/0.18.3
  (item A verified 0.18.1 ≡ 0.18.2 ≡ 0.18.3 on its rows).
- **Single-run**: each pair ran once; the cf arm appeared in all three
  runs and reproduced identically (an internal consistency check).

## Rig notes for whoever runs next

- **`setup-nutshell.sh` venv lane is broken**: `/tmp/nutshell-src` has
  drifted to main (`7126dd4`, post-0.21.0) and lost its local
  workarounds (breez-sdk-spark back in pyproject, unguarded sparkl2
  import) — the script's `[ ! -d "$SRC/.git" ]` skip-condition silently
  reuses the mutated checkout and dies on
  `ModuleNotFoundError: breez_sdk_spark`. Docker `cashubtc/nutshell:0.20.3`
  with `--network host` is the working bring-up (used here).
- gonuts cmd/mint needs a `.env` in CWD (else log.Fatal) and a
  `MINT_PORT` override (default 3338 — someone else's port).
- Ports 4470/4472/4474 used and torn down after this run; docker
  containers `shadow-ns0203` / `shadow-cdk0181` + workdir
  `~/ab-matrix/shadow-cdk0181` removed.
