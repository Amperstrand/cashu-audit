# Scenario: Race Condition — Double Proof Invalidation (#683)

> **Source**: [cashubtc/nutshell#683](https://github.com/cashubtc/nutshell/issues/683)
> **Severity**: Medium (low probability, high impact)
> **Affects**: Nutshell (confirmed), cashu-cf (needs testing), CDK (needs testing)

## Description

When a melt operation takes a long time (e.g., Lightning payment delay), the user can GET the melt quote status concurrently. If the mint marks the quote as PAID in the GET handler AND invalidates proofs there, the original POST handler will try to invalidate the same proofs again when it returns.

## Reproduction steps

1. Configure FakeWallet with `fakewallet_delay_outgoing_payment = 15` seconds
2. Mint tokens (amount=100)
3. Create melt quote
4. Fire `POST /v1/melt/bolt11` with the tokens (will block ~15s)
5. After ~8s, fire concurrent `GET /v1/melt/quote/bolt11/{id}`
6. Wait for POST to complete
7. Check:
   - POST returns 200 (not error)
   - GET returns state=PAID
   - `POST /v1/checkstate` shows proofs as SPENT (not error)
   - No "already spent" errors in mint logs

## Expected behavior

- Both requests return 200
- Proofs are marked SPENT exactly once
- No double-invalidation error
- Mint state is consistent

## What catches this

| Layer | Catches? | Why |
|---|---|---|
| Layer 1 (greatspectations) | ❌ | No spec text about concurrency |
| Layer 3 (AI audit) | ❌ | Static code reading can't predict runtime race |
| **Layer 4 (E2E)** | ✅ | **Concurrent HTTP requests with timing control** |

## Implementation

Requires:
- FakeWallet with configurable delay
- Concurrent HTTP client (asyncio)
- Proof state verification after race

See: `e2e/lib/mint_client.py` → `scenario_race_condition_683()`

**Note**: Full reproduction requires real blind signature crypto to construct valid proofs. The current implementation uses dummy B_ values which will fail at the crypto verification stage. To fully test, we need either:
1. @cashu/cashu-ts integration (JavaScript crypto)
2. CDK wallet library (Rust)
3. Manual proof construction with secp256k1 operations

## Cross-implementation testing

Run against all implementations to see which have the race:
```bash
# cashu-cf
python3 e2e/lib/mint_client.py --mint-url http://localhost:8787 --scenario race-condition

# testnut (remote FakeWallet)
python3 e2e/lib/mint_client.py --mint-url https://testnut.cashu.exchange --scenario race-condition
```
