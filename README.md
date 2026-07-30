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

## Python version requirement (important)

`coincurve` (the secp256k1 binding used for BDHKE crypto) ships prebuilt
wheels for **CPython 3.9–3.13 only**. It does NOT yet ship wheels for
**Python 3.14** (released Oct 2025; upstream typically lags 1–3 months).

On a system with Python 3.14 as the default, `pip install coincurve` falls
back to a source build that fails with:

```
RuntimeError: Expected exactly one LICENSE file in cffi distribution, got 0
```

(a separate hatchling/cffi packaging bug, exposed whenever prebuilt wheels
are unavailable).

### Permanent fix — use Python 3.13 via Homebrew + a project venv

```bash
brew install python@3.13
/usr/local/opt/python@3.13/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -r conformance/requirements.txt
python3 conformance/run_matrix.py --mint https://testnut.cashu.exchange
```

This isolates cashu-audit from system Python upgrades and uses prebuilt
wheels — install completes in seconds, no source build, no LICENSE-file bug.

### When can I go back to system Python?

Once `coincurve` publishes cp314 wheels (watch
<https://pypi.org/project/coincurve/#files> for a `cp314` row). At that
point the `.venv` can be recreated with system Python and the brew
dependency retired.

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
