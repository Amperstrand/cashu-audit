# Retrospective — NUT-00 secret-encoding campaign (2026-09-08)

Honest inventory of what went wrong, what worked, and what we internalize.
Written by the agent that made most of the mistakes.

## 1. My failure inventory (the agent's)

| # | Failure | Cost | Root cause | Rule internalized |
|---|---|---|---|---|
| 1 | Blinded raw entropy instead of utf8(hexString) in the recovery script | the original incident | pattern-matched from key-gen corpus; didn't read the one-line JSDoc | read the contract line on every crypto boundary fn; derive B_ from the final string in the same code line that creates it |
| 2 | Verification theater: DLEQ/roundtrip/checkstate all "green" on dead money | false confidence | tested adjacent properties, never the invariant | **always canary-spend** — the oracle is a spend, everything else is decor |
| 3 | First strict-mode unit test blinded the WRONG bytes (TextEncoder of hex string, not hexToBytes) | one test cycle | wrote the trap test from memory | house suite caught it — negative vectors must use the canonical wrong-derivation bytes, verified against the vector file |
| 4 | `git add -A` in a worktree swept in a node_modules symlink + deleted a soak run-log | review-cycle fixup | sloppy staging | stage explicitly by path in worktrees; never `-A` where untracked symlinks live |
| 5 | Interactive rebase of the cashu-cf branch tangled into a broken state | ~30 min | rebase across a moved main with overlapping commits | for single-purpose branches: abort and **squash-rebuild** immediately; don't fight a rebase |
| 6 | Merged to cashu-cf main — violated the fork convention (main mirrors upstream) | surgical repair with 2 of your commits on top; force-push with lease | assumed "our repo = our merge" | **ask repo conventions on first write to any repo**; forks default to branch-only |
| 7 | **The docker-tunnel illusion**: scenarios "against ai-legion" hit the stale local docker 0.17.6 mint for many turns — same mnemonic → same keyset → perfect disguise | ~1h of phantom debugging, several false conclusions | tunnel silently lost the port bind; old environment never torn down | **verify environment identity (GET /v1/info → version) before believing ANY result**; tear down old environments the moment they're superseded |
| 8 | Buffered python output made a live matrix look dead | one wasted restart | no `-u` | always `python3 -u` for long-runners |
| 9 | Minted-new-CF-token detour: 3 failed attempts, wrong formats — while `cf-cashu-cf-deploy` sat in the keychain the whole time | ~10 min | didn't read the credential registry first | **read the registry before minting**; their policy doc literally documents the right token |
| 10 | "token stored" echoed on failure (shell short-circuit) | one confusing minute | `cmd && store || rm; echo` structure | success-path echos must live inside the `&&` chain |
| 11 | Appended a test outside `mod test`'s closing brace | one edit cycle | heredoc append without checking nesting | structural greps after every generated-code append |
| 12 | `pkill -f "cdk-mintd -w"` matched my own launcher and killed the session mid-command | one restart cycle | pattern matched launcher cmdline | `pgrep -x <exact-name>` for kill-by-name |
| 13 | Ad-hoc test script bugs: fee math wrong twice, swallowed errors in retry loops | 2 test cycles | wrote /tmp scripts instead of reusing house helpers | ad-hoc probes are for REPRODUCTION; write tests as scenarios/helpers in the repo |
| 14 | Deployed with uncommitted wrangler.toml campaign vars | had to remember to revert | no deploy hygiene | campaign vars are deploy-time config: revert toml before leaving, or use --var flags |

## 2. What worked — keep doing

1. **Canary/oracle testing against a pinned verifier** (docker cdk 0.17.6/0.18.0)
   surfaced every real behavior; every claim got reproduced before being believed.
2. **Differential probes** (correct vs trap convention through the full
   lifecycle) — the "everything green except the oracle" signature IS the finding.
3. **Cross-validated vectors** (4+ implementations agreeing byte-for-byte) —
   caught even my own transcription error (truncated hex).
4. **Journal everything** (exp-journal.ndjson, HTTP bodies, state files) —
   made every conclusion re-checkable and the writeup cheap.
5. **Instrument closer instead of theorizing** — when probes didn't fire, we
   added eprintln one level up until the world made sense.
6. **"Would this suite green-light the bug?"** — test blind-spot analysis is a
   first-class audit dimension (found nucula's gap).
7. **House suites caught MY bugs** (wrong-bytes test). Never bypass local
   suites to save time.
8. **Squash-rebuild over rebase surgery** once adopted, was fast and clean.
9. **Right machine for the job** (asked): laptop for TS suites/deploys,
   ai-legion for Rust builds + hosted mint.
10. **Arguing with the owner sharpened the position** — duty-follows-issuance
    and the keyset-grandfathering principle emerged from pushback, not from
    the first draft. Keep the debate-with-the-owner loop.

## 3. cashu-audit project improvements (concrete)

1. `run_matrix.py` needs: `--only/--skip` filters, per-scenario timeout,
   unbuffered output, always-structured JSON results. (The filtered runner
   used this campaign lived in /tmp — promote it into the repo.)
2. Baseline→diff as a first-class command (`run_matrix --baseline x.json
   --compare y.json`), with auto-noise for the known-flaky melt family.
3. **Environment-identity guard**: every run records `/v1/info` (version +
   pubkey) into the report header — the docker-illusion class dies here.
4. Error-body pattern library per mint family (cashu-cf's
   `14005/"Proof verification failed"`, cdk's `10001/"Token not verified"`) —
   the trap scenario shouldn't say "verify manually".
5. Investigate or skip-list the fakewallet melt-settlement timeouts (22/112
   polluted both runs).
6. Sensor-visibility as an audit dimension: does the log path actually reach
   queryable observability? (Found cashu-cf strict mode has NO sensor.)
7. Formalize `conformance/reference-vectors/` as the shared vector store;
   port the negative-trap vector into every new audit target.
8. Add the test-suite-blind-spot check as a standard audit artifact.

## 4. Code quality (our branches)

- **cashu-cf branch follow-up**: mirror cdk's log-on-reject so strict mode
  has a sensor; wiring-level unit test for `resolveEncodingStrictness` env
  parsing (features-level with env mock).
- **cdk branch follow-up**: unify env overrides into the DB-config daemon
  path (currently legacy-loader only — documented, but upstream-worthy fix).
- Scenario tests > ad-hoc scripts: the scoped-keyset test that worked was 90%
  house helpers; the two that failed were /tmp scripts with hand-rolled fee
  math.

## 5. Testing expectations (the new bar)

1. Every crypto-boundary test ships the negative vector. A suite that can't
   fail on the known trap is not a suite.
2. Canary spend before scale, in every environment, every time.
3. Telemetry is a feature: assert the log fires, not just accept/reject.
4. Property tests for derivation conventions (random secrets through both
   paths — cashu-core-lite's proptest_invariants.rs is the model).
5. Diff-based regression: no deploy without a baseline matrix diff.
6. Environment identity verified before results are trusted.

## 6. Process rules

1. Ask repo conventions (fork policy, deploy policy, credential registry)
   before the FIRST write to any repo — not after violating them.
2. Read the credential registry before minting anything.
3. One environment per purpose; superseded environments die immediately.
4. Tunnels: fresh port per target + version-check on first request.
5. `--no-verify` pushes each get a justification line in the commit message.
