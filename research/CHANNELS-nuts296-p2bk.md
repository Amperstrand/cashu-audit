# Channels (nuts#296), P2BK (NUT-28), and the SatsAndSports ecosystem

*2026-09-09. Internal research — nothing filed or linked upstream. Companion to
`CENSUS-nut10-11-14-correct-behaviour.md` and `WALLETS-spending-conditions.md`.*

## nuts#296 — Offline Spilman (unidirectional) channel

Open since 2025-10-14, 60 commits, **still active (Aug 27–28, 2026 pushes)**.
Author: SatsAndSports. Model: Alice ↔ Charlie channel, Bob = mint (naming
settled after robwoodgate's review). One funding tx → billions of offline
micropayment updates; receiver verifies without contacting the mint; mint
involved only at close.

Mechanisms it stacks (all from our divergence surface):
- **P2PK (NUT-11)** 2-of-2 *funding token* between channel parties
- **P2BK (NUT-28)** for pubkey blinding/privacy
- **Deterministic outputs** derived from a channel secret (HKDF/HMAC,
  domain-separated stage-1 key tweaks — spec'd in Aug 2026 commits with
  test vectors)
- **Locktime refunds** (the d6 surface) as the failure-mode recovery
- **DLEQ (NUT-12)** for offline signature verification
- **SIG_ALL** for transaction-level authorization

Key discussion facts:
- SatsAndSports (Oct 2025, in-thread): implemented it and found "Some mints
  don't support everything correctly. Some mints only have partial support
  for P2PK; they don't support SIG_ALL and they don't seem to support
  locktime correctly either" — the channel author hit the exact divergence
  wall our probe measures. He built the checker *because of this*.
- cdk PR #1195 ("fix for SIG_ALL and P2PK… after the locktime, support
  SIG_ALL with refund keys", Oct 2025) was **abandoned, replaced by #1212** —
  cdk's SIG_ALL+refund semantics were churned during channel development.
- robwoodgate points at **audit.8333.space** (community mint auditor);
  SatsAndSports's reply is the auditor-coverage-gap insight: an operator
  "could behave flawlessly with the auditor's usages, but rug everybody
  when the user deviates from what is covered."

## NUT-28 — Pay-to-Blinded-Key (read from local nuts clone)

Extends NUT-11 (and by implication NUT-14). ECDH-derived blinding scalar
per proof; receiver's long-lived pubkey never appears — privacy against
mint linkage. **Kind stays `P2PK`** with `p2pk_e` ephemeral-pubkey metadata
on the proof — so NUT-28 does NOT trigger d1's unknown-kind path; instead
it *deepens dependence on NUT-11 exactness*: "up to 11 locking 'slots' in
the order `[data, ...pubkeys, ...refund]`" (this slot order is itself a
fresh spec constraint — cashu-ts had to align to it). Nutshell's wallet on
main already implements P2BK signing (blinded-key derivation, `p2pk_e`,
SIG_ALL with P2BK keys).

## The PoC: SatsAndSports/cashu_spilman_channels

Reference implementation, "Early Alpha": `cdk-spilman` Rust crate
(0.16.0-rc.1), WASM/Python/Go bindings, integration kits, sans-IO
prepare/validate/complete/record primitives, multi-server integration
tests, **and its own standalone local test mint** (`cdk-spilman-test-mint`)
— a telling workaround when real mints diverge. Recent hardening PRs
(#18–#23, Aug 2026) include "Do not silently truncate close recovery on
restore failures" — recovery paths are where our d-class findings bite.

## The checker: SatsAndSports/nut10_compatibility_checker

58 scenarios (swap + melt × P2PK/HTLC × SIG_INPUTS/SIG_ALL × locktime/
refund), tracked published results, naming scheme shared with our
conformance suite and the cashu-ts integration suite — three independent
artifacts of the same test-space.

| Mint (2026-05-18 run) | Score | Notable |
|---|---|---|
| cdk-mintd/0.16.0 | 58/58 | **incl. `htlc_locktime_after_expiry_refund_succeeds` ✅** — the sigs-only refund SPENT. Combined with our 0.18.0 REJECT: **cdk's d6 regression landed between 0.16.0 and 0.18.0.** (The error string itself dates to 2024-04, `db14c117` "feat: NUT14" — the routing behavior changed, not the message.) |
| Nutshell/0.20.0 | 38/58 (45/58 legacy SIG_ALL) | the #1009 list — the motivation for the #1008 overhaul |
| Nutmix/0.4.0 | 48/58 | **over-acceptance**: `htlc_sigall_signature_only` and `htlc_sigall_wrong_preimage` "swap unexpectedly succeeded" — invalid HTLC SIG_ALL spends accepted. Cross-checked against our `reference-reports/nutmix.json` (July): agrees on `htlc_preimage_only_no_pubkeys_succeeds: fail` and `htlc_locktime_after_expiry_refund_succeeds: fail` — Nutmix's HTLC verification is loose in both directions. Fourth-implementation data point; over-acceptance class, unlike cdk/nutshell. |

## Where our findings sit in this picture

- **d6 (refund witness incompatibility)** lands directly on the channel
  failure-mode: a Spilman close/refund is a locktime refund spend, and the
  default wallet emission (see WALLETS doc) is the shape cdk rejects. The
  PoC sidesteps real mints with its own test mint; production channels
  cannot.
- **d2/d3 (MUST-unenforcement)** + Nutmix's over-acceptance define the
  ecosystem spread a channel client must survive: DotNut rejects what
  cdk/nutshell accept; Nutmix accepts what everyone else rejects.
- **SIG_ALL message format** (nuts#302) churned during channel development;
  nutshell's legacy format is why the checker has a legacy mode and our
  suite auto-detects (`sigall_mode`).
- The channel spec's Aug 2026 test-vector discipline (channel secret,
  channel ID, deterministic outputs) is the model our d-fixes should ride:
  vectors in the NUT, not prose.

## Open items

1. Read `ARCHITECTURE.md` + close/recovery flow of the PoC for the exact
   witness shapes channels emit (extends WALLETS doc).
2. Watch #296: any change to refund-slot semantics re-runs our d3/d6 probe
   cells for free.
3. audit.8333.space: compare its scenario coverage vs the 58-case checker —
   the auditor-coverage-gap SatsAndSports named is our "verification
   theater" finding in community form.
