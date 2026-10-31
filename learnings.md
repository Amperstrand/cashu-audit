# Learnings & Patterns from the cashu-cf Audit Pilot

Lessons from adopting greatspectations + 3-layer audit on cashu-cf (July 2026). Captured so other implementations can adopt faster.

## Layer 1: greatspectations adoption

### What worked
- **Tool is production-ready**: 121 quotes across 18 NUTs, all passing `spectate check`. Zero false positives after initial learning curve.
- **Catches real bugs fast**: ISSUE-023 (`===` vs `<=`) surfaced within 10 minutes of the first quote. The 48KB human-written NUT-04 review had missed it.
- **Co-exists with legacy comments**: Existing `// NUT-XX:` paraphrases are silently ignored (lack `#id`). New `// NUT #XX:` verbatim style is additive.
- **CI integration is trivial**: 5-line GitHub Actions workflow, pinned to greatspectations v0.1.1.
- **Coverage mode is actionable**: `spectate coverage --all-sections` shows which spec text isn't covered by any quote — useful for finding gaps.

### Friction points
1. **Markdown bold must be preserved verbatim**: `**MUST**` not `MUST`. Developers reading rendered docs will forget asterisks. **Mitigation**: documented in `spec-quotes.md` contributor guide.
2. **Continuation-line parsing**: any `//` comment after a `// NUT #NN:` quote is parsed as a continuation (appended to quote text). **Rule**: place NUT quotes LAST before code, with no other `//` comments between.
3. **Section-header comments trigger parse errors**: `// NUT-04 errors (spec)` (no colon after NUT-04) fails parsing. **Rule**: reword to `// Errors (NUT-04, spec)` — move NUT reference out of prefix position.
4. **Code blocks in spec can't be quoted**: whitespace collapse destroys indentation inside ```` ``` ```` blocks. **Rule**: quote prose only, never code examples.

### Patterns for new implementations

**Adoption checklist:**
1. Clone cashubtc/nuts to `../nuts` (or `nuts/` subdir)
2. Install greatspectations: `pip install git+https://github.com/rustyrussell/greatspectations.git`
3. Copy `templates/specquotes.toml` to your repo root
4. Add `spec:check` and `spec:coverage` npm scripts (or equivalent)
5. Copy `.github/workflows/spec-quote-drift.yml` for CI
6. Start with mandatory NUTs (00-06): ~5-10 quotes each, ~1h total
7. Expand to optional NUTs you implement

**Per-NUT workflow:**
1. Read `nuts/NN.md` spec
2. Identify MUST/MUST NOT statements (grep for `**MUST**`)
3. For each: find the implementing code, add `// NUT #NN: <verbatim quote>` comment
4. Run `spec:check` — fix any markdown-bold or continuation issues
5. Run `spec:coverage --all-sections` — triage remaining gaps
6. Document findings (drift? deviation? missing implementation?)

## Layer 2: Reference implementation notes

### Pattern: inline `// REF-CDK:` / `// REF-NUTSHELL:` comments

```
// REF-CDK: <behavior description>
// REF-NUTSHELL: <behavior description>
// NUT #NN: <verbatim spec quote>
<code that implements this behavior>
```

**Order matters**: REF comments BEFORE NUT quote (to avoid continuation parsing).

**When to add REF notes:**
- When a known divergence exists (check `divergences/NUT-XX.md`)
- When the code handles an edge case differently from the spec's primary path
- When the code has a compatibility hack (e.g., cashu-cf's 10 SIG_ALL message variants)

## Layer 3: AI audit prompts

### What makes a good audit prompt

1. **Structured checklist**: per-requirement items with binary PASS/FAIL/WARN verdicts
2. **Evidence requirement**: every verdict must cite `file:line`
3. **Cross-impl awareness**: include the divergence table so the auditor knows what to look for
4. **Model-agnostic**: no model-specific instructions; just the spec, the code, and the checklist
5. **Reproducible sign-off**: prompt version + hash + target commit + spec commit recorded in output

### Prompt structure that worked

```
## System Prompt (role definition)
## Context Injection (spec text, target code, divergence table)
## Audit Checklist (per-requirement items)
## Output Format (structured markdown with metadata header)
## Notes for Iteration (how to adapt for other impls/models)
```

### Findings from GLM-5.2 audit of cashu-cf

- **Speed**: ~3 minutes to audit 880 LOC of spending conditions against 15 MUST requirements + 8 divergence checks
- **Accuracy**: 23/23 verdicts correct (verified by human spot-check). No false positives or negatives.
- **Depth**: Found 2 non-blocking warnings (partial duplicate tag enforcement, SIG_ALL compat hack) that a mechanical tool couldn't surface
- **Limitation**: can't run the code — verdicts are based on reading, not execution. Runtime testing is complementary.

## General patterns

### The "drift exposure" pattern
The most valuable use of greatspectations is NOT finding existing bugs — it's PREVENTING future drift. The CI gate ensures that any future code change that contradicts a `// NUT #NN:` quote will fail the build.

### The "AI as auditor" pattern
AI audits are point-in-time snapshots. They're valid as of the audited commit. Any code change after the audit invalidates the signoff for changed files. Re-run after significant changes.

### The "cross-impl divergence database" pattern
The divergence database is the highest-value artifact for the Cashu community. It enables:
- Wallet developers to test against multiple mint behaviors
- Mint operators to understand compatibility implications
- Spec authors to clarify ambiguous requirements
- New implementations to make informed behavioral choices

## 2026-09-08 — NUT-00 secret-encoding boundary

- NUT-00's secret is a string; verification couples it to a curve point only at
  spend time. Wallets blinding raw entropy instead of utf8(string) produce
  valid-looking, permanently-unspendable tokens (recurring class: 2 wallet
  ports, Java NUT-11 charset bug, our tooling test).
- cashu-cf accepts BOTH derivations (dual-verification leniency) — masks buggy
  wallets until tokens hit a strict mint. Filed as divergence. cdk is strict.
- Canonical vectors incl. a negative trap vector now live in
  `conformance/reference-vectors/nut00-secret-encoding.json`; the scenario
  module `nut00_secret_encoding.py` (control / trap / forged-C) is the cheap
  ongoing probe — run it in every matrix pass.
- Lesson for the framework: audit both sides of every encoding boundary — the
  wallet trap AND mint leniency are the same divergence seen from two ends.

## 2026-10-22 — miniflare as a free real-mint probe target + v4 transport traps

- cashu-cf's miniflare lane (miniflare@5-alpha, wrangler-shaped
  `workers[].config` constructor) gives audits a FREE in-process mint:
  real bundle, real Durable Objects, real crypto — zero live exposure,
  zero deploys. `experiments/miniflare-spend-matrix/` is the template:
  frozen predictions → characterization → error-identity locks →
  repro scripts preserved. It found cashu-cf ISSUE-126 (duplicate-input
  swap amplification: 8→16 liquid) in its first adversarial run —
  the local matrix caught what weeks of clean-traffic greens could not.
- cashu-ts v4 transport traps (bite every probe script):
  1. `new Wallet(url, { customRequest })` SILENTLY DROPS the transport —
     v4 forwards only `authProvider`/`logger` to its internal Mint. Wire
     as `new Wallet(new Mint(url, { customRequest }), { unit })`.
  2. v4 request bodies carry BigInt/Amount value objects — serialize with
     a bigint→Number replacer at the boundary; and v4 MUTATES parsed
     response objects in place (Amount instances appear inside objects the
     caller captured by reference).
- Error-identity lesson reinforced: the first S8 check "passed" a 200
  through a family regex. Always assert the exact (status, error, code)
  triple; family regexes are how enforcement gaps read as green.

## Cross-implementation research arc lessons (2026-10-21 → 10-30, agenda #43)

From the keyset-ID/NUT-02/V4-pool/dleq research arc (cdk 0.17.6–0.18.3,
nutshell 0.20.3/0.21.0, cashu-ts 4.11.0/rc.9, cashu-cf). Operational
lessons; finding details live in the findings docs + registry.

### Method rules that earned their keep
- **Frozen predictions forced the best findings**: P1 predicted wrong
  ("mints flip active on expiry" — they never do) and the mandatory
  triage turned a wrong prediction into the enforcement-divergence
  finding. Predict, run, triage the surprise — never skip to the result.
- **Error-identity assertions** caught three separate one-class-per-bug
  splits: same unresolvable short-id → three wallets, three identities
  (deadlock/KeyError/CTSError); `cashuC` prefix → three identities;
  cdk's dedicated `MultiMintTokenNotSupported` shadowed by a generic
  earlier error. Any-4xx/any-reject suites would have collapsed these.
- **Surprising FAIL = probe bug until proven otherwise** — twice: the
  "Unsupported token" surprise needed a single-entry control token to
  isolate parse-vs-receive; a cashu-ts harness rejection was a
  keyset-list gap, not a divergence. Both triages prevented false
  findings from entering the registry.
- **Version-generality checks before filing**: cheap source diffs
  proved pe-serde identical across cdk 0.18.1–0.18.3 (struct
  byte-identical) and both nutshell defects present in 0.20.3 AND
  0.21.0 — filing texts would otherwise have shipped wrong version
  framing. Diff the struct/file, don't trust the release notes.
- **New-release checkpoint**: when a new release lands (upstream-watch
  CHANGE line), first-hand re-verify each committed finding against
  the tag — the digest said "NUTs: none" for 0.18.3 and was right, but
  the registry-grade claim needed the four regions grepped on the tag.

### Environment gotchas (ai-legion class)
- **earlyoom kills release-profile cargo builds** (it prefers killing
  rustc); `nice -n 10 cargo build -j 2` debug-profile builds cdk-cli
  in <2 min — use debug for probes.
- **Docker arms die to the OOM killer under load** (exit 137) — arms
  are restart-safe: keysets derive deterministically from the
  mnemonic, so `docker start` resumes identical state.
- **/tmp is wiped between windows** — durable copies immediately;
  /tmp holds machinery only, never the record.
- **Wallet env vars have no CASHU_ prefix** (MINT_HOST not
  CASHU_MINT_HOST) — a wrong-prefix wallet silently hits the DEFAULT
  public mint (8333.space). Verify the env mapping with a local
  (echo/info) command before the first network call; keep first calls
  local-only.
- **nutshell management RPC needs MINT_RPC_SERVER_MUTUAL_TLS=false**
  (mTLS defaults ON and blocks insecure boot with a confusing
  missing-cert error); in-container `mint-cli -h 127.0.0.1 -p 8086 -i`.
- **cdk-mintd multi-unit arms**: `[[payment_backend]]` is a LIST with
  one entry per unit — `[fake_wallet] supported_units` alone does not
  create the second unit's keyset.

### Workflow lessons
- **The private mirror must be the birthplace** (2026-10-27 policy):
  drafting in a gitignored dir of a public repo is one accidental
  `git add -f` away from disclosure; the CI guard catches it but the
  mirror is the real control.
- **Decision briefs beat final reports for owner throughput**: the
  D1–D7 one-page briefs (finding, evidence pointer, decision ask)
  moved faster than any long-form doc; the long-form log stayed as
  backup.
- **Check the other lanes' commits before writing anything** — two of
  this arc's conclusions were already being consumed/extended by
  parallel lanes; reading HEAD first avoided duplicated work twice.
