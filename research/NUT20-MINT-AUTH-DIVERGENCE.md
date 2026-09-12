# NUT-20 Mint-Auth Scheme Divergence: nutshell wallet 0.20.3 cannot mint on cdk 0.17.x

*2026-09-12. Found while completing the wallet-side HTLC refund test —
the wallet failed to MINT on cdk before ever reaching the refund path.
Wire captured via httpx monkeypatch. Probes:
`experiments/must-gap-vectors/` (wallet_mint_probe / mint_shape_probe
logic inlined in research notes below).*

## The finding

nutshell wallet **0.20.3** (released 2026-07-22, current latest) attaches
NUT-20 authentication to every mint:

1. Quote creation includes `pubkey` (ephemeral wallet key)
2. `/v1/mint/bolt11` includes `signature` — schnorr over the
   **new-scheme message**:
   `sha256("Cashu_MintQuoteSig_v1" ‖ len(quote) ‖ quote ‖ Σ len-prefixed(amount, B_))`

cdk **0.17.0/0.17.6** mints verify the **legacy scheme**:
`sha256(quote_id ‖ concat(B_ as utf-8))` — and reject the new-scheme
signature with `{"code":20008,"detail":"Signature missing or invalid"}`.

cdk **0.18.0** accepts BOTH schemes (new-with-pubkey 200, legacy 200;
it does reject a signature with no pubkey bound to the quote — sane).

## Empirical matrix

| Mint request | cdk 0.17.0 | cdk 0.17.6 | cdk 0.18.0 | nutshell 0.20.3 |
|---|---|---|---|---|
| no signature (raw) | 200 | 200 | 200 | 200 |
| new-scheme sig, pubkey bound | **400/20008** | **400/20008** | 200 | 200 |
| new-scheme sig, no pubkey | 400/20008 | 400/20008 | 400/20008 | 200 (ignored) |
| legacy-scheme sig, pubkey bound | 200 | 200 | 200 | (untested) |

Wallet-side boundary (wallet images minting 2 sats on cdk 0.17.0):

| nutshell wallet | 0.16.5 | 0.18.2 | 0.19.0 | 0.20.0 | 0.20.2 | **0.20.3** |
|---|---|---|---|---|---|---|
| mint on cdk 0.17.0 | PASS | PASS | PASS | PASS | PASS | **FAIL 20008** |

## Full sweep (wallet 0.20.3 × 9 battery mints, 2026-09-12)

| Mint | Mint result for nutshell wallet 0.20.3 |
|---|---|
| cdk 0.17.0 | **FAIL** 20008 (NUT-20 legacy-only) |
| cdk 0.17.6 | **FAIL** 20008 (NUT-20 legacy-only) |
| cdk 0.18.0 | PASS |
| nutshell 0.16.5 | **FAIL** KeysetNotFoundError (no `active` in keyset schema) |
| nutshell 0.18.2 | **FAIL** KeysetNotFoundError (same) |
| nutshell 0.19.0 | **FAIL** 20008 (mint lacks new-scheme verification) |
| nutshell 0.20.0 | **FAIL** 20008 (same) |
| nutshell 0.20.2 | **FAIL** 20008 (same) |
| nutshell 0.20.3 | PASS |

**The current nutshell wallet can mint on 2 of 9 tested mints.** The
NUT-20 blast radius is larger than the cdk 0.17.x finding: every
nutshell mint before 0.20.3 also rejects the new-scheme signature
(mint-side verification landed with 0.20.3). The 0.16.5/0.18.2 failures
are the previously-documented keyset-schema change.

## Impact

**The current nutshell wallet cannot mint on any cdk 0.17.x mint, nor
on any nutshell mint below 0.20.3.**
Users experience: "Mint Error: Signature missing or invalid" — opaque,
no hint that it's a scheme mismatch. Not fund-loss (no tokens yet), but
a total mint-flow block between the two most-deployed implementation
families at their common versions (cdk 0.17.x mints are widely deployed;
nutshell 0.20.3 is the latest wallet release).

## Relationship to the earlier "blind-sig" correction

`research/CORRECTION-blind-sig-false-positive.md` stated the nutshell
wallet CAN mint on all implementations — true for wallet ≤0.20.2. The
0.20.3 wallet changed mint-quote behavior (NUT-20 always-on). The
historical extensive-003 matrix recorded nutshell-0.20.3-wallet ×
cdk mint_swap as FAIL (driver crash), so this incompatibility was never
measured with a working driver until now.

## Spec status

NUT-20 mint-request authentication is not in the published NUTs the
auditor quoted (scheme lives in the implementations; nutshell core has
`construct_message` (new) and `construct_message_legacy`). Two live
schemes + one migration = the same dual-representation pattern as the
SIG_ALL message change (F5). Amendment material: normative NUT-20
message construction + transition rules.

## Reproduce

```bash
# wallet boundary
for v in 0.16.5 0.18.2 0.19.0 0.20.0 0.20.2 0.20.3; do
  docker run --rm --network host -e MINT_URL=http://127.0.0.1:35000 \
    -w /app -e PYTHONPATH=/app cashubtc/nutshell:$v \
    python3 /drv/wallet_mint_probe.py
done
# scheme matrix: mint_shape_probe.py against each battery cdk port
```
