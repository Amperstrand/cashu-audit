# AGENTS.md — cashu-audit Operating Manual

This repo audits Cashu wallet×mint interoperability: surface spec
divergences, enforcement gaps, and fund-loss vectors; hold the evidence;
stage upstream contributions for owner approval. Nothing here files,
posts, or publishes upstream on its own.

## Where things live

- `research/` — published findings (committed). `private/` — staged
  drafts and strategy (gitignored; NEVER commit, NEVER post without
  explicit owner approval).
- `experiments/must-gap-vectors/` — the 17-vector enforcement probe,
  wallet-emission capture scripts, `verify.sh` (clean-VM one-command
  repro), nightly cron on ai-legion (03:17, drift-diffed).
- `research/DIVERGENCE-REGISTRY.md` — the map of our findings ↔
  upstream venues ↔ what upstream already knows. **Read before any
  upstream-contribution work; update after any venue research.**

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
6. Anything sourced from Cashu dev calls is under the Chatham House
   rule: use the information, never attribute the speaker.
