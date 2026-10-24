# NUT-13 deterministic derivation — SOURCE READ, three-way divergence on the 0x01 slot (2026-10-24)

NUT row: NUT-13. **Source-level analysis, not wire-measured** (labels
per house method). Sources: NUTs 13.md @ 1363de4; cdk v0.18.2
crates/cashu/src/nuts/nut13.rs; nutshell 0.21.0 cashu/wallet/secrets.py
(+ wallet.py grep). Local clones: /root/src/upstream-cache/*.

## What the spec says

- message = b"Cashu_KDF_HMAC_SHA256" || keyset_id || counter_be64 ||
  derivation_type_byte; type byte: **0x00 = secrets, 0x01 = blinded
  messages** (13.md "HMAC-SHA256 Derivation").
- P2PK keys: **BIP32 path m/129373'/10'/0'/0'/{counter}** — explicitly
  NOT the HMAC slot ("allow wallets to swap proofs still locked to a
  public key during a restore").

## What the implementations do

| Impl | 0x00 slot | 0x01 slot | P2PK keys (129373 path) |
|---|---|---|---|
| nutshell 0.21.0 | secret = HMAC(base‖00) ✓ | **blinding factor r** = HMAC(base‖01) ✓ (spec table reading) | **ABSENT** — no 129373 anywhere (only legacy 129372 V1 path) |
| cdk 0.18.2 | Secret::derive HMAC(base‖00) ✓ | **SecretKey::derive = P2PK private key** ✗ (spec assigns this slot to blinded messages) | not the spec path — P2PK keys come from the HMAC 0x01 slot instead |

## Findings

1. **The 0x01 slot is claimed by two different consumers across the
   reference implementations**: blinding factor (nutshell, matches the
   spec's type table) vs P2PK secret key (cdk, contradicts the table
   and the separate BIP32-path instruction). Same mnemonic + keyset +
   counter → nutshell's r and cdk's P2PK key derive from the same HMAC.
   Harmless until someone cross-derives, but the spec text is being
   read two ways by its own reference set.
2. **nutshell 0.21.0 has no deterministic P2PK derivation at all** —
   after a seed-restore, a nutshell wallet cannot re-derive keys for
   P2PK-locked proofs (NUT-13's stated restore purpose fails for
   locked tokens). Fund-loss class on restore.
3. **cdk's P2PK keys don't follow the spec's 129373 path** — a
   spec-path wallet (if one exists — check cashu-ts) and cdk would not
   re-derive the same P2PK keys from the same seed.
4. cdk scar: test comment in nut13.rs names the old
   `Cashu_KDF_HMAC_SHA512` message (dead `_expected_prefix` var) —
   pre-#368 residue, spec-drift documentation debt.

## Verification update (2026-10-24, ~08:05): cashu-ts is the third vote — 2-1 against cdk

cashu-ts `src/crypto/NUT13.ts` (current main, shallow clone in
/root/src/upstream-cache/cashu-ts):

- **Implements the spec type table exactly**: `secretKey: 0x00,
  blindingFactor: 0x01` (its DERIVATION_TYPE map; comment: "0x00-0x03
  are components of one proof allocation" — it even extends the table).
- **Implements the spec P2PK path exactly**: BIP32
  `m/129373'/{purpose}'/0'/0'/{counter}` with `P2PK: 10` — matching
  13.md's `m/129373'/10'/0'/0'/{counter}` verbatim (plus a QuoteLock
  purpose at 20 the spec doesn't define).

**Verdict: nutshell + cashu-ts + the spec table read 0x01 = blinding
factor; cdk 0.18.2 alone reads it as P2PK key material.** Consequences:

1. Cross-family P2PK restore is broken by construction: the same seed
   yields cashu-ts P2PK keys from the BIP32 129373 path, cdk keys from
   the HMAC 0x01 slot, nutshell none at all. A user restoring a wallet
   in different software does not recover the same locked keys.
2. The contested-slot collision is numeric, not hypothetical — same
   mnemonic + keyset + counter, the 0x01 HMAC output IS both
   nutshell's r and cdk's P2PK key material
   (`experiments/fresh-must-wave/out/nut13_slot_collision.json`).
3. The spec's own vectors (tests/13-tests.md) cover only V1 BIP32
   derivation — **no V2 HMAC vectors exist**, which is exactly why two
   reference readings could ship. Candidate registry row / nuts issue
   draft (owner-gated): add 0x00/0x01 V2 vectors; note cashu-ts's
   0x02/0x03 extension; cdk's P2PK slot choice needs an explicit
   spec/cdk reconciliation.

## Verification queue (wire/derived-vector, next session)

- ~~cashu-ts third vote~~ DONE (above).
- Derive (seed, keyset, counter) with cdk 0.18.2 code vs nutshell 0.21.0
  code vs 13.md test vectors: secret streams agree (both 0x00;
  slot collision JSON demonstrates the 0x01 identity).
- If filing: registry row (spec-ambiguity + missing V2 vectors +
  cdk divergence).
