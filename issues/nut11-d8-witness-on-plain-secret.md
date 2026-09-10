# d8 — Witness on a plain secret: settled by convergence (both reject)

**Status:** INTERNAL RESEARCH (overview build, 2026-09-09; revised same day). Nothing filed.
**Upstream novelty:** PARTIAL — known as a divergence (cdk#2252 item 8:
cdk rejects, nutshell accepted-and-ignored); we measured the image-era
flip to reject (#1008), and now the measured preview of the NEXT release
flipping it back to accept. Reference-only; nothing to file.

## Release-preview update (2026-09-09, MEASURED — status revised)

"Settled by convergence" is already obsolete. Run
`version-matrix-20260909-224356` (git arm `ab-matrix:nutshell-main` =
upstream main + 42 unreleased commits): **d8 flips back to ACCEPT** — the
#1008 rewrite silently dropped the witness-on-plain-secret rejection the
released image has. Post-release: cdk REJECT vs nutshell ACCEPT — the
ORIGINAL cdk#2252 divergence re-opens. Spec is silent both ways; the
finding is the undocumented loosening (a smuggling-surface check ships
out with nobody noting it), not either behavior itself.

## What we found (measured 2026-09-09)

A proof with a plain (non-NUT-10) hex secret and a well-formed but
irrelevant witness (`{"signatures":[<valid schnorr sig>]}`) attached:
REJECT at both arms — cdk `IncorrectWitnessKind` (HTTP 400, code 20008
"Witness is not a p2pk witness"), Nutshell 0.20.3 code 11000 "witness data
not allowed without a spending condition.".

Spec status: silent. Both readings were defensible; the ecosystem landed
on reject, which is the safer rule (a witness on a plain secret signals a
confused client or a smuggling attempt; nothing legitimate needs it). Our
July divergence-DB row ("all 3 impls now reject") was correct for cdk +
then-current wallets, and #1008 brought nutshell's mint in line.

## How we tested

- Probe cell `d8_witness_on_plain_secret` (plain secret via
  `generate_secret`, stray-key signature witness).
- Same arms/lifecycle/evidence as d1; stable ×2.

## Community discussion (summary)

- #1008 introduced nutshell's explicit check (error 11000).
- No thread debates the behavior itself (census checked); it appears only
  as a row in cdk#2252's comparison.
- Adjacent: nutshell#1126's absent-vs-malformed witness folding — different
  cell (missing witness on P2PK), same "witness shape diagnostics" family;
  tracked under our error-code-registry issue (#6).

## Historic context

- 2026-07-23: cdk#2252 item 8 records cdk=reject / nutshell=ignore.
- 2026-08-11: #1008 merges the rejection.
- 2026-09-09: both-reject measured with both error texts captured.

## Links (internal reference; no upstream engagement)

- cashubtc/cdk#2252 (item 8) — prior state
- cashubtc/nutshell#1008, #1126 — the flip + diagnostics context
- Census: `research/CENSUS-nut10-11-14-correct-behaviour.md`

## Direction (our read)

Closed. One sentence in NUT-10 ("a witness MUST NOT be attached to a
secret that is not a well-known Secret; mints MUST reject such inputs")
would canonize the converged behavior — fold into any future spending-
conditions nuts PR, not standalone.
