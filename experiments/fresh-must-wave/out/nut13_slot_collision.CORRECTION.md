# CORRECTION (2026-10-31) — nut13_slot_collision.json is a misread artifact

This JSON does not recompute from its own documented inputs:

- The `mnemonic` field is elided (literally "…(NUTs 13-tests
  vector)") and the `keyset_id` (`01adc013…`) is not the 13-tests
  V2 id (`015ba18a…`); recomputing HMAC(seed, msg‖type) for
  counter 0 with the 13-tests mnemonic and this keyset yields
  cf9a5ea1…/66a2ea01… — neither recorded value.
- The `note` ("slot_0x01 IS cdk v0.18.2 SecretKey::derive input
  (P2PK key material)") encodes the type-name confusion corrected
  on 2026-10-25/10-31: cdk's `SecretKey` is its blinding-factor
  type; its 0x01-slot output is the SAME blinding factor nutshell
  and cashu-ts derive — agreement, not a collision.

See research/FINDINGS-2026-10-31-nut18-payload-spelling.md §2 and
research/NUT13-INTENT-RESEARCH-2026-10-25.md. Do not cite this JSON
as evidence of a NUT-13 divergence.
