# FROZEN PREDICTIONS — cdk 0.17.7 backport arm (2026-10-26, before run)

cdk 0.17.7 (2026-09-16) = backport on the 0.17.x line: mint-recovery
saga timing (10s payment-status cap, deferred sagas keep reserved
proofs), cdk-lnd expired-invoice rejection, integration-test fixes.
Release has NO NUT-tagged commits (digest: 8 commits, NUTs: none).

| Check | Prediction (vs 0.18.x behavior) |
|---|---|
| swap replay (byte-identical) | 200 identical (0.18.x caches; 0.17.7 shares the architecture) |
| keyless swap 64->[63,1] | reject; 0.17.x identity may differ from 0.18's 12001 |
| locked quote, no signature | 400/20008 (NUT-20 predates; expect same code) |
| batch quotes: 51 unknown ids + outputs | 4xx; cap unknown on 0.17.x (0.18.2 = 100) |
| melt with valid proofs (oracle invoice) | 200 PAID |
| recovery-adjacent: mint quote after auto-settle | normal (the saga change is internal timing) |

Any deviation from 0.18.x on the wire surface = backport-line drift
finding; identical behavior = the backport is invisible externally
(consistent with its changelog).
