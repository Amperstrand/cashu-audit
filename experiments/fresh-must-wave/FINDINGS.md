# FINDINGS — fresh-MUST wave (NUT-03/05/06/19) across 6 arms

Measured 2026-10-24 07:20–07:45 UTC. Frozen predictions:
`PREDICTIONS.md` (written 07:15, before any probing). Drivers: `probe.py`
(first sweep), `followup.py` (mismatch resolution). Artifacts:
`out/results.json`, `out/followup.json`. Arms: ns-0.20.3, ns-0.21.0,
cdk-0.18.1, cdk-0.18.2 (docker FakeWallet, conformance-v2 recipe),
testnut (cashu-cf production).

## Prediction scorecard (frozen vs measured)

| Cell | Predicted | Measured | Verdict |
|---|---|---|---|
| P1 ns 1001-array | 200 (no enforcement) | 422 pydantic "at most 1000" | MISS — ns enforces |
| P1 cdk 1001-array | 4xx | 400/11014 "Maximum inputs exceeded" | HIT (after probe fix) |
| P1 testnut 1001 | 200 | 400/14005 "Too many Y values (max 1000)" | MISS — cf enforces at 1000 |
| P2 all | cf/ccdk ETag+304 | no ETag anywhere; cf Cache-Control only | MISS — and P2 measured the wrong construct entirely (see below) |
| P3 all accept | accepted | 200 on all 6; echo nowhere | HIT |
| P4 testnut usd 200 / others 4xx | as predicted | exactly that | HIT |

Two probe bugs found and fixed per the mismatch discipline: (1) cdk
validates Y as a curve point at checkstate, so placeholder-hex Ys failed
public-key validation before any length check — cdk limit cell required
real pubkeys (`followup.py`); (2) P2's ETag/Cache-Control construct is
NOT what NUT-19 specifies (19.md = request-replay caching with
advertised `cached_endpoints`) — re-scoped below.

## NUT-06 max_array_length — enforcement is universal at 1000; cashu-cf advertises 50

| Arm | Advertised | Enforcement at 1001 | Error identity |
|---|---|---|---|
| testnut (cf) | **50** | **400** | `invalid_request` "Too many Y values (max 1000)" code **14005** |
| ns-0.20.3 | *(absent)* | 422 | pydantic `too_long` "List should have at most 1000 items" (no code) |
| ns-0.21.0 | 1000 | 422 | same as 0.20.3 |
| cdk-0.18.1 | 1000 | 400 | code **11014** "Maximum inputs exceeded: 1001 provided, max 1000" |
| cdk-0.18.2 | 1000 | 400 | same as 0.18.1 |

- **All five arms enforce at 1000** on checkstate. cashu-cf's advertised
  50 is simply wrong — off by 20x against its own enforcement. Corrects
  the earlier same-day claim of "non-enforcement" (the 60-Y probe was
  under the real limit; divergences/NUT-06-MAX-ARRAY-LENGTH-2026-10-24.md
  updated accordingly).
- ns-0.20.3 enforces 1000 WITHOUT advertising the field — wallets can't
  discover the limit, but it exists (fail-late, not fail-open).
- Error identity: three-way fork (14005 / bare-422 / 11014) plus a
  status-code fork (422 vs 400) for the identical failure.
- Side finding — checkstate Y strictness: cdk requires a valid curve
  point (422 "malformed public key" on arbitrary hex); cf and ns accept
  any hex. Extends issues/nut07-checkstate-shape.md with a validation
  layer, not just a shape layer.

## NUT-19 — nobody advertises cached_endpoints; quote creation is not idempotent anywhere

- All arms declaring NUT-19 (testnut, cdk ×2) carry **`{}` params** — no
  `cached_endpoints`, no `ttl`. Per 19.md the info entry should list the
  cached endpoints; wallets get no signal. ns does not declare NUT-19 at
  all.
- Replay probe (identical `POST /v1/melt/quote/bolt11` body, twice, all
  5 arms): **new quote id every time**, 200 both times. Not a NUT-19
  violation per se (quote creation is likely not a cached endpoint), but
  it extends the registry's retry-fork row: quote-create is
  non-idempotent everywhere, while `/v1/mint/bolt11` is idempotent on cf
  and 400 on ns (registry, measured 2026-10-23). A timeout-retry wallet
  gets a fresh quote per retry on every implementation — orphaned-quote
  accumulation, harmless unless quoted fees are locked.
- Full NUT-19 verification (replay on `/v1/swap`, `/v1/mint/bolt11`,
  `/v1/melt/bolt11` with byte-identical bodies) still open — needs real
  blind outputs; queued in the tracker card.
- Informal HTTP-cache observation (not NUT-19): testnut sends
  `Cache-Control: public, max-age=600`; no arm sends ETag; cdk sends no
  caching headers despite declaring NUT-19.

## NUT-05 prefer_async (#339) — accepted everywhere, echoed nowhere

`prefer_async: true` on a melt quote: 200 on all 6 arms; the response
never contains the field (checked full bodies). No arm rejects the
unknown-to-spec-older field — consistent with the lenient-parse class.
fee_reserve at quote time forks: cf 10, ns 10, cdk 20 (same invoice).
Quote ids are UUIDv7-shaped on all arms (matches #383).

## NUT-03 unit consistency (#406) — three error codes for one failure class, plus intra-ns drift

| Arm | unit=usd | unit=eur | identity |
|---|---|---|---|
| testnut | 200 (usd advertised) | 400 | `unsupported_unit` code **11005** "Only sat and usd units are supported" |
| ns-0.20.3 | 400 | 400 | code **10000** "unit 'usd' not supported in any keyset." |
| ns-0.21.0 | 400 | 400 | code **11013**, same message |
| cdk-0.18.1/2 | 400 | 400 | code **11013** "Unit unsupported" |

- Same failure class, three codes across families — and **intra-nutshell
  drift 10000→11013 between 0.20.3 and 0.21.0** (silent error-code
  migration; wallets keying codes fork across ns versions). ns 0.21.0
  converged on cdk's 11013.
- testnut's message leaks its supported set ("Only sat and usd") — the
  only arm whose error is self-describing.

## Tracker updates applied

NUT-03/05/06/19 cards updated; NUT-06 divergence doc corrected
(enforces 1000 / advertises 50). Registry candidate (owner-gated): the
max_array_length advertise-vs-enforce gap on cashu-cf is OUR bug (fix
in cashu-cf), not an upstream filing; the three-way limit error-identity
fork + intra-ns code drift extend the standing error-code-registry issue
draft (issues/error-code-registry.md).
