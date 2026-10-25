# FINDINGS — NUT-20 batch locked-mint + version stability (2026-10-25)

Frozen predictions: `PREDICTIONS-nut20batch.md`. Arms: ns-0.21.0,
cdk-0.18.2, testnut + version spot-checks on ns-0.20.3, cdk-0.18.1.

## Batch locked-mint (29.md signatures array) — full convergence

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| BL1 batch [locked + unlocked quote], signatures [sig, null], valid | **200** | **200** | **200** |
| BL2 same batch, signatures omitted | 400/**20008** ("signatures array is required when any quote is NUT-20 locked") | 400/20008 | 400/20008 |

The per-quote signature array works with the same post-#370 message
machinery as single mints; 29.md's "required if ANY quote is locked"
is enforced identically everywhere. The NUT-20 lock-path audit is now
COMPLETE — every cell measured, no divergence except the known L5
(single-mint spurious-sig fork).

## Version stability (house rule 4)

| Check | ns-0.20.3 | cdk-0.18.1 |
|---|---|---|
| keyless swap (16→[3,12] class) | opaque `detail:"3"` code 0 — identical to 0.21.0 | balance-first 11005 (fee-0 arm; the balanced keyless cell on 0.18.2 gave 12001) |
| locked quote, no signature | 400/20008 — identical to 0.21.0 | 400/20008 — identical to 0.18.2 |
| swap replay (byte-identical) | **400 — no cache (same as 0.21.0)** | **200 identical — cached (same as 0.18.2)** |

The replay-caching pattern (cf+cdk cache, ns never) holds across ALL
FOUR pinned versions — it is architecture, not release drift.
