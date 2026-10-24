#!/bin/bash
# Daily upstream watch for cashu-audit: NUTs spec drift + cdk/nutshell releases.
# Designed for cron; safe to run by hand. Log: /root/upstream-watch.log
#
# On CHANGE: commits research/ + tools/ (watch state, digests, regenerated
# timelines) and pushes. A failed push leaves the commit local — the next
# session or run picks it up; the log records PUSH-FAILED.

set -u
REPO=/root/src/cashu-audit
LOG=/root/upstream-watch.log
PY=/usr/bin/python3
export PATH="$PATH:/usr/local/bin:/usr/bin"

cd "$REPO" || { echo "$(date -u '+%F %T') FATAL: no repo at $REPO" >> "$LOG"; exit 1; }

# work off latest main (nightly-corpus bot also commits here)
git pull --rebase --quiet >>"$LOG" 2>&1

OUT=$($PY tools/upstream_watch.py 2>&1)
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
