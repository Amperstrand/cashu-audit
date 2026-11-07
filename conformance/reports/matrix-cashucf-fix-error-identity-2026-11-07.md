<!-- Provenance: Amperstrand/cashu-cf branch fix/error-identity-audit68 @ 28f08ca5
(off origin/main 2e3c5cf9), PR #116, ISSUE-148 — wrangler dev --env local
(wrangler 4.154.0, FakeWallet, MINT_PRIVATE_KEY-derived keysets, sat-only,
--var ENABLE_USD_BACKEND:true to mirror the deployed testnut's flag-on/
keysets-sat-only shape), arm name "cashucf-errid-local".
Same-session pristine-main baseline (origin/main @ 2e3c5cf9, same env, same
port): errid 3/8; full-suite 112/11/130.
Row-by-row diff vs baseline: exactly the 5 errid rows flip red->green.
Raw capture: ../results/error-identity/cashucf-errid-local-20261107-041656.json
(local NUT19 cache OFF — env.local default; the deployed testnut runs ttl 300). -->

# Cashu Conformance Matrix — 2026-11-07 (cashu-cf fix/error-identity-audit68, local arm)

**Targets** (identity captured at run start):
- `http://127.0.0.1:8799` — cashucf-errid-local / Nutshell-CF/0.0.1

**Summary**: 117 passed, 6 failed, 7 skipped (130 total)
Baseline (pristine `origin/main` @ 2e3c5cf9, same env): 112/11/7.

## NUT-00 error identity

| Scenario | baseline `main@2e3c5cf9` | branch `fix/error-identity-audit68@28f08ca5` |
|---|---|---|
| `errid_swap_unknown_keyset_code_12001` | ❌ 400/14005 `Invalid output keyset id: 0000000000000000` | ✅ 400/**12001** |
| `errid_swap_duplicate_inputs_code_11007` | ✅ 400/11007 (ISSUE-138 phase 1) | ✅ 400/11007 |
| `errid_swap_underfunded_code_11005` | ❌ 400/10000 `available for fees (-8)` | ✅ 400/**11005** (detail unchanged) |
| `errid_swap_spent_proofs_code_11001` | ❌ 400/14005 (T1-wrapped `Failed to batch set proofs to PENDING: ProofStateError: …` collapsed to generic) | ✅ 400/**11001** `token_already_spent` (detail unchanged) |
| `errid_swap_outputs_already_signed_code_11003` | ❌ **200 + identical sigs** (ungated restore-replay) | ✅ 400/**11003** (restore now gated on inputs consumed; concurrent/retry replay unchanged; inputs not burned — cashu-cf spend-matrix S13b) |
| `errid_mint_quote_unit_unsupported_code_11013` | ❌ **200 + sat invoice for `unit:"usd"`** (env-flag-only validation; flag ON, keysets sat-only) | ✅ 400/**11013** `No active keyset for unit "usd". Active units: sat` |
| `errid_validation_error_nut00_envelope` | ✅ 400/{error,detail,code} 14005 | ✅ 400/{error,detail,code} **10001** (P07-class alignment; envelope shape unchanged) |
| `errid_p2pk_wrong_witness_reasoned_rejection` | ✅ 403/30006 `Signature threshold not met. 0 < 1` | ✅ unchanged |

> Audit-snapshot note: the 2026-11-04 matrix measured testnut @ cashu-cf
> `6cd249e` at **2/8** (pre ISSUE-138 phases 1+2: dup-inputs 14008,
> spent 30001). At current `origin/main` (phases 1+2 merged) the same
> family is 3/8 locally — the residual five are what ISSUE-148 closes.
> Post-deploy re-verification on the deployed testnut arm is queued in
> ISSUE-148 (the deployed P09 shape — flag ON, sat-only pinned keysets —
> is what this local arm mirrors).

## Full-suite no-drift (130 scenarios, both arms)

Row-identical between baseline and branch except exactly the five errid
rows above. Residual branch FAILs, all pre-existing on the baseline arm
in this env (not error-identity rows):

- `mint_info_nut19_supported`, `swap_replay_returns_cached_response`,
  `melt_replay_returns_cached_response` — NUT-19 cache OFF in env.local
  (deployed testnut advertises ttl 300 and passes these).
- `secret_encoding_entropy_trap_rejected` — positioned lenient-mint
  divergence (registry row 38: "do not refile per run").
- `swap_never_signs_keyless_amount`, `mint_never_signs_keyless_amount` —
  pre-existing on both arms of this env shape.

## Mutation-checking

The baseline arm IS the red side: the branch differs from pristine main
only by the ISSUE-148 diff, and exactly the five guarded rows clear —
no scenario passes vacuously, no unrelated row moves. Cashu-cf-side
locks: `test:spend-matrix` 18/18 (S1/S2 re-locked to 10001; new S11
12001, S12 11005, S13/S13b 11003 + inputs-still-spendable, S14/S14b
11013 + sat quotes unblocked), unit families in
`test/unit/{error-codes,swap/swap-idempotency,mint/mint-api}` including
both sides of the restore gate and the T1-wrapped spent/pending shapes.

## Battery disclosure (cashu-cf CI is billing-blocked)

Local battery minus fleet-health: typecheck ✓, spec:check ✓,
test:unit 2731/0 ✓, test:spend-matrix 18/18 ✓,
validate:logging:enhanced ✓, audit:nut08 36/36 ✓, test:live:testnut
109/110 (the 1 failure — restore.live.test.ts empty-outputs-array,
deployed mint returns 200 — reproduces 1:1 from pristine main; disclosed
in PR #116). **fleet-health SKIPPED** (WOS leg, billing-blocked).
