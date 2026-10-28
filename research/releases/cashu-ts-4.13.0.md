# cashu-ts 4.13.0 — NUT-impact digest

Released: 2026-10-27 · range `v4.12.0..v4.13.0` · 5 commits · generated 2026-10-28 by `tools/release_digest.py`
Maps to arms: cashu-ts 4.11.0 (v4-pool consumer corpus; 5.0.0-rc wallet-emission work)

## NUTs touched → tracker cards to re-check

| NUT | commits touching it |
|---|---|
| NUT-11 | 2a5da9d8 |
| NUT-18 | 3fe57640, 8622889f |

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `etc/cashu-ts.api.md` | 3 |
| `src/model/PaymentRequest.ts` | 3 |
| `test/utils/tlv-roundtrip.test.ts` | 2 |
| `src/utils/tlv.ts` | 2 |
| `src/wallet/types` | 2 |
| `test/wallet/paymentRequests.test.ts` | 2 |
| `.release-please-manifest.json` | 1 |
| `CHANGELOG.md` | 1 |
| `package-lock.json` | 1 |
| `package.json` | 1 |
| `docs-src/usage/payment_requests.md` | 1 |
| `docs-src/usage/usage_index.md` | 1 |

## Commit subjects (newest first)

- `7d201a42` 2026-10-23 fix(mint): null a melt payment_preimage that is not a string (#1339)
- `8622889f` 2026-10-26 feat(model): encode and decode NUT-18 payment payloads, read mint preference (mp) (#1345)
- `3fe57640` 2026-10-26 feat(model): read and price NUT-18 supported methods (sm) (#1346)
- `2a5da9d8` 2026-10-26 feat(wallet): pay and validate payment requests end to end (#1348)
- `bbd73dda` 2026-10-27 chore(v4-dev): release 4.13.0 (#1340)

## Release notes (verbatim)

_source: https://github.com/cashubtc/cashu-ts/releases/tag/v4.13.0_

This release brings end-to-end NUT-18 payment request handling to v4:
- `sendToRequest`: pay a request in one call with fees, mints and locks handled, so you can't underpay
- `isPaymentRequestSatisfied`: payees check incoming ecash in one call
- `mp`/`sm` support, at parity with v5

There's a new usage guide in `payment_requests.md`.

---

## What's Changed
* fix(mint): null a melt payment_preimage that is not a string [backport v4-dev] by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1339
* feat(model): encode and decode NUT-18 payment payloads, read mint preference (mp) by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1345
* feat(model): read and price NUT-18 supported methods (sm) by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1346
* feat(wallet): pay and validate payment requests end to end by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1348
* chore(v4-dev): release 4.13.0 by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1340


**Full Changelog**: https://github.com/cashubtc/cashu-ts/compare/v4.12.0...v4.13.0
