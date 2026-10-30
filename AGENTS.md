# AGENTS.md — cashu-audit Operating Manual

This repo audits Cashu wallet×mint interoperability: surface spec
divergences, enforcement gaps, and fund-loss vectors; hold the evidence;
stage upstream contributions for owner approval. Nothing here files,
posts, or publishes upstream on its own.

## Where things live

- `research/` — published findings (committed). `private/` — staged
  drafts and strategy (gitignored; NEVER commit, NEVER post without
  explicit owner approval).
- **Security-sensitive findings (2026-10-27 rule, owner directive):**
  vulnerabilities in OTHER implementations (fund-safety, crash-on-input,
  auth bypass classes) live in `private/` from discovery until the
  upstream disclosure lands — evidence, repro scripts, captures, and
  registry-grade writeups ALL stay private until the vendor knows.
  Evidence stays private PERMANENTLY unless the owner explicitly
  decides otherwise (owner directive 2026-10-27: "no intention of going
  public — research stays with us, responsible disclosure to the vendor
  only"). Vendor disclosure is NOT publication. `research/` and `experiments/` remain fine for our
  interop/behavior findings (divergences, error identities, fee
  semantics) that don't arm an attacker against an unaware vendor.
  Rationale: this repo is PUBLIC; a "public archive + owner-gated
  filing" split once left a fund-safety wallet bug fully reproducible
  in the open for 4 days while the vendor was unaware (dleq-bypass,
  2026-10-23→27; moved to private/, registry row redacted). Note: git
  history retains pre-move content — moves are forward hygiene, not
  retraction; disclose promptly rather than relying on obscurity.
- `experiments/must-gap-vectors/` — the 17-vector enforcement probe,
  wallet-emission capture scripts, `verify.sh` (clean-VM one-command
  repro), nightly cron on ai-legion (03:17, drift-diffed).
- **CI lanes** (ops details in `conformance/README.md`):
  `nightly-corpus` — nightly 03:17 UTC, offline decode/portal corpus
  lanes, divergence-gated, docker-based nutshell reference
  (PyPI-immune); `conformance-v2` — Mondays 06:00 UTC, deterministic
  live-verdict lane on 4 local docker arms (nutshell 0.20.3/0.21.0, cdk
  0.18.1/0.18.2) + invoice-oracle, expected-fail seeds,
  v2_diff divergence gate. `experiments/miniflare-spend-matrix/` —
  the adversarial spend battery (canonical driver lives in cashu-cf
  `scripts/validation/spend-matrix.mjs`, a battery step there).
- `research/DIVERGENCE-REGISTRY.md` — the map of our findings ↔
  upstream venues ↔ what upstream already knows. **Read before any
  upstream-contribution work; update after any venue research.**
- **Prior-art sweeps cover OPEN PRs, not just issues** (2026-10-30
  rule): an unmerged PR can describe a defect publicly for months —
  that is venue intel (and severity calibration), never proof it was
  handled; the sweep that only reads issues will miss it. And the
  inverse holds: public prior art alone does not get a fix merged.

## Method (non-negotiable)

1. **Frozen predictions before every run.** A surprising FAIL is a
   probe bug until proven otherwise — read the driver's stderr.
2. **Error-identity assertions.** Any-4xx-is-pass suites hide exactly
   the bug class this repo exists to find.
3. **Wire evidence at the request layer**, not just the transport.
4. **Version matrices**, not latest-vs-latest.

## Upstream contribution protocol (hard rules)

1. **Research prior PRs and issues first** — in the target repo, the
   spec repo, and both implementation families — before drafting
   anything. The finding may already be catalogued upstream; a venue
   (open issue, tracking comment) may already exist. The registry
   records what that research found.
2. **Add or stay silent.** GitHub threads are read by humans. If the
   maintainers already understand the issue and our logs do not add a
   *new* fact — impact, regression window, blind spot, design trap,
   proposal — then our comment is noise. Do not post it.
3. **New facts only.** Never restate what the issue text already says.
4. **No self-narration** ("we did X", "we have measured") and **no
   offers** ("happy to share", "happy to PR"). State facts. Share only
   if asked.
5. **Draft → owner approval → post.** Always. No exceptions.
6. **Agents never open external pull requests.** Not even with owner
   approval in-session — an approval to "prepare" or "stage" a
   contribution is NOT approval to open the PR. Staging means: local
   branch, our fork, or `private/` draft. Clicking "open PR" (or
   `gh pr create`) against any repo we do not own is an owner-only
   action. Same for opening issues on external repos: stage the text,
   let the owner file it. (2026-09-27: MintRadar PR #98 was opened in
   violation of this — the rule exists so it is never repeated.)
7. Anything sourced from Cashu dev calls is under the Chatham House
   rule: use the information, never attribute the speaker.

## private/ is NOT access control (earned 2026-10-30)

This repo is PUBLIC. A directory named `private/` plus a `.gitignore` line only hides files that were never tracked — files committed before (or during) the "hygiene" move stay world-readable and code-search-indexed, and gitignore makes the untracked ones invisible in `git status`, so nobody notices either state. Disclosure-grade material (findings writeups, repros, captures, disclosure email texts, upstream drafts) lives in the PRIVATE mirror repo `Amperstrand/cashu-audit-private` from birth. CI (`.github/workflows/no-private-paths.yml`) fails any push that tracks `private/`.
