# Cashu Conformance Suite

## Running Tests

```bash
pip3 install requests coincurve pyyaml --break-system-packages
python3 run_matrix.py --mint https://testnut.cashu.exchange
```

## Current Coverage

| NUT | Scenarios | Description |
|-----|-----------|-------------|
| NUT-01/06 | 6 | Info endpoint, keysets, mint metadata |
| NUT-02 | 6 | Keyset validation, fees, units |
| NUT-03 | 3 | Swap (split tokens) |
| NUT-04 | 5 | Mint quote accounting (amount_paid, amount_issued, updated_at) |
| NUT-05 | 3 | Melt quote lifecycle |
| NUT-07 | 2 | Checkstate (UNSPENT/PENDING/SPENT) |
| NUT-08 | 6 | Fee calculation and validation |
| NUT-09 | 1 | Restore signatures |
| NUT-11 | 20+ | P2PK SIG_INPUTS + SIG_ALL (swap + melt) |
| NUT-14 | 10+ | HTLC spending conditions (swap + melt) |
| NUT-19 | 1 | Cache headers |
| NUT-20 | 4 | Quote signature validation |
| NUT-29 | 3 | Batch mint/check operations |
| **Total** | **80+** | |

## Adding Scenarios

See `scenarios/` directory for examples. Use the `@scenario` decorator.
