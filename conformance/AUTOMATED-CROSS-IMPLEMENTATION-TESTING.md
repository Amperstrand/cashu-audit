# Automated cross-implementation testing — architecture & runbook

*2026-09-09. How we run regular, automated NUT-10/11/14 differential probes
across implementations, releases, branches, and commits — and how the run
registry turns silent behavior flips into first-class findings.*

## The problem this solves

We have twice caught silent behavioral softforks by hand:

1. nutshell flipped d1 (unknown kind), d7 (duplicate sigs), d8 (witness on
   plain) between our July measurements and 0.20.3 — inside routine
   releases, with no issue, changelog line, or test failure anywhere.
2. cdk flipped d6 (HTLC refund witness shape) between 0.16.0 (SatsAndSports
   checker: 58/58 incl. the refund succeeding) and 0.18.0 — and every
   existing suite "passed" both sides because expected-reject scenarios
   count any rejection as success.

Point-in-time audits rot in ~6 weeks. The fix is standing infrastructure:
a matrix runner that brings up any set of mint versions, runs the frozen-
prediction probe, and diffs results across arms (same run) and across time
(registry).

## Components

| Piece | Role |
|---|---|
| `ab_probe_p2pk_htlc.py` | The probe: 12 cells (2 controls + 8 cdk#2252 divergences + d6b/d6c witness frontier), frozen predictions per family, N-arm capable (`--arm NAME=URL`, family-resolved predictions: `cdk*`/`nutshell*` prefixes get the frozen tables; anything else runs verdict-only) |
| `version_matrix.py` | The runner: arm bring-up (docker tags, git refs, live URLs), dynamic ports, probe orchestration, run registry, intra-run version diff, inter-run drift diff |
| `runs/` | The registry: one `version-matrix-<ts>.json` + `.md` per run; JSON keeps full per-cell verdicts + error details + arm identities |
| `.github/workflows/version-matrix.yml` | Scheduled CI (optional; needs push to activate) |

## Arm types

```bash
# Docker Hub version tag (the common case — full version history available:
# nutshell 0.14.1→, mintd 0.17.0→)
python3 version_matrix.py --docker-arm cdk-0.17.6=cdk:cashubtc/mintd:0.17.6

# Any git ref of a local clone — branch, tag, or commit SHA. Builds a docker
# image from the repo, then runs it as an arm (experimental; first build of
# cdk source is slow under emulation — prefer releases for cdk).
python3 version_matrix.py --git-arm nutshell@main=nutshell:../nutshell:origin/main

# A mint that is already running (no bring-up, no teardown)
python3 version_matrix.py --url-arm testnut=https://testnut.cashu.exchange
```

Arm names carry the comparison semantics: the dash-less prefix is the
FAMILY (`cdk`, `nutshell`, …). Same-family arms are diffed pairwise in the
intra-run report; identical names across runs are diffed in the inter-run
report. Version-pinned names (`cdk-0.17.6`) give stable inter-run identity;
floating names (`cdk-latest`) drift-track whatever the tag currently is —
both are useful, for different questions.

## What the runner encodes (so nobody re-learns it)

- **nutshell images**: no ENTRYPOINT — command must be `poetry run mint`;
  env is `MINT_BACKEND_BOLT11_SAT` / `MINT_LISTEN_HOST` / `MINT_LISTEN_PORT`
  (the older `MINT_LIGHTNING_BACKEND` / `MINT_HOST` / `MINT_PORT` names are
  silently ignored — the mint just never listens); `MINT_RATE_LIMIT=FALSE`
  for probe bursts; fresh `MINT_PRIVATE_KEY` per arm (same key = same
  keyset = camouflage hazard); ~3 min startup patience under emulation.
- **cdk ≥0.18**: requires `config init --new-mint` from a TOML into a
  work-dir database before the daemon starts; work dir must live under
  `$HOME` (colima only mounts home); BIP39 mnemonic via env reference.
- **cdk ≤0.17.x**: legacy env config — `CDK_MINTD_LN_BACKEND=FakeWallet`
  (NOT `CDK_MINTD_BACKEND`), `CDK_MINTD_LISTEN_HOST/PORT` (NOT HOST/PORT);
  surface enumerated from the binary (`strings` + grep CDK_MINTD). The
  runner auto-detects via `cdk-mintd --help`.
- **FakeWallet + bark**: invoices never need payment; the runner puts a
  fail-fast `ssh` shim on the probe's PATH so the house client's payment
  attempt costs nothing.
- All arms listen on 3338 in-container; the runner maps distinct host
  ports (picked free at bring-up).

## Reading a run

1. **Per-arm frozen-prediction check** — MISMATCH lines are findings (the
   d6b/d6c refutations are permanent by design; predictions stay frozen).
2. **Intra-run family diffs** — `FLIP cell: armA=X armB=Y` lines. This is
   release-vs-release / branch-vs-branch / commit-vs-commit comparison.
3. **Inter-run drift** — same arm name, different runs. This catches the
   silent-softfork class (works for floating tags like `:latest`).
4. **Registry** — `runs/*.md` renders the cells × arms matrix; `runs/*.json`
   keeps error codes/details for the error-code census.

### Measured with this infrastructure (2026-09-09, first runs)

- cdk 0.17.0 ≡ 0.17.6 ≡ 0.18.0 on all 12 cells → the **d6 witness-shape
  frontier (reject absent/null preimage, accept dummy) landed by 0.17.0**;
  with the checker's 0.16.0 refund-success, the regression window is
  **0.16.0 → 0.17.0** (no 0.16.x images on Docker Hub — source build via
  `--git-arm` is the way to tighten further).
- nutshell 0.20.2 ≡ 0.20.3 on all 12 cells → the shipped #1008 profile
  (strict d1/d7/d8, lenient d2–d5, d6-accept) was already in 0.20.2.
- Inter-run diff validated: run 2 shared the cdk-0.17.6 arm with run 1 and
  correctly reported "no drift on shared arms".

### Docker tags measure releases, git arms measure development (2026-09-09, corrected)

An earlier revision of this section claimed the 0.20.3 image diverged from
its git tag ("version identity lies"). That was our own verification error,
worth keeping as a lesson:

1. **The image is faithful.** `cashubtc/nutshell:0.20.3` was built from git
   tag `0.20.3` (image `/app/.git/FETCH_HEAD` records the exact tag
   checkout; upstream `ls-remote` agrees). The tag points at the
   `chore(release): bump version to 0.20.3` commit of **2026-07-22**
   (`1853902`), and Docker Hub shows the push the same morning.
2. **The #1008 overhaul merged 2026-08-11 — three weeks AFTER the tag.**
   `git merge-base --is-ancestor 8e19619 0.20.3` → NO. As of 2026-09-09,
   **42 commits are unreleased**: main carries the strict validators
   (duplicate-tag rejection, n_sigs-vs-pool, lowercase hash) that the
   published image lacks — not because the image is wrong, but because the
   release train is ~7 weeks behind main.
3. **Our verification bug (two parts, both instructive):** nutshell tags
   are UNPREFIXED (`0.20.3`, not `v0.20.3`) — `git log v0.20.3..origin/main`
   errored and `| wc -l` swallowed it into "0 commits", which we read as
   "tag == main". House rule reaffirmed: piped git commands must fail loud
   (`set -o pipefail` or explicit rev-parse preflight).

**Operational consequence (the real finding):** the d2/d3/d5 leniency we
measured on image 0.20.3 is a *release snapshot*; the first nutshell image
built after these 42 commits will flip d2/d3/d5 to REJECT for every
operator simultaneously — a scheduled softfork-by-release. The weekly
matrix's floating `:latest` arm exists to catch exactly this; the
`ab-matrix:nutshell-main` git arm previews it before it ships.

**Preview MEASURED 2026-09-09** (run `version-matrix-20260909-224356`:
`ab-matrix:nutshell-main` — built from `spectate/main` = upstream main +
comment-only quote lines — vs the published 0.20.3 image). **Seven flips**:

| cell | 0.20.3 image | nutshell main (next release) |
|---|---|---|
| d2 duplicate tags | ACCEPT | REJECT |
| d3 n_sigs > pool | ACCEPT | REJECT |
| d4 empty `["pubkeys"]` | ACCEPT | REJECT |
| d5 uppercase hash | ACCEPT | REJECT |
| d6c dummy preimage (refund) | REJECT | **ACCEPT** |
| d7 duplicate signatures | REJECT | **ACCEPT** |
| d8 witness on plain | REJECT | **ACCEPT** |

Findings beyond the prediction: (1) nutshell-main matches the ORIGINAL
cdk#2252 table on all 8 divergences — the table described the branch that
merged, not the image that shipped; it was never stale, just early.
(2) The #1008 rewrite silently **dropped two hardening checks** the
released image has (d7 uniqueness, d8 witness-on-plain) — spec-defensible
readings both (d7 matches the CAUTION's count-unique-pubkeys letter;
d8 is spec-silent), but it means the release *loosens* as well as
tightens, and nobody has said so. (3) **d6c → ACCEPT heals the HTLC
Sender Pathway incompatibility**: post-release, `{"preimage": <any
64-hex>, "signatures": [...]}` spends refunds on BOTH cdk and
nutshell-next — the empty-intersection finding is specific to the current
image pair. (4) Identity caveat: main's /v1/info still says "0.20.3"
(pyproject unbumped), so the identity guard cannot distinguish release
from dev — the registry's arm/image names carry the provenance.

## Scheduling

**CI (recommended):** `.github/workflows/version-matrix.yml` in this repo —
weekly cron + `workflow_dispatch`, runs the default matrix on ubuntu
runners (docker preinstalled, no emulation slowdown), commits new registry
entries back to `main`. Registry diffs become visible in the commit and in
the job summary. Needs one push to activate; arm the matrix by editing the
`ARMS` env list in the workflow.

**Local:** `python3 version_matrix.py` on demand (full matrix ≈ 15 min
under colima emulation; ≈ 4 min on native linux). A launchd plist or cron
entry calling it weekly is sufficient — sample in the workflow file.

**Cadence recommendation:** weekly on latest tags + one floating `:latest`
arm per family (drift detection); on every upstream release announcement,
add the new pin + previous pin as a pair (window pinning); before any
upstream engagement from `issues/`, re-run to confirm the finding is
current.

## Relation to the rest of the audit stack

- **greatspectations branches** (planned): catch spec→code quote drift and
  unimplemented-MUST coverage gaps statically. The matrix runner catches
  behavior drift dynamically. d7/d8 (spec-silent) are invisible to
  spectate coverage — only vectors + this runner see them. Complementary
  by design.
- **Scenario suite** (`run_filtered.py`/`run_matrix.py`): breadth (~100
  scenarios incl. melt/checkstate); the probe is the frozen-prediction
  depth instrument. Next improvement, adopted from the checker's Nutmix
  lesson: assert error codes/details on expected-rejects, not just status
  (cdk 0.16→18 "passed" `htlc_signature_only_fails` for the wrong reason).
- **Upstream engagement**: registry entries + markdown matrices are the
  evidence bundle format for issue drafts in `issues/`.

## Limitations / next

- git-ref arms build untested for cdk (cargo build cost); nutshell git
  arms should work via its Dockerfile.
- Single-unit (sat) FakeWallet only; no multi-keyset or fees-on cases.
- The probe's lifecycle is swap-based; melt-path variants (the checker's
  melt rows) are not yet cells.
- No alerting yet — flips print and land in the registry; wiring to
  Nostr/TestEvidence events is the natural next step (framework §4).
