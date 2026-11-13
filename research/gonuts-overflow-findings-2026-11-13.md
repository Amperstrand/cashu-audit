# Value-flow retest findings — gonuts-tollgate wallet (2026-11-13)

Retest of the gonuts wallet code with the value-flow pass (the #1212 lesson:
every numeric field from the mint/wire, check overflow in aggregates). Four
overflow-prone sites in the melt path, all on **mint-supplied** values with
**no overflow check**:

## The sites

| Line | Expression | Fields | Consequence of overflow |
|---|---|---|---|
| wallet.go:1239 | `amountNeeded := quote.Amount + quote.FeeReserve` | both from the mint's quote response | wraps to small number → `getProofsForAmount` selects too few proofs → melt fails or underpays |
| wallet.go:1560 | `meltQuoteResponse.Amount + meltQuoteResponse.FeeReserve + fees > proofsAmount` | mint-supplied + computed fees | wraps → comparison inverts → MPP split goes wrong |
| wallet.go:1716 | `selectedProof.Amount >= remainingAmount + fees` | wallet + computed | wraps → break condition never fires → wrong proof set |
| wallet.go:2371 | `total < quoteAmount + uint64(fees)` | wallet + quote + fees | wraps → insufficient-inputs check passes when it shouldn't → **this is the `constructMeltChangeProofs` ceiling path** |

## Reachability

All four are in the melt path, which is the exact path the #46 recovery
contract governs. The mint supplies `Amount` and `FeeReserve` in the quote
response (`wallet/client/client.go` performs no validation on either). A
hostile mint returning `Amount = MaxUint64-1, FeeReserve = 2` makes line
1239's `amountNeeded` wrap to `1` — the wallet then attempts to select 1
satoshi of proofs for a MaxUint64 melt.

Line 2371 is the ceiling check inside `constructMeltChangeProofs` — the same
function the #46 contract's ceiling gate (ACC-V3) protects. The ceiling is
`total - quoteAmount - fees` — if `quoteAmount + fees` wraps, the ceiling
itself becomes a huge number (the opposite of the intended bound).

## Severity

Same class as felixfelix-bot's #1212 [MAJOR]: unchecked arithmetic on
mint-supplied numeric fields feeding selection/aggregate logic. Not
exploitable by a honest mint; exploitable by a hostile mint front (the V1/V2
proxy class from the hostile harness). Less severe than #1212 because the
gonuts wallet's blast radius is a failed melt, not a durable budget brick.

## Recommended fix

Overflow-checked arithmetic at each site (the paymentjournal's own `add()`
helper is the in-repo pattern):

```go
amountNeeded, err := add(quote.Amount, quote.FeeReserve)
if err != nil {
    return nil, fmt.Errorf("mint quote overflows: %w", err)
}
```

All four sites are one-line changes plus a shared `add()`/`sub()` helper.
These belong in the #46 guarded implementation (murdawk's branch), alongside
the existing guards, as an additional named gate.
