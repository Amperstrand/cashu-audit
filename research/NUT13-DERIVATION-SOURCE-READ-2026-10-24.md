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

## Verification queue (wire/derived-vector, next session)

- Derive (seed, keyset, counter) with cdk 0.18.2 code vs nutshell 0.21.0
  code vs the 13.md test vectors: confirm secret streams agree (both
  0x00) and r/key streams disagree (0x01 consumer split).
- Check cashu-ts's NUT-13 for which reading it implements (third vote).
- If confirmed: candidate registry row (spec-ambiguity class: the type
  table vs the P2PK-path paragraph invite both readings).
