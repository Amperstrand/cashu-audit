# FROZEN PREDICTIONS — fresh-MUST wave probes (2026-10-24, written 07:15 UTC BEFORE any probing)

Arms: ns-0.20.3, ns-0.21.0, cdk-0.18.1, cdk-0.18.2 (docker, FakeWallet,
conformance-v2 recipe) + testnut (cashu-cf production). Melt-quote probes
use an invoice-oracle arm (scratch nutshell FakeWallet) so target arms
never auto-settle it.

Any mismatch between prediction and measurement = probe bug until proven
otherwise (read the response body first, then the driver).

## P1 — NUT-06 max_array_length enforcement (#425)

`POST /v1/checkstate` with N distinct valid-hex placeholder Ys (control
N=60; probe N=1001 > every advertised limit). Advertised: testnut 50,
ns-0.20.3 ABSENT, ns-0.21.0 1000, cdk 1000/1000.

| Arm | N=60 prediction | N=1001 prediction |
|---|---|---|
| testnut (50) | 200 (measured 2026-10-24 — non-enforcement) | 200 (same class) |
| ns-0.20.3 (absent) | 200 | 200 — no field, no limit shipped; ns historically advertises without enforcing |
| ns-0.21.0 (1000) | 200 | 200 — field added for wallets, enforcement unlikely in ns style |
| cdk-0.18.1 (1000) | 200 | 4xx — cdk ships validators (type-state) and is the stricter family; expect an explicit array-length error |
| cdk-0.18.2 (1000) | 200 | 4xx same identity as 0.18.1 |

Side-probe (NUT-07 shape, already partially known): ns checkstate
request shape — prediction: ns accepts `{"outputs":[...]}` (its wallet's
shape) and ALSO `{"Ys":[...]}`; cdk accepts `{"Ys"}` only; cf accepts
both (measured earlier).

## P2 — NUT-19 caching (declared by cf+cdk, not ns)

Two GETs /v1/info; then conditional GET with the returned ETag.

| Arm | ETag / Cache-Control prediction | If-None-Match prediction |
|---|---|---|
| testnut | Cache-Control present (cf declares NUT-19) | 304 |
| ns-0.20.3 | neither header | 200 always |
| ns-0.21.0 | neither (ns does not declare NUT-19) | 200 always |
| cdk-0.18.1 | ETag present | 304 |
| cdk-0.18.2 | ETag present | 304 |

## P3 — NUT-05 prefer_async (#339, landed 2026-02)

`POST /v1/melt/quote/bolt11` with oracle invoice, `unit: "sat"`, and
`prefer_async: true`.

| Arm | prediction |
|---|---|
| testnut | accepted, response echoes state/payment fields; prefer_async echo unknown (cf may ignore unknown field silently — its lenient-parse class) |
| ns-0.20.3 | accepted (unknown-field-ignored is ns's known parse class, cf. registry pe-vector) — no echo |
| ns-0.21.0 | accepted; echo of prefer_async plausible (ns tracks spec post-#1008) — 50/50 call |
| cdk-0.18.1 | accepted (spec is 8 months old, cdk 0.18 is Sep-2026 vintage); echo likely |
| cdk-0.18.2 | same as 0.18.1 |

## P4 — NUT-03 unit consistency (#406, 2026-09-15)

`POST /v1/mint/quote/bolt11` with `unit` values: "usd" (real unit,
advertised by testnut only), "eur" (no arm advertises).

| Arm | unit=usd prediction | unit=eur prediction |
|---|---|---|
| testnut | 200 quote (usd advertised) | 4xx unit-not-supported |
| ns-0.20.3 | 4xx (sat-only arm) | 4xx same class |
| ns-0.21.0 | 4xx | 4xx |
| cdk-0.18.1 | 4xx | 4xx |
| cdk-0.18.2 | 4xx | 4xx |

Error-identity (code + message) recorded per cell; the interesting
output is identity DIVERGENCE for the same failure class, not the pass/fail.
