# SIG_ALL Melt-Path Vectors (11.md:153-161)

*2026-09-12. Driver: `experiments/must-gap-vectors/sigall_melt_vectors.py`.
Fee-free ephemeral nutshell 0.20.3 + battery cdk 0.17.0/0.18.0.*

## Vectors

- M1: plain melt (no conditions) — control
- M2: single-input SIG_ALL melt, spec message (`secret‖C … ‖amount‖B_ … ‖quote_id`)
- M3: multi-input SIG_ALL melt (same data+tags, distinct nonces), witness on first input

## Results

| Mint | M1 | M2 | M3 |
|---|---|---|---|
| nutshell 0.20.3 (fee-free) | 200 | 200 | **200** |
| cdk 0.17.0 | 200 | 200 | 200 |
| cdk 0.18.0 | 200 | 200 | 200 |

All conformant with the spec message order. Notable details:

1. **Message order matters and the spec is right**: `inputs ‖ outputs ‖ quote_id`
   (quote LAST — 11.md:157). My first attempt put quote_id in the middle and
   nutshell rejected it ("signature threshold not met. 0 < 1."). Implementations
   follow the spec order; drivers and wallets must too.
2. **Multi-input SIG_ALL melts work on nutshell 0.20.3** — the same
   construction that fails for SWAPS (F5's opaque `{"detail":"3"}`) succeeds
   for melts. The multi-input SIG_ALL defect is **swap-path-specific** on
   nutshell 0.20.3, narrowing the F5 bug to the swap verification/pending
   handling rather than the sigall core.
3. cdk melts return `change` + `fee_reserve` accounting (spec-conformant
   NUT-05 melt semantics); FakeWallet settles melts instantly on all three.

## Reproduce

```bash
docker run --rm --network host -v /tmp/mgv-drv:/drv:ro \
  cashubtc/nutshell:0.20.3 python3 /drv/sigall_melt_vectors.py <mint_url>
```

## Version sweep (nutshell release line)

| Mint | M2 single-input | M3 multi-input |
|---|---|---|
| 0.16.5 | REJECT "no valid signature provided" | REJECT |
| 0.18.2 | REJECT "threshold 0 < 1" | REJECT |
| 0.19.0 | REJECT "threshold 0 < 1" | REJECT |
| 0.20.2 | REJECT "threshold 0 < 1" | REJECT |
| **0.20.3** | **200** | **200** |
| cdk 0.17.0/0.18.0 | 200 | 200 |

The SIG_ALL melt message family flipped old→new at the same boundary as
the swap message (0.20.2 → 0.20.3). Every nutshell below 0.20.3 rejects
the spec-conformant melt signature; cdk accepts it across 0.17–0.18.
