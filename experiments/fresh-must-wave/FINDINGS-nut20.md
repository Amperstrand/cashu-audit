# FINDINGS — NUT-20 quote-lock path (2026-10-25)

Frozen predictions: `PREDICTIONS-nut20.md`. Driver: `nut20_lock.py`
(crypto self-tested against cdk v0.18.2's own test vector BEFORE any
probing: message bytes, sha256, signature, and an odd-y-inclusive
signer round-trip all green). Artifacts: `out/nut20.json`. Arms:
ns-0.21.0, cdk-0.18.2 (docker), testnut (cashu-cf).

## Verdict

**The NUT-20 lock path is implemented, interoperable, and error-code
converged on all three families.** Locked quotes accept a wallet
pubkey; minting without a valid BIP340 signature is rejected with the
spec-named code **20008 on every arm**; a correctly-signed mint
(third-party construction: x-only BIP340 over the post-#370
domain-separated len32-framed message, SHA-256 pre-hash) is accepted
by all three; rejected quotes survive (retry with a valid signature
mints — both after a missing-sig and a wrong-key rejection). One soft
divergence (L5) and one spec-doc defect found.

## Measured matrix

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| L1 locked quote (pubkey) | 200, echoed | 200, echoed | 200, echoed |
| L2 mint, no signature | 400/**20008** | 400/**20008** | 400/**20008** |
| L3 valid sig (after L2 reject) | **200 + sigs** | **200 + sigs** | **200 + sigs** |
| L4 wrong-key sig | 400/20008 | 400/20008 | 400/20008 |
| L4b retry valid (after L4) | 200 + sigs | 200 + sigs | 200 + sigs |
| L5 UNLOCKED quote + spurious sig | **200 (ignored)** | **200 (ignored)** | **400/20008 (rejected)** |

## Findings

1. **Error code 20008 is converged** across all three families (with
   11016 from the NUT-29 probes, the second spec-named code with
   three-way convergence — the freshest spec text is being adopted
   uniformly; the drift pattern applies to OLD codes, not new ones).
2. **L5 divergence — signature-on-unlocked-quote**: a wallet that
   always attaches a quote signature (even when the quote has no
   pubkey) works on ns and cashu-cf but is REJECTED by cdk (20008).
   20.md is silent for the single-mint case (the "unlocked → null"
   rule is only written for the NUT-29 batch `signatures` array);
   cdk's fail-closed reading is defensible, ns/cf's ignore reading is
   lenient. Wallet-compat trap of the familiar class: works-everywhere
   behavior = only sign when the quote is locked.
3. **All three arms verify the CURRENT (post-#370, 2026-06-07
   "harden... breaking") message format** — a third-party signer built
   purely from the current 20.md text interoperate with all three.
   cdk additionally accepts the legacy format (source-read:
   `sign_legacy`/`legacy_msg_to_sign`, quote-id || raw-hex B_, no
   lengths/amounts) with a warning — two live formats in the
   ecosystem, cdk being the compatible one.
4. **Verification semantics are x-only BIP340 everywhere** (odd-y
   pubkeys accepted; the even-y canonicalization is internal to the
   signer) — matches bitcoin-core schnorr conventions.
5. **SPEC-DOC DEFECT: 20.md's own worked example does not verify**
   under the normative construction, nor the legacy format, nor
   raw-unhashed legacy (`selftest.spec20_example` all false) — the
   example's signature/pubkey pair is decorative (likely never
   re-signed after #370's breaking message change). Anyone implementing
   from the example alone would produce a non-verifying signer.
   Internal candidate for an upstream note (owner-gated; low priority —
   the normative TEXT is unambiguous, which is why all three arms
   agree).

## Prediction scorecard

- L1/L2/L3/L4 as predicted (20008-convergence call for cdk extended to
  all three — right direction, wider than predicted).
- L5: predicted "accepted-or-ignored (measure)" — the cdk rejection is
  the measured answer; a genuine fork, now recorded.
