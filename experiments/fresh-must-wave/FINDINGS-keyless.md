# FINDINGS — keyless amounts + melt change-output caps (2026-10-25)

Frozen predictions: `PREDICTIONS-keyless.md`. Drivers: inline probes
(this file records them; the cf defect has its own divergences doc:
`divergences/CASHU-CF-KEYLESS-AMOUNT-SIGNING-2026-10-25.md`). Arms:
ns-0.21.0, cdk-0.18.2, testnut.

## Keyless-amount family matrix

See the divergences doc for the cf fund-loss bug (signs 63, refuses
redemption). Full matrix:

| Arm | Swap w/ keyless amount | Identity quality |
|---|---|---|
| cf | 200 signed → stranded | fund-loss (internal fix queued) |
| cdk | 400/12001 "Unknown Keyset" | misleading but safe |
| ns | 400 `{"detail":"N","code":0}` | F5-class opaque (third instance of the class: SIG_ALL multi-input, single-input keyless, now balanced-decomposed keyless) |

Also measured: cdk's balance check fires BEFORE keyset validation
(fee-0 arms reject unbalanced keyless requests with 11005 first);
ns's balance check passed (fee 1) before the crash.

## Melt change-output caps (M1)

| Arm | melt with 1001 change outputs |
|---|---|
| cf | **200 OK** — the melt path handles 1001 outputs (no SQLite-variable error) — the swap-path DB leak is swap-specific |
| cdk | 400/**11015** "Maximum outputs exceeded: 1001 provided, max 1000" (shares the output cap with swap) |

cf's melt response for the 1001-output melt included the full change
array (per earlier melt-change probes' response shape).

## Prediction scorecard

- K1 cf "clean 4xx": **MISS — cf SIGNS (the finding of the night)**;
  cdk's balance-first ordering hid its keyless cell until the balanced
  leg (12001). K2 cf: balance check fired first (needed 2^17×2 inputs
  for a balanced beyond-max test — not run; the 63 case already
  establishes the class). M1: cf "SQL-variables again?" → **MISS —
  melt path is clean** (sharpens the swap-path defect as
  swap-specific); cdk 11015 HIT.
