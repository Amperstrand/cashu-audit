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

58 scenarios organized by spending condition type × signature flag × transaction type:

| Category | Count | What it tests |
|----------|-------|---------------|
| NUT-11 P2PK SIG_INPUTS | 10 | Basic P2PK lock/spend, multisig, locktime, refund |
| NUT-11 P2PK SIG_ALL | 16 | SIG_ALL message construction, aggregated signatures |
| NUT-12 HTLC SIG_INPUTS | 8 | Hash-lock verification, preimage + signature |
| NUT-12 HTLC SIG_ALL | 8 | HTLC + aggregated signatures |
| Melt spending conditions | 12 | P2PK/HTLC in melt pathway, SIG_ALL melt messages |
| **Total** | **54** | |

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

### cashu-cf (testnut.cashu.exchange)

- **FAIL** `p2pk_locktime_after_expiry_primary_still_works` — drops primary
  P2PK pathway after locktime expiry. Same bug as [nutshell #1009](https://github.com/cashubtc/nutshell/issues/1009).
  NUT-11 says primary conditions "continue to apply" after locktime.

## Future: Wallet auditing

The framework is designed to extend to wallet-side testing. A `WalletClient`
interface (parallel to `MintClient`) would test:
- Token receiving (NUT-04/05 quote → receive → balance check)
- Token sending (create → send → recipient receives)
- Spending condition creation (wallet constructs P2PK/HTLC secrets)
- Migration and backup (wallet DB format compatibility)
