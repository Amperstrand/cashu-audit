# FINDINGS — NUT-03 unit consistency on the only multi-unit arm (2026-10-25)

Frozen predictions: `PREDICTIONS-nut03.md`. Arm: testnut (cashu-cf) —
the only arm with two units (sat + usd keysets, both listed active).

## Measured

| Leg | Result |
|---|---|
| U1 full usd lifecycle (quote → paid → mint → proof) | **200 OK** — the usd unit works end-to-end |
| U2 sat inputs → usd-keyset output | 400 `invalid_request` "Invalid output keyset id: 0039ff…" **14005** |
| U3 mixed-unit inputs (sat + usd proofs) | 400 "All input proofs must be from the same unit. Found units: sat, usd" **14005** |
| U4 sat inputs/amount, usd keyset id on output | 400 "Invalid output keyset id…" 14005 |

1. **cashu-cf enforces #406's unit-consistency normative text on the
   swap path**: same-unit inputs required; outputs must be under the
   inputs' keyset. All three violation shapes rejected. (The only
   multi-unit arm measured — ns/cdk arms are sat-only by config; a
   multi-unit cdk/ns arm would complete the family matrix.)
2. **Error identities**: the mismatch rejections are phrased as
   "Invalid output keyset id" for a VALIDLY-LISTED keyset (slightly
   misleading — the keyset is valid, the combination is not); the
   mixed-input message is the most self-describing error measured in
   this whole program ("Found units: sat, usd").
3. **Probe-bug datum**: a sat quote + usd-keyset outputs (unit
   mismatch at MINT time) → 12001 "Invalid keyset ID in output" — the
   mint-path identity for the same class differs from the swap-path
   identity (14005) for the identical conceptual violation.
4. Prediction scorecard: 4/4 HIT (rejections + lifecycle).

## Update to the tracker

NUT-03's card gap ("mixed-unit swap lifecycle unmeasured") closes for
cf; open: ns/cdk multi-unit arms (config work, queued low — the
family matrix wants a cdk arm with two units).
