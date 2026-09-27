# Wallet×Zoo Spike — RESULT (2026-09-27)

Wallet: cashu.me @ 4abd268 (served at https://cashume.cashu.exchange, zoo
tunnel alias → socat 3081 → container :3080). Driven via Playwright
(Chromium). Payments: inr2 cln-swap-signet (routed) / cln-hub-signet
(melt destinations + self-pay fallback) via the herdr-hosted payer
helper (/tmp/opencode/spike-payer.sh, pane w2:p3).

## Matrix result — 25/25 PASS (prediction: 25/25 ✓)

| Cell | Mint | ADD | MINT(21sat) | SEND(5) | RECV | MELT(10) | Post-melt balance |
|---|---|---|---|---|---|---|---|
| C1 | cdk-4312959 (0.17.6) | ✅ | ✅ | ✅ | ✅ | ✅ | ₿11 (21−10, reserve returned) |
| C2 | cdk-d3dec24 (0.18.0) | ✅ | ✅ | ✅ | ✅ | ✅ | ₿11 |
| C3 | cdk-a056e0f (0.18.1) | ✅ | ✅ | ✅ | ✅ | ✅ | ₿11 |
| C4 | ns-1853902 (0.20.3) | ✅ | ✅ | ✅ | ✅ | ✅ | ₿8 (20−10−2 fee) |
| C5 | ns-a974914 (0.21.0) | ✅ | ✅ | ✅ | ✅ | ✅ | ₿8 |

Every melt destination invoice settled `paid` on cln-hub-signet
(`listinvoices`), every mint payment routed through cln-swap-signet.

## Findings beyond pass/fail

1. **Fee-structure divergence, surfaced by balance arithmetic.**
   cdk mints: redeem returned exact amounts (16+5=21); melt shows an
   explicit "Fee Reserve ₿2" in the quote UI and returns it (21−10=11).
   Nutshell mints (both 0.20.3 and 0.21.0): redeem charged 1 sat input
   fee (16+5−1=20); melt showed no reserve row and consumed 2 sats
   (20−10−2=8). Same wallet, same amounts — different money mechanics
   per family. Not a bug; exactly the cross-family UX delta this
   harness exists to measure.
2. **cashu.me publishes mint backups to Nostr by default** (log: "Mint
   backup published to Nostr: 45b8d8c0…"). A wallet pointed at private
   mints syncs their URLs (encrypted) to public relays. Same privacy
   leak class we fixed in MintRadar's reviews-sync. Worth a divergence
   note; also relevant for anyone running private mints.
3. **Harness learnings** (cost of the spike, recorded for the next
   wallet):
   - cashu.me's clipboard paths (Capacitor) require a secure context —
     the http origin blocked both Copy and Paste flows. The tunnel
     alias (https) is now the standing harness origin.
   - Manual token entry works via native-setter + input event + Enter
     (`handleReceive`); synthetic events alone do not wake Vue v-model
     on the Quasar inputs.
   - The wallet UI displays sat amounts as "₿21" (unit SAT).
   - Multi-mint wallet state keyed by mint URL — one wallet instance
     ran all five cells without cross-contamination.

## Evidence

- Screenshots: wallet-spike-C1-complete.png, wallet-spike-complete-all-mints.png (this dir)
- Browser console log: .playwright-mcp/console-2026-09-27T22-45-57-760Z.log (mint activations, token flows, proof PENDING→SPENT)
- Payer log: herdr pane w2:p3 (all PAY_OK / paid)

## Next candidates for the matrix

- Wallets: Enuts/Minibits (mobile emulators), coco (terminal), gonuts,
  nutshell CLI, cdk-cli (already proven via pay-and-mint.sh).
- Flows: P2PK send/receive, multimint Lightning swap (the UI has
  "Multimint Swaps" — melts on A, mints on B, atomicity budget vs fees),
  NUT-18 payment requests, checkstate after send.
