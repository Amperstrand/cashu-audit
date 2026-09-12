# Corrected Compatibility Matrix (historical-003) + Witness Catalog

*2026-09-12. Run: ai-legion:~/wallet-mint-interop/artifacts/historical-003-corrected
(144 cells; CLN auto-payer v2 paid 10/10 invoices, 0 failures; verdicts
EVIDENCE-BASED — a PASS requires proofs returned or a swap on the wire;
the old driver's silent no-op passes are impossible now).*

## Why the old matrix was wrong

The historical cashu-ts v4 p2pk/htlc "PASS"es were builder no-ops
(`ops.mintBolt11(64)` without quote or `.run()` → no HTTP, no throw).
Every v4 p2pk PASS in extensive-003..009 was fiction. v3.x rows had
the same class of problem.

## Corrected results (evidence-backed rows)

| wallet | flow | PASS/9 | Notes |
|---|---|---|---|
| cashu-ts v4 | mint_swap | **9/9** | real |
| cashu-ts v4 | p2pk_send_spend | **7/9** | ns-0.16.0: `AmountError: Unsupported amount input type` (keyset-schema family); cdk-0.17.0: `Quote not paid` (FakeWallet lazy-settle race — infra, not protocol) |
| cashu-ts v4 | htlc_receive | **6/9** | ns-0.16.0 (keyset); cdk-0.17.0 (race); cdk-0.18.0: `Cannot use 'in' operator to search for 'unit' in undefined` — **v4 wallet chokes on cdk 0.18.0's /v1/info shape** (new minor finding) |
| cashu-ts v3.6 | mint_swap | 9/9 | real |
| cashu-ts v3.0 | mint_swap | 4/9 | `Keyset verification failed` on 5 mints (version boundary, real) |
| nutshell 0.20.3 | mint_swap | 1–2/9 | F10 + keyset schema (matches the dedicated wallet sweep) |
| all wallets | htlc_refund | 0/36 | mint-side (F6/F7) + wallet-driver gaps (see below) |

## Witness-emission catalog (the d6 evidence, wire-captured)

| Wallet | Condition | Wire witness shape | N |
|---|---|---|---|
| cashu-ts v4.10.1 | P2PK spend | `{"signatures":["<64B schnorr>"]}` (string-encoded) | 14 |
| cashu-ts v4.10.1 | HTLC spend | `{"preimage":"<64-hex>"}` (string-encoded) | 18 |
| nutshell wallet 0.20.2 | HTLC refund | `{"preimage":null,"signatures":["<sig>"]}` | 1 (campaign capture) |

Cross-referenced with the mint-side vectors: cashu-ts v4's P2PK shape
is accepted by all 16 mint versions; its HTLC preimage shape likewise.
The nutshell wallet's refund shape is rejected by all cdk (F6) — the
one wallet×mint combination whose divergence is proven at BOTH ends.

## Driver status (documented limits of this run)

- v3.x p2pk/htlc flows and v4 htlc_refund still fail on API mismatch
  ("no swap on the wire" verdicts are honest FAILs, not false PASSes)
- cdk FakeWallet lazy-settle race: driver sleeps 2.5s instead of
  polling the quote (1-cell flake)
- Remaining work to a fully-real matrix: v3 flow adaptation +
  v4 htlc_refund builder + quote polling (one driver session)

## Reproduce

```bash
ssh ai-legion 'cd ~/wallet-mint-interop && python3 runner.py'   # matrix.yml: historical-003-corrected
```
