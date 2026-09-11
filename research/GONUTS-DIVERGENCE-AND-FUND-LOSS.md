# Gonuts Variants: Historical Divergence & Compatibility Analysis

*2026-09-11. Internal research — static analysis + historical matrix correlation.
Links gonuts variants to the fund-loss vectors we've documented.*

## The three variants

| | elnosh/gonuts | OpenTollGate/gonuts-tollgate | Origami74/gonuts-tollgate |
|---|---|---|---|
| **Role** | Upstream reference | Production TollGate wallet | Earlier TollGate fork |
| **Last commit** | 2026-05-04 | 2026-07-17 | 2025-07-14 (stale) |
| **Keyset V2** | ✓ (recent addition) | ✓ (separate implementation) | ✗ (V1 only) |
| **NUTs** | 01-15,17 (no 20) | 01-15,17,20 | 01-15,17,20 |
| **NUT-20 quote signing** | ✗ | ✓ | ✓ |
| **Offline mode** | ✗ | ✓ (offline.go) | ✓ |
| **Secret derivation** | hash(utf8(hex_string)) — correct | hash(utf8(hex_string)) — correct | hash(utf8(hex_string)) — correct |
| **P2PK/HTLC** | ✓ (NUT-11/14) | ✓ (NUT-11/14) | ✓ (NUT-11/14) |
| **Thread safety** | No mutex | No mutex (partial) | Mutex added |

## Derivation analysis: all three are SAFE from the NUT-00 trap

All three variants generate secrets as:
```go
secretBytes := make([]byte, 32)
rand.Read(secretBytes)
secret := hex.EncodeToString(secretBytes)  // hex STRING
```

Then blind with:
```go
Y := HashToCurve([]byte(secret))  // []byte(string) = UTF-8 bytes of the hex string
```

This is the **correct** derivation: it hashes the UTF-8 encoding of the
final hex string, not the raw 32 bytes of entropy. The Go type system
naturally prevents the trap because `[]byte(secret)` on a Go string
produces the UTF-8 bytes.

**Contrast with the trap:** the receipt incident happened because a
TypeScript tool did `hash_to_curve(secretBytes)` (raw entropy bytes)
instead of `hash_to_curve(secret.encode())` (UTF-8 of the hex string).
Go's string-as-readonly-bytes convention makes this mistake structurally
harder to make.

**However:** the deterministic secrets (NUT-13) also derive correctly:
```go
secretKey := secretDerivationPath.ECPrivKey()
secretBytes := secretKey.Serialize()  // 32 raw bytes
secret := hex.EncodeToString(secretBytes)  // → hex string → correct
```

## Keyset ID divergence: the actual compatibility risk

The three forks diverge on keyset ID handling:

| Variant | V1 keyset | V2 keyset | Risk |
|---|---|---|---|
| elnosh/gonuts (pre-V2 commit) | ✓ | ✗ | Tokens minted with V1 IDs fail at V2-only mints |
| elnosh/gonuts (post-V2) | ✓ | ✓ | Backward compatible |
| OpenTollGate | ✓ | ✓ (separate impl) | Potential derivation differences from elnosh's V2 |
| Origami74 | ✓ | ✗ | **Cannot spend at mints that only offer V2 keysets** |

**Fund-loss vector:** A TollGate user holding V1-keyset tokens at a mint
that rotates to V2-only. The Origami74 fork (stale since 2025-07) would
be unable to recognize the new keyset, making the tokens appear as zero
balance. This matches the **ManyKeys** report: "shows 0 balance, tried
multiple mints, incomplete migration."

## Compatibility with our historical matrix

Projecting gonuts variants onto our measured mint matrix:

| Mint | elnosh/gonuts | OpenTollGate | Origami74 |
|---|---|---|---|
| ns-0.16.0–0.19.x | ✓ (V1 keysets) | ✓ | ✓ |
| ns-0.20.0–0.20.3 | ✓ | ✓ | ✓ (if V1 still offered) |
| cdk-0.17.x | ✓ | ✓ | ✓ |
| cdk-0.18.0 | ✓ | ✓ | likely ✓ |
| Future V2-only mints | ✓ (post-V2) | ✓ | **✗ — bricked** |

## Connection to real-world fund-loss reports

### Directly attributable

1. **Keyset migration breaks token decoding**
   - Report: g4tt0 — "Tokens containing Keyset V2 Proofs CANNOT be fully decoded"
   - Gonuts vector: Origami74 fork lacks V2 support
   - Mechanism: mint rotates to V2 → Origami74 can't derive/recognize new keyset → balance shows 0
   - **Recoverable:** switch to elnosh/gonuts or OpenTollGate fork

2. **Wallet migration incomplete**
   - Report: ManyKeys — "shows 0 balance, tried multiple mints, incomplete migration"
   - Gonuts vector: switching between gonuts variants with different keyset handling
   - Mechanism: proofs stored under V1 derivation path, new wallet looks under V2
   - **Recoverable:** re-import with correct derivation path

### Partially attributable

3. **Opaque redemption failures**
   - Report: DireMunchkin — "weird wallet/mint state snafu where my notes just wouldn't redeem"
   - Gonuts vector: keyset mismatch (wallet expects V1, mint offers V2)
   - The Go implementation itself is derivation-safe, but the keyset format
     divergence between forks creates the same user-facing symptom
   - **Recoverable:** if user can identify which fork minted the tokens

### NOT attributable to gonuts (but affects TollGate users)

4. **NUT-00 secret encoding trap** — all gonuts variants are immune
   (Go's string type prevents the bytes-vs-string confusion)

5. **Hash algorithm drift** — gonuts uses the current domain-separated
   algorithm; only pre-0.15.1 nutshell tokens would be affected

6. **HTLC refund witness shape (d6)** — gonuts implements NUT-14 but the
   witness format would need testing against both cdk and nutshell mints

## What backwards compatibility would look like

For the keyset ID divergence specifically:

### Option A: Dual-keyset support (what elnosh/gonuts did)
```go
if crypto.IsKeysetIdV2(id) {
    derivedId = crypto.DeriveKeysetIdV2(keys, metadata.unit, metadata.inputFeePpk)
} else {
    derivedId = crypto.DeriveKeysetIdV1(keys)
}
```
**Cost:** ~20 lines. **Risk:** low. **Coverage:** all current mints.
**What it doesn't fix:** users who already hold V1 tokens at a mint that
has fully rotated away from V1.

### Option B: Claim migration (what our POSITION doc proposes)
On upgrade, the wallet:
1. Enumerates all stored proofs
2. For each keyset, verifies the proofs still validate
3. Swaps old-keyset proofs for new-keyset proofs (atomic swap)
4. Only then marks migration complete

**Cost:** medium (swap logic + state management). **Risk:** swap failure
mid-migration = lost funds (the interrupted-operation vector #13 from our
enumeration). **Coverage:** complete.

### Option C: Mint-side leniency (delay-mode)
The mint accepts both V1 and V2 keyset proofs, but V1 spends are delayed
by 60s (surfacing the issue without confiscating).

**Cost:** small mint-side change. **Risk:** Postel's law — may mask the
underlying incompatibility. **Coverage:** all wallets, transparently.

## Trade-off summary

| Approach | User effort | Mint effort | Fund risk | Discovery |
|---|---|---|---|---|
| Dual-keyset (A) | None (upgrade) | None | Low | Silent (works) |
| Claim migration (B) | None (auto) | None | Medium (swap failure) | Progressive |
| Mint delay-mode (C) | None | Small | Zero | Loud (60s delay) |
| Do nothing | High (manual) | None | High (bricked) | Silent (balance=0) |

## The broader lesson for the user's question about wrong derivations

> "if the derivation is what can be inferred by the spec then it's not
> really wrong and mints should consider honoring them with an
> intentional delay"

This is exactly the POSITION doc's argument, now with gonuts evidence:

1. **The spec's descriptive language permits multiple readings.** Go's
   implementation happens to be correct because of the language's type
   system — but that's luck, not spec clarity.

2. **"Wrong" derivations are spec-compliant readings.** A wallet that
   hashed `hex.DecodeString(secret)` instead of `secret.encode()` made a
   valid interpretation of ambiguous text. The mint blind-signed it.

3. **The mint's signature IS the claim.** Once the mint has signed a
   blinded message (regardless of how it was constructed), it has
   issued value. Refusing to honor that signature destroys user funds
   for what is, at worst, a documentation gap.

4. **Delay-mode is the proportionate response.** It surfaces the issue
   (60s hang is noticeable), doesn't confiscate (money is still
   spendable), and gives the ecosystem time to converge on the correct
   reading without stranding anyone.
