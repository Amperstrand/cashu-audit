#!/usr/bin/env bash
# must-gap-nightly.sh — standing NUT-11/14 vector regression on the mint battery
# Runs the 17-vector suite against all 9 battery mints, detects drift vs the
# previous run, logs to ~/must-gap-runs/. Called from cron (see install below).
set -u
RUNS="$HOME/must-gap-runs"
mkdir -p "$RUNS" /tmp/mgv-drv
cp -f "$HOME/src/must-gap-vectors/must_gap_vectors.py" /tmp/mgv-drv/mgv.py 2>/dev/null \
  || true  # keep whatever driver is staged if no repo checkout
TS=$(date +%Y%m%d-%H%M%S)
OUT="$RUNS/run-$TS.txt"
MINTS=""
for p in 35000 35001 35002 35003 35004 35005 35006 35007 35008; do
  curl -s -m 3 "http://127.0.0.1:$p/v1/info" >/dev/null 2>&1 && MINTS="$MINTS http://127.0.0.1:$p"
done
[ -z "$MINTS" ] && { echo "$(date -Is) no mints reachable" >> "$RUNS/nightly.log"; exit 1; }
docker run --rm --network host -v /tmp/mgv-drv:/drv:ro \
  cashubtc/nutshell:0.20.3 python3 /drv/mgv.py $MINTS > "$OUT" 2>&1
PREV=$(ls -1 "$RUNS"/run-*.txt 2>/dev/null | grep -v "$OUT" | tail -1)
if [ -n "$PREV" ]; then
  DIFF=$(diff <(grep "^http" "$PREV") <(grep "^http" "$OUT") || true)
  if [ -n "$DIFF" ]; then
    echo "$(date -Is) DRIFT DETECTED:" >> "$RUNS/nightly.log"
    echo "$DIFF" >> "$RUNS/nightly.log"
  else
    echo "$(date -Is) stable" >> "$RUNS/nightly.log"
  fi
fi
# keep last 60 runs
ls -1t "$RUNS"/run-*.txt 2>/dev/null | tail -n +61 | xargs -r rm -f
