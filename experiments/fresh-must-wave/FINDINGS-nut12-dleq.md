# FINDINGS — NUT-12 DLEQ acceptance matrix (2026-10-31, window D)

Frozen predictions: PREDICTIONS-nut12-dleq.md (written BEFORE probes,
including the discovery pass — house rule honored).

Verifier: pure-Python secp256k1 (padd/pmul) + coincurve decompression;
hash_e = SHA256 over the ASCII hex of uncompressed (65-byte) points
(R1,R2,A,C') — cross-checked against cdk `dhke::hash_e` and ns
`b_dhke.hash_e` sources. SELFTESTED against spec vectors
(tests/12-tests.md): hash_e vector TRUE; BlindSignature verify vector
TRUE; corrupted-e negative control FALSE. The deterministic-nonce
DERIVATION vector (v2) did NOT reproduce locally (my HMAC/ctr
construction differs from the reference) — mint-side only, not
wire-observable; recorded as untested, not as a finding.

## Matrix (all legs wire-measured)

| Leg | cf (testnut) | ns-0.21.0 | cdk-0.18.3 |
|---|---|---|---|
| D1 /v1/info nuts.12 | supported | supported | supported |
| D2 mint dleq on EVERY BlindSignature {e,s} | yes | yes | yes |
| D4 mint dleq verifies (Alice equations) | yes | yes | yes |
| D5 swap accepts dleq-BEARING proof inputs | 200 | 200 | 200 |
| D3 swap dleq on every signature + verifies | yes | yes | yes |

## Verdict

FULL THREE-WAY CONVERGENCE. All-or-nothing completeness holds (no arm
ever returns a mixed dleq/partial response), proofs are mathematically
valid per the spec's own hash, and no arm rejects dleq-bearing inputs
(spec's privacy note — mints SHOULD see them stripped but none
enforces). The registry's D3 "cdk dual-gate" hint did not materialize
on the 0.18.3 wire path (no request-side gate observed). No divergence
row; NUT-12 card moves partial → measured-converged. Version
stability: predictions were all-yes and confirmed; sibling arms
(0.20.3/0.18.1) not re-run — convergence on latest arms with zero
forks makes a stability pass low-value; revisit on any NUT-12 spec
epoch change (watch regenerates SPEC-HISTORY).
