# cdk 0.18.3 — NUT-impact digest

Released: 2026-10-28 · range `v0.18.2..v0.18.3` · 6 commits · generated 2026-10-30 by `tools/release_digest.py`
Maps to arms: cdk 0.18.x

## NUTs touched → tracker cards to re-check

_(no NUT-referencing commits or nut-named paths in range)_

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `crates/cdk-sqlite/src` | 3 |
| `crates/cdk-sql-common/src` | 2 |
| `CHANGELOG.md` | 1 |
| `Cargo.lock` | 1 |
| `Cargo.lock.msrv` | 1 |
| `Cargo.toml` | 1 |
| `bindings/kotlin/gradle.properties` | 1 |
| `fuzz/Cargo.lock` | 1 |
| `crates/cdk-ffi/src` | 1 |

## Commit subjects (newest first)

- `1f17b045` 2026-10-19 Do not block when dropping an owned runtime from async context
- `39ebdf7f` 2026-10-21 Merge pull request #2731 from cashubtc/backport-2581-to-v0.18.x
- `f1cbc303` 2026-10-26 fix(sql): harden transaction cleanup
- `c64d253e` 2026-10-26 fix(sqlite): fail instead of replacing a lost in-memory database
- `d21f3304` 2026-10-27 Merge pull request #2769 from cashubtc/backport-2761-to-v0.18.x
- `b2035a35` 2026-10-28 chore: bump version to v0.18.3

## Release notes (verbatim)

_source: https://github.com/cashubtc/cdk/releases/tag/v0.18.3_

## [0.18.3](https://github.com/cashubtc/cdk/releases/tag/v0.18.3)

### Summary

Version 0.18.3 fixes FFI runtime teardown panics, hardens SQL transaction cleanup, and prevents lost SQLite in-memory databases from being silently replaced with empty databases.

### Fixed

- cdk-ffi: Dropping an owned Tokio runtime from an async context no longer panics during binding teardown. Drops from synchronous contexts retain graceful blocking shutdown (#2731).
- cdk-sql-common/cdk-sqlite: Transaction cleanup retains ownership of pooled connections until the transaction has ended and discards connections when cleanup fails, is cancelled, or times out. SQLite skips rollback when no transaction is active, preserving healthy connections (#2769).
- cdk-sqlite: Losing an in-memory database connection now causes subsequent operations to return a database error instead of silently opening a fresh, empty database (#2769) ([thesimplekid]).
