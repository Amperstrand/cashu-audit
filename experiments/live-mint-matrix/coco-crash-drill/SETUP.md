# Standing coco crash-drill — setup

Harness: drill.ts + drill-proxy.ts (this dir). Driven by the standing
leg in experiments/fresh-must-wave/certify_testnut.py. Requires:

1. bun on PATH (any recent; 1.4.2 proven).
2. A pinned coco checkout at ~/src/upstream-cache/coco @ 2d6aa583
   (override with COCO_DIR env):

     git clone https://github.com/cashubtc/coco.git ~/src/upstream-cache/coco
     cd ~/src/upstream-cache/coco && git checkout 2d6aa583

3. Workspace install + builds (ONE-TIME; re-run after re-clone):

     cd ~/src/upstream-cache/coco
     printf '[install]\nminimumReleaseAge = 0\n' > bunfig.toml
     # (playwright-core is pinned exactly by upstream's committed lockfile;
     #  the age gate otherwise blocks the install)
     bun install --linker=hoisted --force
     (cd packages/core && bun run build)        # exports point at dist/
     (cd packages/sql-storage && bun run build)

Pitfalls learned building this (2026-11-12):
- bun 1.4's isolated linker leaves per-package deps unresolved for this
  workspace — use --linker=hoisted and a CLEAN node_modules if an
  install ever fails midway (a partial install poisons node_modules and
  later "no changes" installs will NOT repair it: rm -rf node_modules
  packages/*/node_modules first).
- packages/core + sql-storage must be BUILT (tsdown) — the workspace
  exports map points at dist/, but a fresh clone has none.
- Do NOT hand-symlink per-package node_modules — resolution then stops
  at the incomplete nearest dir instead of falling back to the root.
- The drill imports ./coco/... (a symlink the certifier creates in the
  run dir pointing at the clone) — keep the import paths relative to
  the harness file, not the clone.
- The proxy swap counter is PER-PROCESS: the leg restarts the proxy
  between phase1 (inject swaps >= 2) and phase2 (INJECT_OFF=1).
