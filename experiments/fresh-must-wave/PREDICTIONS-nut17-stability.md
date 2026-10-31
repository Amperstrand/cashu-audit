# FROZEN PREDICTIONS — NUT-17 ws version stability (2026-10-31, BEFORE the run)
Baseline (0.21.0 / 0.18.3): both 101+OK+current-state push; ns ×3 PAID
pushes, cdk ×1; field drift ns expiry:null+pubkey:"" vs cdk int/absent.
Predictions:
- ns-0.20.3: IDENTICAL to 0.21.0 (×3 triple-fire, same field shapes) —
  the ws notification path is unlikely to have changed within 0.20.x.
- cdk-0.18.1: IDENTICAL to 0.18.3 (×1, int expiry, no pubkey).
Any deviation = re-check probe before believing it.
