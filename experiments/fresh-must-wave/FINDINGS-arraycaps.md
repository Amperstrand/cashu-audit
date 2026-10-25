# FINDINGS — mint/swap array caps on the fund path (2026-10-25)

Frozen predictions: `PREDICTIONS-arraycaps.md`. Driver: `array_caps.py`.
Artifacts: `out/array_caps.json`. Arms: ns-0.21.0, cdk-0.18.2, testnut.

## Cap landscape (wire-measured unless noted)

| Endpoint | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| mint outputs | **100** (14005 "Too many outputs") | ≥128 ok | ≥128 ok |
| swap inputs | **100 (source-read only** — mint cap blocked the 128-proof setup wire test; info.ts MAX_SWAP_INPUTS default) | ≥128 (structural accept; fee-balance error is self-describing: "inputs (128) - fees (13) vs outputs (128)") | ≥128 → **200 OK** (arm keyset ppk=0, fee-free) |
| swap outputs | **NO explicit cap — SQLite layer error leaks** | 1000 (pydantic 422 too_long) | 1000 (**11015** "Maximum outputs exceeded", spec code) |
| checkstate Ys | 1000 (14005) | 1000 (422) | 1000 (11014) |
| batch quotes | 50 (11017) | 1000 (422) | 100 (11017, advertised 1000) |
| batch outputs | 1000 (source) | — | — |

## Findings

1. **cashu-cf defect (new): the swap path has no explicit output-count
   check — the DB layer's limit is the cap, and the raw error leaks**:
   1001-output swap → 400 `invalid_request` "too many SQL variables at
   offset 344: SQLITE_ERROR" (code 14005). Internal technology + SQL
   detail disclosed; crash-class opacity on the fund path; the
   effective cap is whatever the SQLite variable limit works out to
   per-statement, not a policy. Candidate cashu-cf fix (explicit
   length check + clean spec-code error, 11015-shaped) — pairs with
   the batch-B_ 500 fix. Fund-safe: repeated 400s, no burn observed.
2. **cf mint-output cap is 100** — below ns/cdk (both ≥128; ns 1000
   class). A wallet building 128-output mints works on the references
   and fails on cf (14005). cf cap set is now: mint 100 / swap-in 100
   (source) / swap-out (none, DB-limited) / batch-Q 50 / batch-out
   1000 / checkstate 1000 — every endpoint different, only batch-Q 50
   is advertised (min).
3. **cdk's 11015 output-cap error is spec-listed and clean** —
   consistent with the error-registry adoption pattern (cf+cdk adopt;
   ns pydantic-bypasses on framework paths).
4. ns's fee-balance rejection is self-describing (fee arithmetic in
   the message); cdk's arm-level ppk=0 made its 128-input swap
   fee-free — cross-arm fee defaults differ (ns docker keyset ppk=100,
   cdk docker ppk=0) — a suite-calibration datum, not a divergence.
5. Prediction scorecard: cf swap-input 100 untestable this run (mint
   cap blocked setup — probe limitation recorded); swap-output cells:
   cdk HIT (11015), ns HIT (422/1000), cf MISS in the best way (no
   cap exists — the finding).
