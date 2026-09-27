# Wallet×Zoo Spike — cashu.me × 5 signet mints (2026-09-27)

One popular wallet (cashu.me, the official web wallet) against the full
zoo matrix, real signet sats end to end. Spike goal: prove the harness
(mint-add → paid mint → send → receive → melt per mint) and surface the
first real interop data.

## Matrix

Wallet: cashu.me @ git 4abd268 (PR #612 merge), served locally
(:3080, docker container `cashu.me`), driven via Playwright.

Mints (tunnel hostnames, pinned commits):

| Cell | Mint | Impl/version | Commit |
|---|---|---|---|
| C1 | cdk-4312959.cashu.exchange | cdk 0.17.6 | 4312959 |
| C2 | cdk-d3dec24.cashu.exchange | cdk 0.18.0 | d3dec24 |
| C3 | cdk-a056e0f.cashu.exchange | cdk 0.18.1 | a056e0f |
| C4 | ns-1853902.cashu.exchange | nutshell 0.20.3 | 1853902 |
| C5 | ns-a974914.cashu.exchange | nutshell 0.21.0 | a974914 |

## Flows per cell

1. ADD — add mint by URL; info + keysets load; no error state
2. MINT — Lightning invoice for 21 sats; paid via cln-swap-signet
   (inr2, real routing; hub self-pay fallback); balance appears
3. SEND — send 5 sats; token produced (swap + encode); balance -5
4. RECV — redeem that token back; balance restored
5. MELT — melt 10 sats to a fresh hub invoice; invoice settles PAID

Fresh browser profile per cell (isolated localStorage wallet state).

## Frozen predictions (written BEFORE any run)

- ADD: 5/5 PASS — all five serve /v1/info + /v1/keysets; no known
  add-path divergence.
- MINT: 5/5 PASS — NUT-04 v1 spec flow; pay-and-mint.sh already proved
  paid mints on cdk 0.18.1 and ns via cdk-cli; cashu.me uses cashu-ts
  spec flow.
- SEND: 5/5 PASS — plain multi-proof swap, no spending conditions
  (SIG_ALL F5 class not exercised in the spike core).
- RECV: 5/5 PASS — token v3/v4 decode + swap; both families tested
  before via cashu-ts e2e.
- MELT: 5/5 PASS, **risk cell** — cdk returns fee_reserve and change;
  fractional overpay handling differs per family. A FAIL here is the
  most informative outcome.
- Total: 25/25 expected. Any FAIL → probe-bug-until-proven-otherwise
  applies to the harness first (stderr, screenshots, mint logs, wire).

## Evidence per cell

Playwright screenshots per flow, browser network log (mint API calls),
mint container log tail, payer script log. Results table in RESULT.md.

## Payment rail

- Mint quote invoices paid from inr2 cln-swap-signet via ssh (fallback:
  cln-hub-signet self-pay) — same rail as pay-and-mint.sh.
- Melt-target invoices created on cln-hub-signet (`lightning-cli
  invoice`), settlement confirmed via `listinvoices`.
- Queue directory /tmp/opencode/spike-queue/ drives a herdr-hosted
  payer helper so browser waits never block on ssh round trips.
