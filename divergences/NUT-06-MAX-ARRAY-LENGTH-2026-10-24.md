# NUT-06: `max_array_length` — advertisement vs enforcement (2026-10-24, corrected same day)

NUT row: NUT-06 (tracker card updated). Source: tracker-priority probe +
fresh-must-wave follow-up (experiments/fresh-must-wave/, FINDINGS.md P1).
Method: `/v1/info` capture across 6 arms + checkstate array probes with
valid curve-point Ys (first sweep's placeholder-hex Ys were invalid for
cdk — curve validation fired before the length check; corrected in
followup.py).

## Spec (06.md:102, after #425 landed 2026-08-15)

`max_array_length` is **(optional)**: "the maximum length the mint
accepts for any array in a request, such as `inputs`, `outputs` or
`Ys`. Wallets **SHOULD** split larger requests into batches no bigger
than this."

## Advertisement vs enforcement (wire, all arms, 2026-10-24)

| Arm | Advertised | Enforces at 1001 Ys | Error identity |
|---|---|---|---|
| testnut (cashu-cf) | **50** | **400** — real limit is **1000** | `invalid_request` "Too many Y values (max 1000)" code 14005 |
| rugs (cashu-cf) | **50** | (same software as testnut) | — |
| nutshell 0.20.3 | *(absent)* | 422 — enforces 1000 anyway | pydantic `too_long` "List should have at most 1000 items" (no code) |
| nutshell 0.21.0 | 1000 | 422 | same as 0.20.3 |
| cdk 0.18.1 | 1000 | 400 | code 11014 "Maximum inputs exceeded: 1001 provided, max 1000" |
| cdk 0.18.2 | 1000 | 400 | same as 0.18.1 |

**Correction of the same-day first version:** an earlier draft of this
doc claimed testnut does not enforce ("60 Ys over the advertised 50 →
200"). That probe was under the REAL limit; at 1001 Ys testnut rejects
with 14005 and names the true bound (1000). The bug is not absence of
enforcement — it is the **advertisement being wrong by 20x** (50
advertised, 1000 enforced).

## Findings

1. **cashu-cf advertises 50, enforces 1000.** Wallets honoring the
   advertised value over-batch-split (harmless); wallets ignoring it
   still work — but any peer mint that genuinely enforces 50 would fork
   behavior. Our advertisement should say 1000 (or the config value
   should be the enforced one). Fix in cashu-cf — owner-gated.
2. **ns 0.20.3 enforces a limit it does not advertise.** Wallets cannot
   discover the bound on that release (fail-late, not fail-open).
3. **Error identity forks three ways** (14005 vs bare-422 vs 11014) plus
   status-code fork (400 vs 422) for one failure class — extends
   issues/error-code-registry.md.
4. **cdk curve-validates Ys at checkstate** (422 "malformed public key"
   on non-point hex); cf and ns accept arbitrary hex — a validation
   strictness divergence on NUT-07's surface.

## Testnut response shape note

cashu-cf checkstate accepts multiple request shapes (`Ys`, `proofs`, or
`secrets`); first probe's `outputs`-shaped body got
`400 "Missing Ys, proofs, or secrets"` — cross-ref
issues/nut07-checkstate-shape.md.

Follow-up in cashu-cf (our repo, owner-gated like all changes): align
the advertised value with the enforced 1000. The 1001-Y probe
(`experiments/fresh-must-wave/followup.py`) is the regression vector.
