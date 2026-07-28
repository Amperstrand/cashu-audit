# Cashu Conformance Suite (Layer 4)

Runtime conformance testing for Cashu mints. Constructs real
spending-condition proofs (P2PK, HTLC) and verifies the mint's
accept/reject behavior across 58 scenarios.

## Quick start

```bash
cd conformance
pip install -r requirements.txt

# Run against a single mint
python run_matrix.py --mint https://testnut.cashu.exchange

# Run against multiple mints (generates comparison matrix)
python run_matrix.py \
  --mint https://testnut.cashu.exchange \
  --mint http://localhost:3338 \
  --output reports/comparison.md
```

## Scenario taxonomy

69 scenarios organized by category:

| Category | Count | What it tests |
|----------|-------|---------------|
| NUT-11 P2PK SIG_INPUTS | 10 | Basic P2PK lock/spend, multisig, locktime, refund |
| NUT-11 P2PK SIG_ALL | 16 | SIG_ALL message construction, aggregated signatures |
| NUT-12 HTLC SIG_INPUTS | 8 | Hash-lock verification, preimage + signature |
| NUT-12 HTLC SIG_ALL | 8 | HTLC + aggregated signatures |
| Melt spending conditions | 12 | P2PK/HTLC in melt pathway, SIG_ALL melt messages |
| NUT-00/03/04/05/07 Basics | 15 | Swap, mint quote, melt, checkstate, restore, token format |
| **Total** | **69** | |

Each scenario:
1. Mints regular proofs via NUT-04 (FakeWallet auto-pays)
2. Swaps them for proofs with specific spending conditions (NUT-10 secrets)
3. Attempts to spend via swap or melt with specific witness configurations
4. Checks if the mint accepts or rejects (per NUT-11/NUT-12 spec)

## Comparison matrix output

```
| Scenario | `testnut` | `cdk-local` | `nutshell` |
|----------|-----------|-------------|------------|
| `p2pk_swap_signed_succeeds` | ✅ | ✅ | ✅ |
| `p2pk_locktime_after_expiry_primary_still_works` | ❌ | ✅ | ❌ |
| `p2pk_sigall_multisig_2of3` | ✅ | ✅ | ❌ |
```

## Adding new scenarios

```python
# scenarios/my_new_tests.py
from conformance.scenarios import scenario, ScenarioResult, Result

@scenario("my_test_name", "My Category")
def _(mint):
    # construct proofs, try to spend, check result
    return ScenarioResult("my_test_name", "My Category", Result.PASS, "worked")
```

The scenario auto-registers via the `@scenario` decorator. The runner
discovers all modules in `scenarios/` automatically.

## Architecture

```
conformance/
├── conformance/
│   ├── crypto.py     # secp256k1: keygen, Schnorr, hash-to-curve, blind/unblind
│   ├── client.py     # MintClient: HTTP wrapper for NUT-03/04/05/07/11/12
│   ├── builder.py    # ProofBuilder: P2PK/HTLC construction, swap, witness
│   ├── scenarios.py  # @scenario decorator, Result enum, registry
│   └── matrix.py     # Comparison matrix generator (markdown output)
├── scenarios/
│   ├── nut11_p2pk_siginputs.py
│   ├── nut11_p2pk_sigall.py
│   ├── nut12_htlc.py
│   └── nut11_melt.py
├── run_matrix.py     # CLI entry point
├── requirements.txt
└── reports/          # Generated matrices
```

## Findings

### Multi-mint comparison (138 tests = 69 × 2 mints)

| Mint | Pass | Fail | Rate |
|------|------|------|------|
| **Nutshell v0.20.0** | 60 | 9 | 87% |
| **cashu-cf (testnut)** | 61 | 8 | 88% |
| **Combined** | 121 | 17 | **88%** |

### Bugs found and fixed in cashu-cf

| Bug | Issue | Status | Fix |
|-----|-------|--------|-----|
| #1 Locktime drops primary pathway | [cashu-cf#37](https://github.com/Amperstrand/cashu-cf/issues/37) | **FIXED** | Deploy 1d1e401 |
| #2 HTLC receiver path after locktime | [cashu-cf#37](https://github.com/Amperstrand/cashu-cf/issues/37) | **FIXED** | Deploy 1d1e401 |
| #3 HTLC refund requires preimage | [cashu-cf#38](https://github.com/Amperstrand/cashu-cf/issues/38) | **FIXED** | Deploy 1d1e401 |
| #4 HTLC + SIG_ALL sig verification | [cashu-cf#39](https://github.com/Amperstrand/cashu-cf/issues/39) | **PARTIAL** | Deploy a0347e3 (3/5 fixed) |
| #5 Shared SIG_ALL + locktime | [nutshell #1100](https://github.com/cashubtc/nutshell/issues/1100) | **UPSTREAM** | Filed on nutshell |

### Remaining failures (8 cashu-cf, 9 Nutshell)

**cashu-cf only (8):**
- 2 melt SIG_ALL scenarios (message format + HTLC)
- 2 locktime + anyone-can-spend edge cases
- 1 output tampering accepted (security concern)
- 1 HTLC SIG_ALL preimage-only
- 1 HTLC SIG_ALL locktime refund
- 1 swap double-spend not rejected at swap level

**Shared (3):**
- `p2pk_sigall_locktime_after_expiry_primary_still_works` (Bug #5)
- `p2pk_sigall_multisig_locktime_primary_still_works` (Bug #5)
- `htlc_sigall_receiver_path_after_locktime` (Bug #5)

**Nutshell only (6):**
- `mint_quote_zero_amount_fails` — Nutshell accepts amount=0
- `melt_valid_proofs_succeeds` — both mints fail this (test artifact)
- `mint_info_nut19_supported` — Nutshell doesn't report NUT-19

## Future: Wallet auditing

The framework is designed to extend to wallet-side testing. A `WalletClient`
interface (parallel to `MintClient`) would test:
- Token receiving (NUT-04/05 quote → receive → balance check)
- Token sending (create → send → recipient receives)
- Spending condition creation (wallet constructs P2PK/HTLC secrets)
- Migration and backup (wallet DB format compatibility)
