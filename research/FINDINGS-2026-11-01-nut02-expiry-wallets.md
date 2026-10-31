# FINDINGS 2026-11-01 — NUT-02 final_expiry wallet legs: all three families now live-pinned (survey completion)

Closes the expiry remainder of agenda #43 item 2. Evidence: `live`
(docker nutshell 0.21.0 arm WITH mgmt-RPC, deterministic mnemonic —
recreated same-keyset; cashu-ts v5.0.0-rc.9 vitest; cdk-cli v0.18.2
debug), `src` (cited). Frozen predictions PE1–PE4 written before the
run (`private/nut18-live/PREDICTIONS-expiry-wallets.md`, mirror); all
four confirmed, zero surprises. Runners stopped — local gates only.

Setup (PE1, confirmed): mgmt-RPC `next-keyset sat 0 8 <now-3600>` →
mint lists keyset `01b367ce…aefdeaf` with `final_expiry` one hour in
the PAST, `active: true`, `input_fee_ppk: 0` (old 100-ppk keyset →
`active: false`). Nutshell 0.21.0 never evaluates expiry — the arc's
P1 listing finding, now with a PAST-expiry keyset on the wire.

## Wallet legs (was: nutshell live + cdk-against-cdk-mintd; now: all three)

| Wallet | Behavior on the expired-ACTIVE keyset | Evidence |
|---|---|---|
| nutshell 0.21.0 | minted (arc, live) — no expiry refs in tree | arc P2-wallet |
| cashu-ts v5.0.0-rc.9 | **minted** — `withKeyset(expired)` + `ops.mintBolt11` → proofs on `01b367ce…`; expiry is a preference-sort input in `KeyChain.getCheapestKeyset` (sorts by latest expiry) but never a gate; the only gate is `isActive` | live PE3 (`harness/nut02-expiry.node.test.ts`) |
| cdk-cli 0.18.2 | **minted — and SELECTED the expired keyset unprompted**: fee-preferred selection picked the 0-ppk expired keyset over the 100-ppk unexpired one; the sent V4 token carries `i = 01b367ce9ed7d8cb` (out/pe4_cdk_expired_keyset.token) | live PE4 |

Mint leg re-verified on this arm (PE2): direct `/v1/mint/bolt11` on
the expired keyset → 200 + signatures (nutshell signs expired
forever — arc P2).

## What this adds to the record

1. **Wallet-side uniformity**: NO reference wallet family consults
   `final_expiry` as a spend/mint gate. cashu-ts is the only one
   that reads it at all (keyset preference), which can steer it
   AWAY from expired keysets when an unexpired alternative exists —
   but binding (or a mint with only expired-active keysets left)
   mints anyway.
2. **cdk selection trap (new)**: cdk's cheapest-fee selection
   actively PREFERs a 0-ppk expired-active keyset. On a nutshell
   mint (lists expired as active, signs forever) a cdk wallet
   accumulates proofs on an expired keyset without any signal;
   those proofs are then refused at swap/melt by a strict mint
   (cdk-mintd `verification.rs:145`, src-pinned) — the
   stranded-late-swapper composition produced end-to-end from the
   wallet side. NUT-02 assigns no wallet duty (candidate wording
   gap, already rowed).
3. The expired-active listing is reachable by ordinary operator
   action (`next-keyset … <past>` passes a past timestamp through
   unvalidated — one-line rotation hygiene note for the staged
   nutshell filing).

## Version/state pins

nutshell 0.21.0 (rotation RPC passes past expiry through); cashu-ts
rc.9; cdk 0.18.2 (selection code unchanged through 0.18.3 — the
0.18.2→0.18.3 diff touches no wallet/keyset-selection region;
main `Id`/keyset regions unchanged). Upstream NUTs frozen @ 1363de4
(no 02.md movement since 2026-10-23).

Registry: row "final_expiry enforcement diverges mint-side…"
updated with the three-family wallet-leg completion + the cdk
selection trap.
