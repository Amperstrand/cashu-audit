#!/usr/bin/env bash
# Local nutshell 0.20.3 mint for the shadow-proxy study (cashu-audit
# experiments/shadow-proxy-nutshell). FakeWallet backend; listen :8737.
#
# Workarounds required on this host class (all local-checkout-only,
# none upstream):
#  1. pyproject drops `breez-sdk-spark = "^0.15.0"` — no matching wheel on
#     this index/platform (available >= 0.18.0); spark backend unused here.
#  2. cashu/lightning/__init__.py sparkl2 import guarded with try/except —
#     the eager import crashes without breez_sdk_spark.
#  3. `marshmallow<4` (environs crashes on v4) — known 0.20.3 quirk.
#  4. `limits==3.5.0` — limits>=5 dropped the "fixed-window-elastic-expiry"
#     strategy string the mint's rate limiter passes.
set -euo pipefail

SRC=${NUTSHELL_SRC:-/tmp/nutshell-src}
VENV=${NUTSHELL_VENV:-/tmp/nutshell-venv}
DATA=${NUTSHELL_DATA:-/tmp/opencode/nutshell-mint}
PORT=${NUTSHELL_PORT:-8737}
KEY=${NUTSHELL_PRIVATE_KEY:-1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f1f}

if [ ! -d "$SRC/.git" ]; then
  git clone --quiet https://github.com/cashubtc/nutshell "$SRC"
  git -C "$SRC" checkout --quiet 0.20.3
  # workaround 1: drop the unresolvable spark dependency
  grep -v '^breez-sdk-spark = ' "$SRC/pyproject.toml" > "$SRC/pyproject.toml.tmp"
  mv "$SRC/pyproject.toml.tmp" "$SRC/pyproject.toml"
  # workaround 2: guard the eager sparkl2 import
  python3 - "$SRC" <<'PY'
import sys
p = sys.argv[1] + '/cashu/lightning/__init__.py'
s = open(p).read()
s = s.replace('from .sparkl2 import SparkL2Wallet  # noqa: F401',
              'try:\n    from .sparkl2 import SparkL2Wallet  # noqa: F401\nexcept ImportError:\n    SparkL2Wallet = None')
open(p, 'w').write(s)
PY
fi

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  (cd "$SRC" && "$VENV/bin/pip" install --quiet -e .)
  "$VENV/bin/pip" install --quiet 'marshmallow<4' 'limits==3.5.0'   # workarounds 3+4
fi

mkdir -p "$DATA"
echo "nutshell 0.20.3 (FakeWallet) starting on 127.0.0.1:$PORT (data: $DATA)"
cd "$DATA"
CASHU_DIR="$DATA" MINT_BACKEND_BOLT11_SAT=FakeWallet \
  MINT_LISTEN_HOST=127.0.0.1 MINT_LISTEN_PORT="$PORT" \
  MINT_INFO_NAME=nutshell-shadow MINT_PRIVATE_KEY="$KEY" \
  exec "$VENV/bin/python" -m cashu.mint
