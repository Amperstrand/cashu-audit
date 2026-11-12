#!/usr/bin/env bash
# cdk-mintd upgrade matrix — which (source → 0.18.3) in-place paths work.
# Shapes: A = fresh-idle; B = rotated-past keyset (boot plain, then restart
# with CDK_MINTD_FAKE_WALLET_KEYSET_ROTATIONS expiring the first keyset).
# No external output; results land next to this script.
set -u
PORT=33390
WROOT=/tmp/opencode/upgradematrix
MNEM="uniform round silly sea fruit cannon laptop domain nose cradle genius alarm"
TARGET=0.18.3
mkdir -p "$WROOT"
RESULTS="$WROOT/results.tsv"; : > "$RESULTS"
echo -e "source\tshape\tinit_or_start\tversion\tpubkey_same\tkeysets_pre\tkeysets_post\tverdict" >> "$RESULTS"

free_port() { for p in $(seq 33390 33420); do ss -tln | grep -q ":$p " || { echo $p; return; }; done; }

record() { # name file
  curl -s -m 4 "http://127.0.0.1:$PORT/v1/info" | jq -r '.version,.pubkey' > "$2.ver" 2>/dev/null
  curl -s -m 4 "http://127.0.0.1:$PORT/v1/keysets" | jq -r '[.keysets[].id] | join(",")' > "$2.ks" 2>/dev/null
}

write_modern_toml() {
  cat > "$WORK/modern.toml" <<EOF2
[info]
url = "http://127.0.0.1:$PORT/"
listen_host = "0.0.0.0"
listen_port = 8085
mnemonic = "env:UM_MNEMONIC"
[mint_info]
name = "upgrade matrix"
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
EOF2
}

boot_src() { # image extra_env...
  local img=$1; shift
  CNAME=um-run
  sudo -n docker rm -f $CNAME >/dev/null 2>&1
  sudo -n docker run -d --name $CNAME -p 127.0.0.1:$PORT:8085 \
    -e CDK_MINTD_LN_BACKEND=FakeWallet \
    -e CDK_MINTD_FAKE_WALLET_SUPPORTED_UNITS=sat \
    -e CDK_MINTD_LISTEN_HOST=0.0.0.0 \
    -e CDK_MINTD_LISTEN_PORT=8085 \
    -e CDK_MINTD_URL="http://127.0.0.1:$PORT/" \
    -e CDK_MINTD_MINT_NAME="upgrade matrix" \
    -e CDK_MINTD_MNEMONIC="$MNEM" \
    "$@" -v "$WORK:/data" "$img" cdk-mintd -w /data >/dev/null
}

boot_modern() { # image
  CNAME=um-run
  sudo -n docker rm -f $CNAME >/dev/null 2>&1
  sudo -n docker run -d --name $CNAME -p 127.0.0.1:$PORT:8085 -e UM_MNEMONIC="$MNEM" -v "$WORK:/data" "$1" cdk-mintd -w /data >/dev/null
}

run_case() { # source shape
  local src=$1 shape=$2
  WORK="$WROOT/${src}_${shape}"; rm -rf "$WORK"; mkdir -p "$WORK"
  PORT=$(free_port)
  local pre_ks="" pre_pub="" post_ver="" post_pub="" init=OK start=OK

  # --- phase 1: run the source version
  if [[ "$src" == 0.18.* ]]; then
    write_modern_toml
    INI0=$(sudo -n docker run --rm -v "$WORK:/data" -e UM_MNEMONIC="$MNEM" "cashubtc/mintd:$src" cdk-mintd -w /data config init --new-mint --file /data/modern.toml 2>&1)
    grep -q "Configuration initialized" <<<"$INI0" || { echo -e "$src\t$shape\tSRC_INIT_FAIL\t-\t-\t-\t-\tSRC_INIT_FAIL" >> "$RESULTS"; echo "$INI0" > "$WORK/src-init-fail.log"; return; }
    if [[ "$shape" == "B" ]]; then
      boot_modern "cashubtc/mintd:$src"
      sleep 5
      sudo -n docker rm -f $CNAME >/dev/null 2>&1
      sudo -n docker run -d --name $CNAME -p 127.0.0.1:$PORT:8085 \
        -e 'CDK_MINTD_FAKE_WALLET_KEYSET_ROTATIONS=[{"unit":"sat","version":"v1","input_fee_ppk":0,"expired":true},{"unit":"sat","version":"v1","input_fee_ppk":0,"expired":false}]' \
        -e UM_MNEMONIC="$MNEM" -v "$WORK:/data" "cashubtc/mintd:$src" cdk-mintd -w /data >/dev/null
    else
      boot_modern "cashubtc/mintd:$src"
    fi
  elif [[ "$shape" == "B" ]]; then
    boot_src "cashubtc/mintd:$src"
    sleep 5
    boot_src "cashubtc/mintd:$src" -e 'CDK_MINTD_FAKE_WALLET_KEYSET_ROTATIONS=[{"unit":"sat","version":"v1","input_fee_ppk":0,"expired":true},{"unit":"sat","version":"v1","input_fee_ppk":0,"expired":false}]'
  else
    boot_src "cashubtc/mintd:$src"
  fi
  sleep 6
  if ! sudo -n docker ps --format '{{.Names}}' | grep -q $CNAME; then
    echo -e "$src\t$shape\tBOOT_FAIL\t-\t-\t-\t-\tBOOT_FAIL" >> "$RESULTS"; sudo -n docker logs $CNAME 2>&1 | tail -3 > "$WORK/boot-fail.log"; return
  fi
  record pre "$WORK/pre"
  pre_ks=$(cat "$WORK/pre.ks"); pre_pub=$(sed -n 2p "$WORK/pre.ver")
  sudo -n docker rm -f $CNAME >/dev/null 2>&1
  cp -a "$WORK/cdk-mintd.sqlite" "$WORK/backup.sqlite" 2>/dev/null

  # --- phase 2: upgrade to target
  if [[ "$src" == 0.15.* || "$src" == 0.17.* ]]; then
    cat > "$WORK/legacy.toml" <<EOF
[info]
url = "http://127.0.0.1:$PORT/"
listen_host = "0.0.0.0"
listen_port = 8085
mnemonic = "env:UM_MNEMONIC"
[mint_info]
name = "upgrade matrix"
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
    MIG=$(sudo -n docker run --rm -v "$WORK:/data" -e UM_MNEMONIC="$MNEM" cashubtc/mintd:$TARGET cdk-mintd -w /data config migrate --file /data/legacy.toml --output /data/mig.toml 2>&1)
    echo "$MIG" > "$WORK/migrate.log"
    VAL=$(sudo -n docker run --rm -v "$WORK:/data" -e UM_MNEMONIC="$MNEM" cashubtc/mintd:$TARGET cdk-mintd -w /data config validate --file /data/mig.toml 2>&1)
    echo "$VAL" > "$WORK/validate.log"
    INI=$(sudo -n docker run --rm -v "$WORK:/data" -e UM_MNEMONIC="$MNEM" cashubtc/mintd:$TARGET cdk-mintd -w /data config init --existing-mint --file /data/mig.toml 2>&1)
    echo "$INI" > "$WORK/init.log"
    grep -q "Configuration initialized" <<<"$INI" || init="INIT_FAIL:$(grep -oE 'Error: [^;]{0,90}' <<<"$INI" | head -1)"
  fi

  if [[ "$init" == OK ]]; then
    boot_modern "cashubtc/mintd:$TARGET"
    sleep 6
    if sudo -n docker ps --format '{{.Names}}' | grep -q $CNAME && curl -s -m 4 "http://127.0.0.1:$PORT/v1/info" >/dev/null 2>&1; then
      record post "$WORK/post"
      post_ver=$(sed -n 1p "$WORK/post.ver"); post_pub=$(sed -n 2p "$WORK/post.ver")
    else
      start="START_FAIL"; sudo -n docker logs $CNAME 2>&1 | tail -3 > "$WORK/start-fail.log"
    fi
  else
    start="SKIPPED"
  fi
  sudo -n docker rm -f $CNAME >/dev/null 2>&1

  local verdict
  if [[ "$init" == OK && "$start" == OK && "$post_pub" == "$pre_pub" ]]; then verdict=PASS
  elif [[ "$init" != OK ]]; then verdict=UPGRADE_BLOCKED
  elif [[ "$start" != OK ]]; then verdict=START_BROKEN
  else verdict=IDENTITY_MISMATCH; fi
  echo -e "$src\t$shape\t$init\t$post_ver\t$([[ "$post_pub" == "$pre_pub" ]] && echo yes || echo no)\t$pre_ks\t$(cat "$WORK/post.ks" 2>/dev/null)\t$verdict" >> "$RESULTS"
  echo "[$src/$shape] $verdict ($init / $start)"
}

for src in 0.15.0 0.17.0 0.17.2 0.17.6 0.17.7 0.18.0 0.18.1 0.18.2; do
  for shape in A B; do run_case "$src" "$shape"; done
done
column -t -s$'\t' "$RESULTS"
