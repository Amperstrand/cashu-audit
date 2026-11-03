# nutshell 0.22.0 — NUT-impact digest

Released: 2026-11-02 · range `0.21.0..0.22.0` · 120 commits · generated 2026-11-03 by `tools/release_digest.py`
Maps to arms: nutshell 0.20.3/0.21.0 (conformance-v2 arms)

## NUTs touched → tracker cards to re-check

| NUT | commits touching it |
|---|---|
| NUT-18 | 18f5acb, 1b71252, d7ad270, fd9603c |
| NUT-26 | 18f5acb, d7ad270, fd9603c |
| NUT-28 | a2656a6, f2f2b43 |

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `cashu/mint/ledger.py` | 13 |
| `cashu/core/models` | 11 |
| `cashu/core/base.py` | 10 |
| `cashu/wallet/cli` | 9 |
| `tests/wallet/test_wallet_cli.py` | 8 |
| `cashu/lightning/lnd_grpc` | 7 |
| `tests/mint/test_mint_melt.py` | 7 |
| `tests/mint/test_mint_app_router.py` | 7 |
| `tests/helpers.py` | 6 |
| `tests/lightning/test_lightning_backends_mocked.py` | 6 |
| `cashu/lightning/lndrest.py` | 6 |
| `README.md` | 5 |

## Commit subjects (newest first)

- `9bfc2e9` 2026-03-27 fix(mint): graceful shutdown of background tasks and db connections
- `833560d` 2026-03-27 feat(mint): add cleanup method to LightningBackend abstract class
- `c88f8c6` 2026-04-09 fix(mint): clean up background tasks in FakeWallet to prevent CI hangs
- `350fc05` 2026-09-11 test(mint): pin absent-witness error code and message
- `faf79ca` 2026-09-11 fix(mint): distinguish unparsable witness from absent witness
- `2d9e688` 2026-09-11 refactor(mint): raise on an unparsable witness instead of flagging it
- `aa6bec9` 2026-09-16 fix(mint): catch backend errors during startup status check (#1124)
- `3e2b7d1` 2026-09-16 fix(wallet): accept legacy melt quote responses (#1160)
- `ca2bf38` 2026-09-16 fix(packaging): validate clean installs before publishing (#1161)
- `f3228df` 2026-09-16 chore: update dependencies (#1162)
- `fd9603c` 2026-09-17 test(wallet): consolidate CLI tests
- `b5146cb` 2026-09-17 Merge pull request #1130 from KvngMikey/fix/unparsable-witness-error
- `2a47ca1` 2026-09-17 Merge pull request #1163 from cashubtc/test/consolidate-wallet-cli-tests
- `fd371f5` 2026-09-17 chore: run lnd self-payment test in regtest CI
- `1233aa1` 2026-09-17 chore: move and repair mint watchdog tests
- `129a3c1` 2026-09-18 feat(lightning): probe LND routing fees
- `2f3a6b7` 2026-09-18 fix(lightning): prefer successful LND fee probes
- `49db753` 2026-09-18 fix(lightning): enforce LND fee probe deadline
- `13a951a` 2026-09-18 fix(lightning): buffer probed LND fee quotes
- `6c5e1d4` 2026-09-18 test(lightning): accommodate probed LND fee reserves
- `9f3704f` 2026-09-19 fix(mint): refuse the .env.example placeholder as a seed
- `1c682a8` 2026-09-20 fix(wallet): require boolean true for advertised NUT support
- `a453386` 2026-09-21 fix(tests): isolate settings subprocess from mutmut stats
- `6133ce2` 2026-09-21 fix(tests): isolate witness migration database per run
- `e589f63` 2026-09-21 fix(tests): isolate named wallet databases per invocation
- `de65038` 2026-09-21 fix(ci): continue mutation runs with reported baseline exclusions
- `6360b9b` 2026-09-21 fix(tests): parse wallet CLI payloads from stdout
- `e107c6d` 2026-09-21 feat(mint): enforce keyset redemption balances
- `0b7e752` 2026-09-22 test: clarify mutation runner fixtures and separate report coverage
- `8f33961` 2026-09-22 test: remove mutation tooling test modules
- `92fce71` 2026-09-22 fix(tests): retry Postgres schema reset on deadlock (#1159)
- `e9dd82a` 2026-09-22 Merge pull request #1172 from KvngMikey/fix/strict-boolean-nut-support
- `ae7b9ae` 2026-09-23 Merge pull request #1169 from btcforplebs/fix/reject-placeholder-seed
- `875adce` 2026-09-23 Merge pull request #1095 from a1denvalu3/feat/lnd-route-fee-estimation
- `ce1adcf` 2026-09-23 Merge pull request #1176 from cashubtc/feat/keyset-balance-enforcement
- `6ef7717` 2026-09-24 Merge pull request #1164 from orangeshyguy21/lnd-self-payment-test
- `82ae218` 2026-09-24 Merge pull request #1165 from orangeshyguy21/watchdog-regtest-coverage
- `c32cb38` 2026-09-24 Merge pull request #1174 from cashubtc/fix/mutation-settings-subprocess
- `5f1ed7a` 2026-09-28 docs: add responsible disclosure guidance for agents
- `33a0ea1` 2026-09-29 fix(ci): isolate and resume sharded mutation profiles
- `4ee43d7` 2026-09-30 feat(fakewallet): choose the payment outcome per invoice
- `4af8688` 2026-10-02 fix(ci): invalidate mutation caches on test configuration changes
- `e688266` 2026-10-03 fix(mint): return null for unlocked quote pubkeys
- `c7d9ace` 2026-10-03 fix: enforce protocol string limits and clean up legacy witnesses
- `21259e4` 2026-10-03 refactor: use Pydantic constraints for proof secrets
- `ad80a7e` 2026-10-05 Merge pull request #1194 from a1denvalu3/fix/mint-quote-null-pubkey
- `beb827c` 2026-10-05 fix: remove witness cleanup changes from string limit patch
- `94c547d` 2026-10-05 fix(mint): validate proof secrets only on incoming requests
- `e59e022` 2026-10-05 refactor(mint): simplify incoming secret length validation
- `c66faa2` 2026-10-07 fix: keep keyset seeds encrypted at rest
- `78157da` 2026-10-08 Merge pull request #1188 from cashubtc/fix/mutation-profile-reliability
- `a9c3e20` 2026-10-08 docs(tests): clarify fake invoice signing key comment
- `751c2c5` 2026-10-08 fix(mint): omit unset pubkey in mint quote responses
- `7a8258a` 2026-10-08 Merge pull request #1190 from robwoodgate/feat/fakewallet-invoice-states
- `e062b16` 2026-10-08 chore: remove plaintext seeds beside ciphertext
- `462446d` 2026-10-09 Merge pull request #1195 from a1denvalu3/fix/bound-protocol-strings
- `33128c9` 2026-10-09 fix(mint): stop using hardcoded auth ledger seed (#1187)
- `2f82453` 2026-10-09 chore: test wallet against released mints (#1184)
- `f2f2b43` 2026-10-09 fix(p2bk): refuse a slot index outside one byte (#1204)
- `ad607fa` 2026-10-09 test(wallet): add multimint transfer coverage (#1196)
- `f96b919` 2026-10-09 fix(mint): downgrade CashuError log level to info (#1191)
- `e5500d9` 2026-10-12 fix(wallet): preserve mixed-mint V3 tokens during decoding
- `9bd6078` 2026-10-13 fix: make encrypt migrate save encrypted seeds
- `d99acd8` 2026-10-14 Merge pull request #1182 from cashubtc/docs/responsible-disclosure-guidance
- `cd89cd5` 2026-10-14 Merge pull request #1210 from KvngMikey/fix/wallet-multimint-decoder
- `63d4a11` 2026-10-14 Merge pull request #1202 from orangeshyguy21/secure-seeds
- `cb330c4` 2026-10-14 Merge pull request #1212 from orangeshyguy21/fix-encrypt-script
- `d9c2fe8` 2026-10-15 refactor(auth): remove unused ledger CRUD duplication
- `2ba2c98` 2026-10-15 Merge pull request #1173 from KvngMikey/fix/auth-ledger-crud-m1
- `a2656a6` 2026-10-16 test(nut28): pin the NUT-28 HTLC example proof and V4 token vectors (#1214)
- `29d30b7` 2026-10-21 Merge pull request #1205 from cashubtc/fix/mint-quote-omit-empty-pubkey
- `b394377` 2026-10-21 fix(mint): resolve shutdown conflicts and support backend restarts
- `7a5a7ce` 2026-10-21 fix(mint): use request path consistently in auth middleware (#1215)
- `ac1c2e0` 2026-10-21 docs: add a pull request template (#1223)
- `8f1f0a5` 2026-10-21 fix(mint): include payment and event tasks in shutdown
- `e3cf93a` 2026-10-24 fix(deps): restore installs with breez-sdk-spark 0.21.1 (#1229)
- `d7ad270` 2026-10-25 feat(wallet): support NUT-18 and NUT-26 payment request updates
- `18f5acb` 2026-10-25 fix(wallet): harden NUT-18 and NUT-26 payment requests
- `1b71252` 2026-10-25 refactor(core): separate payment request fees from mint capabilities
- `d6bb098` 2026-10-26 chore(tests): cover payment request creation and payment behavior
- `f44e732` 2026-10-26 test(mint): guard payment request value after input fees
- `e7af367` 2026-10-26 fix(wallet): validate payment request mint candidates
- `c15cba5` 2026-10-26 fix(tests): await melt task cleanup callbacks
- `0c677e0` 2026-10-26 fix: address highlighted mutation survivors
- `a391c0a` 2026-10-26 fix: use backend-normalized mint quote amounts
- `e3c611b` 2026-10-26 chore: sync main to restore package installs
- `836c738` 2026-10-26 fix(wallet): enforce payment request value after input fees
- `9b46063` 2026-10-26 ci: cancel superseded PR runs
- `26a0328` 2026-10-26 fix(ci): preserve every main branch run
- `d80539b` 2026-10-26 Merge pull request #1236 from robwoodgate/ci/cancel-superseded-pr-runs
- `7126dd4` 2026-10-27 Merge pull request #954 from cashubtc/fix-mint-shutdown-hang
- `4d81a2f` 2026-10-27 feat(mint): add in-memory response caching
- `92e5ff1` 2026-10-27 test(mint): use regtest invoices for cached melt replay
- `9a2530d` 2026-10-28 docs(mint): move response caching details into docs
- `0a613a9` 2026-10-28 check for inactive keyset only in _verify_outputs
- `65072c8` 2026-10-28 restore it
- `970309d` 2026-10-28 Merge pull request #1059 from KvngMikey/payment_request_update
- `8419a2a` 2026-10-28 fix(mint): honor accepted outputs after keyset rotation
- `a29aac3` 2026-10-28 feat: support a BIP39 mnemonic as the mint seed (#1222)
- `420841f` 2026-10-28 test(mint): cover auth output keyset rotation
- `723a895` 2026-10-28 fix: mask database URLs in startup log
- `076d4fe` 2026-10-28 Merge pull request #1226 from orangeshyguy21/mask-db-urls
- `e965af3` 2026-10-28 Merge pull request #1237 from cashubtc/fix/in-memory-response-cache-1235
- `569b5f6` 2026-10-29 fix(mint): reject expired LND invoices without stranding proofs
- `a6f7e4f` 2026-10-29 test(mint): refresh invoice in Redis cache regression
- `9c17548` 2026-10-29 test(mint): fix LND expiry regtest fixtures and waits
- `b96b0de` 2026-10-29 test(mint): validate pending melt fixtures with both LND backends
- `208a67c` 2026-10-29 refactor(mint): validate payment requests at quote creation
- `14d4278` 2026-10-29 fix(tests): reconcile payment fixtures with main
- `0483af8` 2026-10-29 fix(tests): xfail normalized quote test below minimum mint
- `60d8d3c` 2026-10-29 Merge pull request #1186 from cashubtc/fix/melt-invoice-expiry
- `dc089e5` 2026-10-29 Merge pull request #1231 from cashubtc/fix/mint-spark-msat-rounding
- `4546ea9` 2026-10-29 fix(mint): cache batch mint endpoint responses
- `b768cec` 2026-10-29 test(mint): consolidate coverage for all cached endpoints
- `dc0b700` 2026-10-29 Merge pull request #1243 from cashubtc/fix/batch-mint-response-cache
- `b613236` 2026-10-30 Merge pull request #1234 from cashubtc/fix/mutation-survivors-1228
- `8133cbf` 2026-11-02 test(mint): move keyset rotation tests into test_mint_keysets
- `c7a07ce` 2026-11-02 Merge pull request #1241 from cashubtc/fix/check-keyset-active-on-verification
- `f1d5b05` 2026-11-02 chore(spark): update payment lifecycle handling (#1248)
- `968c687` 2026-11-02 chore(mint): update payment lifecycle handling (#1247)

## Release notes (verbatim)

_source: https://github.com/cashubtc/nutshell/releases/tag/0.22.0_

# Nutshell 0.22.0

> [!CAUTION]
>
> This release includes database migrations for the mint. Back up your databases and stop all older mint workers before upgrading.
>
> Spark operators should reconcile existing pending payments before upgrading.

Nutshell 0.22.0 brings BIP-39 mint seeds, updated payment requests, response caching without Redis, improved Lightning payment handling, and security fixes.

### Compatibility Notes

- **Mint seeds:** `MINT_PRIVATE_KEY` is deprecated but remains supported. Existing mints can set `MINT_MNEMONIC` and transition each unit through an explicit `next-keyset` rotation. Setting the mnemonic does not rotate existing keysets automatically. Back up the mnemonic securely and keep it configured once mnemonic-derived keysets exist.
- **Seed encryption:** operators using legacy keysets with `MINT_SEED_DECRYPTION_KEY` should re-run `poetry run python -m cashu.mint.encrypt migrate --no-dry-run` after upgrading.
- **Python installation:** Python 3.12 is recommended for pip and pipx installations to avoid current Coincurve build issues on Python 3.13/3.14.

## Notable Changes

### Mint

- **BIP-39 mint seeds:** support for `MINT_MNEMONIC`, with CDK-compatible key derivation and validation at startup.
- **NUT-19 response caching:** successful mint, batch mint, swap, and melt responses are cached in memory by default. Redis remains available for shared caching across workers and instances.
- **LND routing fees:** REST and gRPC backends now probe route fees when creating full-invoice melt quotes, with a fallback to the configured fee reserve.
- **Payment handling:** improved melt execution, recovery across workers, and management tooling, plus graceful shutdown of background tasks and backend connections.
- **Invoice validation:** earlier rejection of expired LND invoices and improved handling of backend-normalized quote amounts, including Spark’s fractional-satoshi rounding.
- **Keyset rotation:** requests with already-accepted outputs continue correctly through a rotation.
- **Spark:** updated SDK integration and payment lifecycle handling.
- **Security:** fixes and hardening across mint accounting, authentication, seed handling, logging, and request validation.

### Wallet

- **NUT-18/26 payment requests:** updated support for preferred mints, supported payment methods, and method fees.
- **`cashu request`:** create payment requests from the CLI, including optional NUT-26 bech32m encoding.
- **Payment selection and fees:** select a funded, compatible mint and account for input fees so the recipient receives the requested value.
- **Multi-mint tokens:** preserve mixed-mint V3 tokens during decoding.
- **Mint compatibility:** accept older melt quote responses that omit `method`, and use the returned quote amount when minting and transferring between mints.

### Other

- Added clean-install validation before package publishing and updated dependencies.
- Expanded wallet compatibility, multi-mint, payment lifecycle, and mutation test coverage.
- Added configurable per-invoice payment outcomes to FakeWallet.

## New Contributors

- @btcforplebs in [#1169](https://github.com/cashubtc/nutshell/pull/1169)
- @ifuensan in [#1191](https://github.com/cashubtc/nutshell/pull/1191)

[Full Changelog](https://github.com/cashubtc/nutshell/compare/0.21.0...0.22.0)
