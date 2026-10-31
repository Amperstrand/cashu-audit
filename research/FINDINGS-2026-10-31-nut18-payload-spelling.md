# FINDINGS 2026-10-31 — NUT-18 PaymentRequestPayload id-spelling, live; NUT-13 v2-vectors verification corrections

Research session 2026-10-31 (agenda #43 item-6 follow-up + owner
directive: NUT-13 staged-text verification, research only). Evidence
classes: `live` (docker nutshell 0.21.0 arm, FakeWallet sat,
deterministic key; cdk-cli v0.18.2 debug build from the tag; cashu-ts
v5.0.0-rc.9 vitest harness against the live arm; wire captures at the
request layer), `src` (cited lines, pinned tags), `spec`
(cashubtc/nuts @ 2026-10-23). Full transcripts, payloads, captures,
and harnesses: `private/nut18-live/`, `private/nut13-verify/`
(mirrored in the private repo). Security class: none — parse/
settlement interop divergences only, publishable per the 2026-10-27
rule.

## 1. NUT-18 payload `proofs` id-spelling — live matrix (prediction-gated)

Frozen predictions P1–P12 written before any run (mirror doc). Results:

Parse level (cdk harness = the wallet's own
`serde_json::from_str::<PaymentRequestPayload>` from
wallet/payment_request.rs:1839; payloads built from REAL minted
proofs, control-swapped 200 OK first):

| Payload variant | cdk 0.18.2 (=0.18.3, main) | cashu-ts rc.9 `decodePayload` |
|---|---|---|
| full 66-hex ids | PASS | PASS (shape-only: `id` any string) |
| short 16-hex (`01…`, cdk-native V3 / NUT-00 s_id) | **FAIL** `NUT02: ID length invalid, expected 8 bytes (short/v1) or 33 bytes (v2)` | PASS |
| V1-era 16-hex (`00…`) | PASS (parses as V1 Id — 8 bytes) | PASS |
| 18-hex overlong | FAIL (same identity) | PASS |
| mixed full+short | FAIL (whole payload) | PASS |

Settlement level (cashu-ts `Wallet.isPaymentRequestSatisfied`, live
keysets): short → THROW `Proof has unrecognised keyset.
'0115f753f486af11' is not a sat keyset from this mint` (KeyChain
exact full-id lookup); full → TRUE (fee-aware).

Emission on the wire (creqA with POST transport → capture sink):
- **nutshell 0.21.0 CLI `pay`: SHORT ids + no dleq** (capture-01,
  901B). Prediction said full66 — WRONG, triaged to source:
  cli.py:349 sends a TokenV4 (8-byte `i`, verified in the decoded
  token), cli.py:371-384 rebuilds the payload from
  `TokenV4Token.proofs` whose `Proof.id = token.i.hex()` — short
  verbatim. The prior session's "to_dict emits full66" was true in
  isolation, wrong composed. Same flow on nutshell main (ac1c2e0).
- **cdk-cli 0.18.2 `pay-request`: FULL ids + dleq** (capture-02,
  1004B; `token_proofs` → `Token::proofs` resolves full `Id`s).

Cross-family composition (real captured bodies): nutshell emission ×
cdk parse FAIL (NUT02 length); × cashu-ts settlement THROW; cdk
emission × cashu-ts decodePayload **THROW `invalid payment payload:
memo must be a string`** — found via surprising-FAIL triage: cdk
serializes payload `id`/`memo` as JSON `null` when unset (no
`skip_serializing_if`, nut18/payment_request.rs:312-323, unchanged on
main 8006cc30) and cashu-ts (rc.9 AND main 3ca9ff53) rejects null
optionals (their newer null-tolerance covers REQUEST booleans only).
cdk→cdk round-trips.

**Composite**: the only shipped wallet-CLI payload emitter (nutshell)
emits the one spelling the only strict payload parser (cdk) rejects,
and drops dleq; nutshell has no payee-side payload consumer at all
(0.21.0 + main, grep-verified); cashu-ts rc.9 is the first runtime
consumer (v4.11.0 is type-only). Every cross-family NUT-18 payment
direction fails today except cdk→cdk (and a null-stripping cashu-ts
library caller). Spec gap: 18.md:161 points payloads at "Proof (see
NUT-00)" — NUT-00's both-spellings MUST is written for V4 `i` only;
null-vs-absent for payload JSON optionals is unpinned. Folds into
the staged 00-tests contribution (D5).

## 2. NUT-13 staged-text verification — draft premises falsified; corrections

Owner directive: verify `private/UPSTREAM-nuts-13-v2-vectors.md`
offline against official tests/13-tests.md; nothing filed or posted.

Verified offline (independent reimplementation from 13.md text,
`private/nut13-verify/`): **all 25 official vector values reproduce**
— V1 BIP32 ×10, V2 HMAC ×10 (seed = 64-byte BIP39 seed; secret =
HMAC(seed, msg‖0x00); r = HMAC(seed, msg‖0x01) % N), P2PK
m/129373'/10'/0'/0'/{n} ×5. Implementations against the official
vectors: nutshell 0.21.0 reproduces V2 via its own
`WalletSecrets._derive_secret_hmac_sha256` (direct execution);
cashu-ts rc.9 reproduces V2 + P2PK via exported functions (v4.11.0
module identical in shape); cdk 0.18.2 V2 secret/r spec-exact in
nut13.rs (live via `PreMintSecrets::from_seed`) and P2PK path
official with an in-tree test asserting the vector pubkeys.

Corrections issued this session (the 2026-10-25 retraction stands,
strengthened):
- **"tests/13-tests.md has no V2 vectors" was false when written
  (2026-10-24)** — V2 vectors shipped by 2026-03-27 (04cce64), P2PK
  vectors 2026-01-19 (2ce332e). Registry row corrected.
- **"cdk derives P2PK keys from the 0x01 slot" was a type-name
  confusion** — cdk's `SecretKey` is its blinding-factor type; the
  0x01-slot use IS the spec's blinding slot (live, spec-exact).
  Correction block appended to
  research/NUT13-DERIVATION-SOURCE-READ-2026-10-24.md.
- **"cashu-ts extends the type map to 0x00–0x03" is stale** —
  v4.11.0/rc.9 DerivationType = {0, 1}; 10/20 are BIP32 key-pair
  purposes, not HMAC type bytes.
- `experiments/fresh-must-wave/out/nut13_slot_collision.json` does
  not recompute from its documented inputs (elided mnemonic field)
  and its note encodes the SecretKey misreading —
  nut13_slot_collision.CORRECTION.md added next to it.
- Remaining live gap (unchanged from the retraction): nutshell ships
  no deterministic P2PK/quote-lock derivation (zero 129373 refs) —
  feature class, not a divergence; upstream bar not met.

## Next actions

1. Owner review: NUT-18 payload findings → fold into staged
   00-tests/nuts contribution (D5) — payload-spelling + null-vs-
   absent wording; registry row added this session.
2. Owner review: NUT-13 #443 comment text permanently dead (draft
   addendum in the mirror); no upstream writes made.
3. Candidate probes for the weekly lane: payload short/full ×
   parser matrix as a cheap scenario; cdk null-emission vs
   cashu-ts decode as the first NUT-18 battery cells.
