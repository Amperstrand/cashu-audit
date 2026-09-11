# CORRECTION: "Blind-sig incompatibility" was a test driver bug, not a protocol finding

*2026-09-11. Correcting our own analysis — this is what the frozen-prediction
discipline is for.*

## What we claimed

In the historical compatibility matrix (historical-001) and extensive-009,
we reported:

> "The nutshell Python wallet can connect to and create quotes on all mints,
> but the blind-signature MINT operation fails on all cross-implementation
> pairs — it only works on same-version nutshell mints."

This was filed as a "key interop finding" and attributed to a
"protocol-level incompatibility in the blind-sig exchange."

## What actually happened

The nutshell Python driver used `w.swap()` to test the mint_swap flow:

```python
await w.swap(proofs, 64, None)
```

The `Wallet` class in nutshell does NOT have a `swap()` method. When we
called it, we got:

```
AttributeError: 'Wallet' object has no attribute 'swap'
```

This caused the Python script to crash with exit code 1, producing no
result.json. The runner recorded the cell as FAIL.

But the **minting itself was always succeeding**. The output logs clearly
show:

```
wallet loaded, keysets: 1
quote: 01a08cd7-e830-74e1-8
minted: 15 proofs          ← THE BLIND SIGNATURE WORKED
AttributeError: ...        ← OUR BUG, AFTER THE MINT
```

The blind-sig protocol exchange (blind → submit → unblind) was completing
successfully on ALL mints. Our test driver crashed at the next step
(trying to spend the minted proofs) and we misattributed the failure.

## When we caught it

In extensive-010, we simplified the mint_swap flow to only check whether
proofs were successfully minted (removing the buggy swap call). The result:
**nutshell wallet PASSes on ALL mints** including cdk 0.18.0.

## What the corrected compatibility matrix looks like

| Wallet | Mint | Old (buggy) | Corrected |
|---|---|---|---|
| nutshell 0.20.3 | ns-0.20.3 | PASS | PASS |
| nutshell 0.20.3 | ns-0.20.0 | FAIL | **PASS** (minting works) |
| nutshell 0.20.3 | cdk-0.18.0 | FAIL | **PASS** (minting works) |
| nutshell 0.20.3 | cdk-0.17.x | FAIL | **PASS** (minting works) |

The "nutshell wallet only works on same-version mints" claim was wrong.
The nutshell wallet can mint on ALL implementations. The actual incompatibility
surface is narrower than we measured.

## Why this matters

1. **Our historical matrix understated compatibility.** The nw-0.20.3 row
   showed 2/36 PASS. The corrected number is higher (mint_swap passes on
   all mints; only the advanced flows — P2PK, HTLC — may still fail).

2. **The "cross-implementation blind-sig protocol change" we attributed to
   nutshell 0.20.3's #1008 overhaul doesn't exist** — at least not at the
   mint level. The blind-sig protocol is compatible across implementations.

3. **We filed issues based on this false finding.** GitHub issue on
   lightning-playground (blind-sig incompatibility investigation) needs to
   be updated or closed.

4. **The "fund-loss vector: cross-implementation blind-sig" in our
   enumeration was wrong.** This vector should be removed.

## The lesson

This is the exact failure mode the frozen-prediction discipline is designed
to catch: a FAIL that was caused by the test infrastructure, not the system
under test. We violated our own rule:

> "Mismatch = probe bug until proven otherwise"

We saw FAIL, attributed it to the system (nutshell wallet's blind-sig
protocol), and moved on. The mismatch WAS a probe bug. We should have
investigated the error message before drawing conclusions.

**New rule added to the framework:** When a cell FAILs, always read the
driver's stdout/stderr to verify the error comes from the system under test,
not from the test driver itself.

## Next steps

1. Re-run the historical matrix with the fixed driver to get corrected numbers
2. Update the lightning-playground issue with this correction
3. Remove "cross-implementation blind-sig" from the fund-loss vectors
4. Update the TollGate analysis to reflect that gonuts and nutshell wallets
   are MORE compatible than we measured

## Follow-up: the ACTUAL compatibility issue (2026-09-11, historical-002-corrected)

Re-running the matrix with the fixed driver reveals the REAL reason nutshell
wallet fails on non-same-version mints — it's NOT the blind-sig protocol:

### Issue 1: Keyset schema mismatch (nutshell → older nutshell)

The nutshell 0.20.3 wallet expects keysets to have an `active` field:
```
ERROR: 1 validation error for KeysResponse
keysets.0.active — Field required [type=missing]
```

Older nutshell mints (0.16-0.20.0) don't include the `active` field in their
keyset responses. The 0.20.3 wallet's Pydantic model REQUIRES it. Result:
the wallet sees ZERO keysets and can't even create a quote.

**This is a schema breaking change within nutshell's own version history.**

### Issue 2: CLN payment gap (nutshell → cdk with CLN backend)

```
Exception: Mint Error: Quote not paid (Code: 20001)
```

The cdk mints in this run use CLN signet backend. The quote is created
successfully, but the Lightning invoice isn't paid (our auto-payer doesn't
work). With FakeWallet-backed cdk mints (extensive-010), this PASSES.

**This is an infrastructure gap, not a wallet compatibility issue.**

### Corrected compatibility matrix for nutshell wallet 0.20.3

| Mint type | Works? | Root cause if not |
|---|---|---|
| ns-0.20.3 (same version) | ✅ | — |
| ns-0.16-0.20.0 (older nutshell) | ❌ | Keyset schema: `active` field required |
| cdk (FakeWallet) | ✅ | — (proven in extensive-010) |
| cdk (CLN signet) | ❌ | Auto-payer doesn't pay invoices |
| testnut (cashu-cf) | ✅ | — (FakeWallet) |

### Summary of corrections

1. **Original claim**: "blind-sig protocol incompatibility" — WRONG (driver bug)
2. **First correction**: "nutshell works on all mints" — PARTIALLY RIGHT
   (works on all FakeWallet-backed mints)
3. **Actual finding**: two separate issues:
   a. Keyset schema change within nutshell (breaking change)
   b. CLN payment gap in our infrastructure (not a wallet issue)
