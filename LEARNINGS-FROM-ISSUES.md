# Cashu Audit Learnings — Patterns from 36+ Fixed Issues

> **Source**: Mining ISSUE-001 through ISSUE-044 in cashu-cf
> **Purpose**: Improve future audit prompts to catch more issues earlier

## Pattern 1: Spec text drift → greatspectations catches it

**Issues**: ISSUE-023 (`===` vs `<=`), ISSUE-030 (invalid sigflag), ISSUE-033 (NUT-20 format)

**Pattern**: Code was written before a spec change. When the spec evolved, the code wasn't updated.

**How to catch earlier**: greatspectations quotes at the validation point. The quote text sits directly above the code that should implement it.

**Prompt improvement**: Add "check if validation logic at each quote anchor still matches the quote's claim" to the Layer 3 audit prompt checklist.

## Pattern 2: Cross-implementation divergence → reference notes catch it

**Issues**: ISSUE-036 (witness on plain), ISSUE-044 (anyone-can-spend)

**Pattern**: CDK/Nutshell handle an edge case differently. cashu-cf follows one behavior but not the other.

**How to catch earlier**: Layer 2 REF notes + cross-impl comparison.

**Prompt improvement**: Add "for each MUST requirement, identify how CDK, Nutshell, and cashu-cf each handle it" to cross-impl comparison prompts.

## Pattern 3: Accounting fields missing → spec evolution gap

**Issues**: ISSUE-023 (amount_paid/amount_issued), ISSUE-029 (NUT-04 accounting fields), ISSUE-034 (method field), ISSUE-039 (amount_issued persistence)

**Pattern**: NUT-04/05 added new mandatory fields. Implementation has the old response shape.

**How to catch earlier**: Check every response object against the current spec's field list.

**Prompt improvement**: Add a "response schema completeness" checklist to each NUT audit — enumerate every field the spec requires and check if the response object includes it.

## Pattern 4: Security — data leakage in logs and responses

**Issues**: ISSUE-041 (private key leak), ISSUE-042 (raw error messages)

**Pattern**: Error handling paths expose internal details to clients or logs.

**How to catch earlier**: Security-focused audit that greps for `err.message`, `error.message`, `console.log` with sensitive data.

**Prompt improvement**: Add a security audit checklist:
- [ ] No raw exception messages in HTTP response bodies
- [ ] No private keys, secrets, or tokens in log output
- [ ] Error responses follow NUT-00 format exactly
- [ ] Input validation rejects negative amounts, empty arrays, oversized requests

## Pattern 5: State machine bugs → E2E testing catches it

**Issues**: ISSUE-030 (locktime behavior), ISSUE-031 (HTLC pathways), ISSUE-043 (SIG_ALL melt), ISSUE-044 (anyone-can-spend)

**Pattern**: State transitions (locktime expired, refund pathway, SIG_ALL mode) have bugs that only manifest with specific proof configurations.

**How to catch earlier**: Layer 4 E2E tests with all state combinations.

**Prompt improvement**: Generate test vectors for all possible states:
```
States: primary_active, primary_expired, refund_active, refund_expired
Flags: SIG_INPUTS, SIG_ALL
Types: P2PK, HTLC_preimage, HTLC_refund
= 12 base combinations × swap/melt = 24 scenarios
```

## Pattern 6: Dependency hygiene

**Issues**: ISSUE-028 (elliptic CVE), ISSUE-040 (deprecated uuid)

**Pattern**: Old/vulnerable dependencies.

**How to catch earlier**: Regular `npm audit` + dependency age check.

**Prompt improvement**: Add dependency audit to Layer 3 checklist.

## Pattern 7: Error code mismatches

**Issues**: ISSUE-029 (missing 20001-20003 codes), ISSUE-042 (raw error messages), ISSUE-046 (extra `error` field)

**Pattern**: Error codes don't match spec, or error response format deviates.

**How to catch earlier**: Compare every error response against the NUT-00 error code table + response format.

**Prompt improvement**: Add "verify error response format matches NUT-00 exactly: `{detail, code}` with no extra fields" to audit checklist.

## Improved Audit Prompt Template

Based on these learnings, the general NUT audit prompt should now include:

```
## Audit Checklist (updated 2026-07-28)

### Spec Compliance (Layer 1)
- [ ] Every MUST requirement has a greatspectations quote
- [ ] Quotes use verbatim markdown (including **MUST** bold markers)
- [ ] spectate check exits 0

### Response Schema Completeness (NEW)
- [ ] Every response field specified in the NUT is present in the response object
- [ ] Response fields have correct types (string, int, null)
- [ ] No extra non-standard fields (NUT-00 format violation)

### Error Handling (ENHANCED)
- [ ] Error responses follow NUT-00 format: `{detail, code}` only
- [ ] No raw exception messages in HTTP response bodies
- [ ] Error codes match the NUT-00 error code table
- [ ] Missing/invalid inputs return correct error codes

### Security (NEW)
- [ ] No private keys, secrets, or tokens in log output
- [ ] Input validation rejects: negative amounts, empty arrays, oversized requests
- [ ] No stack traces or internal paths in error responses

### Cross-Implementation (ENHANCED)
- [ ] For each MUST: how does CDK handle it? Nutshell? This impl?
- [ ] Are state transitions handled the same way?
- [ ] Are error codes the same?

### Behavioral (Layer 4)
- [ ] All state transitions tested via E2E
- [ ] Locktime + refund + SIG_ALL matrix covered
- [ ] Race conditions tested where applicable
```

---

## Patterns from the 2026-07-30 review pass (ISSUE-050 + refactor review)

> These extend the catalog past ISSUE-044, drawn from auditing a large test-cleanup
> effort + a state-machine refactor extraction. Full checklist: `prompts/CASHU-MINT-AUDIT-CHECKLIST.md`.

### Pattern 4: False-green suites — skips hiding active-feature coverage

**Found in**: cashu-cf ISSUE-050 cleanup (7 `MintCoordinatorDO` crash-recovery tests skipped rather than rewritten; 3 proof/DLEQ-determinism skips).

**Pattern**: a test-count reduction achieved by `.skip`-ping hard-to-fix tests on ACTIVE features (not removed ones). The suite looks greener but coverage actually shrinks. The hardest categories (crash recovery, concurrency, crypto determinism) are the most likely to be punted this way.

**How to catch earlier**: after any "test cleanup" PR, run `grep -rn "\.skip" test/` and require each skip to reference a follow-up issue or name the removed feature. Skips without reasons = finding. Compare the "Test Files" + "skipped" counts run-over-run — a rising skip count during a "fix" effort is the smell.

**Prompt improvement**: add a "skip audit" step to the release runbook: enumerate all skips, classify each as removed-feature (ok) vs active-feature-coverage-gap (finding).

### Pattern 5: JS Number() precision loss on amounts > MAX_SAFE_INTEGER

**Found in**: cashu-cf `deriveKeysetIdFromPublicHexMap` (keyset-ID derivation for large-amount keysets). Hidden behind a skipped test, not filed as a bug.

**Pattern**: Cashu amounts are integers, but in JS any `Number(amount)` on amounts > 2^53 silently loses precision. Amounts feed keyset-ID derivation, fee calc, and signature hashes — so precision loss = wrong keyset ID / wrong signature = silent fund corruption.

**How to catch earlier**: `grep -rn "Number(" src/` over every amount→hash/derive/fee path. CDK (Rust `u64`) and Nutshell (Python arbitrary-precision int) are immune; **JS/TS implementations are the risk zone**. Any `Number()` on an amount that could exceed 2^53 is a finding.

**Prompt improvement**: add "audit all amount-to-hash/derive conversions for Number vs BigInt" to the crypto/keyset audit prompt.

### Pattern 6: CAS atomicity as a first-class audit dimension

**Found in**: cashu-cf ISSUE-049 (concurrent double-melt TOCTOU), verified preserved through the T6 state-machine extraction.

**Pattern**: mint/swap/melt quote state machines are the fund-safety boundary. The question is always: is the UNPAID→PENDING transition a SINGLE atomic conditional write, or a read-check-write with a TOCTOU at the `await`? On Durable Objects / event-loop runtimes, `await` yields control — so a 600-line gap between read and write is a live race window even single-threaded.

**How to catch earlier**: for every state-machine transition, trace: (a) is there exactly ONE entry path, (b) is it atomic on the storage backend (SQL conditional UPDATE yes; KV put no), (c) does the race-loser get a clean rejection BEFORE any side effect (proof reservation, payment dispatch). This is now Section 2 of the audit checklist.

**Prompt improvement**: add "enumerate every UNPAID→PENDING path; verify single + atomic" to the concurrency audit prompt. CDK's `verify_and_set_melt_quote_pending` and Nutshell's `_verify_spent_proofs_and_set_pending` are the reference atomic primitives.

### Pattern 7: Wontfix decisions with unflagged future-work dependencies

**Found in**: cashu-cf ISSUE-052 (wontfix on Failed/Unknown melt states — sound, but safety depends on T11 saga recovery which isn't implemented).

**Pattern**: a wontfix that reasons "X will handle this" where X is unimplemented future work. The decision is correct as a target design but unsafe today, and the gap is invisible because the wontfix label reads as "resolved."

**How to catch earlier**: for every wontfix, ask (a) is the binding constraint real (verify empirically), (b) does the decision depend on unimplemented work. Every "X will handle it" must link X as a precondition; if X is unimplemented, the wontfix is really a "deferred" with an open dependency.

**Prompt improvement**: add a "wontfix dependency audit" — for each wontfix, list any unimplemented preconditions and their tracking issues.
