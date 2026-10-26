# COMPAT LEDGER — what works with what (wallets × mint software)

Purpose: tollgate (and any Cashu wallet) needs to know which mint
software versions behave which way — whole behavior classes ride the
mint's software version, are invisible in `/v1/info`, and flip at
release boundaries. This ledger holds the measured change points and
the wallet-facing matrix. Every cell is wire evidence from
default-config docker arms (identical CDK TOML / ns env) unless
marked otherwise. Method: cashu-audit probes 2026-10-25/26.

## The matrix (measured 2026-10-25/26)

| Wallet-visible behavior | ns 0.20.3 | ns 0.21.0 | cdk 0.17.6 | cdk 0.17.7 | cdk 0.18.0 | cdk 0.18.1 | cdk 0.18.2 | cf testnut |
|---|---|---|---|---|---|---|---|---|
| Default keyset id on `/v1/keys` | 16-hex V1 | 16-hex V1 | **66-hex V2** | **66-hex V2** | **66-hex V2** | **66-hex V2** | **66-hex V2** | 16-hex V1 |
| Byte-identical swap replay | 400 reject | 400 reject | 200 cached | 200 cached | 200 cached | 200 cached | 200 cached | 200 cached |
| Unsupported-unit error code | 10000 | **11013** | 11013 | 11013 | 11013 | 11013 | 11013 | 11005 |
| Batch mint: length cap | n/m | 1000-flat | none (existence-first) | none | none | **11017 @ 100** | **11017 @ 100** | 11016? @ 50 |
| Keyless-amount swap (e.g. 63) | crash `detail:"63"` code 0 | crash `detail:"N"` | 12001 reject | 12001 reject | 12001 reject | 12001 reject | 12001 reject | **SIGNS then refuses redemption — fund strand (fix staged, cashu-cf 97a1654)** |
| Locked quote, no signature | 20008 | 20008 | n/m | 20008 | n/m | n/m | 20008 | 20008 |
| Batch locked-mint, sigs array | n/m | converged 200/20008 | n/m | n/m | n/m | n/m | converged | converged |
| Melt-quote fee_reserve | 10 | 10 | 20 | 20 | 20 | 20 | 20 | 10 |
| Declared change amounts honored? | ignored | ignored | ignored | ignored | ignored | ignored | ignored | ignored |
| checkstate batch cap (advertised/enforced) | n/m | 1000/1000 | n/m | n/m | n/m | n/m | 1000/**100** | **50**/1000 |

n/m = not measured (image exists; one arm-run away). cf = cashu-cf
testnut. cdk batch-check details: pre-0.18.1 a batch of 1001 unknown
ids fails existence-first (`50000 Unknown quote`); 0.18.1+ fails
length-first (11017) regardless of id validity.

## Change points (when things changed)

**cdk line (fakewallet, default config):**
- **≤ 0.17.6: V2 (66-hex) keysets are the default.** Wire-verified at
  0.17.6/0.17.7/0.18.x. Tollgate's code-read dates V2 capability to
  "0.16+" (#952); no docker images exist below 0.17.6 to wire-verify.
  Wallet impact: any wallet assuming 16-hex ids breaks against every
  current cdk mint. V1 spellings still arrive from older keysets
  mid-rotation — wallets must accept both (short/full `i` in V4
  tokens; cashu-ts requires full ids in its keyset list and errors
  "ambiguous" if both spellings are present).
- **0.18.1: batch length cap arrives (11017, max 100), checked
  BEFORE existence.** 0.17.6/0.17.7/0.18.0 have no length check.
  Wallet impact: a wallet batching >100 quotes now fails on 0.18.1+
  even with valid quotes; cdk ADVERTISES max_array_length=1000 (the
  advertisement-vs-enforcement gap is cdk's own).
- Stable across 0.17.6→0.18.2: replay caching (present), keyless
  reject 12001, NUT-20 lock 20008, fee_reserve 20, change-amounts
  ignored.

**nutshell line:**
- **0.20.3 → 0.21.0: unsupported-unit error flips 10000 → 11013**
  (intra-family silent drift; 0.21.0 converges with cdk on the
  registry code). Wallet impact: error-code maps keyed to 10000
  break silently on a minor mint upgrade.
- Stable through 0.21.0: NO replay caching (byte-identical re-POST
  of a successful swap/melt/mint is rejected as double-spend),
  keyless crash `detail:"N"` (framework-layer, no registry code),
  V1 keysets, fee_reserve 10.

**cashu-cf (testnut, tracks nutshell main):**
- Replay caching present (cf+cdk line). Keyless-amount signing bug
  live (fix staged 97a1654; permanent conformance scenarios pin it).
  Unit error 11005 (own code, pre-registry). Batch cap 50.

**Spec line (SPEC-HISTORY timelines):** keyset-id V2 Jan 2026
(#182, merged 2026-01-11); NUT-20 message break (#370) adopted by
all three families; unit consistency (#406); quote accounting Jul
2026; NUT-07/08/12 tightenings Aug–Sep 2026 (#424/#425/#426).

## Tollgate lessons (measured ↔ their tracker)

- **#952 browser payments fail against V2-keyset mints** — the wave
  IS cdk's V2-default keysets (≤0.17.6 onward). Not a mint
  misconfiguration; it's the software line. Both on-the-wire
  spellings must resolve (their #984 pins it).
- **#818 wallet init bricks on "Unknown Keyset" after rotation** —
  that string is cdk's 12001 identity. After rotation the V1-era
  keyset's keys vanish from `/v1/keys`; a wallet that validates
  proofs-at-init against current keys bricks. ns's crash-detail
  variant is even less parseable. Self-heal needs re-fetch + retry
  semantics, not error-map patches.
- **#867 mint replay window 60 s memory-only** — replay caching is
  an ARCHITECTURE line, not a setting: cdk caches (window/TTL
  config-dependent), nutshell never has. A wallet's retry-safety
  assumptions change by mint software, silently. Treat
  "is this mint retry-safe" as a probe, not a property.
- **General, from the matrix:** (1) never key error handling to one
  family's codes — ns flipped its own codes within a minor release;
  (2) trust enforcement over advertisement (cdk advertises 1000,
  enforces 100; cf advertises 50, enforces 1000); (3) `/v1/info`
  exposes none of the rows above — the spec has no capability flags
  for replay caching or keyset-version defaults (filing candidate).

## Corrections (house discipline)

- Mid-session 2026-10-26: a probe sent a FRESH blinded output on the
  "replay" POST — the 400s it produced on 0.18.0/0.18.1/0.18.2 were
  "inputs already spent", not caching behavior. Retracted same
  session; payload-once shape shows caching uniform on all cdk arms.
- 2026-10-25's "batch cap arrived in the 0.18 line" sharpened today:
  the 11017 flip is exactly at 0.18.1.

## Closed-loop upgrades (measured 2026-10-26)

cdk ladder 0.17.6→0.18.2 on one persistent DB (FINDINGS-cdk-upgrade-
ladder.md): keysets stable, spent ledger enforced, parked quotes
mintable at EVERY boundary. Operator migration step at the 0.17→0.18
config-era break: `config init --existing-mint`. Traps: silent exit
on invalid-checksum mnemonic; replay cache keyed on inputs (retry
with re-randomized outputs can receive OLD signatures — 200, not an
error). NOT covered: real-LN backends, keyset rotation mid-ladder,
ns/cf ladders.

## Maintenance

Regenerate cells with the fresh-must-wave probes (each leg is one
arm-run); new rows only with frozen predictions first. When cdk/ns
cut new releases, the upstream watch fires — measure the new arm
BEFORE updating this ledger, and log the delta as a change point.
