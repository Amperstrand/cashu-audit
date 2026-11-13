# AUDIT (open, 2026-11-13): NUT-11/12 DLEQ on cashu-cf — emission verified, scalar serialization flagged

Lane: hermes-cocofix (owner-directed interview, 2026-11-13). Scope note:
keyset-rotation/expiry semantics were already audited deeply (registry rows
32/33 incl. three-family wallet legs) — the genuinely-open surface here is
cf's own DLEQ emission and its cross-family parseability.

## Measured tonight (both mints, deployed vintage ≈ c64592fe)

1. EMISSION: both mints attach `dleq {e, s}` to every signature (mint,
   swap, restore responses). nut12 suite 5/5 applicable scenarios GREEN on
   both (presence, verification, tamper-rejection e and s, swap+restore
   legs; absent-case skip is the suite's own graceful leg).
2. SERIALIZATION: e and s are emitted as SHORT hex — 24 chars (12 bytes)
   observed on live proofs. Reference scalars are 32 bytes (64 hex).
   The Chaum-Pedersen relation VERIFIES with these values (they are valid
   small-valued scalars — leading-zero-stripped serialization or truncated
   e-hash, mathematically sound either way), but any wallet that decodes
   e/s into a FIXED 32-byte buffer (length-checked hex→bytes with
   assertion, or secp scalar parse that rejects short input) will fail on
   cf tokens.

## Open experiment (NEXT, wave-2 audit item A1)

cdk 0.18.2 `verify_token_dleq` (the strict gate of registry row 36 —
requires dleq on EVERY proof) against a cf-minted token: does cdk's
scalar parse accept our short hex? Arms exist (conformance-v2 docker
cdk 0.18.1/0.18.2). Predictions frozen before the run:
- P1 (accept): cdk parses scalars length-agnostically (BigInt-style) —
  cf↔cdk DLEQ interop holds; the short serialization is cosmetic.
- P2 (reject): cdk's Scalar::from_hex enforces 32 bytes — the row-36
  class inverted: cf tokens fail the STRICT cdk gate not for missing
  dleq but for scalar spelling — a live wallet↔mint break that is OUR
  side's fix (pad scalars to 64 hex at emission).
Also queue: cashu-ts rc.13 dleq parse (our own pecan stack consumes
these), nutshell 0.21.0 client verify (nutshell ignores dleq by default —
low value, skip unless cheap).

## Artifacts

- nut12 runs: /tmp/nut12-testnut.md, /tmp/nut12-signut.md (copied to
  research/evidence/2026-11-13-wave2/)
- Probe script shape: MintClient.mint_tokens → signatures[].dleq
