#!/bin/bash
# Daily upstream watch for cashu-audit: NUTs spec drift + cdk/nutshell releases.
# Designed for cron; safe to run by hand. Log: $HOME/upstream-watch.log
#
# Location-independent: derives the repo from this script's path, so any
# clone works (watch host, bench host, laptop). On CHANGE: commits
# research/ + tools/ (watch state, digests, regenerated timelines) and
# pushes. A failed push leaves the commit local — the next session or
# run picks it up; the log records PUSH-FAILED.

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$HOME/upstream-watch.log"
PY="$(command -v python3)"
export PATH="$PATH:/usr/local/bin:/usr/bin:$HOME/bin"

cd "$REPO" || { echo "$(date -u '+%F %T') FATAL: no repo at $REPO" >> "$LOG"; exit 1; }

# work off latest main (nightly-corpus bot + other lanes also commit here)
# — but NEVER destroy local work: reset only a clean tree, else log + run
# against what's checked out.
git fetch origin --quiet >>"$LOG" 2>&1
if [ -z "$(git status --porcelain --untracked-files=no)" ]; then
    git reset --hard origin/main --quiet >>"$LOG" 2>&1
else
    echo "$(date -u '+%F %T') NOTE: dirty tree, skipping sync (lane WIP?)" >> "$LOG"
fi

OUT=$($PY tools/upstream_watch.py \
    --nuts-dir "${NUTS_DIR:-$HOME/src/NUTs}" \
    --clone-dir "${CLONE_DIR:-$HOME/src/upstream-cache}" 2>&1)
echo "$(date -u '+%F %T') $OUT" >> "$LOG"

if echo "$OUT" | grep -q '^CHANGE:'; then
    SUMMARY=$(echo "$OUT" | grep '^CHANGE:' | head -3 | tr '\n' ' | ')
    git add -A research tools
    if git -c user.name="Amperstrand" \
           -c user.email="141745238+Amperstrand@users.noreply.github.com" \
           commit -qm "upstream-watch: ${SUMMARY:0:200}"; then
        if git push --quiet origin main >>"$LOG" 2>&1; then
            echo "$(date -u '+%F %T') committed+pushed" >> "$LOG"
        else
            echo "$(date -u '+%F %T') PUSH-FAILED (commit left local)" >> "$LOG"
        fi
    else
        echo "$(date -u '+%F %T') COMMIT-FAILED (nothing staged?)" >> "$LOG"
    fi
fi
