# Master sequence — NUT-00 secret-encoding work package

*One page, in execution order, with every artifact named and every decision
point owned by a human. Status: everything below is PREPARED; nothing public
has been filed or posted except code branches on Amperstrand forks.*

---

## Phase 0 — what happened (context, not published)

During recovery-tooling tests we hit the NUT-00 secret-encoding trap: blinding
the raw entropy behind a hex secret (instead of the UTF-8 bytes of the string)
produces valid-looking signatures, DLEQ, unblinding and tokens that are
**permanently unspendable** at strict mints (`10001 Token not verified`),
because blind signing cannot detect the divergence and verification only runs
at spend time. Reproduced end-to-end on cdk-mintd 0.17.6 and 0.18.0; recovery
proven impossible (except the astronomically-unlikely valid-UTF-8 entropy
case); the bug class documented as recurring (two wallet ports, a Java
NUT-11 charset bug, ours). Auditing our own stack found cashu-cf lenient at
exactly this boundary.

## Phase 1 — cashu-cf: bug, fix, and documentation (branch `nut00-strict-v2`; main mirrors upstream — house convention: experiments never merge to main)

| Item | Where |
|---|---|
| Finding + fix + tests + rollout plan | `Amperstrand/cashu-cf@nut00-strict-v2` (squashed ISSUE-119: flag + keyset-scoped leniency) |
| Behavior | default lenient (all existing tokens spend); `LEGACY_ENCODING_KEYSETS=<ids>` scopes leniency to listed keysets; `STRICT_NUT00_ENCODING=true` kill switch |
| Tests | 18/18 crypto suite (strict rejects trap, lenient accepts, keyset allowlist, forged-C) |
| Measured matrix | testnut full (lenient confirmed, forged rejected); signut forged-C only (real backend — full matrix needs one funded invoice); cdk local strict |

**Sequence for cashu-cf (branch deploys only — main stays upstream-clean):**
1. Review + deploy from `nut00-strict-v2`.
2. Deploy: no env set → zero behavior change.
3. Watch `verifyProofSignatureWithPrivateKey.hexDecodeMatch` logs per mint.
4. Optional funded run on signut to complete its matrix row.
5. At next keyset rotation: `LEGACY_ENCODING_KEYSETS=<old keyset ids>`.
6. Old keysets drain → leniency retires itself. Kill switch stays available.
7. Separately (own issue, needs storage-migration plan): the `secretToBytes`
   Y-tracking divergence flagged in ISSUE-119.

## Phase 2 — publish reasoning + repro + logs to Nostr (PREPARED, gated)

Content: `NOSTR-DRAFT.md` (kind 30023 long-form). Includes:
- the trap explained for implementers, with the canonical vectors
- repro instructions anyone can run (`docker run cashubtc/mintd:0.17.6` +
  `node demo-bug.mjs`, or `run_matrix.py` against any mint)
- the measured matrix incl. testnut/signut rows and select log lines
- links to all branches (cashu-cf ISSUE-119, cashu-ts, nuts, nucula, cashu-audit)
- explicit framing: found in our own mint first, fixes shipped on our forks

Publish under the Amperstrand identity; pin the note; reference the `naddr`
from future issues. (Nostr here = the signed, timestamped index layer — the
evidence lives in the repos.)

## Phase 3 — upstream engagement (NOT STARTED, one artifact per repo)

| Repo | Artifact | Content |
|---|---|---|
| cashubtc/cashu-ts | issue | footgun API + tested branch (`secret-encoding-guard`): string-first API, guard, vectors |
| cashubtc/nuts | issue or PR if invited | NUT-00 encoding MUST (wallet-side) + vectors incl. negative (branch `nut00-secret-encoding-vectors`) |
| cashubtc/cdk | issue | (a) log-only dual-derivation sensor on 10001s; (b) per-keyset leniency concept + operator runbook for one-time trap-token recovery |
| cashubtc/cashu.me | issue | error-UX: human-readable mint-error mapping (draft in `cashu-me-issue-draft.md`) |
| zeugmaster/nucula | issue | test-suite blind spot + vector offer (branch exists on our fork) |

Each issue: ~10 lines + links to branch + audit run + Nostr note. No PRs
unless invited; never parallel-drive-by.

## Arguments for and against (the decision ledger)

**Mint leniency (accept both derivations)**
- FOR: existing trap-encoded tokens keep spending; zero user impact; not a
  spec violation (NUT-00 has no MUST on verification derivation — checked);
  forging is still impossible (attacker can't compute k·Y).
- AGAINST: validity becomes mint-dependent (money on testnut, trash on cdk);
  masks buggy wallets until the worst moment (funds already committed at a
  strict mint); dual paths breed consistency drift (our secretToBytes already
  drifted); permanent leniency = the bug is never observable anywhere.

**Resolution chosen: keyset-scoped leniency** — compassion bounded by the
protocol's own versioning rail. Finite legacy debt stays spendable; new
keysets strict; leniency self-retires as old keysets drain. Strict-mint
compassion (cdk) goes through one-time operator recovery instead, so the
reference implementations stay clean walls.

**Should cdk/nutshell go lenient?** No: their backlogs are finite; a one-time
recovery runbook + the log sensor covers them without infinite future
masking. Middle path proposed to them: per-keyset allowlist if they want it.

**Compute cost of any of this:** negligible — fallback is one hash_to_curve +
one scalar mult on utf8-miss (~tens of µs); the sensor is log-only.

**Why issue-first everywhere:** maintainers prefer issues; a branch link
gives PR-value without PR-review burden; the audit bundle gives opt-in depth;
our own mint fix ships first, which makes the upstream story "we did the work
on ourselves, here's what we learned" instead of "please fix our bug."

## Artifact index

- cashu-cf: branch `nut00-strict-encoding-option` (ISSUE-119 + code + tests)
- cashu-ts: branch `secret-encoding-guard` · nuts: branch `nut00-secret-encoding-vectors`
- nucula: branch `crypto-test-string-secret-vectors` · cashu-audit: branch `nut00-secret-encoding-audit`
- Local evidence: `receipt/recovery/` (reports, journals, demos, vectors), `receipt/spec-audit-run/` (run bundle, drafts)
- Drafts ready: NOSTR-DRAFT.md, cashu-me-issue-draft.md, cdk issue (to write at filing time)
- Oracle mints still up: `docker rm -f cdk-mint-0176 cdk-mint-0180`
