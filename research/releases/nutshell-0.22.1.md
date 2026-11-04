# nutshell 0.22.1 — NUT-impact digest

Released: 2026-11-03 · range `0.22.0..0.22.1` · 5 commits · generated 2026-11-04 by `tools/release_digest.py`
Maps to arms: nutshell 0.20.3/0.21.0 (conformance-v2 arms)

## NUTs touched → tracker cards to re-check

_(no NUT-referencing commits or nut-named paths in range)_

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `.github/workflows/docker.yaml` | 2 |
| `README.md` | 2 |
| `cashu/core/settings.py` | 2 |
| `pyproject.toml` | 2 |
| `tor/docker-compose.yaml` | 2 |
| `tests/mint/test_mint_init.py` | 1 |
| `tests/mint/test_mint_regtest.py` | 1 |

## Commit subjects (newest first)

- `d714184` 2026-11-03 test(mint): poll payment status by the attempt's checking id
- `76d3c8c` 2026-11-02 chore(release): bump version to 0.22.0
- `dc1cb03` 2026-11-03 Merge pull request #1249 from cashubtc/fix/spark-regtest-melt-status-poll
- `bbb524a` 2026-11-03 Merge pull request #1250 from cashubtc/release/0.22.0
- `3ab0137` 2026-11-03 chore(release): bump version to 0.22.1 (#1254)

## Release notes (verbatim)

_source: https://github.com/cashubtc/nutshell/releases/tag/0.22.1_

# Nutshell 0.22.1

We forgot to bump the version in the last release. Here are the release notes of 0.22.0 again.

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

[Full Changelog](https://github.com/cashubtc/nutshell/compare/0.21.0...0.22.1)
