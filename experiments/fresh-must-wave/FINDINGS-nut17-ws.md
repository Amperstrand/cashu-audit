# FINDINGS — NUT-17 websocket family (2026-10-31, window D)

Retraction first: an earlier probe hit `/v1/notifications` (403 ns / 404
cdk) — that path was INVENTED. The spec endpoint is `/v1/ws`
(17.md:24). Process note: this family ran discovery-first rather than
frozen-predictions-first (a house-method slip); captures below are the
wire evidence, and the version-stability re-run should freeze first.

## Spec flow (17.md subscribe → current-state push → update pushes)

| Arm | /v1/ws upgrade | subscribe | initial push | PAID-transition push |
|---|---|---|---|---|
| cf (testnut) | — (not advertised, no nuts.17 key) | — | — | — |
| ns-0.21.0 | 101 ✓ | OK ✓ | UNPAID ✓ | **PAID ×3 (triple-fire)** |
| cdk-0.18.3 | 101 ✓ | OK ✓ | UNPAID ✓ | PAID ×1 ✓ (spec-clean) |

Raw-socket JSON-RPC over a minimal masked-frame client; mint quotes
created via HTTP, subscription filters on the quote id, fakewallet
PAID observed via HTTP before reading pushes.

## Findings
1. **ns triple-fires the transition push** (3 identical PAID
   notifications for one state change). Wallet impact: notification
   handlers must be idempotent; naive handlers re-process the quote
   (e.g. re-poll, re-log, double UI events). cdk emits exactly one.
2. **Payload field drift** in the quote notification: ns carries
   `"expiry": null, "pubkey": ""` (present-but-empty); cdk carries
   `expiry: <int>` and no `pubkey` field. Wallets reading these fields
   unconditionally will diverge.
3. cf is the only arm with NO NUT-17 (advertises nothing) — wallets
   polling cf fall back to NUT-06/07 polling (ties into the cf
   never-ISSUED trap: a polling wallet on cf today sees PAID forever).
4. Both arms send the CURRENT state immediately on subscribe (spec
   flow step 3) ✓ — useful for wallet cold-start.

Advertised-vs-actual: ns advertises 3 commands, cdk 9 (bolt11+bolt12
sat) — all measured commands behaved as advertised on the bolt11 sat
path; bolt12 commands untested (no bolt12 backend).
