#!/usr/bin/env bash
# verify.sh — one-command reproduction in any environment with docker.
# Spawns a stock cdk-mintd 0.17.6 (fakewallet) and runs the single-vector
# HTLC-refund repro against it. Prints the verdict. Cleans up after itself.
#
# Usage: ./verify.sh [mint_url]
#   with no argument: spawns a stock cdk 0.17.6 fakewallet mint on :36070
#   with an argument: tests that mint directly (any cdk/nutshell mint)
set -u
PORT=36070
CONTAINER=htlc-refund-verify

if [ $# -ge 1 ]; then
    MINT="$1"
else
    docker rm -f "$CONTAINER" >/dev/null 2>&1
    docker run -d --network host --name "$CONTAINER" \
      -e CDK_MINTD_LN_BACKEND=FakeWallet \
      -e CDK_MINTD_FAKE_WALLET_SUPPORTED_UNITS=sat \
      -e CDK_MINTD_LISTEN_HOST=127.0.0.1 \
      -e CDK_MINTD_LISTEN_PORT=$PORT \
      -e CDK_MINTD_URL=http://127.0.0.1:$PORT/ \
      -e CDK_MINTD_MINT_NAME=verify \
      -e CDK_MINTD_MNEMONIC="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about" \
      cashubtc/mintd:0.17.6 >/dev/null || { echo "failed to start mint"; exit 2; }
    for i in $(seq 1 20); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/info" >/dev/null 2>&1 && break; sleep 2; done
    MINT="http://127.0.0.1:$PORT"
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
docker run --rm --network host -v "$HERE":/drv:ro -w /drv cashubtc/nutshell:0.20.3 \
  python3 /drv/verify_htlc_refund.py "$MINT"
RC=$?

[ $# -ge 1 ] || docker rm -f "$CONTAINER" >/dev/null 2>&1
exit $RC
