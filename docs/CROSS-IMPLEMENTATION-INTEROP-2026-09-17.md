# Cross-Implementation Interop: Migration, Derivation, and the Lab

*Companion to issues #27–#31. This is the full analysis the issue stubs
summarize. Written 2026-09-17 after the F1 root-cause + live mirror proof.*

## 1. The migration story (nutshell → CDK → anyone)

### Why mint-side key generation is THE migration surface

The Cashu spec carefully specifies two derivation layers:

- **NUT-02**: keyset ID derivation — from *public* keys, verifiable by anyone
- **NUT-13**: wallet-side secret derivation — deterministic secrets for NUT-09 restore

Between them sits an unspecified layer: **how the mint generates its
per-amount private keys from a seed**. Each implementation chose freely:

| Implementation | Scheme | Seed format | Era notes |
|---|---|---|---|
| Nutshell < 0.15 | HMAC-SHA256(master, domain‖amount) | hex secret | Base64 keyset IDs |
| Nutshell 0.15–0.18 | Same HMAC | hex secret | V1 keyset IDs (00 prefix) |
| Nutshell ≥ 0.20 | Same HMAC | hex secret | V2 keyset IDs (01 prefix); *wallet* secrets switched BIP32→HMAC |
| CDK | BIP32 m/129372'/unit_hash'/keyset_index' hardened children | BIP39 mnemonic | V2 IDs from the start |
| cashu-cf | **Both**: HMAC default + BIP32_CDK mode | hex secret or mnemonic | BIP32_CDK added for ISSUE-095 shadow |

The keyset ID commits the public keys, so any derivation producing those
pubkeys is "correct." But the derivation *scheme* determines whether a
different implementation can reproduce the private keys from the same
seed — which is exactly what migration requires.

### What CDK's migrate-nutshell subcommand tells us

CDK's migration tool reads nutshell's tables and forces them through
CDK's transaction layers. Crucially it **skips pre-0.15.0 keysets**:
"different derivation path logic not supported by CDK." For a migrator:

| Nutshell era | Post-CDK-migration status |
|---|---|
| < 0.15.0 keysets | **Stranded** — CDK refuses to import; tokens unrecoverable |
| 0.15.0–0.18.1 (V1 IDs) | Imported read-only — old proofs verify; no new outputs under V1 |
| ≥ 0.20.0 (V2 IDs) | Full compatibility |

### The F1 class is the migration killer

Our F1 bug (signing provider used HMAC while listing used BIP32_CDK)
is the exact failure mode a migrator fears:

- The mint is **internally consistent** (signs and verifies with the same wrong scalar)
- `/v1/keys` shows the **correct** pubkeys (listing derivation was right)
- Unit tests pass (they test the mint against itself)
- **Only cross-implementation comparison reveals the split**

If a migrator hits F1: tokens minted post-migration fail wallet-side
verification (cashu-ts v4 verifies DLEQ against served pubkeys). User
funds are inaccessible to compliant wallets.

### The mirror as migration validator

The true-mirror (ISSUE-095, live on shadow-cdk.cashu.exchange) is
precisely the pre-migration tool:

1. Configure both implementations with the same seed/mnemonic
2. Route traffic through the mirror (both execute, CDK authoritative)
3. `SHADOW_MATCH` on `/v1/mint/bolt11` = signatures byte-identical = derivation parity
4. `SHADOW_MATCH` on `/v1/swap` = both ledgers accept each other's proofs
5. Any `SHADOW_DIFF` on signatures = F1-class split = **do not migrate yet**

## 2. The F1 root cause (full technical detail)

### The bug

`getPrivateKeyForKeysetId` in `src/mint/keysets.ts` — the hot-path
signing/verification key provider used by MintDO's mint/swap handlers and
`features.ts` proof verification — derived via:

```typescript
const hex = derivePrivateKey(String(this.env.MINT_PRIVATE_KEY), version, unit, amount);
```

The **legacy HMAC scheme**, with no BIP32_CDK branch. Meanwhile:

- `deriveKeysetFromParams` → `generateKeyset` (listing) used mnemonic extras
- The validation path (`keysets.ts:2489`) had the BIP32 branch (ISSUE-102 fixed it there)
- `getPrivateKeyForKeysetId` was missed

### Why it was invisible

The mint was internally consistent: it signed with HMAC scalars and
verified with the same HMAC scalars. The served pubkeys were BIP32
(correct, matching CDK). No single-implementation test can detect this —
you must compare *signatures across implementations* (deterministic BDHKE:
same keyset + same B_ ⇒ same C_).

### The fix (36b5f86)

BIP32_CDK branch in `getPrivateKeyForKeysetId`, mirroring the proven
validation-site derivation:

```typescript
const extras = this.keysetDerivationExtras(version, unit);
if (extras.mnemonic) {
  const { deriveCdkPrivateKey } = await import('../core/bip32-cdk.js');
  const denomIndex = STANDARD_DENOMINATIONS.slice(0, 18).indexOf(amount);
  return deriveCdkPrivateKey(extras.mnemonic, unit, extras.cdkKeysetIndex ?? 0, denomIndex);
}
// else: legacy HMAC (unchanged for non-BIP32 mints)
```

Live-verified: `/v1/mint/bolt11` and `/v1/swap` now SHADOW_MATCH.

### The generalizable lesson

When an implementation supports multiple derivation schemes, **every code
path that produces a private key must agree on which scheme to use**.
The paths to audit (we had four, only two agreed):
1. Listing (serving `/v1/keys`)
2. Signing (mint/swap output signatures)
3. Verification (proof input checking)
4. Recovery/admin (keyset re-derivation, NUT-09 restore)

## 3. The function map (cashu-cf ↔ Nutshell ↔ CDK)

Verified against source code in all three repos.

### Core BDHKE (blind signature chain)

| Step | cashu-cf (TS) | Nutshell (Python) | CDK (Rust) |
|---|---|---|---|
| hash_to_curve | `src/crypto/cashu-crypto.ts: hashToCurve` | `cashu/crypto: hash_to_curve` | `nut01: hash_to_curve` |
| Blind (Alice) | cashu-ts `blindMessage` | `cashu/crypto/secret: step1_alice` | `nut01: SecretKey::blind_message` |
| Sign (Bob) | `features.ts` C_=a·B_ | `secret: step2_bob` | `nut01: SecretKey::sign` |
| Unblind (Alice) | cashu-ts `unblindSignature` | `secret: step3_alice` | `nut01: construct_proof` |
| Verify | `verifyProofSignatureWithPrivateKey` | `secret: verify` | `nut01: verify` |
| DLEQ (NUT-12) | `src/crypto/cashu-crypto.ts` | `cashu/crypto: dleq` | `nut12` crate |

### Keyset derivation

| Concern | cashu-cf | Nutshell | CDK |
|---|---|---|---|
| HMAC scheme | `core/keyset.ts: derivePrivateKey` | `crypto/deterministic_key: derive_keys` | (not present) |
| BIP32 scheme | `core/bip32-cdk.ts` | (abandoned at 0.15) | `MintKeySet::generate` |
| Keyset ID V1 | `core/keyset.ts: deriveKeysetId` | `nut02: derive_keyset_id_v1` | `nut02: Id::v1_from_keys` |
| Keyset ID V2 | `cashuDeriveKeysetId` (cashu-ts) | `nut02: derive_keyset_id_v2` | `nut02: Id::v2_from_data` |

### Spending conditions (NUT-10/11/14)

| Concern | cashu-cf | Nutshell | CDK |
|---|---|---|---|
| Secret parsing | `src/mint/router.ts: parseP2PKSecret` | `mint/secret: check_witness` | `nut10: SecretKey` parse |
| Witness verify | `router.ts: verifyWitnessSignature` | `mint/ledger: _verify_p2pk` | `nut11: verify_p2pk` |
| HTLC verify | `router.ts: verifyHTLCWitness` | `mint/ledger: _verify_htlc` | `nut14: verify_htlc` |

### Other

| Concern | cashu-cf | Nutshell | CDK |
|---|---|---|---|
| Split/denominations | `denominationsForMaxOrder` | `nut02: split_amount` | `nut02: amount_split` |
| NUT-13 wallet derive | cashu-ts `derive` | `wallet/secret: derive` | `cdk-sdk: derive` |
| Token encode V4 | cashu-ts `getEncodedToken` | `wallet/v4: serialize` | `nut00: Token::v4` |

## 4. Spec ambiguities (the full map)

| # | Ambiguity | Spec says | Spec doesn't say | Our issue |
|---|---|---|---|---|
| 1 | Mint key generation | Nothing | The entire derivation scheme | #28 |
| 2 | Keyset rotation timing | "can rotate" | When, why, lifecycle | #11 (draft) |
| 3 | Quote retention | Nothing | How long terminal quotes persist | (ISSUE-121 is our answer) |
| 4 | Melt FAILED state | UNPAID→PENDING→PAID | Terminal failure state | (ISSUE-052 decision) |
| 5 | Error content | Format (detail+code) | Actual string content | #9 (draft) |
| 6 | Recovery from interrupted ops | Nothing | The entire saga/compensation area | #10 (draft) |
| 7 | Secret encoding | "bytes" | UTF-8 vs binary, P2PK prefix detection | #1, #13 (drafts) |
| 8 | hash_to_curve versioning | Algorithm reference | How to signal/upgrade algorithms | #12 (draft) |
| 9 | Amount JSON type | Examples show int | String in the wild (bigint safety) | #7 (draft) |
| 10 | Empty pubkeys tag | NUT-10: list; NUT-11: ≥1 | Which wins when both apply | #19 (d4) |

## 5. The lab design (issue #29 detail)

### Architecture

```
┌─────────────────────────────────────────────┐
│  vitest (Node)                              │
│  ├── seeded PRNG → inputs                   │
│  ├── cashu-cf functions (direct import)     │
│  ├── nutshell bridge (Python subprocess)    │
│  │   └── JSON-RPC over stdio               │
│  └── CDK vectors (fixture files)            │
│      └── lockstep compare                   │
├─────────────────────────────────────────────┤
│  Assertions:                                │
│  ├── identical outputs (cross-impl)         │
│  ├── property invariants (single-impl)      │
│  └── divergence corpus (persisted seeds)    │
└─────────────────────────────────────────────┘
```

### Python bridge protocol

```python
# nutshell_bridge.py — runs as subprocess, reads JSON lines on stdin
from cashu.crypto import secret as csecret
from cashu.crypto.deterministic_key import derive_keys

for line in sys.stdin:
    req = json.loads(line)
    method = req["method"]
    # dispatch to real nutshell functions...
    print(json.dumps({"id": req["id"], "result": result}))
```

### Fuzz invariants

1. **Cross-impl equality**: cashu-cf(secret, r, a) == nutshell(secret, r, a) for BDHKE
2. **Keyset parity**: deriveCdkKeysetPubkeys(mnemonic, unit, idx) == CDK's MintKeySet keys
3. **Value conservation**: split(n) → sum == n (all impls)
4. **Idempotent verification**: verify(proof) is stable across repeated calls
5. **DLEQ round-trip**: blind → sign → dleq → unblind → verify succeeds
6. **Serialization round-trip**: encode → decode → identical proof

### What the lab would have caught (retrospective)

| Bug | How the lab catches it | How we actually found it |
|---|---|---|
| F1 (derivation split) | derive-and-compare on one amount | e2e mirror (minutes) |
| ISSUE-030 (P2PK violations) | witness-condition property test | manual conformance |
| ISSUE-031 (HTLC violations) | HTLC edge-case vectors | manual conformance |
| Secret encoding trap (#13) | round-trip on non-UTF8 secrets | cross-impl fuzz |

## 6. Three-layer testing methodology

| Layer | Tool | What it catches | Speed |
|---|---|---|---|
| Wire | Conformance matrix (cashu-audit) | API shape, error codes, spec compliance | minutes |
| State+signature | True-mirror (ISSUE-095) | F1-class, state machines, serialization | seconds per cycle |
| Pure function | Fuzz lab (#29) | crypto correctness, derivation parity, properties | milliseconds per case |

Together: the most thorough cross-implementation test bed any Cashu
implementation has. The lab catches what the mirror is too slow for
(thousands of seeds per minute); the mirror catches what the lab can't
(routing, DO storage, KV eventual consistency, serialization on the wire).
