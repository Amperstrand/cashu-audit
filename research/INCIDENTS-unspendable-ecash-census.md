# Census: public reports of money loss / stuck funds from boundary-mismatch bugs (genus of the NUT-00 encoding trap)

**Date:** 2026-09-08 · Method: GitHub issue search (gh api), Nostr/web search,
source autopsy of archived implementations.

## The precedent that settles the governance question

**nutshell — the reference mint — ships permanent dual-derivation leniency
today** (`cashu/core/crypto/b_dhke.py`):

```python
def verify(a, C, secret_msg):
    Y = hash_to_curve(secret_msg.encode("utf-8"))        # current (domain-separated)
    valid = C == Y * a
    # BEGIN: BACKWARDS COMPATIBILITY < 0.15.1
    if not valid:
        valid = verify_deprecated(a, C, secret_msg)      # pre-0.15.1 algorithm
    return valid
```

When NUT-00's `hash_to_curve` was tightened (nutshell 0.15.1 introduced the
domain separator), every pre-0.15.1 token would have become unspendable under
strict verification. The reference implementation chose to honor issued
claims: permanent fallback, still present. The archived lnbits cashu
extension (a nutshell fork) carries the same dual-verify block — with the
fallback order inverted (legacy first), independently re-implementing the
same policy.

**Implication:** "spec tightening is honored prospectively; issued claims
keep verifying" is not our invention — it is the ecosystem's existing
practice for the algorithm-drift species. Our cdk per-keyset proposal applies
the same principle to the encoding species, with a better boundary (keyset
scoping instead of an unconditional fallback).

## Confirmed public loss/stuck-funds reports (same genus, other species)

| # | Report | Species | Amount | Outcome |
|---|---|---|---|---|
| 1 | Nostr, 2026-02-02: "A lesson in Cashu wallet safety — how I lost 1,824 sats" — **written by an AI agent** about its own custom cashu-ts wallet (melt crash, change never persisted) | state boundary | 1,824 sats | **final loss**, self-reported |
| 2 | Amethyst #3847: melt change matched by amount, mint imputes by index (NUT-08 blank outputs) → wallet discards change after successful payment | representation mismatch (sibling of ours) | user change amounts | "funds appear lost"; recoverable only via NUT-09/NUT-13 |
| 3 | cdk #1180: proofs stuck PENDING after melt rejection (proof-count limit) — L402 nginx integrator | state machine | user balances | "effectively lost" pending manual fix |
| 4 | gonuts #88: send leaves proofs deleted-not-pending; Alby Hub users affected | state machine | user balances | recoverable via wallet restore |
| 5 | lnbits/cashu #68: mint's ecash unspendable in ALL wallets after Lightning top-ups (extension bug); multiple reporters | impl divergence | deposited sats | stuck at mint |
| 6 | Nostr 2026-02 (minibits support): user locked out of ~16k sats by pending-proof cascade across minibits → cashu.me → macadamia | state machine | ~16,000 sats | support case |
| 7 | 2023 bounty thread + FreedomMan note: "could not verify proofs" spend failures on cashu.me / lnbits wallets, multi-user | mixed: pending-state + the 0.15.1 algorithm migration era | unquantified | largely resolved; the migration-era failures are what the nutshell fallback absorbs |

## The encoding species specifically

**No confirmed public loss report found.** Interpretation (argued, not
assumed): consistent with underdiagnosis — the error is cryptic and
unattributable, lenient mints absorb the trap silently, affected wallets are
often custom/one-off scripts whose authors never report. Absence of reports
is not absence of losses; the sensor proposal exists precisely because
nobody can currently count them.

## What this does to our campaign

- The nutshell precedent **strengthens** the cdk per-keyset-leniency proposal:
  we are asking cdk to adopt a bounded version of what nutshell already ships
  unbounded.
- Incident #1 (AI agent losing real sats with a hand-rolled wallet) is the
  clearest public datapoint for the LLM-client risk thesis.
- The census gives the Nostr post its "this genus eats real sats" texture
  without overclaiming the encoding species.
