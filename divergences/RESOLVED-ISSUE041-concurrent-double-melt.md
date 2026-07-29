# RESOLVED: cashu-cf #41 — Concurrent Double-Melt (TOCTOU on UNPAID→PENDING)

| Field | Value |
|-------|-------|
| Status | **RESOLVED** (2026-07-29) |
| Severity | CRITICAL |
| Found by | cashu-audit Layer 3 deep audit |
| Fix commit | `83235ed` (cashu-cf main) |
| Deployed to | testnut.cashu.exchange, signut.cashu.exchange |
| Internal issue | ISSUE-049 (`docs/issues/ISSUE-049-concurrent-double-melt.md`) |

## The finding

The melt handler (`src/api/melt.ts`) read the melt-quote state to reject
already-PENDING/PAID quotes, then performed the `UNPAID → PENDING` transition
~650 lines later via an **unconditional** `ctx.updateMeltQuote(quote)`. The
SQL `updateQuoteState` had no `AND state = ?` guard, so the write was not
atomic either.

Between the read check and the write are many `await` points. A Durable
Object serializes requests at the event-loop level, but `await` yields
control — so two concurrent melt requests on the same quote (with disjoint
proof sets) interleaved: both read `UNPAID`, both passed the check, both wrote
`PENDING`, and both called `pay_invoice`. The loser's proof set was burned
for nothing.

## The fix

Atomic Compare-And-Set on the `UNPAID → PENDING` transition:

- New repository contract method `compareAndSetState(id, expectedFrom, newState, patch?)`.
- SQLite impl: a single conditional
  `UPDATE melt_quotes SET state=?, data=?, input_amount=? WHERE id=? AND state=?`
  — returns `changes > 0` (truly atomic w.r.t. other writers).
- KV impl: best-effort read-check-write (KV has no conditional put); the
  TOCTOU window is narrowed because the CAS is invoked at the write site, not
  600 lines earlier.
- Wired through `LedgerCrud` → `Ledger` (cache + broadcast on win) →
  `MeltContext.compareAndSetMeltQuoteState?` → `router.ts` → `handleMelt`.
- The handler now CAS-transitions `UNPAID→PENDING`; the race-loser gets
  `QuotePendingError` (HTTP 403, code 20005) **before any proof is touched**,
  so no rollback is required. Backward-compatible fallback to the
  unconditional write when the context lacks the CAS method.

## Evidence

### Unit tests (cashu-cf)

`test/unit/repositories/melt-quote-repository.contract.unit.test.ts` adds a
`compareAndSetState (atomic CAS — issue #41 concurrent double-melt)` block
run against BOTH the SQLite and KV backends (10 tests total). The load-bearing
case:

```
KV: MeltQuoteRepository > compareAndSetState ... > rejects the second concurrent writer (the race-loser) — regression for double-melt ✓
SQLite: MeltQuoteRepository > compareAndSetState ... > rejects the second concurrent writer (the race-loser) — regression for double-melt ✓
```

Both backends: first CAS `UNPAID→PENDING` returns `true`; the second
concurrent CAS on the now-`PENDING` quote returns `false`. All 186 tests in
the melt / repository / idempotency suites pass; the 156 pre-existing unit
failures (ISSUE-050) are unchanged.

### Conformance scenario (cashu-audit)

`conformance/scenarios/security_concurrent_melt.py` adds two live scenarios:

1. `concurrent_double_melt_rejected` — fires two concurrent melts on the same
   quote with disjoint proof sets via a 2-worker thread pool; asserts exactly
   one pays and the loser is rejected.
2. `sequential_double_melt_rejected` — the non-concurrent control case
   (second melt on a PAID quote is rejected).

Run against the deployed mint:

```bash
cd conformance && python3 run_matrix.py --mint https://testnut.cashu.exchange
```

## Verification of deploy

Both environments were redeployed with the fix and confirmed live:

- `https://testnut.cashu.exchange/v1/info` → "Testnut mint"
- `https://signut.cashu.exchange/v1/info` → "Signet Cashu Mint"

## Related / still open

This closes the #41 / ISSUE-049 concurrency hole. Other cashu-cf conformance
gaps tracked in `CASHU-CF-CONFORMANCE-20260728.md` (HTLC + SIG_ALL, locktime
primary pathway, HTLC refund preimage) remain open and are independent of
this fix.
