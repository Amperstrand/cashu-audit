# FINDINGS — upstream release sweep 2026-10-26 (cdk 0.17.7 + cashu-ts 4.12.0)

Trigger: owner asked to check recent releases beyond our pinned arms.
The daily watch missed both: its `releases/latest` check cannot see
backport lines (cdk 0.17.x) and cashu-ts was not a watch target.
Both fixed today (watch now lists 3 most-recent releases incl.
prereleases; cashu-ts added to WATCH_TARGETS).

## cdk v0.17.7 (2026-09-16, backport on the 0.17.x line)

Digest: `research/releases/cdk-0.17.7.md` (8 commits, no NUT tags).
Content: mint-recovery saga timing — payment-status checks capped at
10s during recovery, timed-out sagas DEFERRED with reserved proofs
kept; cdk-lnd expired-invoice rejection; test fixes.

Wire battery (PREDICTIONS-cdk0177.md frozen first; arm cdk-mintd/0.17.7):

| Check | cdk 0.17.7 | vs 0.18.2 |
|---|---|---|
| swap replay (byte-identical) | 200 identical | same — replay caching is architecture |
| keyless swap 64→[63,1] | 400/12001 Unknown Keyset | same identity |
| locked quote, no sig | 400/20008 | same |
| batch 51 unknown ids + outputs | 400/50000 Unknown quote | same (existence-first ≤ cap) |
| batch 1001 unknown ids | **400/50000 Unknown quote** | **DIFFERS: 0.18.2 → 400/11017 max-batch** |

Drift datum: 0.18.x checks batch LENGTH before existence (11017 fires
at 1001 regardless of id validity); 0.17.7 checks existence first —
the length cap (or its ordering) arrived in the 0.18 line. No
fund-safety impact (both reject); recorded as NUT-29 version drift.

## cashu-ts v4.12.0 (2026-10-20)

Digest: `research/releases/cashu-ts-4.12.0.md` (6 commits; NUT-10/11/19).
Release-note deltas touching our audit surface: #1308 V4 text-field
decode validation; #1324 locktime-0 read as expired + expire-after-
locktime; verifyMintSignatures added (v5 prep), hasValidDleq deprecated.

Decode-matrix differential (19-vector v4-pool, both versions side by
side; knownIds = [kg181-full66, v3 id]; runner scratch/ts411+ts412):

- **19/19 verdict parity.** Every negative (c_text, i_text, dleq_text,
  prefix_C, truncated) rejects identically; every positive decodes.
  The one nominal flip (p2pk_locked_live) is the documented cold-mint
  harness identity — 4.11.0's recorded verdict itself notes decode
  requires that mint's keyset in the list.
- **No API change on our surface**: getDecodedToken's mandatory
  keysetIds argument throws the identical message on 4.11.0 — the
  two-arg requirement predates 4.12.0.
- Note: PR #1308's text-field validation was already present in
  4.11.0 (our 4.11.0 verdicts rejected the text vectors) — the 4.12.0
  change is presumably an extension/backport refinement our corpus
  cannot distinguish. Corpus limitation, not a finding.

**Untested delta: #1324 (locktime-0 semantics).** Spend-path P2PK
condition evaluation — our decode corpus cannot see it and the pool
has NO locktime-0 vector. Action: add locktime-0 (and locktime-past)
P2PK vectors to the pool; the change also interacts with our
locktime==now boundary gap (registry: no boundary-exact data held).

## Project updates from this sweep

- `tools/upstream_watch.py`: WATCH_TARGETS += cashu-ts; release check
  now enumerates 3 most-recent releases (catches backport lines).
- `tools/release_digest.py`: PROJECTS += cashu-ts (npm name
  @cashu/cashu-ts — NOT @cashu-ts/core, which is the v5 scope).
- Digests: research/releases/cdk-0.17.7.md, cashu-ts-4.12.0.md.
- Pinned-arm set unchanged (0.18.1/0.18.2, 0.20.3/0.21.0 remain the
  matrix; 0.17.7 measured ad hoc — add as standing arm only if the
  recovery-saga behavior becomes audit-relevant).
