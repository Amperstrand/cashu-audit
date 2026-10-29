# FROZEN PREDICTIONS — keyset-rotation rung, cdk 0.18.2 (2026-10-29)

Setup: cdk-mintd 0.18.2 fakewallet arm + management RPC enabled;
mint proof P under keyset A; call RotateNextKeyset (fresh amount
list, V2); then measure. Tollgate #818 is the motivating incident
(wallet init bricks on "Unknown Keyset" after rotation).

| Leg | Prediction |
|---|---|
| R1 /v1/keys after rotation | new keyset B only (A gone from active keys) |
| R2 /v1/keysets | BOTH A and B listed (A active=false or expired flag) |
| R3 /v1/keysets/{A}/keys | 200 (retired keys still served — wallets must re-fetch) |
| R4 swap: inputs = A-proof P, outputs = B | 200 (old proofs stay spendable — fund safety) |
| W1 swap: inputs = A-proof, outputs = A-referenced | 4xx; 12001-class "Unknown Keyset" (the #818 brick identity) |
| W2 mint: paid quote, outputs reference A | 4xx 12001-class |
| W3 /v1/checkstate with A-proof's Y | 200 SPENT/UNSPENT (no keyset error on state checks) |

Any fund-loss leg failing (R4) = P0. W-legs document the wallet trap,
not a cdk bug — #818's fix is wallet-side self-heal.
Probe bugs first per house rule.
