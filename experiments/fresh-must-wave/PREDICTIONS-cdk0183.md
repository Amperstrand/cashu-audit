# FROZEN PREDICTIONS — cdk v0.18.3 ledger column (2026-10-30, before run)

Release content per digest/code-read (commit 3657c46): sqlite/ffi-only,
findings unchanged. Wire prediction: identical to 0.18.2 on every
ledger leg.

| Leg | Prediction (0.18.3) |
|---|---|
| keyset id length | 66-hex V2 |
| swap replay (payload-once) | 200 cached, byte-identical |
| keyless swap 64→[63,1] | 400/12001 Unknown Keyset |
| locked quote, no signature | 400/20008 |
| batch 1001 unknown ids + outputs | 400/11017 max 100 (length-first) |
| checkstate 1001 valid Ys | 400/11014 max 1000 |

Any miss = probe bug first; a real delta would contradict the
sqlite/ffi-only release claim and become a change point.
