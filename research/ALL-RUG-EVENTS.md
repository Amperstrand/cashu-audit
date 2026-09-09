# All known Cashu fund-loss ("rug") events — comprehensive inventory

**Date:** 2026-09-09 · **Method:** GitHub issues/PRs, Nostr posts, Substack
disclosures, audit.8333.space data, dev call minutes

## Category 1: Keyset rotation stranding (recurring, ongoing)

The #1 fund-loss vector. Every keyset rotation risks stranding proofs from
the old keyset if wallets don't handle the transition perfectly.

| Event | Date | What happened | Fund impact |
|---|---|---|---|
| Minibits keyset rotation | Jan 2026 | Mint rotated `005...` → `001...`; users hit "keyset not found" | Users couldn't access funds until manually clicking mint (calle's workaround) |
| cdk #1994 | 2026 | Wallet operations fail for inactive-keyset proofs | Can't swap or melt rotated tokens |
| cdk #1753 / PR fix | Mar 2026 | `restore()` only scanned ACTIVE keysets | Rotated-keyset proofs invisible during recovery |
| cashu-ts #486 / PR fix | Feb 2026 | Same restore bug in TypeScript | Same — couldn't restore from inactive keysets |
| cashu-ts #706 / PR fix | Aug 2026 | Wallet refused to send melts on inactive keysets | Users couldn't WITHDRAW from shutting-down mints |
| cdk #2447 | Aug 2026 | Keyset rotates during async melt | Change outputs fail permanently, no recovery path |
| cdk keyset expiry (bbe7be0) | Jul 2026 | New feature: explicitly expire keysets, reject tokens | "Wallets discover expiry at use time" — by design |
| nutshell #534 | May 2024 | Unredeemed sent tokens are "lost" forever | Sender can't re-claim; feature request never built |

## Category 2: Keyset residue collision (vulnerability, Mar 2026)

floppy's disclosure (uncensoredtech.substack.com):
- Two 64-bit keyset IDs collide mod 2^31 → same BIP-32 derivation path
- User mints 1 EUR + 1 SAT → same secret → one flagged "already spent"
- "This vulnerability can spread like a virus and burn the cashu tokens
  for several users"
- Nutshell patched (OutputsAlreadySignedError); nutmix still vulnerable
- Most wallets don't validate keyset IDs before deriving secrets

## Category 3: Hash-to-curve derivation changes (4 events)

| # | When | Change | Compat |
|---|---|---|---|
| 1 | Feb 2024 | nutshell introduced domain separator (0.15.0→0.15.1) | Fallback shipped |
| 2 | Feb 2024 | cashu-ts 1.0 changed hash + secret format | None — "reset counters and self-spend" |
| 3 | Jul 2026 | nutshell removed deprecated fallback (0.20.3) | Shipped as a "chore" |
| 4 | Always | cdk never had the fallback | Permanent divergence |

54% of tracked mints still on versions with the fallback (35/65).

## Category 4: Interrupted operations (186 auditor failures)

| Event | Count | Impact |
|---|---|---|
| "proofs/token pending" (audit.8333.space) | 186/1000 | Proofs stuck in pending state, no recovery |
| AI agent crash (Nostr, Feb 2026) | 1,824 sats | Melt succeeded, change never saved |
| cdk #2335 | npubcash legacy scrub | Quote secret equals seed[..32] → saga aborts after signatures issued |
| Minibits hold invoice (Nostr, Feb 2026) | 5,028 sats | Hold invoice canceled after ecash spent, no refund mechanism |

## Category 5: NIP-60 wallet portability races

| Event | Impact |
|---|---|
| Two clients racing to spend same proofs | One succeeds, other's state corrupted |
| Relay deletes kind:7375 events | Only copy of proofs lost = funds gone |
| Lose nsec | Lose entire NIP-60 wallet (proofs encrypted to that key) |
| Official advice | "Don't use two NIP-60 wallets simultaneously on two devices" |

## Category 6: Cross-implementation divergence (cdk#2252)

8 documented behavioral divergences in NUT-10/11/14 (P2PK/HTLC spending
conditions) between cdk and nutshell. "A token spendable at a CDK mint can
be bricked at a nutshell mint and vice versa."

## The common pattern (every single event)

```
Something changes (rotation, upgrade, crash, format, collision)
    ↓
Old tokens become invalid or stuck
    ↓
Error is cryptic ("not verified", "keyset not found", "pending")
    ↓
User has no recovery path
    ↓
Nobody measures how many people are affected
    ↓
The change happens again to the next batch of users
```

## Root cause

The spec defines happy paths only. Every implementation solves the edge
cases differently (or not at all). No signaling, no observability, no
error taxonomy, no recovery semantics.

## Proposed fixes (our tested implementations)

| Fix | Prevents | Cost |
|---|---|---|
| Observe mode | Silent stranding (all categories) | 6-20 lines |
| Warn-and-delay | Invisible acceptance | +4 lines |
| Distinct error codes | Cryptic failures (all categories) | Error registry |
| Even-bit signaling | Pre-commitment fund waste | NUT-06 field |
| Spec MUST + vectors | New implementation bugs | Spec PR |
| Upgrade A/B testing | Behavioral divergence | Framework (built) |
| NUT-XX: recovery spec | Interrupted operations | New spec |
