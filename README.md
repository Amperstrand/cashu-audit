# cashu-audit

Cross-implementation Cashu conformance testing and spec compliance auditing.

## Quick Start

```bash
cd conformance
pip3 install requests coincurve pyyaml --break-system-packages

# Run against a single mint
python3 run_matrix.py --mint https://testnut.cashu.exchange

# Run against multiple mints
python3 run_matrix.py --mint https://testnut.cashu.exchange --mint https://rugs.cashu.exchange

# Run from config file
python3 run_matrix.py --mints mints.yaml
```

## Architecture

```
conformance/
├── conformance/          # Framework core
│   ├── client.py         # HTTP client for Cashu NUT REST endpoints
│   ├── crypto.py         # BDHKE crypto (hash_to_curve, blinding, Schnorr)
│   ├── builder.py        # Proof construction (P2PK, HTLC, multisig)
│   ├── scenarios.py      # Scenario registration framework
│   └── matrix.py         # Cross-mint comparison matrix generator
├── scenarios/            # Test scenarios (NUT-by-NUT)
│   ├── nut_basics.py     # NUT-01/06/19: Info, keysets, caching
│   ├── nut02_keysets.py  # NUT-02: Keyset validation
│   ├── nut11_p2pk_*.py   # NUT-11: P2PK SIG_INPUTS + SIG_ALL
│   ├── nut11_melt.py     # NUT-11: P2PK in melt operations
│   ├── nut12_htlc.py     # NUT-14: HTLC spending conditions
│   ├── nut04_accounting.py # NUT-04: Accounting fields
│   ├── nut20_quotesig.py # NUT-20: Quote signatures
│   └── nut29_batch.py    # NUT-29: Batch operations
├── reports/              # Generated test reports
├── mints.yaml            # Mint endpoint configuration
└── run_matrix.py         # CLI runner
```

## Scenario Framework

Each scenario is a Python function decorated with `@scenario`:

```python
from conformance.scenarios import scenario, ScenarioResult, Result

@scenario("my_test", "NUT-11", "Tests P2PK verification")
def my_test(mint: MintClient) -> ScenarioResult:
    # Create proofs, call mint, check result
    if success:
        return ScenarioResult(name="my_test", category="NUT-11", result=Result.PASS)
    else:
        return ScenarioResult(name="my_test", category="NUT-11", result=Result.FAIL, note="reason")
```

## Adding New Mints

Edit `mints.yaml`:
```yaml
mints:
  - name: my-mint
    url: https://my-mint.example.com
    type: cashu-cf  # or nutshell, cdk, nutmix
```

## Reports

Reports are generated in `reports/`:
- `matrix.md` — Cross-mint comparison matrix
- `FINDINGS-*.md` — Detailed findings per mint

## Divergence Reports

`divergences/` contains spec compliance divergence reports comparing cashu-cf
against Nutshell (Python reference) and CDK (Rust reference).
