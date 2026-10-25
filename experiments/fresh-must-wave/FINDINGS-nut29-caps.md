# FINDINGS — batch-quote caps + error-registry adoption (2026-10-25)

Driver: `nut29_caps.py` + cf follow-up with outputs present. Artifacts:
`out/nut29_caps.json`. Frozen predictions in the driver docstring.
Arms: ns-0.21.0, cdk-0.18.2, testnut.

## Batch-quote-count limits (the batchQuotesCap sizing question)

| Arm | Batch-quote cap | Advertised max_array_length | Honest? |
|---|---|---|---|
| testnut (cf) | **50** (11017 `batch_too_large`) | 50 | yes |
| ns-0.21.0 | **1000** (pydantic 422 `too_long`) | 1000 | yes |
| cdk-0.18.2 | **100** (11017 "Maximum batch size exceeded: max 100") | **1000** | **NO — overstates batch capacity 10x** |

1. **Three different batch caps** (50 / 100 / 1000), none matching.
   cashu-cf's 50 is not the outlier it seemed — cdk's is 100.
2. **cdk advertises 1000 but enforces 100 on the batch endpoint** — a
   wallet batching ≤1000 per the advertisement fails on cdk with 11017.
   The advertisement-vs-enforcement gap is cdk's, not cf's (cf's
   min-of-caps advertisement is the honest shape). This completes the
   NUT-06 max_array_length story: every family enforces per-endpoint
   caps; only cdk's single advertised number misdescribes one endpoint.
3. Check order (batch endpoint): length (11017) before existence on
   cf+cdk; ns validates request-model structure (422) before handler
   checks — three-layer ordering recorded.

## Error-registry adoption pattern (sharpens the drift narrative)

11016 (dup quotes), 11017 (max batch), 20008 (NUT-20 sig) — all spec-
listed (error_codes.md) and **all converged on cf+cdk**. cdk's 11014
(checkstate max-inputs) is also spec-listed. Pattern: **the spec error
registry is being adopted faithfully by cashu-cf and cdk; nutshell's
pydantic-layer rejections (422, no code) bypass the registry entirely**
— ns is the registry laggard, not a three-way drift. The earlier
"error-identity fork" framing (three-way unit-error fork, intra-ns
10000→11013 drift) refines to: ns pre-dates/skips the registry on
framework-validated paths; its HANDLER-level codes (11000/11003/11013)
do track the spec. Prediction for future probes: handler-level errors
converge; framework-validation errors stay ns-422.

## Prediction scorecard

- cf 50-cap: HIT. ns 1000: HIT. cdk "unknown": answered 100 (the only
  unpredicted cell, now the headline finding).
