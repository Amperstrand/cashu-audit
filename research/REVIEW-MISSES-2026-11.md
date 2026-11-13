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

---

## Appendix (2026-11-13): is the fee-bound question well-studied? Ecosystem survey

**NUT-05 spec**: `fee_reserve` is defined as a *quote-time estimate* ("the
additional fee reserve for using the method; the wallet provides proofs
covering at least amount + fee_reserve + fee"). The spec is silent on what
happens when the actual fee exceeds the reserve — no bound, no reconciliation
vocabulary. So there is no spec position to cite; both murdawk's
consumer-verifies and the journal-bounds positions are spec-compatible.

**cdk** (the reference implementation): in `add_transaction_for_pending_melt`
the recorded fee is **derived, never ingested**: `fee = proofs_total
.checked_sub(amount).checked_sub(change_total)` — saturating subtraction, so
the recorded fee structurally cannot exceed the inputs the wallet itself
committed. The number of record is computed from other verified quantities,
not accepted from a caller. cdk#2859 (open) is tightening exactly this fee
accounting further. **This is the strongest precedent against unbounded
ingestion: the reference wallet derives fees rather than accepting them.**

**nuts issues**: #480 (blank-output sizing when inputs exceed invoice —
adjacent, change-side), #335 "Capped Input Fee melt quotes" (closed proposal —
the community has already tried to formalize fee caps at the quote layer),
#364 (zero fee_reserve for internal channels — reserve is a policy knob, not
a law). No issue found that discusses the *journal/ledger* layer's
responsibility for fee magnitude. **The layer in question appears
under-specified ecosystem-wide — which is itself worth saying.**

**Payment-ledger engineering** (outside Cashu, heavily studied): the invariant
literature is unanimous that a ledger must enforce its invariants *at the
write boundary*, not trust callers to pre-check — "re-validate on every Post
rather than trusting the caller to have pre-checked" (five-invariants
pattern); amounts stored as integers with **overflow checks on running sums**
precisely because "a malicious or buggy caller cannot wrap around to zero";
balances derived from entries, never written from caller input. Double-entry's
zero-sum rule is an *ingestion* constraint: the ledger rejects what it can't
balance at the door. The consistent principle across Stripe/Square/bank-grade
ledger write-ups: **the entity that enforces an aggregate owns the bounds of
what feeds the aggregate.** Verification of external truth stays with the
caller; magnitude bounds at the posting boundary belong to the ledger.

**Our position after the survey** (context, not verdict): murdawk's
settlement-verification doctrine is correct and matches cdk practice; but the
specific question — may an unbounded caller-supplied number feed the journal's
own budget aggregate — has a clear answer in both the reference
implementation (derives, never ingests) and five centuries of ledger practice
(the aggregate owner bounds the input). The honest framing for the thread:
not "you're wrong," but "this layer is under-specified in the ecosystem, and
both the reference wallet and payment-ledger practice point the same way."
