# FINDINGS — NUT-29 batch atomicity (2026-10-25)

Frozen predictions: `PREDICTIONS-nut29.md`. Driver: `nut29_batch.py` +
targeted same-quote retry probe. Artifacts: `out/nut29.json`. Arms:
ns-0.21.0, cdk-0.18.2 (docker), testnut (cashu-cf).

## Verdict

**Batch atomicity HOLDS on all three families.** No leg ever returned
partial signatures; every failure mode rejected the whole batch (the
spec's "MUST reject the entire batch... without minting any quotes" is
honored), and a rejected batch does NOT burn paid quotes — testnut
live-proof: corrupt batch → 500, then the SAME paid quote re-submitted
with a valid batch → 200 with signatures. No fund-loss vector.

## Measured matrix

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| control (2 paid quotes, valid outputs) | 200, sigs | 200, sigs | 200, sigs |
| A: corrupted B_ in balanced batch | **500 `internal_error` "Failed to batch mint"** (no partial sigs) | 400/11000 "invalid blinded message." | 422 "malformed public key" (secp parse) |
| B: unknown quote id | 400 (fired on already-issued first — see check-order) | 400/11003 "outputs already signed" (dup-outputs fired first) | 400/**50000** "Unknown quote" (clean cell) |
| C: duplicate quote ids | 400/**11016** "Duplicate quote ID" | 400/**11016** "Duplicate quote IDs provided" | 400/**11016** "Duplicate quote IDs" |
| D: empty quotes array | 400 invalid_request | 400/11000 "batch must not be empty" | 400/**50000 "Unknown quote"** (misleading) |
| recontrol (fresh quotes after rejections) | 200 | 200 | 200 |
| same-quote retry after rejection (cf) | **200 — quote survived** | — | — |

## Findings

1. **Spec-named error code 11016 is converged across ALL THREE
   families** — a rare counter-example to the usual error-code drift
   (cf. the intra-ns 10000→11013 drift and the three-way unit-error
   fork). The freshest spec text got adopted everywhere.
2. **cashu-cf crashes (500) instead of 4xx on a malformed B_ in a
   batch** — the batch saga does not pre-validate blinded-message
   points; the failure surfaces as an internal error mid-processing.
   Fund-safe (quote survives, no partial sigs) but crash-class opacity
   — same family as our other cf opaque-error warts. Candidate cashu-cf
   fix (pre-validate B_ points in the batch saga → clean 4xx),
   owner-gated; pairs with the max_array_length advertisement fix.
3. **Check-order divergence**: ns validates duplicate-outputs before
   unknown-quotes; cf validates already-issued before unknown-quote;
   cdk reports the unknown quote directly. A wallet debugging a bad
   batch gets different first-error identities per mint. (Leg B's
   ns/cf cells were confounded by control-leg quote/output reuse — the
   confound itself is the check-order datum.)
4. cdk's empty-batch identity is **"Unknown quote" 50000** — misleading
   (empty ≠ unknown); ns/cf identities are self-describing.
5. Observability: after a successful batch mint, testnut's quote state
   remains `PAID` (no ISSUED exposure on the quote endpoint) — weakens
   NUT-04 accounting observability for batch-minted quotes.

## Prediction scorecard

- Atomicity (the probe's question): all-family whole-reject — the
  "candidate for partial" suspicion (cf saga-per-item history) was
  WRONG; no partial-signature cell exists. Honest miss, good outcome.
- 11016 convergence: HIT (predicted cdk-only).
- Whole-reject on B/D: HIT.
- A-leg identities: cf 500 unpredicted (crash-class), ns/cdk HIT.
