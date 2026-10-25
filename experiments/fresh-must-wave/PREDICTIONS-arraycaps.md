# FROZEN PREDICTIONS — mint/swap array caps (2026-10-25, before run)

Question: per-endpoint input/output caps on the FUND-PATH endpoints
(mint outputs, swap inputs, swap outputs), and their error identities.
Spec error_codes.md: 11014 "Max inputs exceeded" (NUT-03/05), 11015
"Max outputs exceeded" (NUT-03/04/05).

| Probe | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| mint 128 × 1-sat outputs | accept (mint-output cap ≥128? unknown) | accept | accept |
| swap 128 inputs → 1 output | **reject: cf swapInputsCap=100 (source: MAX_SWAP_INPUTS default)**; identity 11014 or cf-14xxx? | 422 pydantic or 11014 | 11014 |
| swap 16 inputs → 1001 outputs | length-check-first or balance-error-first (check-order datum); then adjusted-sum retry → cap cell | 422 too_long (1000) | 11015 |

Secondary: which check fires first (length vs balance vs keyset);
exact "max N" values from error messages; whether mint-endpoint output
caps exist at all below 1001.

Honest note: 128-input leg assumes the mint of 128 one-sat proofs
succeeds; if the MINT endpoint caps outputs below 128, that is itself
the mint-cap datum and the swap-input leg reruns at the achieved count.
