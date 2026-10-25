# FROZEN PREDICTIONS — NUT-19 replay on fund paths (2026-10-25, before run)

Question: re-POST a byte-identical request after SUCCESS — does the
mint return the cached response (NUT-19: 200 identical) or reject
(spent/duplicate)? NUT-19 (19.md) defines replay caching for
successful responses on cached endpoints; declaring arms advertise
{} params (no cached_endpoints list). Known: /v1/mint/bolt11 replay =
cf 200-identical, cdk 200-identical, ns 400/11003 (registry row).

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| swap replay (identical inputs+outputs after 200) | ? — cf's idempotency pattern says maybe 200-identical; but swap consumes inputs, and cf's melt saga... genuine unknown, lean 400 | 400 (spent inputs or 11003 class — ns rejects replays) | ? — cdk implemented NUT-19? lean 400 (inputs spent) |
| melt replay (identical quote+inputs+outputs after PAID) | ? — 400 quote-already-paid/melted, or idempotent 200 | 400 | ? |

Any 200-identical cell = that arm implements request-replay caching on
that endpoint (NUT-19 behavior without advertising cached_endpoints).
Any 400 = no caching; the retry wallet fork extends beyond mint.

Control: first swap/melt must succeed (200); replay compared
byte-for-byte on signatures.
