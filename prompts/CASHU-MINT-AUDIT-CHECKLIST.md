# Cashu Mint Audit Checklist — Implementation-Agnostic

> **Purpose**: A reusable checklist for auditing ANY Cashu mint implementation
> (cashu-cf, CDK, Nutshell, Nutmix, macadamia, …) for correctness, security, and
> test-suite honesty. Distilled from the cashu-cf audit (ISSUE-001 → ISSUE-052 +
> the 2026-07-30 review pass). Each check names the pattern, how to detect it, and
> a worked cashu-cf example. Apply per-implementation; record findings in
> `divergences/`.

## How to use

For each implementation under audit, run every section. A "finding" is filed as
`divergences/<IMPL>-<CATEGORY>-<DATE>.md`. Patterns that are genuinely
implementation-specific go there; patterns that recur across implementations get
promoted into this checklist's worked examples.

---

## 1. Test-suite honesty (false-green detection)

A green `npm test` / `cargo test` / `pytest` that hides real bugs is worse than a
red one — it kills the CI signal. This is the highest-leverage audit dimension.

### 1a. Skipped tests hiding active-feature coverage
**Detect**: `grep -rn "\.skip\|describe\.skip\|# pytest.mark.skip|ignore" test/ tests/`.
For each skip, ask: does it skip a **removed/unimplemented feature** (legitimate)
or an **active feature the fixer couldn't repair** (coverage gap)?
**Worked example (cashu-cf)**: the ISSUE-050 cleanup skipped 7
`MintCoordinatorDO` crash-recovery/concurrency tests rather than rewriting the
stale RPC simulations — leaving the reserve/commit/rollback crash-recovery
guarantees **unverified**. Also 3 proof-verification + DLEQ-determinism skips.
**Cross-impl note**: CDK/Rust uses `#[ignore]`; Nutshell uses `@pytest.mark.skip`.
**Action**: every skip must reference a follow-up issue or state the removed
feature. Skips without a reason are a finding.

### 1b. Loosened assertions (strict → weak matcher)
**Detect**: diff recent test-fix commits; flag `-toBe(X)` → `+toBeDefined/toBeTruthy`,
removed `expect()` calls, or `toBe` → `toContain` on contract fields.
**Worked example (cashu-cf, CLEAN)**: the ISSUE-049 concurrent-melt CAS test was
*updated* (422→400, `.error`→`.code`) but the core invariant
`expect([200].length).toBe(1)` (exactly-one-succeeds) was preserved — the right
way to fix drift. The bad pattern would have been dropping the count assertion.
**Action**: any strict→weak drift that isn't a field-rename is a finding.

### 1c. Stale named constants
**Detect**: tests asserting `CashuErrorCodes.X` where the constant diverges from
the actually-emitted value (common when error classes and constant enums evolve
independently).
**Worked example (cashu-cf)**: `CashuErrorCodes.INVOICE_ALREADY_PAID = 40003` but
`InvoiceAlreadyPaidError` emits `20006`; `PAYMENT_FAILED` constant vs literal
`20004`. Tests using the wrong constant pass against the constant but fail
against reality (or vice-versa).
**Action**: cross-check each error-code constant against the class that emits it.

### 1d. Load-failure masking
**Detect**: a test file that fails to IMPORT/transform silently removes its tests
from the count. A suite can look "more green" after breaking imports.
**Worked example (cashu-cf)**: 14 files importing `@cashu/crypto/modules/*`
(non-existent subpath) silently dropped ~60 tests from the count until fixed.
**Action**: compare "Test Files" count run-over-run; unexplained drops =
load failures.

---

## 2. State-machine concurrency (the fund-safety core)

Mint/swap/melt quote state machines are the fund-safety boundary. A TOCTOU here
= double-spend or fund loss.

### 2a. Atomic UNPAID→PENDING (the double-melt guard)
**Detect**: find every UNPAID→PENDING transition. Is it a **single conditional
UPDATE** (`UPDATE ... WHERE id=? AND state=?`, check `changes>0`), or a
**read-check-write** (read state, `await`, write) that re-opens a TOCTOU at the
await boundary?
**Worked example (cashu-cf ISSUE-049)**: the melt handler read state at L1539
but wrote PENDING at L2185 (unconditional) — a 650-line TOCTOU window. Fix: CAS
primitive. CDK uses `verify_and_set_melt_quote_pending` (atomic DB tx).
**Cross-impl note**: CDK = SQL transaction; Nutshell = `_verify_spent_proofs_and_set_pending`;
cashu-cf = conditional UPDATE. Verify the chosen primitive is actually atomic on
the storage backend (SQLite yes; KV no — KV-only is best-effort).
**Action**: confirm there is exactly ONE UNPAID→PENDING path and it's atomic.

### 2b. Fund-loss-prevention on Unknown payment status
**Detect**: when a Lightning payment returns Unknown/Pending, does recovery
**assume failure** (→ compensate/rollback = fund loss if it actually settled) or
**re-check the real status** before deciding? CDK rule: never compensate after
payment is attempted.
**Worked example (cashu-cf ISSUE-052)**: wontfix decision to NOT add CDK's
`Failed`/`Unknown` wire states is sound (cashu-ts only has 3), but it **depends
on T11 saga recovery** which isn't implemented — so Unknown melts currently rely
on a 1800s stale-proof backstop (#48). The decision is correct as a *target* but
unsafe *today*.
**Action**: trace the Unknown-status path end-to-end; confirm recovery re-checks
LN, never assumes.

### 2c. Crash recovery determinism
**Detect**: simulate a crash at every saga/state step; does recovery resolve to a
terminal state (finalize or compensate) deterministically, or can proofs strand
PENDING?
**Action**: if the impl has a saga/recovery table, verify recovery exists AND is
wired to an alarm/cron — not just schema.

---

## 3. Numeric precision (Cashu's silent corruption)

Cashu amounts are integers (sats), but keyset IDs and signatures hash over them.
A `Number()` where `BigInt` is needed silently corrupts.

### 3a. BigInt vs Number for amounts > MAX_SAFE_INTEGER
**Detect**: `grep -rn "Number(" src/` over any path that feeds amount into a hash
or keyset-ID derivation. Amounts > 2^53 lose precision.
**Worked example (cashu-cf)**: `deriveKeysetIdFromPublicHexMap` uses `Number()`
for amounts > MAX_SAFE_INTEGER → wrong keyset ID for large-amount keysets.
Currently hidden behind a skipped test (finding: file as a bug, not a skip).
**Cross-impl note**: CDK uses `u64`/`Amount`; Nutshell uses Python int (arbitrary
precision) — both safe. JS impls are the risk zone.
**Action**: audit every amount→hash/derive path for Number overflow.

### 3b. msat↔sat conversion rounding
**Detect**: NUT-15 `mpp_amount` is msat; melt quote `amount` is integer sats. Find
the conversion. `Math.ceil` overcharges; `Math.floor`/`round` can yield 0-sat
quotes for tiny partials.
**Worked example (cashu-cf #49)**: `Math.ceil(mppAmount/1000)` overcharges up to
999 msat/partial. No single rounding direction is always correct — the honest fix
is reject sub-sat partials (Cashu can't represent them).
**Action**: confirm the conversion direction is deliberate + documented.

---

## 4. Error-format consistency (wire contract)

Wallets pattern-match on error shape; inconsistency breaks them silently.

### 4a. Two error shapes coexisting
**Detect**: do all error responses use ONE shape? Cashu-cf has two:
`createStandardErrorResponse` → `{error, detail, code}` and `CashuError` subclass
via `createErrorResponse` → NUT-00 `{detail, code}` (no `error` field).
**Worked example (cashu-cf)**: `QuoteExpiredError`/`InvoiceAlreadyPaidError` emit
`{detail, code}` while most others emit `{error, detail, code}`. Tests must
assert the right shape per error class.
**Action**: enumerate error responses; confirm shape consistency or document the
two families.

### 4b. HTTP status standardization
**Detect**: are double-spend / quote-pending / spending-condition errors returned
at consistent, spec-aligned statuses? (NUT-03/05 don't mandate, but wallets
expect 400/403, not 422.)
**Worked example (cashu-cf ISSUE-046)**: standardized 422/424 → 400 across the
board; the canonical `CommonErrors.tokenAlreadySpent()` already used 400.
**Action**: grep for non-400/403/404/500 statuses on error paths; justify each.

---

## 5. Decision / wontfix scrutiny

Wontfix decisions accumulate tech debt invisibly. Audit the reasoning, not just
the label.

### 5a. Does the wontfix reasoning hold? Are dependencies flagged?
**Detect**: for each wontfix, (a) is the binding constraint real (verify it
empirically — e.g., does the type library really lack the variant?), (b) does
the decision depend on unimplemented future work?
**Worked example (cashu-cf ISSUE-052)**: wontfix on Failed/Unknown states —
reason 1 (cashu-ts 3-variant enum) verified binding; reason 3 (saga subsumes)
correct but depends on T11 (not implemented). Decision stands but the T11
dependency was under-flagged.
**Action**: every wontfix citing "X will handle it" must link X as a precondition.

---

## 6. Cross-implementation divergence (the reusable database)

When a finding is implementation-specific, record it; when it recurs, promote it
here. Maintain `divergences/CDK-VS-NUTSHELL-ALIGNMENT-*.md` as the live table.

**Rule**: for any NEW conformance failure, first check whether BOTH other
references pass it. If yes → Category A (impl-specific bug, fix to match spec).
If no → Category B (genuine divergence, record in the alignment table, default
resolution = follow CDK unless the NUT spec is explicit).
