# FINDINGS — NUT-19 replay caching on the fund paths (2026-10-25)

Frozen predictions: `PREDICTIONS-nut19.md`. Driver: `nut19_replay.py` +
fee-adjusted follow-ups. Artifacts: `out/nut19_replay.json`. Arms:
ns-0.21.0, cdk-0.18.2, testnut.

## The complete replay-caching matrix (byte-identical re-POST after success)

| Endpoint | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| /v1/mint/bolt11 (registry, known) | **200 identical** | 400/11003 | **200 identical** |
| /v1/swap | **200 identical** | **400 "proofs already spent" 11001** | **200 identical** |
| /v1/melt/bolt11 | **200 identical** | **400 "melt quote is not unpaid: paid" 20006** | **200 identical** |

1. **cashu-cf and cdk replay-cache ALL THREE fund endpoints; nutshell
   caches NONE.** The registry's mint-retry fork generalizes into a
   complete 3×3 pattern: a timeout-retry wallet gets its cached
   response on cf/cdk and a rejection on ns — for every operation
   type. Retry-on-400 logic (treat rejection as failure) is safe
   everywhere; retry-and-assume-success logic forks on mint family.
2. **Declaration correlates with behavior**: ns does not declare
   NUT-19 (no caching); cf and cdk declare `"19": {}` (caching) — but
   the `{}` params advertise NO cached_endpoints list while caching
   everything. Per 19.md the info entry should list endpoints + ttl;
   both under-advertise. Nobody advertises the surface they implement.
3. ns's replay rejections reuse *adjacent* spec codes (11001 spent
   inputs, 20006 invoice-already-paid for quote-already-melted) —
   self-describing but semantically borrowed.

## Bonus findings (from the fee-adjustment legs)

4. **ns opaque-crash class extends to PLAIN swaps**: a single-input,
   no-conditions swap whose output amount has no keyset denomination
   (64→63, one output) → **400 `{"detail":"63","code":0}`** — the F5
   `detail:"N"` crash class (registry: multi-input SIG_ALL on 0.21.0)
   reproduces on a plain swap with a keyless amount. #1008's "what
   error?" question remains unanswered on yet another path. (cdk/cf:
   testnut's keyset lacks 63 too — but cf never received that shape
   here; the crash cell is ns-specific as measured.)
5. **Keyset amount ranges diverge by orders of magnitude**: testnut's
   sat keyset tops out at 131,072 (2^17, 18 denominations); the ns
   docker arm ships 64 denominations up to 2^63. A wallet constructing
   a >2^17-sat output works on ns and fails on cf (no key). NUT-02
   leaves the denomination set to the mint — ecosystem-wide, max
   ecash value per proof varies per mint by design; wallet-side
   splitting must consult the keyset, not assume.

## Prediction scorecard

- ns 400-reject: HIT (both legs). cf/cdk "lean 400" on swap: **MISS —
  both cache** (the finding). Melt legs: genuine unknowns, now
  measured (cf/cdk cache, ns rejects).
