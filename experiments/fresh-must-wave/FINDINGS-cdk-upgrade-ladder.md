# FINDINGS — cdk closed-loop upgrade ladder (2026-10-26)

Frozen predictions: `PREDICTIONS-cdk-upgrade-ladder.md`.
Driver: `cdk_upgrade_ladder.py` (rerunnable). Data:
`out/cdk-upgrade-ladder.json`. One workdir (sqlite + TOML), one
mnemonic, sequential containers 0.17.6 → 0.17.7 → 0.18.0 → 0.18.1 →
0.18.2, fakewallet sat.

## Verdict: the upgrade path is CLEAN end to end

| Boundary | K keyset | R old-proof | S spent-ledger | Q parked-quote |
|---|---|---|---|---|
| 0.17.6 → 0.17.7 | same | redeemable | enforced | minted |
| 0.17.7 → 0.18.0 (config-era break) | same | redeemable | enforced | minted |
| 0.18.0 → 0.18.1 | same | redeemable | enforced | minted |
| 0.18.1 → 0.18.2 | same | redeemable | enforced | minted |

- Keyset id (66-hex V2) identical across all five versions —
  mnemonic-derived continuity; no re-keying on upgrade.
- The spent-proof ledger survives every boundary: no double-spend
  window opens on upgrade.
- Paid-but-unminted quotes survive every boundary (no burned money).
- The 0.17 → 0.18 config-era break is survivable with the documented
  operator step: `cdk-mintd config init --existing-mint --file …`
  (env config gone in 0.18; a hand-written TOML is refused until
  init registers it — the daemon exits with "configuration is not
  initialized"). Init is once-per-workdir: later upgrades boot
  directly.

## Sharp edges measured on the way (operator/wallet traps)

1. **Invalid-checksum mnemonic = near-silent exit.** cdk-mintd
   initializes the DB, constructs the backend, THEN exits(1) with a
   one-line stderr error ("mnemonic has an invalid checksum") and an
   INFO-level log that ends in a normal-looking shutdown sequence. A
   supervisor restarting it loops quietly. (16-word mnemonic:
   explicit word-count error; 12-word-but-invalid-checksum: this
   near-silent form.)
2. **Replay cache keys on INPUTS, not the request body.** A retry of
   a consumed swap with DIFFERENT (re-randomized) outputs receives a
   200 carrying the signatures of the ORIGINAL outputs (measured on
   0.17.7 during bring-up; the final ladder's discriminated leg
   shows the fresh-outputs retry REJECTED when the cache is not hit
   — rung timing/cache eviction decides which). Wallet rule: on
   retry, keep the original outputs; re-randomizing silently gets
   you signatures you cannot unblind. Footnote: one bring-up run
   showed the 200-cache form, the final run the 400 form — cache
   window sensitivity unmeasured; both are safe (no fresh sigs for
   spent inputs ever observed).

## What this ladder does NOT cover

- Real LN backends (LND/CLN) across the upgrade — invoice states,
  melt fulfillment, backend credential continuity. That is the KVM/
  regtest tier, not docker-fakewallet.
- Keyset ROTATION across upgrades (old keyset retired mid-ladder) —
  the tollgate #818 scenario; needs a rotation-triggered rung.
- nutshell/cashu-cf upgrade ladders (ns has no persistent-container
  upgrade story in our harness yet).
