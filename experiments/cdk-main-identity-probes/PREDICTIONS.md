# FROZEN PREDICTIONS — cdk-main identity probes (2026-10-31, pre-run)

Target: cdk main @ 3523c8a9 (unreleased 0.19-candidate; binary reports
0.18.0 — workspace version unbumped; provenance proven behaviorally by C1,
which exists only post-`0b225c9b`, Oct 1). mintd + FakeWallet bolt11, :8739.
Frozen from test-artifacts/UPSTREAM-AUDIT-2026-10.md §1.2/§1.3/§1.7.
Surprising FAIL = probe bug until proven otherwise.

| # | Scenario | Prediction (cdk-main wire) | 0.18.x contrast |
|---|---|---|---|
| C0 | control: mint 2-sat + plain swap | 200 / 200 | same |
| C1 | POST /v1/restore {"outputs":[]} | **200 `{"outputs":[],"signatures":[]}`** | errors (empty falls through DB path) |
| C2 | HTLC refund path: PAST locktime + refund tag, witness = refund-key signature ONLY (no preimage) | **200 swap ACCEPT** (cd8c84d9 converts P2PKWitness→empty-preimage HTLCWitness → refund path) | **20008** reject (`IncorrectSecretKind`) — registry #2252 item 6 |
| C2b | control: FUTURE locktime + refund tag, same sig-only witness | 400 reject (refund path blocked by locktime; exact identity recorded — source-uncertain between LocktimeNotPassed/20008 family) | 20008 reject |
| C3 | GET /v1/info NUT-19 + NUT-29 | (captured pre-run, boot check) nut19 {ttl:60, 7 cached_endpoints incl. bolt12+onchain}; nut29 max_batch_size=100 while top-level max_array_length=1000 — advertised-vs-enforced fork on the wire | same on 0.18.2 |
| C5 | bolt11 mint-quote create (unlocked) | 2xx; response has `method:"bolt11"`, NO `pubkey` key; `state:"UNPAID"` | pubkey: null present on some 0.18.x? (identity recorded) |

Assert style: exact error-identity (status + code + detail) where frozen; C0/C2 are accept/reject verdicts with body capture.
