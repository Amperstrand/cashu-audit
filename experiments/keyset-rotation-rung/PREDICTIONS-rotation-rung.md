# FROZEN PREDICTIONS — cashu-cf keyset-rotation rung (2026-10-29, before run)

Driver: `rotation_rung.py`. Target: local wrangler-dev boot of cashu-cf
origin/main `d890974` (post-094 tree; ISSUE-127 rotate fix included), env
testnut + ENVIRONMENT=signut + ADMIN_ENABLED/ADMIN_API_KEY overrides.
Scenario: mint under keyset A → admin-rotate (sat, input_fee_ppk=40) →
verify old-era proof spendability + issuance gating + identities.

| # | Prediction |
|---|---|
| P1 | Pre-rotation default mint lands on the single active keyset A (sat). |
| P2 | `POST /v1/admin/keysets/rotate {unit:sat, input_fee_ppk:40}` → 200 `{ok:true, id:B}` with B ≠ A, `input_fee_ppk:40`. |
| P3 | `GET /v1/keysets` after rotation lists A (inactive) AND B (active). |
| P4 | SWAP spending A-proofs to plain outputs → 200 (old keyset stays spendable; repo NUT-02 policy). |
| P5 | MELT spending A-proofs → 200 `state:PAID` (same spendability class). |
| P6 | `POST /v1/mint/bolt11` with explicit `keyset_id:A` → 4xx (inactive keyset not issuable), clean error identity; NOT silent issuance under A. |
| P7 | Post-rotation default mint lands on B. |
| P8 | A-proofs remain checkstate-queryable (NUT-07). |
| P9 | Fee identity: if any input fee is charged on A-proofs, it is A's fee (measured, not assumed — feeds the ISSUE-128 identity-binding question). |

A surprising FAIL is a probe bug until proven otherwise (method rule 1);
error identities are asserted, not just status codes (rule 2).
