# FROZEN PREDICTIONS — NUT-08 fee-ledger probe (leg D, 2026-10-24, before run)

Question: is the ~16-sat gap (128 in, 60 invoice, reserve 1-2, change 50)
input-count-dependent (per-input fee beyond keyset ppk) or fixed?

Arms: testnut (ppk 10), ns-0.21.0 (ppk 100). Invoice 60 sat each leg,
4 blank change slots each leg. Inputs: A={64,64} (2 inputs), B={64,32,16,16}
(4), C={16×8} (8).

| Hypothesis | Prediction |
|---|---|
| per-input hidden fee (~4/input) | A gap ~8, B ~16, C ~32; totals A≈58, B≈50, C≈34 |
| fixed payment-side fee | same gap (~16) for A, B, C |
| keyset ppk (spec: ceil(ppk×n/1000)) | gap ≤1 everywhere — REFUTED already by leg C data (ppk 10/100 cannot produce 16) |

Secondary prediction: melt response `fee_reserve` stays 1–2 (testnut)
/ 2 (ns) across legs; if the response carries an actual-fee field it
should reveal the ledger.
