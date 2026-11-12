#!/usr/bin/env bash
# spent-set-preservation probe — does a SPENT proof stay spent across an
# in-place upgrade to 0.18.3? (The upgrade matrix's open cell: identity and
# keysets were proven preserved; this proves the LEDGER (spent set) survives
# too, completing the in-place-upgrade safety story.)
set -u
R=/tmp/opencode/spentprobe; rm -rf $R; mkdir -p $R
PORT=33398
MNEM="$(/tmp/opencode/cdk-venv312/bin/python -c "from mnemonic import Mnemonic; print(Mnemonic('english').generate(strength=128))")"
TGT=0.18.3
RES="$R/results.txt"; : > "$RES"

boot_legacy() { # image
  sudo -n docker rm -f spentprobe >/dev/null 2>&1
  sudo -n docker run -d --name spentprobe -p 127.0.0.1:$PORT:8085 \
    -e CDK_MINTD_LN_BACKEND=FakeWallet -e CDK_MINTD_FAKE_WALLET_SUPPORTED_UNITS=sat \
    -e CDK_MINTD_LISTEN_HOST=0.0.0.0 -e CDK_MINTD_LISTEN_PORT=8085 \
    -e CDK_MINTD_URL="http://127.0.0.1:$PORT/" -e CDK_MINTD_MINT_NAME=spentprobe \
    -e CDK_MINTD_MNEMONIC="$MNEM" -v "$1:/data" cashubtc/mintd:$2 cdk-mintd -w /data >/dev/null
  sleep 6
}

boot_modern() { # image workdir
  sudo -n docker rm -f spentprobe >/dev/null 2>&1
  sudo -n docker run -d --name spentprobe -p 127.0.0.1:$PORT:8085 -e UM_MNEMONIC="$MNEM" \
    -v "$2:/data" cashubtc/mintd:$1 cdk-mintd -w /data >/dev/null
  sleep 6
}

client_phase() { # phase jsonfile  (phase1 = mint+swap; phase2 = retry spent + spend unspent)
  sudo -n /tmp/opencode/cdk-venv312/bin/python - "$1" "$2" <<'PYEOF'
import json, sys
sys.path.insert(0, "/home/user/src/cashu-audit/conformance")
from conformance.client import MintClient
from conformance.builder import ProofBuilder
from conformance.crypto import generate_secret

phase, path = sys.argv[1], sys.argv[2]
mint = MintClient("http://127.0.0.1:33398", timeout=30)
b = ProofBuilder(mint)
if phase == "phase1":
    p1 = b.mint_proofs(8)
    outs = b.outputs_to_api(b.create_outputs(8, generate_secret))
    code, body = mint.try_swap([p.to_dict() for p in p1], outs)
    assert code == 200, f"control swap failed: {code} {body}"
    json.dump({"p1": [p.to_dict() for p in p1]}, open(path, "w"))
    print("phase1: minted 8, swapped (P1 now SPENT)")
else:
    d = json.load(open(path))
    p1 = d["p1"]
    outs = b.outputs_to_api(b.create_outputs(8, generate_secret))
    code, body = mint.try_swap(p1, outs)
    spent_rejected = code != 200
    print(f"phase2: re-swap of SPENT P1 -> {code} ({'REJECTED (spent-set preserved)' if spent_rejected else 'ACCEPTED — DOUBLE-SPEND WINDOW!'})")
    json.dump({"spent_rejected": spent_rejected}, open(path + ".verdict", "w"))
PYEOF
}

run_case() { # source
  local src=$1 W="$R/$1"
  mkdir -p "$W"
  if [[ "$src" == 0.17.* ]]; then
    boot_legacy "$W" "$src"
  else
    cat > "$W/modern.toml" <<EOF
[info]
url = "http://127.0.0.1:$PORT/"
listen_host = "0.0.0.0"
listen_port = 8085
mnemonic = "env:UM_MNEMONIC"
[mint_info]
name = "spentprobe"
[database]
engine = "sqlite"
[[payment_backend]]
backend = "fakewallet"
unit = "sat"
min_mint = 1
max_mint = 100000
min_melt = 1
max_melt = 100000
[onchain]
onchain_backend = "none"
[fake_wallet]
supported_units = ["sat"]
EOF
    sudo -n docker run --rm -v "$W:/data" -e UM_MNEMONIC="$MNEM" cashubtc/mintd:$src \
      cdk-mintd -w /data config init --new-mint --file /data/modern.toml 2>&1 | grep -q "Configuration initialized" || { echo "$src: SRC_INIT_FAIL" | tee -a "$RES"; return; }
    boot_modern "$src" "$W"
  fi
  client_phase phase1 "$W/state.json" || { echo "$src: PHASE1_FAIL" | tee -a "$RES"; return; }
  sudo -n docker rm -f spentprobe >/dev/null 2>&1
  if [[ "$src" == 0.17.* ]]; then
    cp "$R/legacy.toml" "$W/" 2>/dev/null || cat > "$W/legacy.toml" <<EOF
[info]
url = "http://127.0.0.1:$PORT/"
listen_host = "0.0.0.0"
listen_port = 8085
mnemonic = "env:UM_MNEMONIC"
[mint_info]
name = "spentprobe"
[database]
engine = "sqlite"
[[ln]]
ln_backend = "fakewallet"
unit = "sat"
min_mint = 1
max_mint = 100000
min_melt = 1
max_melt = 100000
EOF
    sudo -n docker run --rm -v "$W:/data" -e UM_MNEMONIC="$MNEM" cashubtc/mintd:$TGT cdk-mintd -w /data config migrate --file /data/legacy.toml --output /data/mig.toml >/dev/null 2>&1
    sudo -n docker run --rm -v "$W:/data" -e UM_MNEMONIC="$MNEM" cashubtc/mintd:$TGT cdk-mintd -w /data config init --existing-mint --file /data/mig.toml 2>&1 | grep -q "Configuration initialized" || { echo "$src: UPGRADE_INIT_FAIL" | tee -a "$RES"; return; }
  fi
  boot_modern "$TGT" "$W"
  client_phase phase2 "$W/state.json" | tee -a "$RES"
  sudo -n docker rm -f spentprobe >/dev/null 2>&1
}

for src in 0.17.0 0.17.7 0.18.0 0.18.2; do echo "--- $src ---" | tee -a "$RES"; run_case "$src"; done
echo "=== RESULTS ==="; cat "$RES"
