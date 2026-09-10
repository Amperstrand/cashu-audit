# d3 — n_sigs exceeding the key pool: both references keep the refund hatch, MUST says reject

**Status:** INTERNAL RESEARCH (overview build, 2026-09-09). Nothing filed.
**Upstream novelty:** NOVEL — same class as d2: the divergence was known
(cdk#2252 item 3); the converged-on-violation state is untracked. Filing
candidate (bundle with d2 — same spec clause, same fix).

## What we found (measured 2026-09-09)

Secret with key pool of 2 (data + 1 pubkeys tag), `n_sigs=3`, expired
locktime, 1-of-1 refund: the **refund-path spend succeeds at BOTH**
cdk-mintd/0.18.0 and Nutshell 0.20.3. NUT-11 (nuts#358): "If `n_sigs` …
exceeds the total number of keys in its pathway, the P2PK secret is
malformed and the Proof **MUST** be rejected as unspendable" — the proof
should never be spendable at all, by any pathway. Both references violate.

Nuance worth keeping: cdk#2252 framed cdk's refund-hatch as "leniency
preserves the refund escape hatch" — operationally kind to holders, since
blind signing means the mint cannot refuse to issue these. That argument is
our POSITION doc's duty-follows-issuance, again.

## How we tested

- Probe cell `d3_nsigs_exceeds_pubkeys_refund` (raw-tag secret builder;
  locktime = now − 10s; refund-key SIG_INPUTS witness).
- Same arms/lifecycle/evidence as d1; stable ×2.

## Community discussion (summary)

- Same #358 thread and same a1denvalu3 split-handling exchange as d2 —
  the community's mint-lenient direction directly covers this clause.
- cdk#1966 ("fix: num sig zero is invalid", 2026-05-14) shows cdk enforcing
  the *adjacent* rule (n_sigs=0) — the exceeds-pool half was left unenforced
  on the verification path by design.
- cdk#2252 item 3 recorded nutshell-branch=bricked-up-front; the merged #1008
  dropped that (our July DB even measured nutshell rejecting upfront —
  that row is now stale; the divergence DB 2026-09-09 section supersedes).

## Historic context

- 2026-04→06: #358 merges the MUST (paper only, vectorless).
- 2026-07-18: callebtc's "guard n_sigs" commit on #1008 — guards, not rejects.
- 2026-08-03: DotNut#42 enforces the letter.
- 2026-09-09: both-accept measured.

## Links (internal reference; no upstream engagement)

- cashubtc/nuts#358 — clause + split-handling exchange
- cashubtc/cdk#1966 — adjacent enforcement
- cashubtc/cdk#2252 (item 3) — prior state, reference-only
- Kukks/DotNut#42 — spec-literal enforcement
- Census: `research/CENSUS-nut10-11-14-correct-behaviour.md`

## Release-train update (2026-09-09, source-read)

Same picture as d2: nutshell-main carries the validator
(`_validate_condition` rejects `n_sigs` exceeding the key pool — read
directly on `spectate/main`), but **42 commits were unreleased** at audit
time. Tag `0.20.3` is the Jul-22 version-bump commit and the published
image is a faithful build of it; #1008 merged Aug 11, after the tag. The
next nutshell image flips this cell to REJECT for every operator at once —
which also **kills the refund-hatch reading this issue documents as the
"least-damage" behavior**. That makes the nuts amendment (split handling:
mint-lenient + wallet-strict + vectors) the only path that doesn't strand
blind-signed value on upgrade day; the alternatives are cdk matching
nutshell's rejection (two references strict, DotNet-aligned, holder-hostile)
or operators pinning 0.20.x indefinitely.

## Direction (our read)

Bundle with d2 into one nuts amendment (split handling + vectors). If
implementations must move instead, the refund hatch is the humane target to
*keep* — rejecting upfront strands blind-signed value; rejecting only the
primary pathway (current both-ref behavior) is the least-damage reading of
the MUST, and deserves explicit spec blessing rather than accident.
