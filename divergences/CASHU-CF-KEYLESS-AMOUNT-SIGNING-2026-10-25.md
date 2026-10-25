# CASHU-CF VIOLATION — swap signs keyless amounts, redemption refuses them (fund-loss class) (2026-10-25)

NUT rows: NUT-03 (swap output validation), NUT-02 (keyset model).
Internal finding (our implementation). Evidence:
`experiments/fresh-must-wave/` keyless probes (this session, artifacts
in FINDINGS-keyless.md context + the probe transcripts below).

## The bug (measured live on testnut 2026-10-25)

1. `POST /v1/swap` with inputs 64 sat and a single output of amount
   **63** (no 63 key exists in the keyset — all listed denominations
   are powers of 2) → **200 with a blind signature for amount 63**.
2. That signature's `C` (unblinded) **verifies against NOTHING in the
   listed keyset** — no (listed key × multiplier) combination produces
   it. The signing path uses something other than the listed
   per-amount keys for unlisted amounts.
3. Spending that 63-proof back → **400 "No public key found for amount
   63 in keyset 008e808b89acc141" (14005)** — the redemption path
   looks up the listed keyset and fails.

**The mint signs what it cannot redeem.** A wallet that swaps into a
non-denomination output amount (send-exact-amount flows produce this
shape naturally: 64 → [63, 1] to pay 63) receives ecash that the
issuing mint itself refuses — permanent, on the same mint, no recovery
path. Sign-path and verify-path disagree about the keyset.

## Family matrix (keyless output amount, balanced request)

| Arm | Swap with keyless amount | Result |
|---|---|---|
| cashu-cf (testnut) | **200 — signed, then stranded on redemption** | fund-loss |
| cdk 0.18.2 | 400/**12001 "Unknown Keyset"** (misleading identity — the keyset is known, the amount has no key — but clean reject, no loss) | safe |
| nutshell 0.21.0 | 400 opaque `{"detail":"62","code":0}` (F5-class crash identity) | safe |

Nobody returns a GOOD error for this class (cdk's "Unknown Keyset" and
ns's `detail:"N"` are both poor identities), but only cashu-cf strands
funds.

## Fix (cashu-cf, owner-gated)

Validate every swap/mint/melt output amount against the keyset's
listed denominations at request validation — the redemption path
already performs the lookup; move (or duplicate) it ahead of signing.
Error shape: 4xx with a self-describing message ("amount 63 has no key
in keyset X" — better than both references' identities). Regression
vector: the two-step probe above (swap→200-with-63 must become
swap→4xx).

## Probe transcripts (key calls)

- swap 64→[63]: 200, signatures[0].amount=63 (C_ 038f7c49…)
- unblind + exhaustive (key × multiplier) match: no hit
- swap [63-proof]→[62]: 400 "No public key found for amount 63 in
  keyset 008e808b89acc141" code 14005
- cdk balanced 64→[63,1]: 400 12001 "Unknown Keyset"
- ns balanced 64→[62,1]: 400 {"detail":"62","code":0}
