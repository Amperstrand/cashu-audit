# NUT-00 Secret-Encoding Leniency in cashu-cf (2026-09-08)

Source: LLM spec audit of the NUT-00 blinding/verification boundary, run via
`conformance/scenarios/nut00_secret_encoding.py`.
Full report: docs/audits/results/NUT-00-secret-encoding-result.md

## Summary

cashu-cf accepts proofs blinded over EITHER encoding of the secret — the
spec-conformant `hash_to_curve(utf8(secret_string))` AND the entropy-hashing
trap `hash_to_curve(raw_entropy_bytes)` — while reference mints (cdk 0.17.6,
0.18.0) accept exactly one. Signature verification itself is present (forged-C
proofs are rejected), so this is dual-derivation leniency, not a missing check.

## Violation

| # | Requirement | Spec | cashu-cf behavior | cdk behavior | Severity |
|---|------------|------|-------------------|--------------|----------|
| 1 | Mint MUST verify `C == a * hash_to_curve(utf8(secret))` only | NUT-00 "secret … is a utf-8 encoded string" | Also accepts `C == a * hash_to_curve(hex_decode(secret))` | rejects with 10001 | **HIGH** |
| 2 | (implied) single canonical derivation per proof | NUT-00 encoding requirement (draft) | dual acceptance | strict | — |

## Consequence

Wallets that implement the entropy-hashing trap (a documented, recurring bug
class: two independent wallet ports, a Java NUT-11 platform-charset bug, and
one reproduction in our own tooling tests) **work fine against cashu-cf** and
discover the fault only when their tokens are spent at a strict mint — where
the money is already committed and permanently unspendable. The mint-side
leniency masks the wallet-side bug until the worst possible moment.

## Verification matrix (2026-09-08)

| Mint | control (utf8) | entropy trap | forged C |
|---|---|---|---|
| testnut (cashu-cf) | ✅ spendable | ❌ **ACCEPTED** | ✅ rejected ("Invalid proof signature") |
| cdk-mintd 0.17.6 (local, docker) | ✅ spendable | ✅ rejected (`10001 Token not verified`) | ✅ rejected |

## Resolution

To be filed in cashu-cf `docs/issues/` (P1): verify strictly against
`hash_to_curve(utf8(secret))`; if backward compatibility with existing
trap-convention tokens is required, do a one-time migration sweep instead of
permanent leniency. Upstream context and tested fixes for the wallet side:
`Amperstrand/cashu-ts@secret-encoding-guard` (string-first API +
`verifyOutputConsistency` guard) and `Amperstrand/nuts@nut00-secret-encoding-vectors`
(MUST wording + canonical vectors incl. the negative trap vector).
