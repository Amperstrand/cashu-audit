# FROZEN PREDICTIONS — keyless amounts + melt change-output caps (2026-10-25, before run)

ns measured already: output amount 63 (no key in ANY of these keysets,
all powers of 2) → opaque 400 {"detail":"63","code":0}.

| Leg | testnut (cf) | cdk-0.18.2 |
|---|---|---|
| K1 swap 64→single 63 output (keyless) | 4xx clean-ish (cf has keyset validation somewhere) or crash-class? | 4xx (type-state) |
| K2 swap 64→single 2^18 output (beyond cf keyset max 2^17; ns HAS this key) | 4xx no-key | 4xx (keyset max 2^? cdk arm keyset also large) |
| M1 melt with 1001 change outputs | 4xx — SQL-variables class again? or a melt-specific cap | 4xx 11015-class? |

Prediction: cf's keyless-amount identity is cleaner than ns's crash;
the interesting cell is whether cf's melt change path ALSO lacks an
explicit cap (like its swap path).
