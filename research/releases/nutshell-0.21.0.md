# nutshell 0.21.0 — NUT-impact digest

Released: 2026-09-16 · range `0.20.3..0.21.0` · 63 commits · generated 2026-10-24 by `tools/release_digest.py`
Maps to arms: nutshell 0.20.3/0.21.0 (conformance-v2 arms)

## NUTs touched → tracker cards to re-check

| NUT | commits touching it |
|---|---|
| NUT-06 | 33cc52e |
| NUT-10 | 8e19619 |
| NUT-11 | 8e19619 |
| NUT-14 | 8e19619 |
| NUT-26 | 65c3de1 |
| NUT-29 | bffb901 |

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `cashu/core/models` | 12 |
| `cashu/mint/ledger.py` | 8 |
| `.github/workflows/regtest-mint.yml` | 7 |
| `.github/workflows/regtest-wallet.yml` | 6 |
| `tests/mint/test_mint_melt.py` | 6 |
| `cashu/mint/verification.py` | 6 |
| `CONTRIBUTING.md` | 5 |
| `tests/helpers.py` | 5 |
| `tests/lightning/test_lightning_backends_mocked.py` | 5 |
| `cashu/core/settings.py` | 5 |
| `cashu/lightning/lnd_grpc` | 5 |
| `cashu/lightning/lndrest.py` | 5 |

## Commit subjects (newest first)

- `94d7eca` 2026-07-18 fix(wallet): pass wallet name when constructing mint_wallet on receive paths
- `72e27ac` 2026-07-18 test(wallet): add regression tests for named-wallet P2PK receive
- `aa91d87` 2026-07-18 fix(wallet): derive mint_wallet db location from receiver wallet on receive paths
- `31789d2` 2026-07-27 chore: remove dead regtest tooling (#1098)
- `bffb901` 2026-07-28 test: use a uuid v7 quote id in the NUT-29 signature vector (#1099)
- `06b407e` 2026-07-29 refactor: use Method.bolt11 instead of "bolt11" string literals (#1066)
- `2c98c83` 2026-07-29 refactor: use JSONRPCSubscriptionKinds for subscription kind strings (#1066)
- `241dd22` 2026-08-02 add SECURITY.md (#1102)
- `65c3de1` 2026-08-03 refactor: use Unit.sat instead of sat string literals, Unit is an int-valued enum, so string contexts use Unit.sat.name, which evaluates to sat: no behavior or wire format changes.
- `2f260da` 2026-08-04 fix(mint): validate blinded output points
- `f2732ec` 2026-08-05 Merge pull request #1089 from KvngMikey/fix/receive-wallet-name
- `e6765b6` 2026-08-05 Merge pull request #1101 from KvngMikey/refactor/central-constants
- `e909c13` 2026-08-09 test(mint): update invalid blinded message error
- `7c7e56e` 2026-08-09 refactor(mint): extract blinded message validation
- `6691b1b` 2026-08-10 Merge pull request #1106 from a1denvalu3/fix/check-melt-output-points-validity
- `8e19619` 2026-08-11 fix a variety of issues with SIG_ALL and its interaction with P2PK and HTLC (#1008)
- `cf1cf76` 2026-08-11 Align protected routes and payment state handling (#1108)
- `8fc40b4` 2026-08-11 feat(lightning): add setting to allow LND self-payments  Closes #1092 (#1107)
- `0e896c0` 2026-08-11 Chore/retire deprecated code (#1086)
- `0ae760f` 2026-08-11 [Wallet] fix: handle unpaid invoices in the CLI invoice command (#1022)
- `cdb61ef` 2026-08-13 fix(lightning): improve error message for unsupported LND partial self-payments (#1113)
- `89b98bd` 2026-08-13 test: melt with real routing fees on regtest (#1103)
- `917bd11` 2026-08-13 feat(mint): advertise the maximum request array length
- `6948528` 2026-08-14 fix(wallet): send blank change outputs with amount 0 (#1118)
- `8562322` 2026-08-14 chore(lightning): remove Blink and LNbits backends (#1110)
- `e5ea0ca` 2026-08-14 feat: add scheduled mutation testing (#1094)
- `65a9ddd` 2026-08-14 refactor(mint): rename max_request_length to max_array_length
- `83655e5` 2026-08-16 fix(mint): return inactive keyset error code (#1120)
- `6eed7b2` 2026-08-16 fix(mint): enable balance watchdog with SIGTERM process shutdown (#1117)
- `3282be2` 2026-08-19 use cln xpay (#1127)
- `271e2ba` 2026-08-25 fix(ci): restore mutation testing reports
- `5535cc1` 2026-08-25 test(mint): isolate URL removal coverage
- `ba2e8a4` 2026-08-28 Merge pull request #1136 from cashubtc/fix/mutation-testing-workflows
- `33cc52e` 2026-09-01 Merge pull request #1115 from robwoodgate/feat/nut06-max-request-length
- `8849620` 2026-09-02 Fix: Standardize error codes (#1129)
- `25bcd76` 2026-09-03 fix(deps): bump breez-sdk-spark to ^0.17.0 to unbreak poetry install in CI
- `e3f766e` 2026-09-03 Merge pull request #1144 from KvngMikey/fix/breez-sdk-spark-lockfile
- `b30e931` 2026-09-03 fix(wallet): dispatch NPC already-issued check on 20002 not 11000
- `1b2c0cf` 2026-09-03 chore: enforce LF line endings
- `772b6e3` 2026-09-03 chore: configure pre-commit to fix line endings
- `11c9e30` 2026-09-03 Merge pull request #1141 from a1denvalu3/chore/enforce-lf-line-endings
- `3e19084` 2026-09-04 Merge pull request #1142 from KvngMikey/fix/npc-already-issued-error-code
- `ed157de` 2026-09-10 ci: pull prebuilt cashu-regtest-environment image instead of cloning and bootstrapping from source
- `16c1517` 2026-09-10 fix(ci): use current regtest images and clean up Compose stack
- `7e40d92` 2026-09-10 test: make routing fee rounding independent of path selection
- `672120a` 2026-09-10 ci: allow slower runners to finish mint regtests
- `4a8d8b7` 2026-09-11 chore(ci): remove regtest revision comments
- `84d85e5` 2026-09-11 Merge pull request #1148 from a1denvalu3/ci/pull-regtest-docker-image
- `7ecdf40` 2026-09-11 fix(mint): unblock mutation tests with RPC state cleanup
- `af2b64b` 2026-09-11 test(mint): hoist startup import
- `0a5a4d6` 2026-09-11 Merge pull request #1149 from cashubtc/fix/mutation-empty-url-list
- `5803469` 2026-09-11 fix(mint/auth): align auth promises schema with the mint CRUD
- `8629c1b` 2026-09-11 fix(mint/auth): drop no-op foreign key pragmas from m005
- `6e77e85` 2026-09-11 Merge pull request #1145 from KvngMikey/fix/auth-promises-schema
- `53b2a8c` 2026-09-11 fix(ci): run Keycloak auth integration tests
- `fbefa7d` 2026-09-11 chore(ci): remove redundant auth test report check
- `dbb4f96` 2026-09-15 Merge pull request #1150 from cashubtc/fix/keycloak-auth-ci
- `327566b` 2026-09-16 fix: use wallet name in wallets command (#1155)
- `66b643f` 2026-09-16 fix(lightning): preserve msat amounts in LND invoices (#1156)
- `05c312e` 2026-09-16 refactor(mint): align ledger execution and Lightning backend contracts (#1157)
- `ea627d9` 2026-09-16 fix(lightning): don't treat sub-satoshi rounding as a partial payment (#1153)
- `b3c3e1e` 2026-09-16 chore(release): bump version to 0.21.0 (#1158)
- `a974914` 2026-09-16 test(spark): run shared mint and wallet regtests (#1147)

## Release notes (verbatim)

_source: https://github.com/cashubtc/nutshell/releases/tag/0.21.0_

# Nutshell 0.21.0

> [!CAUTION]
>
> This release includes database migrations for the mint and mint authentication databases. Ensure you back up your databases before upgrading your Nutshell instance to avoid data loss.

Nutshell 0.21.0 brings security hardening, Lightning backend improvements, wallet fixes, and the retirement of deprecated integrations and APIs.

### Compatibility Notes

- **Removed Lightning backends:** `BlinkWallet`, `LNbitsWallet`, and the deprecated `CoreLightningRestWallet`. Operators using these must switch to a supported backend before upgrading. Core Lightning users should use `CLNRestWallet` with `xpay` available.
- **Removed legacy API support:** deprecated mint endpoints and wallet compatibility fallbacks for older mint responses have been retired. Integrations should use the current `/v1` API.

## Notable Changes

### Mint

- **LND self-payments:** optional support through `MINT_LND_ALLOW_SELF_PAYMENT`, disabled by default, for both REST and gRPC backends.
- **LND invoice compatibility:** fixes for millisatoshi invoice creation and sub-satoshi rounding, plus clearer errors for unsupported partial self-payments.
- **Core Lightning:** `CLNRestWallet` now uses `xpay` for outgoing payments.
- **NUT-06 request limits:** `/v1/info` now advertises `max_array_length`, allowing wallets to size requests before submitting them.
- **Standardized error codes:** aligned with the Cashu specifications, including error `12002` for inactive output keysets.
- **Spark:** updated the Breez SDK dependency.

### Wallet

- **Named wallets:** receiving tokens and listing wallets now consistently use the correct wallet name and database.
- **CLI invoice handling:** unpaid invoices are no longer reported as paid, and waiting for WebSocket payment notifications is bounded.
- **Lightning change:** blank change outputs now use amount `0` for NUT-08 compatibility.
- **npub.cash:** correctly recognizes already-issued quotes using the updated mint error code.

### Other

- Added scheduled mutation testing and expanded Lightning, Spark, mint, wallet, and authentication integration tests.
- Removed obsolete regtest tooling and standardized LF line endings.

## New Contributors

- @orangeshyguy21
- @SatsAndSports
- @Hardeezah

**Full Changelog**: https://github.com/cashubtc/nutshell/compare/0.20.3...0.21.0

## What's Changed
* chore: remove dead regtest tooling by @orangeshyguy21 in https://github.com/cashubtc/nutshell/pull/1098
* feat: update nut29 test vector with uuidv7 by @KvngMikey in https://github.com/cashubtc/nutshell/pull/1099
* add SECURITY.md by @callebtc in https://github.com/cashubtc/nutshell/pull/1102
* fix(wallet): pass wallet name when constructing mint_wallet on receive paths by @KvngMikey in https://github.com/cashubtc/nutshell/pull/1089
* Refactor: use central constants for method and subscription kind strings by @KvngMikey in https://github.com/cashubtc/nutshell/pull/1101
* fix(mint): validate blinded output points by @a1denvalu3 in https://github.com/cashubtc/nutshell/pull/1106
* fix a variety of issues with SIG_ALL and its interaction with P2PK and HTLC by @SatsAndSports in https://github.com/cashubtc/nutshell/pull/1008
* Align route and payment state handling by @a1denvalu3 in https://github.com/cashubtc/nutshell/pull/1108
* feat(lightning): add setting to allow LND self-payments  Closes #1092 by @Hardeezah in https://github.com/cashubtc/nutshell/pull/1107
* Chore/retire deprecated code by @callebtc in https://github.com/cashubtc/nutshell/pull/1086
* fix(wallet): handle unpaid invoices in the CLI invoice command by @edgarmuyomba in https://github.com/cashubtc/nutshell/pull/1022
* fix(lightning): improve error message for unsupported LND partial self-payments by @Hardeezah in https://github.com/cashubtc/nutshell/pull/1113
* test: melt with real routing fees on regtest by @orangeshyguy21 in https://github.com/cashubtc/nutshell/pull/1103
* fix(wallet): sen
