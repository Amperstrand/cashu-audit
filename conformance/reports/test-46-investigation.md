# Conformance Test 46: p2pk_sigall_output_amounts_swapped_fail

## Bug Description

The conformance test `p2pk_sigall_output_amounts_swapped_fail` verifies that a
SIG_ALL swap with tampered output amounts (amounts swapped between outputs) is
rejected by the mint. The mint should reject this because the SIG_ALL signature
is computed over the ordered (amount, B_) pairs, so swapping amounts invalidates
the signature.

**Expected:** HTTP 400 (rejected)
**Actual:** HTTP 200 (accepted) — the swap succeeds with tampered outputs.

## Reproduction

```python
# From conformance/scenarios/nut11_p2pk_sigall.py test 46
# 1. Create P2PK proofs with SIG_ALL
# 2. Construct swap with output amounts deliberately swapped
# 3. Compute SIG_ALL witness over the SWAPPED order
# 4. Submit swap — should be rejected but isn't
```

## Environment Results

| Environment | Result | Notes |
|---|---|---|
| testnut | ✅ rejected | Passes — likely keyset config difference |
| signut | ❌ accepted | Fails |
| nofees.testnut | ❌ accepted | Fails |
| v2.testnut | ❌ accepted | Fails |
| payto.fakewallet | ❌ accepted | Fails |

## Hypothesis: Keyset Configuration Difference

testnut uses `max_order: [10,18]` (array format) while other envs use
`max_order: 10` or `max_order: 18` (single value). The SIG_ALL validation
may behave differently depending on how output amounts are decomposed
across keyset denominations.

## Investigation Steps

1. Compare wrangler.toml KEYSETS config for testnut vs nofees/v2/payto
2. Check if the SIG_ALL validation in `src/mint/spending-conditions.ts`
   properly validates output amounts against the witness
3. Run the test scenario manually with debug logging to see exactly
   what the mint accepts/rejects
4. Check if the issue is in the swap handler (`src/mint/router.ts`)
   vs the spending condition validator (`src/mint/spending-conditions.ts`)

## Priority: P2

The test passes on testnut (our primary CI environment), so this is not
blocking development. However, it's a real spec compliance gap that
affects 4/5 deployed environments.
