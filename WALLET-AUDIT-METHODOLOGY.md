# Wallet Audit Methodology — First Application

> **Date**: 2026-07-28
> **Scope**: cashu-ts v4.7.2 + coco (latest master)
> **Purpose**: Document the process for future wallet audits

## How wallet audits differ from mint audits

| Aspect | Mint audit | Wallet audit |
|---|---|---|
| Spec perspective | Mint MUSTs (serve endpoints, verify proofs) | Wallet MUSTs (construct proofs, verify mint responses) |
| Direction | Incoming requests | Outgoing requests |
| Key concern | Proof validation, state machine | Proof construction, key management, privacy |
| greatspectations focus | Response objects, validation logic | Request construction, crypto operations |
| E2E testing | Send proofs to mint | Use wallet to mint/swap/melt against a running mint |

## cashu-ts structure (v4.7.2)

```
src/
├── crypto/           — NUT-00 DHKE, NUT-11 P2PK, NUT-14 HTLC, NUT-20 quote sig
├── wallet/           — Wallet, KeyChain, P2PKBuilder, WalletOps
├── model/            — Amount, BlindedMessage, Proof, SigAll, PaymentRequest
│   └── types/        — Token V4, NUT-03/04/05/06/07/19/23/25/29/30 types
├── transport/        — HTTP client, WebSocket (NUT-17)
├── auth/             — NUT-21/22 authentication
├── utils/            — CBOR, base64, bech32m, TLV, UUID
└── mint/             — Mint-side HTTP client (used by wallet to talk to mints)
```

87 source files. Key areas for wallet audit:
1. **Crypto correctness** (src/crypto/) — blind/unblind, hash_to_curve, Schnorr
2. **P2PK construction** (src/crypto/NUT11.ts) — secret format, witness signing
3. **SIG_ALL message** (src/model/SigAll.ts) — binary format, domain separator
4. **NUT-20 signing** (src/crypto/NUT20.ts) — quote signature binary format
5. **V4 token encoding** (src/model/types/token.v4.ts) — CBOR, base64url
6. **Wallet operations** (src/wallet/Wallet.ts) — mint, swap, melt, receive, send

## coco structure

Multi-package monorepo (TypeScript/Bun):
- `packages/core/` — Manager, adapter, types, amounts
- `packages/react/` — React hooks
- `packages/sqlite3/` — SQLite storage adapter
- `packages/indexeddb/` — IndexedDB storage adapter
- `packages/adapter-tests/` — Shared adapter conformance tests

## Process for this audit

1. **Fork + checkout stable release** — cashu-ts v4.7.2, coco master
2. **Configure greatspectations** — specquotes.toml pointing at NUT specs
3. **Add spec-quote comments** — wallet-side MUSTs in source files
4. **AI audit** — verify crypto correctness, spec compliance
5. **Compare with mint expectations** — does wallet produce what mints expect?
6. **Document findings** — wallet bugs affect every wallet built on the library

## What we're looking for (wallet-specific)

### Crypto correctness (HIGH priority)
- hash_to_curve: does the wallet use the same algorithm as the mint?
- Blind/unblind: are B_ and C values computed correctly?
- Schnorr: does the wallet sign the correct message for P2PK?
- SIG_ALL: does the wallet construct the binary message correctly?

### Privacy (MEDIUM priority)
- NUT-03: wallet SHOULD order outputs by ascending amount
- Does the wallet leak information via output ordering?
- Does the wallet rotate secrets for each swap?

### Token handling (MEDIUM priority)
- V4 token encoding: correct CBOR structure?
- Trailing slash normalization on mint URL?
- Memo field handling?

### Error handling (LOW priority)
- Does the wallet handle NUT-00 error responses correctly?
- Does it retry on transient failures?

## Learnings for future audits

1. **Wallet audits are harder to automate** — the wallet is a library, not a server. Can't curl endpoints.
2. **E2E testing requires a running mint** — need testnut or local wrangler dev.
3. **The crypto module is the highest-risk area** — bugs there affect every operation.
4. **Cross-check with mint expectations** — the wallet's output is the mint's input. If the wallet produces wrong format, the mint rejects it. We've already seen this with SIG_ALL message format.
