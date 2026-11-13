# Adversarial passes — the murdawk method, decomposed and mechanized

Observed across his 2026-11 audit rounds (fixture audit, round-2 type audit):

1. **Read the assertion, never the name.** First move is always the source of
   the check, not the verdict text. "Cached" in a name means nothing until
   the `if` that gates PASS is read.
2. **Counterexample + honest control, both synthetic.** For any claim, build
   the minimal input that must fail and the minimal input that must pass, and
   run both. "Both counterexamples reproduced, with their honest controls
   passing." A test that cannot fail is decoration.
3. **Enumerate the equation before judging the number.** The input-fee find:
   list every term of both sides (amount, fee_reserve, input fees, rounding),
   compute the interval, then check the observation against it. Divergence
   claims require the arithmetic, with the target's actual metadata.
4. **Attack the comparator, not just the values.** `True == 1`, `1 == 1.0`,
   dict-vs-bytes: the equality operator's semantics are part of the attack
   surface.
5. **Audit the claim's scope, not just its result.** Does the label say what
   was measured (decoded vs byte identity; self-reported vs pinned version;
   which endpoint, which fields differ)?
6. **Separate evidence classes, always.** Source-read ≠ synthetic-repro ≠
   live-observation; state which one each sentence is, and never let one
   impersonate another.

Mechanized here: `negative_controls.py` (mutation runner: honest proxy-fronted
arm + mutation taxonomy; a surviving mutant = a false-positive scenario).
Run it in the pre-cite pass alongside `scenario-drift-lint.sh`.

---

## Prompt 1 — TEST-AUDIT pass (reviewing our own or others' tests)

    You are auditing a test suite for FALSE POSITIVES — tests that pass when
    they should fail. For each test below, in order:
    (1) Paste the exact lines that gate the PASS verdict. Ignore the test's
        name and description entirely.
    (2) Name the claim the test makes in one sentence. Does the gated check
        actually test that claim? List any distinction the test REPORTS in
        messages/notes that its verdict does not depend on.
    (3) Construct two synthetic inputs: one that must PASS (honest control)
        and one that must FAIL (counterexample). Include at least one
        comparator-level mutation: type coercion (boolean vs 1, 1 vs 1.0),
        field dropped, field added, value off by the smallest unit the
        equation allows, and — for "identical/cached/exact" claims — a
        second response that differs only in a way a naive `==` accepts.
    (4) If the test has numeric bounds: write out both sides of the equation
        term by term (all fee components, rounding mode and where it applies,
        units). Check the terms against the protocol spec and the target's
        actual published metadata, not assumptions.
    (5) Verdict per test: SOUND / FALSE-POSITIVE (the counterexample passes)
        / SCOPE-MISMATCH (label ≠ measured) / CRASHY (refuses only by
        throwing). Attach the two synthetic inputs to every non-SOUND
        verdict.
    Do not run anything live; synthetic in-process inputs only. State at the
    end which evidence class each verdict rests on.

## Prompt 2 — CLAIMS-AUDIT pass (before publishing any evidence table)

    You are auditing an evidence table before it is cited outside this
    repository. For every cell:
    (1) What exactly was measured — name the endpoint, the request fields,
        the comparator, and the response field the verdict rests on.
    (2) What identity was it measured against — pinned digest/commit, or
        self-reported metadata? If self-reported, the cell must say so.
    (3) Could the scenario that produced this cell survive a mutation?
        Check it against the negative-controls runner; any surviving mutant
        invalidates the cell until fixed.
    (4) Downgrade every cell that cannot show: assertion source + honest
        control + counterexample + identity provenance. Downgraded cells are
        labeled UNVERIFIED — not omitted, not softened.
    (5) Open cells stay visibly open. A table that implies more coverage
        than it measured is the failure mode.

## Prompt 3 — PRE-MERGE adversarial pass (money-path PRs)

    You are the adversary for this diff. Your job is to construct failures,
    not to confirm the author's intent:
    (1) For each invariant the diff claims (ordering, binding, ceiling,
        idempotence), write the wire-level or state-level input that breaks
        it: wrong-echo responses, type-mutated fields, values at and beyond
        each bound, crash-at-every-persistence-boundary, and the race where
        state changes between check and use.
    (2) For each destructive action (delete, retire, mark-paid, release),
        name the unverified premise it rests on and the minimal experiment
        that would falsify that premise on a copy.
    (3) For each error path: what does the code INFER from a rejection? Any
        inference from an error identity must hold across all three
        implementation families or be refused.
    (4) VALUE-FLOW pass (added after the #1212 fee miss): for every numeric
        field written from caller or wire input, state the DOMAIN-valid range
        (e.g. fee vs the operation's reserve — never the type maximum) and
        trace the value into every downstream aggregate (budgets, sums,
        counters, cost models). A value that passes field validation but
        poisons an aggregate is a finding even if nothing crashes.
    (5) Check every comparison of received data for comparator semantics
        (type coercion, decoded-vs-raw, order sensitivity). Run
        dead-bound-lint.sh on the diff — every type-maximum comparison must
        justify itself or be replaced with the domain bound.
    (6) PROBE-ON-HEAD: for each suspected gap, write the smallest real probe
        against the actual branch and run it (then remove it). A finding is
        ready to report when the probe shows the bad value accepted AND its
        downstream consequence — felixfelix-bot's #1212 demonstration is the
        template: 'ACCEPTED fee=9223372036854775807 (reserve was 100)' plus
        'a 10 msat send is now refused'.
    (7) Output: findings as reproducible inputs (curl/python), each with its
        honest control; then the falsification experiments you would demand
        before merge, most-destructive first.

---

## Applying this to PRTA

The router-verification suite (kill/restart at transaction boundaries, mint
faults) deserves the same mutation matrix: for each PRTA leg, inject the bug
classes it exists to catch (silent input destruction, phantom credit,
premature retirement, replay-acceptance) into a stub router/wallet and verify
the leg goes RED. A PRTA leg that stays green with the bug planted is a
false-positive gate — the exact class murdawk found twice in our conformance
scenarios. Same runner shape: honest target behind a fault-injecting front.
