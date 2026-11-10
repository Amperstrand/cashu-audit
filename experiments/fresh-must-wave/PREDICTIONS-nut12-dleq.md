# FROZEN PREDICTIONS — NUT-12 DLEQ acceptance matrix (2026-10-31, BEFORE probes)

Spec basis (12.md, 2026-09-11 #368 epoch): dleq {e,s} in every
BlindSignature for mint+swap; wallets MUST verify when present;
Alice-verifiable equation e == hash(R1, R2, A, C') with
R1 = sG − eA, R2 = sB' − eC'; /v1/info nuts.12 supported flag;
proofs-to-mint SHOULD strip dleq (privacy note, mint-side unspecified).

| Leg | cf (testnut) | ns-0.21.0 | cdk-0.18.3 |
|---|---|---|---|
| D1 info advert nuts.12 | supported (info says all) | supported | supported |
| D2 mint: every BlindSignature carries dleq {e,s} | yes | yes | yes |
| D3 swap: same | yes | yes | yes |
| D4 DLEQ equation verifies as Alice (own B', r) | yes | yes | yes |
| D5 proof-with-dleq as swap input | accepted (mint ignores extra field) | accepted | accepted? (dual-gate D3 says cdk stricter — maybe rejects) |

Registry D3 hint: cdk dual-gate divergence unfiled — D5 is where it
should surface. A surprising cell = probe bug first (esp. D4 math).
