# cashu-ts 4.12.0 — NUT-impact digest

Released: 2026-10-20 · range `v4.11.0..v4.12.0` · 6 commits · generated 2026-10-26 by `tools/release_digest.py`
Maps to arms: cashu-ts 4.11.0 (v4-pool consumer corpus; 5.0.0-rc wallet-emission work)

## NUTs touched → tracker cards to re-check

| NUT | commits touching it |
|---|---|
| NUT-10 | 8545690b |
| NUT-11 | 8545690b |
| NUT-19 | a92acbc4 |

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `src/wallet/Wallet.ts` | 3 |
| `src/utils/core.ts` | 2 |
| `.release-please-manifest.json` | 1 |
| `CHANGELOG.md` | 1 |
| `package-lock.json` | 1 |
| `package.json` | 1 |
| `src/mint/Mint.ts` | 1 |
| `test/mint/Mint.node.test.ts` | 1 |
| `src/crypto/NUT10.ts` | 1 |
| `src/crypto/NUT11.ts` | 1 |
| `test/crypto/NUT11.test.ts` | 1 |
| `test/wallet/wallet-p2pk.node.test.ts` | 1 |

## Commit subjects (newest first)

- `a92acbc4` 2026-09-23 docs(fees): lead with prepare() for send cost, name the input fee in the shortfall message (#1259)
- `7a9590c9` 2026-09-25 feat(utils): add verifyMintSignatures ahead of v5, deprecate hasValidDleq (#1269)
- `9f1fa796` 2026-10-10 fix(core): validate text fields when decoding a v4 token (#1308)
- `8545690b` 2026-10-16 fix(nut11): read locktime 0 as an expired lock, expire only after locktime (#1324)
- `c3b01e27` 2026-10-16 fix(mint): log only the op when a melt quote check answers for another quote (#1327)
- `22c72f4e` 2026-10-20 chore(v4-dev): release 4.12.0 (#1270)

## Release notes (verbatim)

_source: https://github.com/cashubtc/cashu-ts/releases/tag/v4.12.0_

## What's Changed
* docs(fees): lead with prepare() for send cost, name the input fee in the shortfall message [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1259
* feat(utils): add verifyMintSignatures ahead of v5, deprecate hasValidDleq by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1269
* fix(core): validate text fields when decoding a v4 token [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1308
* fix(nut11): read locktime 0 as an expired lock, expire only after locktime [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1324
* fix(mint): log only the op when a melt quote check answers for another quote [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1327
* chore(v4-dev): release 4.12.0 by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1270


**Full Changelog**: https://github.com/cashubtc/cashu-ts/compare/v4.11.0...v4.12.0
