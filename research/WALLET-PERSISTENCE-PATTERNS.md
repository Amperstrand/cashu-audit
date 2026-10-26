# Wallet persistence & recovery patterns across the Cashu ecosystem

Companion to Amperstrand/nucula `research/mcu-money-safety` (the MCU
application of these patterns). Survey conducted 2026-10-26 from source:
cdk 0.18.1, cashu-ts (SDK), cashu-ui (the original wallet.cashu.space
server wallet, Python), minibits_wallet (React Native + SQLite),
CocoCashuSwift (iOS SDK). gonuts excluded (unmaintained).

## The converged doctrine

Three independent implementations — server (cdk/Rust), mobile
(minibits/TypeScript), SDK (CocoCashuSwift/Swift) — arrived at the same
four rules. None of them copied each other's code; the constraints
forced the same answers.

**Rule 1 — Write intent/recovery material BEFORE the external call,
synchronously.**
- cdk mint: `PaymentAttempted` saga state persisted *before dispatch to
  the payment backend* — "a terminal negative status cannot prove that
  the payment was not sent" (`cdk-common/src/mint.rs`,
  MeltSagaState doc).
- minibits: in-flight request rows are "Written before the network call
  so the op can be safely retried against the mint's idempotent
  (NUT-19 cached) endpoint" (`services/db/inFlightRepo.ts`); the melt
  preview (blinded change) is "Written SYNCHRONOUSLY before the melt is
  submitted so a paid-but-unconfirmed melt can always be recovered" —
  and the comment records the lesson: their previous debounced
  whole-tree snapshot "risked losing the preview (and the change) on a
  crash right after submission."
- CocoCashuSwift: a protocol requirement, not a convention — "Implementations
  must persist the advance durably before returning from `reserve`"
  (`Repositories/RepositoryInterfaces.swift`, CounterRepository).

**Rule 2 — Deterministic secrets turn the journal tiny.** With NUT-13
derivation, the write-ahead for a swap's outputs is not the premint
blob — it is a counter range. minibits stores `{keysetId, start, count,
next}` on the reservation row, "written BEFORE the request is sent. If
the process dies after the mint executed the swap, those outputs exist
only at the mint; the range is what lets recovery restore them."
CocoCashuSwift's CounterRepository enforces the invariants: indices are
never reused (duplicate secrets = mint rejection or ambiguity), the
advance is atomic, and after a seed restore the counter moves
forward-only past every index ever used.

**Rule 3 — Reserve-then-commit with deterministic orphan rollback.**
cdk wallet: `ProofsPending → SwapRequested`, un-stuck at boot by
checkstate. minibits Phase 5: "A reservation snapshots the pre-operation
state of a set of proofs and locks them as PENDING in a single SQLite
transaction. The reservation row stays in the DB for the entire lifetime
of the operation so that an orphan (a row left behind by a process that
died mid-operation) can be detected on next startup and rolled back
deterministically."

**Rule 4 — The mint is the source of truth; recovery asks, never
re-fires.** cdk startup: classify (compensate vs check-external), poll
is finalization-only, bounded by timeout. minibits retries in-flight
requests against NUT-19 cached endpoints (same request bytes — the
cache is keyed on inputs, so a re-randomized retry is a NEW operation).
cashu-ts exposes checkProofsStates for wallet-side reconciliation.
Wire-measured boundary (our COMPAT-LEDGER): replay caching exists on
cdk/cashu-cf and NOT on nutshell mints — **retry-based recovery is
mint-family-dependent**; a wallet must know which family it talks to.

## Per-project notes

| Project | Storage | In-flight handling | Recovery |
|---|---|---|---|
| cdk (mint) | SQLite/Postgres, WAL | persisted Saga records | boot: start_up_check classifies; compensate-or-finalize; 10 s bound |
| cdk (wallet) | pluggable store | WalletSagaState per op | boot: rollback if no external call, else checkstate |
| minibits | SQLite (expo) + MMKV snapshot | reservations + inFlight rows + meltRecovery rows | orphan reservations rolled back deterministically; in-flight retried via NUT-19; counter-range re-derivation |
| CocoCashuSwift | protocol-based (SwiftData/in-mem) | CounterRepository write-ahead | seed restore fast-forwards counters; pending quotes fetched at boot (`fetchPending`) |
| cashu-ts | none (SDK: caller persists) | — | checkProofsStates as the reconciliation primitive |
| cashu-ui (wallet.cashu.space) | server-side (nutshell-based) | — | not a constrained-device pattern; reference deployment only |

## Design facts worth stealing verbatim

- minibits schema comment on ownership: "A CHILD of the transaction: the
  primary key IS the parent's id, so the parent owns the mint reference
  and this table stores none. One owner of the fact means nothing here
  can go stale when a mint moves." (Their mint-url race analysis: a url
  edit racing an open send "would commit the new proofs under the
  pre-edit url, stranding them at a url no mint owns — an invisible
  balance.")
- minibits on one-shot ops: "MELT quotes get no table: they are one-shot
  and terminal, so their durable state [lives elsewhere]" — journal only
  what can be ambiguous.
- CocoCashuSwift's never-reuse invariant stated as the failure it
  prevents, not the mechanism it implements — the right way to write a
  protocol contract.

## What this means for constrained wallets (nucula)

See nucula `docs/research/MCU-MONEY-SAFETY.md` (hypotheses H1–H6). The
survey collapses two of them: with NUT-13 derivation, the premint
journal (H1) and seed-derived reconstruction (H5) become ONE mechanism —
persist a ~24-byte counter range before the swap POST (write-ahead),
recover by re-derivation + mint checkstate/replay. Bench power-cut
experiments to quantify the current loss windows are running
(nucula `tools/powercut/`); results will land on the same research
branch.
