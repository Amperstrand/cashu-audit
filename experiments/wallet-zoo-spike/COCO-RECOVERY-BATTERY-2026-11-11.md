# COCO RECOVERY BATTERY — RESULT (2026-11-11, lane A2 offline legs)

Target: cashubtc/coco @ 2d6aa5834bf261749b2453ef64f2b3cd89c0e8c4
(master, post-#613 "settle interrupted send reclaims during recovery").
Driver: bun 1.4.2, coco's own test fixture harness
(`createSendEnvironment`, fake mint remote, in-memory repos). Driver
file preserved next to this doc:
`drivers/SendRecoveryAdversarialBattery.test.ts` (drop into
`packages/core/test/unit/` of a coco clone at the target SHA, then
`bun install && bun test <file>`).

## Baseline (upstream suite, unmodified)

    bun test SendOperationService.recovery.test.ts SendOperationService.test.ts MeltOperationService.test.ts
    → 101 pass, 0 fail, 463 expect() calls

Upstream's own suite covers the sequential decision table end to end
(replay-unspent, restore-completion, recipient-claimed→finalized,
pending-states preserve, restore-unavailable, legacy no-request
unspent/spent, definitive-rejection non-resend, lost-response,
failed-commit, session-replacement fence, already-stored outputs,
inline reclaim attempt-before-reject). No gaps found in sequential
coverage.

## Adversarial legs (ours; frozen predictions in the driver header)

    P1+P3 two Coco Sessions recover the same rolling_back Send concurrently  PASS
    P2     second full recovery pass after settlement is a no-op              PASS
    P4     on-demand api.recovery.run() settles; second run() is a no-op     PASS

    3 pass, 0 fail, 24 expect() calls

Invariants held under P1: terminal state exactly once, exactly one
`send:rolled-back` event, no duplicated proof secrets, available total
exactly the reclaimed 10. Replay identity (P3): the replayed reclaim
call's INPUTS and OUTPUTS both deep-equal the original request — the
recovery never regenerates a request (upstream asserted only the
outputs argument; this extends it to inputs).

## Measured behavior worth knowing (not a bug)

Lock topology is PER-SERVICE-INSTANCE: with two Coco Sessions sharing
one wallet recovering the same operation, BOTH replay the reclaim to
the mint (reclaim calls total = 3 = original + two replays). Safety
comes from the conditional transaction layer (single commit winner),
NOT from avoiding the duplicate network call. Against a real mint the
second replay receives a definitive spent-input rejection and that
session settles from mint evidence instead — upstream's
definitive-rejection path covers this (verified by their suite). Net:
multi-session deployments do duplicate one reclaim request during
concurrent recovery; convergent and idempotent, but not
call-optimal. Recording as behavior; no upstream action (add-or-stay-
silent: their tests document the design; call-count is a new fact of
no safety consequence).

## Lane status

- A2 (offline semantics battery): DONE (this doc).
- A3 (recovery settle-outcomes × live zoo mints — cdk/ns/cf/gonuts
  checkstate+restore divergence surface): bench session pending.
- B (zoo wallet arm + crash flow): pending, same bench session.
