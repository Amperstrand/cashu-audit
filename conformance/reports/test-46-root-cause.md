# Test 46 Root Cause Analysis: p2pk_sigall_output_amounts_swapped_fail

## The Bug Is in the TEST, Not the Mint

### What the test does

```python
# scenarios/nut11_p2pk_sigall.py, line 370-375
tampered_outputs = [dict(o) for o in api_outputs]
if len(tampered_outputs) >= 2:
    # Swap B_ values between outputs 0 and 1
    tampered_outputs[0]["B_"], tampered_outputs[1]["B_"] = \
        tampered_outputs[1]["B_"], tampered_outputs[0]["B_"]
elif tampered_outputs:
    # Single output: flip first char of B_
    tampered_outputs[0]["B_"] = "0" + tampered_outputs[0]["B_"][1:]
```

### Why the single-output path is a NO-OP

Compressed secp256k1 public keys start with `02` or `03` (hex prefix). The
tamper replaces the first character with `"0"`:

- `"02abc..."` → `"0" + "2abc..."` = `"02abc..."` — **unchanged!**
- `"03abc..."` → `"0" + "3abc..."` = `"03abc..."` — **unchanged!**

The tamper does nothing because the first character is already `"0"`.

### Why testnut passes but others fail

The test amount (8 sats from `_prepare_outputs`) decomposes differently
depending on keyset `max_order`:

- **testnut** (`max_order: [10,18]`): The builder may produce multiple outputs
  (e.g., 4+4 or 2+2+4) depending on how the builder decomposes amounts,
  triggering the `len >= 2` path which actually swaps B_ values.
  
- **Other envs** (`max_order: 10`): The builder produces a single 8-sat output,
  triggering the `elif` path which is a no-op.

The mint accepts the "tampered" swap on other envs because nothing was actually
tampered — the B_ value is identical to the original.

### Fix

The test should use a tamper that actually modifies the B_ value for the
single-output case. For example:

```python
# Flip prefix from 02→03 or 03→02 (valid but different point)
first_char = tampered_outputs[0]["B_"][0]
tampered_outputs[0]["B_"] = ("03" if first_char == "0" and tampered_outputs[0]["B_"][1] == "2"
                            else "02") + tampered_outputs[0]["B_"][2:]
```

Or better: generate 2+ outputs to exercise the swap path:

```python
# Use a larger amount that decomposes to multiple outputs
proofs = builder.mint_proofs(15)  # 8+4+2+1 = 4 outputs
```

### Conclusion

This is **not a mint bug**. The mint correctly validates SIG_ALL signatures
and rejects actual tampering (proven by the 2-output path passing on testnut).
The test's single-output fallback path is broken.

**Action:** File a bug in the cashu-audit repo to fix the test, not the mint.
