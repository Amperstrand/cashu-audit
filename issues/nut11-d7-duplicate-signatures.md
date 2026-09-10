# d7 — Duplicate signatures from one key: settled by convergence (both reject)

**Status:** INTERNAL RESEARCH (overview build, 2026-09-09; revised same day). Nothing filed.
**Upstream novelty:** PARTIAL — known as a divergence (cdk#2252 item 7:
cdk errors, nutshell ignored); we measured the image-era flip to reject
(#1008), and now the measured preview of the NEXT release flipping it
back to accept. Reference-only; nothing to file.

## Release-preview update (2026-09-09, MEASURED — status revised)

The "settled by convergence" call above is already obsolete. Run
`version-matrix-20260909-224356` (git arm `ab-matrix:nutshell-main` =
upstream main + 42 unreleased commits): **d7 flips back to ACCEPT** — the
#1008 rewrite's per-pubkey counting silently dropped the signature-
uniqueness check the released image has. Post-release: cdk REJECT vs
nutshell ACCEPT — the ORIGINAL cdk#2252 divergence re-opens. Both sides
defensible (the CAUTION's letter favors main's leniency); the finding is
that the loosening is undocumented and ships in a release nobody will
describe as loosening anything.

## What we found (measured 2026-09-09)

P2PK 1-of-1 SIG_INPUTS with witness `{"signatures":[sig, sig]}` (same valid
signature twice): REJECT at both arms — cdk with `DuplicateSignature`
(HTTP 400, code 20008 "P2PK spend conditions are not met"), Nutshell 0.20.3
with code 11000 "signatures must be unique.".

Spec status: NUT-11 carries only a non-normative CAUTION — "we expect a
minimum number of **unique public keys** with valid signatures instead of
… a minimum number of signatures" — whose letter arguably favors the old
nutshell behavior (one unique key, threshold met). Both implementations are
now stricter than the guidance. That is acceptable hygiene: a duplicated
signature indicates a broken client, and rejecting it cannot strand a
correct one.

## How we tested

- Probe cell `d7_duplicate_signature` (witness with the same sig twice).
- Same arms/lifecycle/evidence as d1; stable ×2.

## Community discussion (summary)

- #1008's merged code introduced the uniqueness check (error 11000) — part
  of the post-review strictness that shipped while cdk#2252's table still
  described "ignored".
- nutshell#1126 documents the surrounding error-code churn; duplicate-sig
  rejection itself was not contested there.
- cdk's DuplicateSignature long predates (cdk#2252 "points of agreement"
  adjacent).

## Historic context

- 2026-07-23: cdk#2252 item 7 records cdk=error / nutshell=ignore.
- 2026-08-11: #1008 merges uniqueness enforcement.
- 2026-09-09: both-reject measured; divergence closed.

## Links (internal reference; no upstream engagement)

- cashubtc/cdk#2252 (item 7) — prior state
- cashubtc/nutshell#1008, #1126 — the flip and its error-code context
- cashubtc/nuts 11.md — the unique-pubkeys CAUTION
- Census: `research/CENSUS-nut10-11-14-correct-behaviour.md`

## Direction (our read)

Closed in practice. If nuts ever formalizes the CAUTION into a rule,
"count unique pubkeys, reject duplicate signatures" is the converged
behavior to canonize — with a vector pinning it.
