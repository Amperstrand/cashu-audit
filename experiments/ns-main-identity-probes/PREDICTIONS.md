# FROZEN PREDICTIONS — ns-main identity probes (2026-10-31, pre-run)

Target: nutshell main @ ac1c2e0 (unreleased; 0.21.0+70), FakeWallet, :8738.
Baseline contrast arm: released 0.21.0 behavior per audit §2 source reading.
Predictions locked from test-artifacts/UPSTREAM-AUDIT-2026-10.md §2.2-2.5
(source-verified there). A surprising FAIL = probe bug until proven otherwise.

| # | Scenario | Prediction (ns-main wire) | 0.21.0 contrast |
|---|---|---|---|
| S0 | control: FakeWallet mint cycle + plain swap | 200 both (rig health) | same |
| S1a | swap P2PK-locked proof, witness ABSENT | 400 `{"detail":"no signatures in proof.","code":11000}` | same identity (swallowed-parse made absent≡unparsable) |
| S1b | swap P2PK-locked proof, witness `{"foo":"bar"}` | 400 `{"detail":"witness could not be parsed.","code":11000}` | `"no signatures in proof."` (identical to absent — the fork this verifies) |
| S2 | sqlite `keysets.balance` forced to 0, then swap VALID proofs | 400 `{"detail":"keyset balance is insufficient for redemption","code":11000}` | no balance enforcement — swap succeeds 200 |
| S3 | swap input secret = 2000 chars | 422, `detail[0].type=="string_too_long"`, loc contains ("body","inputs",0,"secret"), body has NO `code` field (framework-layer) | 400/`code` path (no pydantic bound) — and hash_to_curve runs |
| S4 | unlocked NUT-04 bolt11 quote create | 2xx, `pubkey` key ABSENT from response JSON | `"pubkey": ""` present |

Assert style: exact error-identity (status + detail string + code field), not any-4xx.

## Discovered during run (post-hoc, NOT frozen predictions)
- S5 single non-denomination swap output (e.g. 63 after 1-sat fee on a
  64-sat input) → 400 `{"detail":"63","code":0}` — `KeyError(amount)` from
  `keyset.private_keys[output.amount]` (ledger.py `_sign_blinded_messages`)
  leaks through the session wrapper. Discovered in probe-bug debugging
  (first two runs); assertion added after observation. F5-class opaque
  identity, ns-main only — cf splits to denominations so wallets never
  hit it; raw-protocol clients do.
