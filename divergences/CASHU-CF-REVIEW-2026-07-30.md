# cashu-cf review findings — 2026-07-30 (test-cleanup + refactor audit)

Findings from the read-only review of the ISSUE-050 cleanup (bg task) and the
ISSUE-051 T6 state-machine extraction (T6 LLM). Filed here so they survive the
session and feed the audit checklist (`prompts/CASHU-MINT-AUDIT-CHECKLIST.md`).

## Finding 1: BigInt precision loss in keyset-ID derivation (REAL BUG, unfiled)

**Severity**: HIGH (silent fund corruption for large-amount keysets)
**Location**: `src/mint/keysets.ts` — `deriveKeysetIdFromPublicHexMap`
**Status**: HIDDEN behind a skipped test, NOT filed as an issue.

`deriveKeysetIdFromPublicHexMap` uses `Number()` for amounts that can exceed
`Number.MAX_SAFE_INTEGER` (2^53). For keysets with a denomination > 2^53 sats,
the precision loss produces a WRONG keyset ID → proofs minted/validated against
the wrong derivation → silent corruption.

Two tests document it (honestly) but as skips:
```
// SKIP: deriveKeysetIdFromPublicHexMap loses precision via Number() for amounts > MAX_SAFE_INTEGER (ISSUE-050).
it.skip('deriveKeysetIdFromPublicHexMap handles very large amounts deterministically', ...)
it.skip('derives keyset id deterministically for large-amount keyset', ...)
```

**Action**: file as a cashu-cf issue (Category A — JS-specific bug, CDK/Nutshell
immune). Fix: use `BigInt` throughout the derivation path. This is Pattern 5 in
`LEARNINGS-FROM-ISSUES.md` and Section 3a of the audit checklist.

## Finding 2: MintCoordinatorDO crash-recovery coverage gap (7 tests skipped)

**Severity**: MEDIUM (recovery/concurrency guarantees currently unverified)
**Location**: `test/unit/mint/mint-coordinator-do.concurrency.unit.test.ts` +
`test/unit/mint/mint-coordinator-crash-restart.unit.test.ts`
**Status**: skipped in the ISSUE-050 cleanup, no follow-up issue filed.

Seven tests covering the `MintCoordinatorDO` reserve/commit/rollback RPC contract
under crash + concurrency were skipped (not fixed) because the RPC contract
drifted and the test simulations went stale:
- `rolls back active reservations during reconciliation after a crash`
- `preserves committed reservations across crash and reconciliation`
- `rolls back pending reservations but preserves committed ones (mixed scenario)`
- `rejects commit requests with mismatched operation_id`
- `concurrent reservations do not double-spend`
- `simulated concurrent commits: only one commit wins`
- `rollback frees pending proofs allowing later success`

These test ACTIVE features (the DO's atomicity guarantees), not removed ones. The
22-failure "green" is therefore partly illusory — the recovery/concurrency layer
is dark.

**Action**: file as a cashu-cf issue — these test simulations need rewriting to
match the current reservation lifecycle (the RPC contract changed). This is
Pattern 4 in `LEARNINGS-FROM-ISSUES.md` and Section 1a of the audit checklist.

## Verified CLEAN (no finding)

- **ISSUE-049 CAS atomicity** preserved through the T6 `state-machine.ts`
  extraction: `transitionToPending` is a single conditional UPDATE, the race-loser
  gets `QuotePendingError` before any side effect, and it's the only UNPAID→PENDING
  path (line 2884 is post-CAS idempotent re-assertion). T1.6 golden test 15 locks
  the fund-safety invariant. ✓
- **T1.6 golden tests (15-22)**: rigorous and substantive — test 15 asserts no
  Lightning/proof mutation on CAS-loss; test 20 asserts full rollback (state,
  payment fields, proofs→UNSPENT, commit-not-reached). No over-loosening. ✓
- **ISSUE-050 assertion fixes** (bg task): the concurrent-melt CAS test, reservation
  assertions, and payment-failure code were properly UPDATED (error shape, snake→camel,
  literal codes) without weakening. ✓
