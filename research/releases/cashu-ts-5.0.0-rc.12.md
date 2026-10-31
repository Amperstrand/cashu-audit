# cashu-ts 5.0.0-rc.12 — NUT-impact digest

Released: 2026-10-29 · range `v5.0.0-rc.11..v5.0.0-rc.12` · 69 commits · generated 2026-10-31 by `tools/release_digest.py`
Maps to arms: cashu-ts 4.11.0 (v4-pool consumer corpus; 5.0.0-rc wallet-emission work)

## NUTs touched → tracker cards to re-check

| NUT | commits touching it |
|---|---|
| NUT-06 | 036a1407, cabc72ee |
| NUT-07 | cabc72ee |
| NUT-10 | bfc64b30 |
| NUT-11 | bfc64b30 |
| NUT-12 | df99db34 |
| NUT-13 | 08e54483, 23a9667c, 44688a19, 63234428, 719abb08, cabc72ee |
| NUT-19 | 47673e33, 6b8226dc |

## Hot zones (top-level paths by file-touch count)

| Zone | touches |
|---|---|
| `package-lock.json` | 25 |
| `etc/cashu-ts.api.md` | 12 |
| `src/wallet/Wallet.ts` | 11 |
| `test/crypto/transcript.test.ts` | 8 |
| `src/utils/core.ts` | 7 |
| `scripts/generate-nutroot-vectors.ts` | 7 |
| `test/vectors/nutroot-v3.json` | 7 |
| `test/wallet/wallet-mint.node.test.ts` | 6 |
| `src/crypto/transcript.ts` | 6 |
| `test/crypto/NUT13.test.ts` | 6 |
| `migration-5.0.0.md` | 6 |
| `src/crypto/NUT13.ts` | 5 |

## Commit subjects (newest first)

- `bc70dc49` 2026-09-22 test(transport): wait for state instead of the clock in the keepalive tests (#1255)
- `47673e33` 2026-09-23 docs(fees): lead with prepare() for send cost, name the input fee in the shortfall message (#1258)
- `6b8226dc` 2026-09-23 feat(wallet): return unselected proofs beside the send preview (#1260)
- `165779a1` 2026-09-23 docs(fees): say receiver's swap fee, and how to read it off a send result (#1261)
- `ed59f2f3` 2026-09-23 docs: name things the way the object does (#1262)
- `2ce0f54f` 2026-09-23 fix(model): let isSupported take a NUT number from a loop (#1263)
- `f4bcd57b` 2026-09-25 test(integration): run against a v3-only mint (#1268)
- `46d7b111` 2026-09-25 feat(wallet): verify proofs and restore in chunks that yield to the event loop (#1264)
- `247e4597` 2026-09-25 chore(deps): bump the dev-tooling group with 4 updates (#1267)
- `b76d12a6` 2026-09-25 chore(deps): bump vitest from 5.0.0 to 5.0.1 in the vitest group (#1266)
- `6223e88d` 2026-09-25 chore(deps): bump prettier from 3.9.6 to 3.9.7 in the prettier group (#1265)
- `9c44601a` 2026-09-25 fix(wallet): yield during witnesses and subscriptions, share the restore budget (#1271)
- `4333eaa8` 2026-09-27 fix(wallet): v3 quote inputs commit the amount issued (#1272)
- `5e7b97ef` 2026-09-29 fix(deps): bump fast-uri from 3.1.6 to 3.1.8 (#1275)
- `4ed1be62` 2026-09-29 docs: add responsible disclosure guidance for agents (#1273)
- `df99db34` 2026-09-29 chore: pass bare literals to Amount methods (#1276)
- `c54acb9b` 2026-10-01 chore(docs): contributing using ai section (#1278)
- `6c107558` 2026-10-01 chore(deps): bump the dev-tooling group with 5 updates (#1283)
- `a0851c66` 2026-10-01 chore(deps): bump vite from 8.3.0 to 8.3.1 in the vitest group (#1282)
- `37e59703` 2026-10-01 chore(deps): bump typescript-eslint from 8.70.0 to 8.70.1 in the eslint group (#1281)
- `d34fefaf` 2026-10-01 chore(deps): bump prettier from 3.9.7 to 3.9.9 in the prettier group (#1280)
- `a910e27a` 2026-10-01 chore(deps): bump korthout/backport-action from 4.6.0 to 4.7.0 in the github-actions group (#1279)
- `981a8441` 2026-10-01 chore(deps): bump brace-expansion from 1.1.18 to 1.1.21 (#1284)
- `acd0cb58` 2026-10-01 chore(deps): bump markdown-it from 14.3.0 to 14.3.2 (#1285)
- `3e6d5d6a` 2026-10-07 feat(crypto): transcript container types carry their section in the high nibble (#1289)
- `719abb08` 2026-10-07 feat(crypto): detect legacy keyset derivation collisions (#1287)
- `2562e6f9` 2026-10-07 feat(errors): add mint error codes and predicates (#1288)
- `999bfc35` 2026-10-08 docs: move error handling guide to usage (#1293)
- `63234428` 2026-10-08 test(vectors): carry the NUT-13 v3 seed as 64 bytes (#1295)
- `44688a19` 2026-10-08 feat(nut13)!: derivation helpers take the 64-byte BIP-39 seed (#1296)
- `08e54483` 2026-10-08 fix(nut13): a v3 derivation scope must be 33 bytes (#1299)
- `b0f22967` 2026-10-08 feat(crypto)!: transcript and signing package refactor for co-signed spends (#1294)
- `da18e1a3` 2026-10-08 fix(nutroot): receipts refuse a malformed signature entry or a stray preimage (#1298)
- `decd7d3d` 2026-10-08 fix(nutroot): an empty tree or a NUMS offset without a tree is malformed spend info (#1300)
- `d37a9ad7` 2026-10-09 chore(deps): bump the dev-tooling group with 8 updates (#1303)
- `33838f32` 2026-10-09 chore(deps): bump typescript-eslint from 8.70.1 to 8.71.0 in the eslint group (#1301)
- `268f2f04` 2026-10-09 chore(deps): bump vite from 8.3.1 to 8.3.2 in the vitest group across 1 directory (#1305)
- `c472c6fc` 2026-10-09 chore(deps): bump source-map-js from 1.2.1 to 1.2.2 (#1304)
- `152a1092` 2026-10-09 fix(nutroot): a hashlock preimage is exactly 32 bytes (#1306)
- `9a6bd03d` 2026-10-10 fix(core): validate text fields when decoding a v4 token (#1307)
- `d4ad7f86` 2026-10-10 feat(utils): getTokenMetadata accepts a raw binary token (#1310)
- `23a9667c` 2026-10-11 feat(nutroot)!: blinded outputs enter the transcript as a hash, derived quote ids (#1313)
- `145d2426` 2026-10-13 fix(auth)!: the version 02 BAT target is relative to the mint URL (#1314)
- `39608f23` 2026-10-16 feat(nutroot)!: a mint quote input commits the quote's amount_issued (#1315)
- `12c4fe37` 2026-10-16 test(wallet): restore spies between abort tests so the mutation run passes (#1322)
- `6dee30eb` 2026-10-16 chore(deps): bump typescript-eslint from 8.71.0 to 8.71.1 in the eslint group (#1318)
- `0f442c69` 2026-10-16 chore(docker): update CDK_IMAGE to cashubtc/mintd:0.18.2 (#1317)
- `7887a582` 2026-10-16 chore(deps): bump the dev-tooling group with 3 updates (#1320)
- `f30c529a` 2026-10-16 chore(deps): bump the vitest group with 2 updates (#1319)
- `bfc64b30` 2026-10-16 fix(nut11): read locktime 0 as an expired lock, expire only after locktime (#1323)
- `faf252c7` 2026-10-16 fix(mint): log only the op when a melt quote check answers for another quote (#1326)
- `438c24b9` 2026-10-21 chore(deps): bump msw from 2.15.0 to 3.0.2 (#1321)
- `b117134a` 2026-10-21 chore(deps): bump markdown-it from 14.3.2 to 14.3.3 (#1331)
- `4342d5b8` 2026-10-22 chore(deps): bump the dev-tooling group with 5 updates (#1335)
- `2fa2ca30` 2026-10-22 chore(deps): bump the vitest group with 2 updates (#1334)
- `41127032` 2026-10-22 chore(deps): bump typescript-eslint from 8.71.1 to 8.71.2 in the eslint group (#1333)
- `14f119b8` 2026-10-22 chore(deps): bump prettier from 3.9.9 to 3.9.10 in the prettier group (#1332)
- `93e1d238` 2026-10-23 fix(mint): null a melt payment_preimage that is not a string (#1337)
- `036a1407` 2026-10-23 refactor(mint)!: fetchMintInfo replaces getLazyMintInfo; getInfo returns the wire response (#1341)
- `cabc72ee` 2026-10-23 feat(nutroot)!: align with the simplified core revision (#1328)
- `3ca9ff53` 2026-10-23 chore(scripts): leave no branches behind after an experimental publish (#1342)
- `49326265` 2026-10-26 fix(wallet): let a v3 mint span v3 keysets (#1343)
- `8d6011f9` 2026-10-26 fix(payment-request): accept quoted proof amounts in decodePayload (#1344)
- `21581c98` 2026-10-26 fix(payment-request): reject a malformed sm list with a CTSError (#1349)
- `7008f962` 2026-10-27 fix(auth): drop request path from BAT log context (#1350)
- `2378de38` 2026-10-28 ci: run weekly agenda at 00:23 UTC (#1354)
- `c4593265` 2026-10-29 fix(deps): bump qs from 6.15.3 to 6.17.0 (#1355)
- `cd1034ba` 2026-10-29 fix(deps): bump fast-uri from 3.1.8 to 3.1.9 (#1356)
- `4d6e1f86` 2026-10-29 chore(main): release 5.0.0-rc.12 (#1256)

## Release notes (verbatim)

_source: https://github.com/cashubtc/cashu-ts/releases/tag/v5.0.0-rc.12_

This release follows the simplified core revision of the nutroot spec, makes proof verification and restore yield to the event loop, and tidies a few APIs before GA. There are more breaking changes since rc.11; the migration guide has each one with before and after code.

### Upgrading from rc.11: read these even if you never touch a v3 keyset

- `prepareSwapToSend()` and `wallet.ops.send(...).prepare()` return `{ preview, unselected }`, and `completeSwap()` returns only what the swap produced. Return `unselected` to your store as soon as `prepare()` returns: it is no longer in `keep`, so code that saved `keep` as the whole remainder will drop those proofs. One-shot `send()` and `run()` are unchanged.
- `hasValidDleq` and `verifyProofsForReceive` are replaced by async `verifyMintSignatures` and `verifyReceivedProofs`, which return `{ valid, invalid }` instead of throwing per proof, run in chunks and accept a `signal`. `checkProofsStates` and restore yield to the event loop too.
- `Mint.getLazyMintInfo()` is replaced by `Mint.fetchMintInfo({ forceRefresh? })`, and `Mint.getInfo()` returns `/v1/info` as the mint sent it, so `SwapMethod.method_name`, `min_amount` and `max_amount` are optional. `Wallet.loadMint()` now reuses info a shared `Mint` already holds; call `loadMint(true)` for a fresh fetch.
- The NUT-13 derivation helpers called directly now require the 64-byte BIP-39 seed, as `Wallet` already did.
- P2PK: a locktime of `0` reads as expired, and a lock expires only once the clock is past its locktime, matching NUT-11 and both mints.
- New: `MintErrorCode` and predicates such as `isAlreadyIssuedError` for handling mint errors by code, and `getTokenMetadata` accepts a raw binary token.

### v3 keysets

Nutroot is still a draft and v3 keysets are served only by demo mints, so nothing here affects funds on a public mint. rc.12 tracks the simplified core revision of cashubtc/nuts#443, so rc.11 v3 transcripts no longer verify against an up-to-date mint: blinded outputs enter the transcript as `SHA256(B_)`, a mint quote input commits the quote's lock key and `amount_issued`, and container types carry their section in the high nibble. Check-state now returns a v3 proof's witness from `PENDING` on, so spend commitments and receipts are gone, as are the leaf `disclosure` field and derived quote ids. A v3 mint request may span several v3 keysets, a lock is refused if it uses a leaf type the mint does not list, and the version 02 BAT target is relative to the mint URL. The `ScriptPath` signing package was refactored for co-signed spends and is marked `@experimental` while cashubtc/nuts#464 is a draft.

---

## What's Changed
* test(transport): wait for state instead of the clock in the keepalive tests by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1255
* docs(fees): lead with prepare() for send cost, name the input fee in the shortfall message by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1258
* feat(wallet): return unselected proofs beside the send preview by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1260
* docs(fees): say receiver's swap fee, and how to read it off a send result by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1261
* docs: name things the way the object does by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1262
* fix(model): let isSupported take a NUT number from a loop by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1263
* test(integration): run against a v3-only mint by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1268
* feat(wallet): verify proofs and restore in chunks that yield to the event loop by @robwoodgate in https://github.com/cashubtc/cashu-ts/pull/1264
* chore(deps): bump the dev-tooling group with 4 updates by @dependabot[bot] in https://github.com/cashubtc/cashu-ts/pull/1267
* chore(deps): bump vitest from 5.0.0 to 5.0.1 in the vitest group by @dependabot[bot] in https://github.c
