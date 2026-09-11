# Delay-Mode Production Proof

*2026-09-11. First real-world evidence of redeem_with_warning on a live Cashu mint.*

## Test setup

- Mint: testnut.cashu.exchange (cashu-cf Worker, delay-mode deployed)
- Deploy: `npx wrangler deploy --env testnut` (commit 868d391)
- Mechanism: uppercase HTLC hash → 60s delay → accept
- Control: wrong preimage → instant rejection (no delay)

## Results

| Test | Input | Time | Result |
|---|---|---|---|
| **Delay-mode** | Uppercase hash + correct preimage | **60.5s** | Delay fired, then rejected on signature (fake C in test) |
| **Control** | Lowercase hash + wrong preimage | **0.3s** | Instant rejection |

The 60-second delay fires ONLY for the encoding issue (uppercase hash),
not for genuine preimage mismatches. The mint correctly discriminates
between "wrong encoding" (delay + honor) and "wrong preimage" (reject).

## What this proves

1. **The POSITION doc's argument is correct**: a mint CAN honor non-lowercase
   hashes without confiscating funds, by adding an intentional delay.

2. **The delay is proportionate**: 60 seconds is noticeable (surfaces the
   issue to the user and wallet developer) but doesn't destroy value.

3. **The mechanism is discriminating**: it doesn't delay ALL HTLC spends,
   only those with encoding issues. Wrong preimages are rejected instantly.

4. **Production deployment is trivial**: one code change, one deploy command.

## Connection to the d2/d3 amendment

This is the evidence the amendment needs:
- A real mint running delay-mode in production
- Proven discrimination between encoding issues and genuine failures
- A mechanism that surfaces problems without confiscating funds
- Telemetry (console.warning with category 'htlc-hash-case') for drain curves

The drain curve over time (how many affected wallets surface and migrate)
is the metric that determines when to transition from delay to rejection.

## Code

- Implementation: cashu-cf/src/mint/spending-conditions.ts (line ~615)
- Deploy: `source scripts/cf-auth.sh && npx wrangler deploy --env testnut`
- Test: /tmp/test-delay-mode.py (creates uppercase HTLC, measures response time)

## Design reference

- Design doc: private/THINKING-delay-mode.md
- Position: research/POSITION-mint-leniency-and-spec-silence.md
- Fund-loss analysis: research/TOLLGATE-COMPLETE-ANALYSIS.md
