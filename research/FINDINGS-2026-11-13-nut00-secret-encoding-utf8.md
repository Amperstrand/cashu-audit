# NUT-00 Secret Encoding: The UTF-8 Question — Research & Decision

*2026-11-13. Answers the owner ask: "research and explain the utf-8
thing in detail." Evidence: source reads at pinned tags, live wire
probes on our mints, spec git history, upstream PR directions.
Registry row: cf#122 (corrected same-day lineage). Decision at the
end, with reversal conditions.*

## 1. What the rule actually is

NUT-00 (current text, /root/src/NUTs/00.md:27,120):

- The secret `x` is a **UTF-8-encoded random string**. `Y = hash_to_curve(x)`.
- The Proof's `secret` field "is a UTF-8-encoded string (the use of a
  64 character hex string generated from 32 random bytes is
  recommended to prevent fingerprinting)".

Read carefully, this says two different things about two layers:

1. **Shape recommendation**: the string should LOOK like 64 hex chars
   (so secrets don't fingerprint as Cashu on-chain/in-logs).
2. **Encoding rule**: whatever the string is, the mint and wallet hash
   its **UTF-8 bytes** — the 64 ASCII characters — never the 32 bytes
   you would get by hex-DECODING it.

The mint verifies at spend time: `C == a · hash_to_curve(utf8(secret))`
(NUT-00's own Carol/Bob verification). The blinding algebra makes this
checkable without knowing the blinding factor: `C = C_ − r·A =
a·B_ − r·a·G = a·(Y + r·G) − r·a·G = a·Y`. So the unblinded signature
is exactly the amount key applied to the secret's point — the mint can
always recompute it from the published secret alone.

## 2. Spec history: there WAS an ambiguous era

- **Pre-2024-01-26**: NUT-00 said "`secret` is the secret message
  (**no encoding enforced**, 32 byte random hex string recommended)".
  Both readings were defensible: hash the string's bytes, or hash the
  32 bytes the hex was "generated from". Wallets written in this era
  are the legacy population.
- **PR #78 (2024-01-26)** closed it: pinned "utf-8 encoded string" and
  added the commit-note clarification "**32 byte hex is a 64 character
  string**" — explicitly: don't decode.
- **PR #322 (2026-02-16, conventions pass)** kept the text unchanged.
  Three further editorial passes touched 00.md without reopening it.

## 3. What every implementation actually does (source-cited)

| Implementation | Binds over | Publishes | Class |
|---|---|---|---|
| cashu-ts v1–v3.1 (v2.9.0 source read) | `hashToCurve(randomBytes(32))` — RAW entropy | `new TextDecoder().decode(raw)` — lossy string | **broken-by-loss** (see §4) |
| cashu-ts v3.2.0+ (through v4/v5-rc) | `TextEncoder().encode(bytesToHex(randomBytes(32)))` | the hex string | spec ✓ (flip pinned at tag v3.2.0) |
| nutshell wallet (0.21.0 `step1_alice`) | `hash_to_curve(secret_msg.encode("utf-8"))` | the string | spec ✓ |
| nutshell Proof (base.py `__init__`) | recomputes `Y = hash_to_curve(secret.encode("utf-8"))` on every Proof | — | spec ✓ |
| cdk (0.18.x, mint verify) | `verify_message(sk, C, secret.as_bytes())` — Secret is a Rust String, so as_bytes() = UTF-8 | — | spec ✓ (strict) |
| gonuts ×3 (prior research, GONUTS-DIVERGENCE-AND-FUND-LOSS.md) | `HashToCurve([]byte(hex_string))` = UTF-8 bytes in Go | hex string | spec ✓ (all three variants) |
| coco master (packages/core/utils.ts) | `hashToCurve(encoder.encode(secret))`, blinding delegated to cashu-ts v4+ | — | spec ✓ |
| tg-portal (our portal, cashu-ts 2.9.0) | display-only (getDecodedToken/getTokenMetadata); never mints | — | no exposure |
| cashu-cf (both live envs) | UTF-8 first, **then hex-decode fallback** for 64-char hex secrets | — | **lenient** (deliberate, documented "legacy backwards compatibility") |
| cdk mint + ns mint (six-arm, wire) | reject the decoded-hex-bound proof | — | spec ✓ (strict) |

## 4. The part that decides the question: the v2 class cannot be saved

cashu-ts v1–v3.1 bound the signature point to the raw 32 random bytes
and then published the secret as a **lossy UTF-8 decode** of those
bytes. Measured (node, 200 fresh random 32B secrets):

- **0/200** are valid UTF-8 at all
- **0/200** survive decode→encode round-trip
- **0/200** produce a 64-char hex-shaped string

So the published secret of a v2-era token cannot re-derive its own
point under ANY convention — and cf's hex-decode fallback never fires
for them (the guard requires a clean 64-char hex string). Live proof
(frozen prediction, then probe, 2026-11-13):

```
v2-style proof (bind over os.urandom(32), publish lossy decode)
  → testnut swap: HTTP 400 {"error":"invalid_request",
    "detail":"Proof verification failed at index 0: Invalid proof
    signature at index 0","code":10001}
```

(Rejection identity identical to what cdk/ns produce for the class.)
Meanwhile the decoded-hex-bound proof with a CLEAN hex string (the
entropy-trap scenario) is ACCEPTED by cf — the standing cf#122 finding.

**Consequence**: cf's fallback does not serve "old ecash" in any form a
real wallet ever produced. The only proofs it can ever accept are from
tools that bind over decoded bytes AND publish clean hex — i.e. buggy
TS-tooling of the receipt-incident class (our own 2026 incident, plus
"two wallet ports, a Java NUT-11 platform-charset bug" per the
scenario docstring — none of which are wallets anyone should keep
masked).

## 5. Upstream direction

- cashu-ts PR #1168 (robwoodgate, recent): quarantines every ad-hoc
  `new TextDecoder` into one module + eslint rule banning new ones;
  explicitly re-keys a duplicate guard off "a lossy decode" because
  "every secret the wallet makes is UTF-8 text". The ecosystem is
  moving strict; non-UTF-8-able secrets are caller error.
- The spec's ambiguity was resolved 22 months ago (#78) and survived
  the 2026-02 conventions pass unchanged.
- Reference tier on the wire (six-arm corpus): cdk 0.18.1/0.18.2 and
  ns 0.20.3/0.21.0 all strict; cf is the only lenient arm we have
  ever measured.

## 6. DECISION (owner-delegated 2026-11-12: "make decisions as you
best think and document them")

**Option A — strict UTF-8 by default, with a per-env escape hatch.**

cashu-cf stops hex-decode-verifying unless `ALLOW_LEGACY_HEX_SECRETS`
is set on the environment. Concretely:

- Default (flag absent): only `C == a·hash_to_curve(utf8(secret))`
  verifies. cf#122's conformance cell flips to PASS; cf joins the
  reference tier.
- Flag on (any env that telemetry says needs it): the legacy path
  re-arms, and cf already logs every legacy-encoding use ("Log when
  legacy encoding is used for monitoring") — that log line becomes
  the audit trail for the hatch.

Why A over B (keyset-cutoff allowlist) and C (keep):

1. The fallback's stated purpose — keeping old ecash spendable — is
   **empirically unreachable**: the biggest legacy class (cashu-ts
   v2/v3.0-3.1) is rejected by cf today anyway (§4), and every
   maintained wallet family is UTF-8-correct (§3).
2. What the fallback actually does is mask buggy tools until their
   tokens reach a conforming mint — the delayed-failure class this
   repo exists to surface.
3. B's machinery (cutoff dates, per-keyset policy) buys nothing while
   zero hex-bound tokens from real wallets can exist in the wild
   population we can enumerate; the env-var hatch IS option B,
   deployable per-env in minutes if evidence ever contradicts us.

**Reversal conditions** (either flips an env back via the flag):

- cf's legacy-encoding log shows ≥1 firing on a production env
  (someone real is holding hex-bound tokens there), or
- an external wallet team reports hex-bound holdings on our mints.

Until either is observed, strict default stands. Deploy remains
owner-only as always; the wire probe after deploy is the existing
conformance scenario flipping RED→GREEN.

## 7. Test plan that follows

1. Unit/miniflare lock (staged with the fix): hex-bound proof →
   400/10001 with flag off; accepted with flag on. RED-on-main proof
   required before landing (the fallback is live there).
2. Post-deploy: the six-arm/live-matrix `secret_encoding_entropy_trap_rejected`
   cell flips PASS on the deployed env(s) — standing certifier material.
3. The legacy-log check (owner/deploy-agent, wrangler-gated): count
   firings per production env before enabling strict anywhere with
   real users.
4. Wallet-side regression sweep (already green by construction):
   coco drill + cashu-ts-modern mint/swap round-trips — all UTF-8,
   unaffected by the flag either way.
