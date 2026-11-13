# Review misses ledger — 2026-11 (what we missed, why, what now catches it)

Three misses this month, each from a different failure mode, each now covered
by a tool or rule. Read this before reviewing anything money-adjacent.

## 1. The fixture false-positives (murdawkmedia, 2026-11-12, two rounds)

**Missed:** our own conformance scenarios passed as evidence while (round 1)
the "cached replay" check accepted any second 200 and the change bounds
omitted NUT-02 input fees; (round 2) our fix compared decoded Python objects
where `True == 1` and `1 == 1.0`.

**Why missed:** we graded our own homework — the same lane wrote, ran, and
interpreted the tests, and read verdict text instead of assertion code.

**Now catches it:** `negative_controls.py` (mutation matrix, ALL GREEN,
pre-cite mandatory), `scenario-drift-lint.sh`, the type-aware canonical
comparator, EXTERNAL-CLAIMS-CHECKLIST.md.

## 2. The wrong-workdir "ghost" (2026-11-12)

**Missed:** our `config init` silently validated an abandoned mint in
`$HOME`; we then spent hours theorizing about hidden keyset history instead
of noticing we were interrogating the wrong database — and took an
unnecessary irreversible action (fresh ledger) under the wrong premise.

**Why missed:** a command with silent defaults ran unaudited; and when an
error named an identity the target provably lacked (we even ran the grep
that showed zero hits), we theorized instead of suspecting the target.

**Now catches it:** `mint-upgrade-preflight.sh` (target echo reads identity
FROM the target; falsify-on-copy before any live touch), the ops addendum
rules (attribution before explanation; falsify before irreversible; second
key for irreversibles).

## 3. The unbounded-fee review miss (felixfelix-bot, 2026-11-13, PR #1212)

**Missed:** `advanceLocked` validated a caller-supplied fee with
`fee > math.MaxInt64` — a bound no real fee approaches, i.e. decoration —
while the domain bound (fee vs the operation's own `FeeReserveMSat`) was
absent. Reachable via `Submitted → Unknown → Paid`. Our review read the same
line and moved on; felixfelix-bot probed the head: `Paid accepted,
ActualFee=MaxInt64, reserve=100` — then a 10-msat send durably refused
(budget poisoning). Independently reproduced by us (probe: both halves
confirmed; incidental bonus: the probe first tripped the fixed
submit-routing, confirming THAT fix too).

**Why missed:** we audited the PRESENCE of guards, not their SUFFICIENCY —
and our adversarial pass covered persistence/identity/state-machine edges and
comparator semantics but had no step for *value-flow*: what domain range can
each numeric field take, and what does each written value do to downstream
aggregates?

**Now catches it:**
- `tools/dead-bound-lint.sh` — flags every type-maximum comparison in
  validation/arithmetic paths; run it on money-path diffs. Proven: flags the
  exact line (store.go:546) plus its sibling (line 109).
- ADVERSARIAL-PASSES.md Prompt 3 gained the value-flow step and
  probe-on-head step (below).
- PR-REVIEW.md (tollgate-module) criterion 4 now requires the domain-range
  statement for every caller/wire-supplied numeric field.

## The general rules (all three misses, one paragraph each)

1. **A guard is a claim, not a fact.** For every bound, ask: what is the
   domain-valid range of this field, and does the check enforce it? A
   comparison against a type maximum is decoration unless the contract is
   genuinely the type range.
2. **Read what the check checks, not what it is named or that it exists.**
   Applies to our tests (miss 1), our commands (miss 2), and other people's
   guards under review (miss 3).
3. **When a result names something the target provably lacks, suspect the
   target before the theory.** And when a finding is reported by someone
   else: reproduce it before concurring (we now did — it took one probe).
