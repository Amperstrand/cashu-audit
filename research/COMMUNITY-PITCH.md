# Community pitch: the spec gap that keeps eating funds

**For:** Cashu dev call (when we join)
**Not:** an unsolicited PR
**Framing:** forward-looking spec gap, not backward-looking revert request

## The one-sentence version

The spec still doesn't say MUST, so every new wallet — especially AI-generated
ones — can still hash the entropy instead of the string, and with the fallback
removed those mistakes are now permanent fund loss instead of silent
compatibility.

## What happened (the facts, no editorializing)

1. **Feb 2024** — nutshell introduced the domain-separated hash_to_curve
   alongside a permanent fallback for the old derivation (PR #421). The spec
   was updated afterward (PR #88, March 2024: "Add a description for h2c" —
   authored by a contributor who said "Idk what I'm doing, just trying to
   contribute"). The spec now describes only the new algorithm with no
   normative force on which derivations mints must accept or reject.

2. **July 2026** — nutshell removed the fallback (PR #1082, "chore: retire
   legacy curve mapping"). The removal was 39 executable lines. The `verify()`
   change itself was 4 lines of logic. Community-reviewed and approved.

3. **The spec gap remains today**: NUT-00 says the secret is a UTF-8 string,
   `hash_to_curve(x: bytes)` takes bytes, and no RFC-2119 keyword tells an
   implementer which bytes to hash. The spec still has only SHOULD-level
   guidance.

## Why this matters going forward (the real argument)

**This is not about old tokens. This is about new code.**

Every new implementation faces the same ambiguity:

```
NUT-00: "x UTF-8-encoded random string"
NUT-00: hash_to_curve(x: bytes)
```

A developer (or an AI generating a wallet) reads this and must figure out:
do I hash the string's UTF-8 bytes, or the entropy the string was derived
from? The spec doesn't say MUST. Both readings are spec-permitted. The
key-generation idiom from every other crypto library says "hash the bytes."

With the fallback present, this mistake was silently absorbed — the mint
verified under both readings, the tokens worked. With the fallback removed,
the mistake is a permanent, silent, unrecoverable fund loss that surfaces
as a generic "Token not verified" error.

**The population of affected implementations is growing, not shrinking.**
AI-assisted development means more wallets, more recovery tools, more custom
integrations written by people (and models) who pattern-match from adjacent
crypto idioms. Every one of them faces this ambiguity fresh.

## The cryptographic reasoning for the original change (acknowledged)

The domain separator was introduced for legitimate reasons:
- **Cross-protocol protection**: `b"Secp256k1_HashToCurve_Cashu_"` prevents
  the same secret producing the same curve point in different protocols
- **Standardized construction**: counter-based try-and-increment follows
  NIST/CFRG patterns; the old hash-chain-retry was ad-hoc
- **Bounded iterations**: 2^16 cap vs the old unbounded loop
- **Formal analyzability**: standard constructions have security proofs

These are good improvements. Nobody is arguing against the new algorithm.
The question is purely about the compat posture for the old one.

## What we're asking for (the minimal ask)

**Observe mode.** Not a revert. Not a policy change. Six lines:

```python
def verify(a, C, secret_msg):
    Y = hash_to_curve(secret_msg.encode("utf-8"))
    if C == Y * a:
        return True
    # observe: 4 lines, no acceptance change, pure visibility
    if verify_deprecated(a, C, secret_msg):
        logger.warning(f"LEGACY_PROOF_REJECTED keyset={keyset_id}")
    return False
```

This tells mint operators whether anyone is submitting proofs that match the
old derivation. It changes zero behavior — proofs are still rejected exactly
as the community decided. It's the same class as adding a metric counter.

**Why this is worth 6 lines:**
- Nobody currently knows whether the removal affected anyone
- The next time a breaking change is considered, this data informs the decision
- If legacy traffic is zero: you now have proof the removal was correct
- If legacy traffic exists: you know before someone's recovery tool fails

## What we've built (available for reference)

- **Cross-implementation A/B test** showing the redemption-rule divergence:
  nutshell (pre-removal) accepts both derivations; cdk never has; nutshell
  (post-removal) accepts only canonical. Docker-reproducible.
- **Three-mode implementation on cdk v0.18.0** (allow / observe / rugpull):
  tested end-to-end, all three modes verified against canonical, algorithm-
  legacy, and entropy-trap derivations.
- **Cross-implementation test vectors** (7/7 validated across cdk, nutshell,
  nucula, cashu-core-lite) including a negative vector for the trap.
- **NUT-00 spec clarification draft** (MUST wording + vectors + wallet
  self-check) aligned byte-for-byte with existing unit tests.

All on Amperstrand forks. Free to lift, reference, or ignore.

## The ask, ranked by invasiveness

1. **Observe mode** (6 lines in verify()) — pure logging, zero behavior change
2. **Observe + spec MUST** — closes the gap for future implementations
3. **Observe + spec MUST + even-bit signaling** — NUT-06 feature bit so old
   wallets abort before sending tokens that will fail
4. **Allow mode** (per-keyset opt-in) — honors issued claims, bounded by keyset

We're asking for #1 as the minimum. #2-#4 are available if the community
wants them.
