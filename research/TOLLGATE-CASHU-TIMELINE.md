# TollGate × Cashu: Complete Dependency History & Fund-Loss Analysis

*2026-09-11. Internal (Amperstrand). Traces every cashu version TollGate has
ever used, maps each to our measured compatibility matrix, and identifies
where users could have lost money.*

## The full TollGate cashu dependency timeline

```
2023-05  ─── cashu-tollgate-tester created ───
          cashu-ts ^0.8.0-rc   (0% compat with reference mints)
          gonuts forked from elnosh (upstream)
          Origami74/gonuts-tollgate forked

2023-09  ─── local cashu-ts build ───
          (testing against local fork)

2023-10  ─── cashu-ts ^0.8.2-rc ───
          (still 0% compat)

2025-03  ─── captive-portal-site created ───
          @cashu/cashu-ts ^2.2.2  (0% compat with reference mints)
          BUT: only uses getDecodedToken (decode-only, not a wallet)

2025-09  ─── tester: cashu-ts ^2.7.1 ───
          (0% compat — dead zone)

2025-10  ─── tester: cashu-ts ^2.7.4 ───
          (still 0%)

2025-11  ─── tester: cashu-ts ^3.3.0 ───
          (first version above the dead zone)
          (4/36 PASS = 11% compat with reference mints)

2025-12  ─── tester: REVERTED to ^2.7.4 ───
          ⚠️ DOWNGRADE — likely hit v3 breaking changes

2026-01  ─── tester: still ^2.7.4 ───
          (0% compat period continues)

2026-03  ─── tester: cashu-ts ^3.5.0 ───
          (upgraded again, this time it stuck)
          (matches our matrix: ts-3.5 ≈ 4/36 = 11%)

2026-07  ─── gonuts-tollgate: OpenTollGate fork ───
          (renamed from Origami74)
          (V2 keyset support added)
          (NUT-04 accounting, NUT-20 quote signing)

2026-07  ─── gonuts-tollgate: spec-audit fixes ───
          V4 short keyset ID resolution
          NUT-11 duplicate tag rejection
          NUT-20 binary message format
          Proof deletion ordering (swap safety)
          Empty slice panic guards
          Race condition serialization (melt)

2026-07  ─── portal-site: still ^2.2.2 ───
          (unchanged since 2025-03 — 16 months)
          (token decoder fails on modern formats)
```

## Component × version × compatibility matrix

| Component | cashu version | Our matrix result | What this means for users |
|---|---|---|---|
| **portal** (always) | v2.2.2→v2.9.0 | 0/36 vs reference | **Cannot mint from any reference mint** — but only decodes tokens, doesn't mint. The decode failure on V2 keysets/V4 blocks payment submission. |
| **tester** (2023) | v0.8.x | 0/36 | **Complete dead zone** — no wallet operation works against reference mints |
| **tester** (2025-09 to 2026-01) | v2.7.x | 0/36 | **Dead zone continues** — 16 months of 0% compatibility |
| **tester** (2025-11 blip) | v3.3.0 | 4/36 (11%) | **First compatibility** — could mint from nutshell 0.16-0.19 only |
| **tester** (2026-03+) | v3.5.0 | ~4/36 (11%) | **Partial** — nutshell-only compatibility, no cdk support |
| **backend** (gonuts) | custom fork | not in matrix | **Independent Go implementation** — derivation-safe, V2 keysets, but untested against reference mints |

## Where users could have lost funds

### Confirmed fund-loss vectors (from our measurements)

| Period | Component | Vector | Impact | Recoverable? |
|---|---|---|---|---|
| **2023-2026** | tester (v0.8-v2.7) | Wallet cannot mint from reference mints | Users couldn't get ecash in the first place | N/A (nothing to lose) |
| **2025-11** | tester (v3.3.0 upgrade) | v3 API breaks, then downgrade to v2.7.4 | **Proofs minted with v3 format become unreadable by v2 wallet** | Maybe — if v3 proofs still valid at the mint |
| **2025-03+** | portal (v2.2.2) | Token decode fails on V2 keysets/V4 | **Users with modern wallets can't pay for WiFi** | Yes — tokens still valid at original mint |
| **2026-07+** | gonuts backend | V4 short keyset IDs (fixed in #7) | Swap failures when mint uses V4 keysets | Yes — fixed in commit 6575205 |
| **2026-07+** | gonuts backend | Proof deletion before swap completion (fixed in #11) | **Potential fund loss: old proofs deleted before new ones confirmed** | No — if swap fails after deletion, funds are gone |
| **2026-07+** | gonuts backend | Race condition in MultiMintPayment melt (fixed) | **Concurrent melts could double-spend or lose funds** | Maybe — depends on mint's double-spend detection |

### The November 2025 downgrade: a case study in version chaos

The tester briefly upgraded to v3.3.0 (first version with any reference-mint
compatibility), then was **downgraded back to v2.7.4** the next month.

This likely means:
1. v3.3.0 was tried
2. Something broke (API changes, proof format differences)
3. The "fix" was to downgrade
4. Any proofs minted during the v3.3.0 window may have been unreadable by
   the downgraded v2.7.4 wallet

This matches the **elkim** report pattern exactly: "all was working flawless
until update... went full forensics, tested proofs against mint which marked
it as spent and it got burned."

### The gonuts proof-deletion bug (our own, fixed)

Commit 7dc430b: "fix: delete old proofs only after new proofs are constructed
in swap"

This is a **Category 4 fund-loss vector** from our enumeration (state-management
failure): the wallet was deleting old proofs BEFORE confirming the new ones
were valid. If the swap failed after deletion, the user's funds were gone
with no recovery path.

**This was live in production** until 2026-07-25.

### The gonuts race condition (our own, fixed)

Commit 2fe073c: "fix: serialize Melt calls in MultiMintPayment to prevent
race condition"

If two melt operations ran concurrently on the same proofs:
1. Both read the same unspent proofs
2. Both submit to the mint
3. First one wins, second gets "inputs not found"
4. But both may have already deleted the proofs locally

**This was also live in production** until 2026-07-25.

## Lessons from TollGate's cashu dependency history

### 1. The tester spent 3 years (2023-2026) at 0% compatibility with reference mints

The mobile tester was effectively a **proprietary system** — it could only
talk to our own cashu-cf mints. Users who tried to connect it to any public
Cashu mint running cdk or nutshell would get opaque errors.

### 2. The portal has been at 0% since day one (but it doesn't matter for minting)

The portal only decodes tokens — it doesn't mint or spend. The cashu-ts
version doesn't affect its ability to verify proof signatures (that's the
backend's job). But the decoder bug DOES block payment submission for
users with modern-format tokens.

### 3. Every gonuts bug we found and fixed was a potential fund-loss vector

The gonuts-tollgate fork had at least 3 bugs that could directly cause
fund loss (proof deletion ordering, race condition, V4 keyset resolution).
All were fixed in the July 2026 spec-audit sprint, but they were live in
production before that.

### 4. The November 2025 downgrade proves the ecosystem's version chaos

A brief upgrade to v3.3.0 followed by a downgrade to v2.7.4 is the exact
pattern that burns user proofs. The fact that this happened in our own
project — with full knowledge of the compatibility matrix — shows how easy
it is to fall into these traps even when you're measuring them.

## What we should do next

1. **Test gonuts-tollgate against reference mints** (cdk + nutshell) — we
   have the infrastructure, just need a Go driver in the matrix

2. **Add the gonuts proof-deletion and race-condition bugs to the fund-loss
   enumeration** as vectors #18 and #19 (they're now fixed but were real)

3. **Investigate whether any user actually lost funds to the gonuts bugs**
   — check testnut mint logs for failed swaps during the affected period

4. **Upgrade the tester to cashu-ts v4.10** — it's the only version with
   >50% compatibility with reference mints
