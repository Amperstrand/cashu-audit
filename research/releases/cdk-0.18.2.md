# cdk 0.18.2 — NUT-impact digest

Released: 2026-10-13 · range `v0.18.1..v0.18.2` · 15 commits · generated 2026-10-24 by `tools/release_digest.py`
Maps to arms: cdk 0.18.x

## NUTs touched → tracker cards to re-check

| NUT | commits touching it |
|---|---|
| NUT-02 | bf8bd20f |
| NUT-20 | 322fe0b0 |

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `crates/cdk/src` | 7 |
| `crates/cdk-ffi/src` | 5 |
| `crates/cdk-mintd/src` | 4 |
| `Cargo.lock` | 3 |
| `crates/cdk-lnd/src` | 3 |
| `crates/cdk-bdk/src` | 3 |
| `Cargo.lock.msrv` | 2 |
| `Cargo.toml` | 2 |
| `crates/cashu/src` | 2 |
| `crates/cdk-cli/src` | 2 |
| `crates/cdk/Cargo.toml` | 2 |
| `docs/migrations/v0.18.md` | 2 |

## Commit subjects (newest first)

- `35a98119` 2026-09-18 fix(ci): keep mintd:latest on the newest stable release
- `3c1afc0d` 2026-09-21 Merge pull request #2577 from thesimplekid/backport-2562-to-v0.18.x
- `dc96d78e` 2026-10-05 chore(deps): refresh workspace dependencies
- `ef2f08bc` 2026-10-06 fix(bdk): migrate to caller-owned signers for BDK 3.2
- `cd199200` 2026-10-06 fix: return persisted wallet quote state after status checks
- `ce19a35a` 2026-10-07 fix(cdk-bdk): log ignored receive outputs only once
- `58096329` 2026-10-08 fix(lnd): validate full payment amounts before dispatch
- `012b0b0a` 2026-10-08 fix(lnd): validate MPP amounts and handle route query failures
- `daa331c0` 2026-10-08 Merge pull request #2673 from thesimplekid/backport-2660-2661-to-v0.18.x
- `45f34a86` 2026-10-09 fix(lnd): round satoshi payment quotes up
- `27cdbd1f` 2026-10-09 fix(mintd): allow legacy metadata pubkeys during config import
- `bf8bd20f` 2026-10-09 fix(mintd): verify historical Nutshell keysets during import
- `3b9ba060` 2026-10-09 test(mintd): supply SQLCipher password in legacy import test
- `322fe0b0` 2026-10-13 feat(wallet): recover mint quote signing keys from seed
- `9f6d3a37` 2026-10-13 chore(release): bump CDK to 0.18.2

## Release notes (verbatim)

_source: https://github.com/cashubtc/cdk/releases/tag/v0.18.2_

## [0.18.2](https://github.com/cashubtc/cdk/releases/tag/v0.18.2)

### Summary

Version 0.18.2 adds seed-based recovery of signing keys for known mint quotes and fixes persisted wallet quote state, LND payment validation and rounding, and legacy mint configuration imports. It also updates dependencies and improves BDK signing and receive logging.
Operators upgrading from v0.17 must still follow the [v0.18 migration guide](docs/migrations/v0.18.md).

### Compatibility Notes

- cdk/cdk-common: **BREAKING for custom wallet trait implementations** - The `Wallet` trait requires `fetch_mint_quote_with_key_search`; downstream implementations must add this method ([thesimplekid]).
- cdk-mintd/cashu: Historical Nutshell BIP32 keysets with IDs containing an explicit zero expiry can be imported while preserving their original IDs and signing keys. This does not change wallet verification: CDK wallets still reject these noncanonical legacy IDs. Preserve the original raw seed and derivation paths when importing; see the migration guide for details ([thesimplekid]).

### Added

- cdk/cdk-ffi: `fetch_mint_quote_with_key_search` recovers a known quote's NUT-20 signing key from the original wallet seed within a caller-specified search limit. Matching keys are stored and the derivation counter advances past the recovered index; existing keys are preserved, NpubCash quotes are skipped, and unsuccessful searches can be retried with a larger limit. Plain `fetch_mint_quote` does not search ([thesimplekid]).
- cashu: `derive_quote_locking_keys` derives a range of NUT-20 quote keys from a shared parent ([thesimplekid]).
- cdk-cli: `mint --quote-id` fetches the quote and searches for its signing key with `--key-search-limit` (default 1,000), allowing restored wallets to claim unissued funds using a known quote ID and the original seed. A `restore-mint-quote` SDK example documents the same workflow ([thesimplekid]).

### Changed

- workspace: Refreshed stable and MSRV dependency lockfiles, including security fixes, and raised the rust-lightning requirement to 0.2.7 ([thesimplekid]).
- cdk-bdk: Requires BDK wallet 3.2 and uses caller-owned signers for both external and change inputs, reconstructing both signers when reloading the wallet ([thesimplekid]).

### Fixed

- cdk: Mint and melt quote status checks return persisted database state, including current versions, ownership, accounting, and retained payment proofs. Recovery reloads quotes before applying updates so stale snapshots do not overwrite recovery changes (#2639) ([asmo]/[thesimplekid]).
- cdk: Mint quote fetches and status checks reject mismatched response quote IDs. Batch status checks validate response counts and ordered IDs before updating any local quote ([asmo]/[thesimplekid]).
- cdk-cli: Minting failures propagate to the caller when claiming quotes ([thesimplekid]).
- cdk-lnd: Amountless BOLT11 quotes and payments require a positive amount; explicit amounts must match fixed-amount invoices, and dispatch lets LND read fixed amounts from the invoice (#2660) ([thesimplekid]).
- cdk-lnd: MPP payments require an invoice total and a positive shard no larger than that total, with checked amount and fee-limit conversions. Route-query failures before the first send return an authoritative failure; failures after a send remain ambiguous for recovery (#2661) ([thesimplekid]).
- cdk-lnd: Sat-denominated BOLT11 quotes round the millisatoshi principal up for fixed, MPP, and amountless payments ([thesimplekid]).
- cdk-bdk: Ignored receive outputs are logged at TRACE instead of DEBUG, reducing noise during repeated scans ([thesimplekid]).
- cdk-mintd: Existing-mint imports accept legacy metadata pubkeys unrelated to the signing seed. Embedded signers are verified against recorded historical keysets; remote signers are checked against historical IDs, including issuance and redemption records, with a stored-pubkey fallback when no history exists. Later configuration updat
