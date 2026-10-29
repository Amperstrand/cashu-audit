# FINDINGS — cashu-ts locktime-0 semantics flip (4.11.0 → 4.13.0, 2026-10-29)

Trigger: cashu-ts #1324 (in 4.12.0, re-touched in 4.13.0) "read
locktime 0 as an expired lock, expire only after locktime". Measured
with the SDK's own exported verifier (`verifyP2PKSpendingConditions`)
on identical proof shapes: `experiments/fresh-must-wave/locktime0_diff.mjs`
(run under @cashu/cashu-ts 4.11.0 and 4.13.0 side by side).

## Measured verdict matrix

| Shape | signer | 4.11.0 | 4.13.0 |
|---|---|---|---|
| lt0 (no refund) | lock key | verifies; `lockState: PERMANENT`, locktime null | **THROWS "signature not required" — lockState EXPIRED** |
| lt0 + refund keys | lock key | **THROWS "refund keys require a locktime"** | verifies; `lockState: EXPIRED` |
| lt0 + refund keys | refund key | throws (sig not required) | verifies |
| ltFuture (+/- refund) | lock key | ACTIVE, verifies | ACTIVE, verifies |
| ltFuture + refund | refund key | throws (not yet) | throws (not yet) |
| ltPast | lock key | throws (expired) | throws (expired) |

## What it means

- **Cross-version wallet break**: a token locked `locktime:0` with
  refund keys is REJECTED by 4.11.0 wallets (construction error) but
  VALID on 4.13.0 (expired → refund path open). A token locked
  `locktime:0` WITHOUT refund keys was spendable by the lock key on
  4.11.0 (PERMANENT) and becomes EXPIRED on 4.13.0 — the lock key's
  signature is no longer the authorizing path.
- Emitting wallets interop differently across receiving-wallet
  versions for the SAME token. Wallets that use `locktime:0` as
  "immediately refundable" only work against ≥4.12.0 receivers.
- The "expire only after locktime" boundary refinement (at vs
  strictly-after) is not distinguishable without clock control at the
  exact locktime second — untested, noted.
- Tollgate/gonuts angle: gonuts' own P2PK locktime reading should be
  pinned against BOTH interpretations; the pool gains lt0 vectors.

## Provenance
Keys/secrets generated per-run via SDK exports; C is a random curve
point (verification is spending-condition-local — no mint involved).
Script: experiments/fresh-must-wave/locktime0_diff.mjs.
