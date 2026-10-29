# FROZEN PREDICTIONS — COMPAT-LEDGER n/m cell fill (2026-10-29)

| Cell | Prediction |
|---|---|
| ns-0.20.3 batch length cap | 1000-flat like 0.21.0 (family-stable); 1001 unknown-quote batch -> 4xx (11016-class or pydantic 422) |
| cdk 0.17.6 locked-quote no-sig | 400/20008 (0.17.7 measured 20008; expect family-stable) |
| cdk 0.18.0 locked-quote no-sig | 400/20008 (0.18.2 measured; expect line-stable) |
| cdk 0.17.6/0.17.7/0.18.0/0.18.1 checkstate cap | enforced 100 with 11014-11017-class error (0.18.2 measured 100; cap predates 0.18 per family behavior) |
| cdk 0.17.6/0.18.0 keyless swap 64->[63,1] | 400/12001 (line-stable) |

Any miss = probe bug first (per house rule), then a real drift cell.
