# cashu-ts 4.13.1 — NUT-impact digest

Released: 2026-11-10 · range `v4.13.0..v4.13.1` · 19 commits · generated 2026-11-11 by `tools/release_digest.py`
Maps to arms: cashu-ts 4.11.0 (v4-pool consumer corpus; 5.0.0-rc wallet-emission work)

## NUTs touched → tracker cards to re-check

| NUT | commits touching it |
|---|---|
| NUT-10 | 8c97e525 |
| NUT-11 | 53306ce7, 8c97e525 |
| NUT-14 | 0254f1eb |

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `src/wallet/Wallet.ts` | 4 |
| `src/wallet/WalletEvents.ts` | 3 |
| `test/wallet/WalletEvents.test.ts` | 3 |
| `test/wallet/wallet-fees.node.test.ts` | 2 |
| `test/crypto/NUT11.test.ts` | 2 |
| `docs-src/wallet_ops/send.md` | 2 |
| `src/mint/Mint.ts` | 2 |
| `test/mint/Mint.node.test.ts` | 2 |
| `src/transport/WSConnection.ts` | 2 |
| `test/transport/WSConnection.test.ts` | 2 |
| `.release-please-manifest.json` | 1 |
| `CHANGELOG.md` | 1 |

## Commit subjects (newest first)

- `8e1864f4` 2026-10-27 fix(auth): drop request path from BAT log context (#1351)
- `aaf8af30` 2026-11-02 fix(ws): route error callbacks through safeCallback (#1363)
- `d6a121ae` 2026-11-03 fix(events): contain remaining consumer callbacks (#1366)
- `faf2d3a0` 2026-11-04 fix(events): contain onDrop and onProgress callbacks (#1368)
- `a3b7cab4` 2026-11-05 fix: keep request paths and full quote ids out of log context (#1375)
- `8d74a82e` 2026-11-05 fix(wallet): drop quote ids and proofs from log context (#1378)
- `913806c1` 2026-11-06 fix(events): contain group subscription setup failures (#1381)
- `aae3036d` 2026-11-07 fix(payment-request): drop an incomplete DLEQ in decodePayload (#1386)
- `01da1d17` 2026-11-07 fix(wallet): keep the DLEQ on offline sends (#1387)
- `ae6a3e0a` 2026-11-07 fix(mint): log the response shape, not the body, on malformed responses (#1390)
- `53306ce7` 2026-11-09 fix(crypto): require a pubkey in P2PK data (#1394)
- `51a0b122` 2026-11-09 fix(wallet): reject malformed locks when checking a payment request (#1396)
- `e8a566cd` 2026-11-09 fix(auth): apply the https discovery rule to device verification links (#1401)
- `254be886` 2026-11-09 fix(wallet): handle legacy keyset ids that are all hex (#1402)
- `5be674c1` 2026-11-10 fix(wallet): swap locked legacy inputs before sending (#1404)
- `a02281c5` 2026-11-10 ci: move v4-dev actions to main's pinned versions (#1407)
- `8c97e525` 2026-11-10 fix(crypto): require values for integer tags (#1414)
- `0254f1eb` 2026-11-10 fix(crypto): normalize HTLC hash comparison (#1416)
- `1e485e3e` 2026-11-10 chore(v4-dev): release 4.13.1 (#1352)

## Release notes (verbatim)

_source: https://github.com/cashubtc/cashu-ts/releases/tag/v4.13.1_

Primarily a hardening release, with fixes to callbacks (events, websockets, progress) and payment request checks that are stricter on malformed input. No API changes, but normal sends now swap locked P2PK/HTLC inputs, and offline sends keep each proof’s DLEQ (pass removeDleq to getEncodedToken if token size matters)

## What's Changed
* fix(auth): drop request path from BAT log context [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1351
* fix(ws): route error callbacks through safeCallback [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1363
* fix(events): contain remaining consumer callbacks by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1366
* fix(events): contain onDrop and onProgress callbacks by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1368
* fix: keep request paths and full quote ids out of log context [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1375
* fix(wallet): drop quote ids and proofs from log context [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1378
* fix(events): contain group subscription setup failures by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1381
* fix(payment-request): drop an incomplete DLEQ in decodePayload [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1386
* fix(wallet): keep the DLEQ on offline sends [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1387
* fix(mint): log the response shape, not the body, on malformed responses [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1390
* fix(crypto): require a pubkey in P2PK data [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1394
* fix(wallet): reject malformed locks when checking a payment request [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1396
* fix(auth): apply the https discovery rule to device verification links [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1401
* fix(wallet): handle legacy keyset ids that are all hex [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1402
* fix(wallet): swap locked legacy inputs before sending [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1404
* ci: move v4-dev actions to main's pinned versions by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1407
* fix(crypto): require values for integer tags [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1414
* fix(crypto): normalize HTLC hash comparison [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1416
* chore(v4-dev): release 4.13.1 by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1352


**Full Changelog**: https://github.com/cashubtc/cashu-ts/compare/v4.13.0...v4.13.1
