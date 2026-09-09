# Issue draft: NUT-00 secret encoding is a dual-representation trap

## Why a developer or LLM gets confused

NUT-00 defines the secret as "a UTF-8-encoded random string" while
`hash_to_curve(x: bytes)` takes bytes. The encoding relationship — hash the
UTF-8 bytes of the FINAL string, not the entropy it was derived from — is
stated only implicitly, in the Proof field description, several sections from
the equation. The type signature (`bytes`) sits next to "random string", and
every adjacent crypto idiom (key generation, hashing preimages) hashes RAW
bytes. An LLM writing client code pattern-matches from that corpus: generate
32 random bytes, hex-encode for the field, hash the bytes. We did exactly
this in an AI-written recovery tool.

The failure is maximally hostile: minting succeeds (blind signatures cannot
know how B_ was derived), DLEQ verifies, unblinding verifies, tokens
serialize — and the first swap/melt fails with an opaque "Token not
verified", permanently. No diagnostic distinguishes it from any other
invalid proof.

## Evidence this is a real, recurring footgun

- Shipped in ≥3 independent implementations: a Go port's Y-derivation, a
  Python port's hex-decode divergence, a Java NUT-11 platform-charset bug;
  plus the AI-tooling case above (full census: cashu-audit
  `research/INCIDENTS-unspendable-ecash-census.md`).
- Most test suites pin only raw-byte primitive vectors — they would
  green-light the trap (nucula's did until we added vectors).
- An AI agent publicly lost 1,824 sats to an adjacent boundary bug in a
  hand-rolled cashu-ts wallet — the LLM-authored-client population is real.

## Position: mints should honor clients that followed the SHOULD

The spec attaches **no RFC-2119 force** to the derivation — a wallet that
hashed entropy violated nothing. Those tokens were issued by mints against
paid quotes: **the mint's own signature is the claim it must honor**
(duty-follows-issuance). The reference mint already does exactly this for the
0.15.1 hash-algorithm migration — nutshell ships a permanent
`verify_deprecated` fallback ("BACKWARDS COMPATIBILITY < 0.15.1") rather than
strand pre-migration tokens. Leniency toward SHOULD-era clients is precedent,
not novelty. Keyset-scoped grandfathering (strict for new keysets, honor
issued claims under old keysets, no sunset) reconciles this with eventual
canonicalization. Full argument:
cashu-audit `research/POSITION-mint-leniency-and-spec-silence.md`.

## Improvement

1. NUT-00: MUST-level wording (input to hash_to_curve is the UTF-8 encoding
   of the final secret string) + positive AND negative test vectors.
2. Wallet-side pre-submit guard: `B_ == hash_to_curve(utf8(secret)) + rG`.
3. Mint-side: per-keyset legacy allowlist + log-on-reject sensor.
4. Tested implementations of (2)+(3) exist on Amperstrand forks:
   cashu-ts `@secret-encoding-guard`, cdk `@nut00-per-keyset-leniency`,
   cashu-cf `@nut00-strict-v2` — free to lift.
