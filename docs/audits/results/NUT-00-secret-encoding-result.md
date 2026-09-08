# The NUT-00 Secret-Encoding Trap — exact bug and root cause

*Discovered during testing of custom low-level Cashu mint tooling against
stock cdk-mintd 0.17.6 (fakewallet, localhost). Reproducible in ~20 seconds
with `demo-bug.mjs` in this directory. Same behavior confirmed on 0.18.0.*

## TL;DR

NUT-00's proof `secret` is a **string**; verification hashes the **UTF-8 bytes of
that string**. If client code hashes the **entropy bytes** the string was derived
from instead, every blinded message still gets signed, every signature still
unblinds, every token still encodes — and the resulting money is **permanently
unspendable**, failing with `10001 Token not verified` at first swap/melt/receive.

## The protocol contract (three independent sources)

NUT-00:

> `x` UTF-8-encoded random string (secret message), corresponds to point `Y = hash_to_curve(x)`
> … verification: `k * hash_to_curve(x) == C`
> `secret` … is a utf-8 encoded string (the use of a 64 character hex string
> generated from 32 random bytes **is recommended**)

cashu-ts `src/crypto/core.ts`:

```ts
const secretStr  = bytesToHex(randomBytes(32));           // the secret IS the string
const secretBytes = new TextEncoder().encode(secretStr);  // hash input = utf8 of string
return blindMessage(secretBytes);
```

cdk-mintd (`db_signatory.rs`): `verify_message(sk, C, proof.secret.as_bytes())`
— Rust `String::as_bytes()` = UTF-8 of the string.

## The two conventions, side by side

Same 32 bytes of entropy, two "reasonable-looking" blinding calls:

| | spec-conformant | the trap |
|---|---|---|
| hash input | `utf8(hex(entropy))` — 64 ASCII chars | `entropy` — 32 raw bytes |
| `Y` | `0244d4bd…`¹ | `02a265a7…` |
| mint accepts `B_ = Y + rG`? | ✅ HTTP 200 | ✅ HTTP 200 (**blindness — mint cannot tell**) |
| DLEQ verifies? | ✅ | ✅ (proves `C_ = a·B_`, says nothing about the secret) |
| unblinding `C = C_ − rA`? | ✅ | ✅ (internally consistent) |
| token encodes/round-trips? | ✅ | ✅ |
| **swap / melt / receive** | ✅ 200 | ❌ `400 {"code":10001,"detail":"Token not verified"}` |

¹ canonical cross-implementation vector (also pinned in Amperstrand
`cashu-cross-vectors.json` / micronuts `cross_vectors.rs`).

## Why every layer except "spend" is blind to it

A blind signature scheme **deliberately** hides how `B_` was constructed — the
mint signs any well-formed point. The coupling between the published secret
string and the point (`H(utf8(secret))`) exists **only** in the verification
equation. Consequence:

- **No mint-side check can exist** (not a cdk bug — blindness is fundamental).
- DLEQ, unblinding-algebra checks, token serialization, NUT-07 checkstate —
  none of them consult `H(utf8(secret))`. Our full verification suite passed
  on proofs that could never be spent.
- The **first** place the bug can surface is the first spend attempt — e.g. a
  receiving wallet's swap, surfacing to end users as an opaque
  *"Token not verified"*.

## The three-line client-side guard (the only pre-submission detector)

```ts
// before POSTing outputs to the mint:
const expected = hashToCurve(new TextEncoder().encode(publishedSecretString))
  .add(secp256k1.Point.BASE.multiply(r));
assert(expected.equals(B_), "output secret/blinding mismatch — DO NOT SUBMIT");
```

Empirically: 8/8 trap-convention outputs fail this check; spec-convention
outputs pass. It belongs in wallet libraries at the `OutputData` factory.

## Is recovery possible once it happens?

Only if the entropy bytes happen to be **valid UTF-8** (then the bytes themselves
can serve as the secret string). For random 32-byte entropy that's ~2⁻³² per
proof. Exhaustively tested on cdk 0.17.6 and 0.18.0: 17 alternative encodings
(hex/base64/base32-style/decimal/JSON-wrapped/…) — none verifies; the JSON layer
hard-rejects non-UTF-8 bytes and lone surrogates; `/v1/restore` re-returns only
already-issued signatures. Full matrix in `EXP-REPORT.md`.

## How we ran into it

We were building a crash-safe, hand-rolled low-level mint flow (custom blinding
for full journaling control) as part of recovery tooling tests. The natural
crypto-instinct pattern

```js
const secret = randomBytes(32);       // "the secret"
blindMessage(secret)                  // blind it
// ... store secret.toString('hex') in the proof
```

is exactly the trap: it follows key-generation habits instead of the protocol's
secret-is-a-string-first rule. Nothing complained — minting, DLEQ, unblinding,
token encoding all succeeded — and the failure only appeared at first spend.
The experience motivated this writeup, the proposed NUT-00 clarification, and
the cashu-ts hardening below.

## Recurrence (why this deserves ecosystem attention)

- Amperstrand cross-vectors comment: *"this exact divergence shipped in two
  implementations"* (a Go port's Y-derivation, a Python port's hex-decode).
- Java `cashu-mint` commit `b5f1dc8`: *"NUT-11 UTF-8 hashing (was platform
  default charset)"* — same class on the witness path.
- cashu-ts PRs #563/#579: malformed/wrong-type secrets accepted silently —
  adjacent class.
- 2023: 21k-sat public bounty for reproducing "Could not verify proofs" in
  cashu.me — the user-facing symptom of this family.
- This incident (testing, caught in local infra) — the fifth occurrence we're
  aware of, and the reason `hash_to_curve`'s input convention deserves
  MUST-level spec language and library-level guards.

---

## Run results (2026-09-08, this audit)

Scenario module: `conformance/scenarios/nut00_secret_encoding.py`
Vectors: `conformance/reference-vectors/nut00-secret-encoding.json` (7/7 cross-validated
against cdk, nutshell, nucula, cashu-core-lite, cashu-ts)

| Mint | control | entropy trap | forged C |
|---|---|---|---|
| testnut (cashu-cf) | ✅ | ❌ ACCEPTED → divergence filed | ✅ rejected |
| cdk-mintd 0.17.6 local | ✅ | ✅ rejected 10001 | ✅ rejected |

Wallet-side audit, ecosystem recurrence, full experiment logs and the bcr-agent
run bundle are preserved alongside the source workspace (spec-audit-run/).
Tested fixes on Amperstrand forks: cashu-ts@secret-encoding-guard,
nuts@nut00-secret-encoding-vectors, nucula@crypto-test-string-secret-vectors.
