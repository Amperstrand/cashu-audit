# FROZEN PREDICTIONS — NUT-07/04 quote-state observability (2026-10-31, before run)

Spec (04.md): quote states UNPAID → PENDING → PAID (+ ISSUED post-mint).
Measurable on fakewallet arms + testnut without a holding backend:
the PENDING window on cdk is its fake-wallet settle delay (1–3s).

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.3 |
|---|---|---|---|
| fresh unpaid quote state | UNPAID | UNPAID | UNPAID |
| rapid-poll during settle window catches PENDING | n/m (instant) | n/m (instant) | **PENDING observable ≥once** (1–3s delay) |
| state after PAID + mint (single) | PAID (known wart: stays PAID) | ISSUED? | ISSUED |
| state after PAID + batch mint | PAID (recorded wart) | ISSUED? | ISSUED |
| unknown quote id → error identity | 400 not_found | 400/422 class | 400 50000 Unknown quote |
| expired-quote state/error | expired error class | expired | expiry error |

Wart re-verification included deliberately (cf PAID-after-batch) —
cheap, and the B2/B3/B6 deploy may flip it.
