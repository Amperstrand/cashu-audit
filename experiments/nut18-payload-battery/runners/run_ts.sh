#!/usr/bin/env bash
# Battery cell: cashu-ts columns (decode + settlement) via vitest on a v5.0.0-rc.9 worktree.
# Env: TS_WORKTREE (a cashu-ts checkout at v5.0.0-rc.9 with node_modules),
#      BATTERY_MINT_URL (optional; settlement cells skip when unset).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TS_WORKTREE="${TS_WORKTREE:-/tmp/opencode/cashu-ts-rc9}"
mkdir -p "$TS_WORKTREE/test/wallet"
cp "$HERE/harness/battery.node.test.ts" "$TS_WORKTREE/test/wallet/"
cd "$TS_WORKTREE" && BATTERY_DIR="$HERE" npx vitest run test/wallet/battery.node.test.ts
