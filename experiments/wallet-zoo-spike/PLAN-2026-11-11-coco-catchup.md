# PLAN — coco catch-up after upstream #277 landed (2026-11-11)

Trigger: cashubtc/coco merged PR #613 + commit e475563 today — the Send
half of our issue #277 (automatic recovery for `rolling_back`). Melt
half was already on master. Verified by source read of master
`SendOperationService.ts` / `MeltOperationService.ts` (2026-11-11).
Upstream npm state: 2.0.0 (2026-08-17) contains the Melt recovery but
NOT today's Send recovery — #613 is master-only until the next release.

Our fork state: June patch (9d07b84) superseded; charter annotated
(Amperstrand/coco fork-charter 7aae3f9). Pecan (giftcard) rides
vendored fork coco 1.0.18 + cashu-ts 5.0.0-rc.9.

This plan covers the audit-repo lanes (target + zoo). The pecan
consumer lane is staged as Amperstrand/pecan issue (fake-money canary).
cashu-cf and lnforward/cashuexchange pins are explicitly NOT in this
pass (2.0 runbook constraints + D1 adapter port are orthogonal).

## Lane A — coco as audit target, refreshed to the recovery merge

1. Pin the target: coco @ merge commit of #613 (master, 5a3a47b merge /
   897a857 squashed content) in a fresh clone; record SHA in any
   findings header. Scope line in WALLET-AUDIT-METHODOLOGY.md still
   says "latest master" — now actually true again.
2. New audit surface — the recovery machinery itself:
   - Crash-injection battery per the PR's own decision table: rolling_back
     before reclaim submission / after mint swap / after strict restore,
     before local commit. Expected outcomes (frozen BEFORE runs, per
     method rule 1): replay-same-request → rolled_back;
     recipient-claimed → finalized + `send:finalized`; already-stored
     outputs → settle without mint; ambiguous evidence → preserved
     rolling_back. Record exact response bodies (error identity IS the
     finding).
   - Multi-session race: `abandonSendReclaim` revision fence — two Coco
     Sessions, one reclaim; predict conflict-not-drop.
   - `ops.send.recovery.run()` trigger + `reclaim()` inline
     attempt-before-reject semantics.
   - Legacy records (no stored reclaim request, spent proofs) → warn +
     manual seed restore: confirm the compat path does NOT auto-fail
     (upstream explicitly rejected our force-fail row as unsafe).
3. Cross-family divergence potential (the actual hunting ground): the
   new recovery is a NEW wallet-side consumer of checkstate (NUT-07) and
   restore (NUT-09). Mint behavior differs per family on both (cdk
   curve-validates Ys; ns Ys-shape-only; cf multi-shape; restore
   completeness semantics). Matrix: coco recovery settle outcomes × zoo
   mints (cdk 0.18.1/.18.2 arms, ns 0.20.3/0.21.0, cf testnut, gonuts).
   Prediction file first; a settle-outcome fork across mints is a
   registry-grade finding.

## Lane B — wallet-zoo: coco master as a first-class wallet arm

1. Add coco (terminal wallet) @ #613-merge SHA as a wallet column in
   the zoo matrix alongside cashu.me. Reuse spike-payer.sh rail (inr2
   cln) + the 5 pinned mint cells.
2. Core five flows per cell (ADD/MINT/SEND/RECV/MELT) — same as the
   cashu.me spike, same evidence discipline (screens/logs/wire).
3. NEW sixth flow, unique to coco: CRASH — kill the wallet mid-send
   (pre-reclaim, mid-reclaim), restart, observe auto-recovery outcome
   per mint. This is the first zoo wallet where crash behavior is
   measurable at all, and it exercises #613 on live mints.
4. Output: coco column + crash-outcome table appended to RESULT.md;
   divergences → divergences/ doc + tracker card per method.

## Order and gates

- A2 crash battery is offline-driver work (no live mints needed for the
  semantics legs) → first.
- A3 + B need zoo mints + payer rail → one bench session.
- Every run: frozen predictions before, error identities recorded,
  version matrix not latest-vs-latest.
- No upstream interaction (watch-only); findings land here, registry
  rows owner-gated as always.

## Consumer lanes (tracked elsewhere, listed for completeness)

- Pecan/giftcard.cashu.exchange: vendored fork 1.0.18 → upstream
  2.0.0-or-master-snapshot + cashu-ts rc.9→rc.13. Staged as
  Amperstrand/pecan issue (fake money = canary).
- cashu-cf pins d78b72e/d9d658e: blocked by COCO-2.0-MIGRATION-RUNBOOK
  constraints (vendoring, v4 peer-range, reserve-DB storage migration).
  Unchanged by today.
- lnforward/cashuexchange pin/* retirement: needs feat/d1-adapter port
  + an upstream release containing #613. Owner-gated, later.
- Amperstrand/coco main mirror: 15 behind → routine fast-forward per
  FORK.md policy (owner action).
