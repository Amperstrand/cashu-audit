# cdk 0.17.7 — NUT-impact digest

Released: 2026-09-16 · range `v0.17.6..v0.17.7` · 8 commits · generated 2026-10-26 by `tools/release_digest.py`
Maps to arms: cdk 0.18.x

## NUTs touched → tracker cards to re-check

_(no NUT-referencing commits or nut-named paths in range)_

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `crates/cdk/src` | 2 |
| `justfile` | 2 |
| `CHANGELOG.md` | 1 |
| `Cargo.lock` | 1 |
| `Cargo.lock.msrv` | 1 |
| `Cargo.toml` | 1 |
| `bindings/kotlin/gradle.properties` | 1 |
| `crates/cdk-integration-tests/tests` | 1 |
| `crates/cdk-lnd/src` | 1 |
| `bindings/README.md` | 1 |

## Commit subjects (newest first)

- `7488fd92` 2026-09-08 fix(ffi): run release workflows from the release tag
- `bf4c3b13` 2026-09-08 fix(release): check release tags on upstream
- `46abf27a` 2026-09-10 fix(lnd): reject expired invoices before payment dispatch
- `fefa1422` 2026-09-13 test(mint): fix pending payment expectations in fake wallet tests
- `40399860` 2026-09-13 fix(mint): bound payment status checks during recovery
- `55d5372c` 2026-09-15 Merge pull request #2524 from thesimplekid/backport-2504-to-v0.17.x
- `e981acaa` 2026-09-16 chore: bump 0.17.7
- `4c511283` 2026-09-16 Merge pull request #2551 from thesimplekid/bump_0_17_7

## Release notes (verbatim)

_source: https://github.com/cashubtc/cdk/releases/tag/v0.17.7_

## [0.17.7](https://github.com/cashubtc/cdk/releases/tag/v0.17.7)

### Fixed

- cdk: Limit payment status checks during mint recovery to ten seconds, deferring timed-out sagas without releasing reserved proofs ([thesimplekid]).
- cdk-lnd: Reject expired Bolt11 invoices before payment dispatch as definitive failures, while preserving existing paid or pending payment results ([thesimplekid]).
- cdk-integration-tests: Correct fake-wallet tests to keep proofs pending for uncertain payment outcomes, use definitive failures for refund checks, and bound uncertain-payment cases to prevent hangs ([thesimplekid]).
- release: Run FFI release workflows from the release tag so backport releases use their matching workflow definitions ([thesimplekid]).
- release: Check for release tags on the upstream remote before publishing crates ([thesimplekid]).
