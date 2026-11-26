# cashu-ts 4.14.0 — NUT-impact digest

Released: 2026-11-25 · range `v4.13.1..v4.14.0` · 47 commits · generated 2026-11-26 by `tools/release_digest.py`
Maps to arms: cashu-ts 4.11.0 (v4-pool consumer corpus; 5.0.0-rc wallet-emission work)

## NUTs touched → tracker cards to re-check

| NUT | commits touching it |
|---|---|
| NUT-10 | 889fd952, c1fac9a9 |
| NUT-11 | 4a9aae29, 4de47949, 794d270f, c1fac9a9, e8331fc2 |
| NUT-13 | c87a5642, eda687df |
| NUT-14 | 4a9aae29 |
| NUT-19 | ca3d0678 |

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `src/wallet/Wallet.ts` | 11 |
| `test/wallet/paymentRequests.test.ts` | 9 |
| `src/model/PaymentRequest.ts` | 8 |
| `src/crypto/NUT11.ts` | 5 |
| `test/wallet/wallet-send.node.test.ts` | 5 |
| `test/crypto/NUT11.test.ts` | 4 |
| `test/mint/Mint.node.test.ts` | 4 |
| `src/utils/core.ts` | 4 |
| `test/utils/core.test.ts` | 4 |
| `src/mint/Mint.ts` | 4 |
| `package-lock.json` | 2 |
| `package.json` | 2 |

## Commit subjects (newest first)

- `e8331fc2` 2026-11-11 fix(crypto): reject key-only NUT-11 tags (#1424)
- `7f993d4a` 2026-11-11 fix(payment-request): omit absent tags from the creqA encoding (#1429)
- `ea1827cc` 2026-11-14 ci: run browser tests in the Playwright image (#1443)
- `cada8842` 2026-11-14 fix(payment-request): read a null id and memo as absent in payment payloads [backport v4-dev] (#1442)
- `d23741d9` 2026-11-14 fix(crypto): require a string message in computeMessageDigest (#1441)
- `936c0f52` 2026-11-14 fix(amount): require a bigint in the Amount constructor (#1440)
- `84f22444` 2026-11-14 fix(utils): check proof field types in verifyReceivedProofs (#1439)
- `d85b2e76` 2026-11-14 fix(wallet): keep proofs skipped by requireDleq in sendOffline (#1438)
- `36ad3f48` 2026-11-14 ci: gate PR checks on lint (#1447)
- `aec0b2cd` 2026-11-14 fix(utils): reject malformed token and request input with CTSError (#1450)
- `b9300e9e` 2026-11-14 fix(payment-request): read null optional fields as absent in creqA requests and received proofs (#1452)
- `d8ed0ad4` 2026-11-14 fix(utils): wrap bech32m encode and decode errors in CTSError (#1454)
- `bedb428d` 2026-11-14 fix(payment-request): check field types when decoding creqA requests (#1457)
- `715cf90c` 2026-11-14 fix(utils): check field types when decoding cashuA tokens (#1458)
- `d0d77350` 2026-11-14 fix(payment-request): read an empty supported-method list as absent (#1461)
- `0dbaecd5` 2026-11-14 fix(payment-request): copy arrays in and out of payment requests and their builder (#1464)
- `c87a5642` 2026-11-14 fix(crypto): keep a private copy of the seed in derivers and wallets (#1466)
- `df06f5e8` 2026-11-15 fix(mint): check that quote responses answer the request (#1468)
- `931e02fa` 2026-11-15 fix(mint): reject malformed fields in mint responses with CTSError (#1470)
- `1d2065cb` 2026-11-16 fix(wallet): report caller-chosen counters through countersReserved (#1474)
- `2cd09abd` 2026-11-16 fix(wallet): refuse oversized arrays when restoring a saved preview (#1477)
- `c6f81d97` 2026-11-17 fix(mint): reject a non-object melt quote response with a CTSError (#1485)
- `eda687df` 2026-11-19 feat(crypto): detect legacy keyset derivation collisions (#1488)
- `6c081fcc` 2026-11-19 chore(deps): bump peter-evans/create-pull-request from 8.1.2 to 8.1.3 in the github-actions group (#1493)
- `798cc578` 2026-11-21 fix(wallet): keep merged and NIP-07 witnesses within the signature limit (#1511)
- `c1fac9a9` 2026-11-21 fix(crypto): apply the secret length limit to every NUT-10 secret (#1512)
- `4b5467c3` 2026-11-21 fix(wallet): check the proof count before other receive work (#1513)
- `fc5f009d` 2026-11-21 fix(mint): read malformed mint info entries as absent (#1514)
- `7f60598f` 2026-11-21 fix(transport): clamp Retry-After to the timer range (#1515)
- `5f1d3ad9` 2026-11-21 fix(wallet): bound the keyset count in a KeyChain cache (#1516)
- `923f3276` 2026-11-21 fix(wallet): bound blindingFactor digits in saved outputs (#1517)
- `cc474865` 2026-11-21 fix(utils): reject malformed proof JSON with CTSError (#1518)
- `dde8fc06` 2026-11-21 fix(wallet): check the melt change count before loading keysets (#1519)
- `bb5c75d4` 2026-11-21 fix(wallet): clamp event timer delays to the timer range (#1520)
- `ebd16e23` 2026-11-21 fix(utils): let timers run when yielding between chunks (#1521)
- `889fd952` 2026-11-21 fix(wallet): keep the witness on a NUT-10 secret over the length limit (#1524)
- `ca3d0678` 2026-11-21 fix(mint): keep NUT-19 cached endpoints only with a string method and path (#1525)
- `a9ddc149` 2026-11-21 fix(utils): throw CTSError when an nprofile cannot be encoded or decoded (#1527)
- `0fed5b7a` 2026-11-21 fix(wallet): split restore requests at max_array_length (#1531)
- `8727e516` 2026-11-21 fix(auth): time out OIDC requests, configurable with requestTimeout (#1532)
- `4de47949` 2026-11-24 perf(crypto): derive each key once per signP2PKProofs call (#1540)
- `0b5a433f` 2026-11-24 fix(wallet): check for duplicate proofs before the requireDleq filter in sendOffline (#1547)
- `794d270f` 2026-11-24 fix(crypto): stop signing a proof once a path has its threshold (#1548)
- `4a9aae29` 2026-11-24 fix(crypto): drop witness entries that are not signatures (#1551)
- `8eb7c4e9` 2026-11-24 fix(wallet): check the melt preimage against the held quote's invoice (#1553)
- `1bba251a` 2026-11-24 fix(wallet): keep the held invoice through prepareMelt and the amount check (#1555)
- `1b47c484` 2026-11-25 chore(v4-dev): release 4.14.0 (#1425)

## Release notes (verbatim)

_source: https://github.com/cashubtc/cashu-ts/releases/tag/v4.14.0_

Another hardening release. Decoders, mint responses and saved previews now check field types and sizes, malformed input throws a `CTSError` instead of a raw `TypeError`, and a `null` optional field reads as absent. No API changes, but a few behaviours are worth knowing:

- A NUT-11 tag with a key and no value (eg `["refund"]`) now throws, matching Nutshell.
- Melt quotes for every method must name the payment target you asked for, as bolt11 already did.
- A bolt11 melt preimage is checked against your own invoice, and reads as `null` if it does not match.
- `OIDCAuth` requests time out after 5 minutes by default (new `requestTimeout` option).
- New: `findLegacyDerivationCollisions()` reports legacy keyset ids that share a derivation path.

---

## What's Changed
* fix(crypto): reject key-only NUT-11 tags [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1424
* fix(payment-request): omit absent tags from the creqA encoding [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1429
* ci: run browser tests in the Playwright image [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1443
* fix(payment-request): read a null id and memo as absent in payment payloads [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1442
* fix(crypto): require a string message in computeMessageDigest [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1441
* fix(amount): require a bigint in the Amount constructor [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1440
* fix(utils): check proof field types in verifyReceivedProofs [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1439
* fix(wallet): keep proofs skipped by requireDleq in sendOffline [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1438
* ci: gate PR checks on lint [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1447
* fix(utils): reject malformed token and request input with CTSError [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1450
* fix(payment-request): read null optional fields as absent in creqA requests and received proofs [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1452
* fix(utils): wrap bech32m encode and decode errors in CTSError [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1454
* fix(payment-request): check field types when decoding creqA requests [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1457
* fix(utils): check field types when decoding cashuA tokens [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1458
* fix(payment-request): read an empty supported-method list as absent [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1461
* fix(payment-request): copy arrays in and out of payment requests and their builder [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1464
* fix(crypto): keep a private copy of the seed in derivers and wallets [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1466
* fix(mint): check that quote responses answer the request [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1468
* fix(mint): reject malformed fields in mint responses with CTSError [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1470
* fix(wallet): report caller-chosen counters through countersReserved [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1474
* fix(wallet): refuse oversized arrays when restoring a saved preview by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1477
* fix(mint): reject a non-object melt quote response with a CTSError by @robwoodgate in https://github.com/cashub
