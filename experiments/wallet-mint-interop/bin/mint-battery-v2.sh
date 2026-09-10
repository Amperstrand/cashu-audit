#!/bin/bash
set -e
COMMAND="${1:-list}"
DATA_DIR="$HOME/mint-battery"
mkdir -p "$DATA_DIR"

MINTS=(
  "cdk-0170|cdk|cashubtc/mintd:0.17.0|35000"
  "cdk-0176|cdk|cashubtc/mintd:0.17.6|35001"
  "cdk-0180|cdk|cashubtc/mintd:0.18.0|35002"
  "ns-2000|nutshell|cashubtc/nutshell:0.20.0|35003"
  "ns-2002|nutshell|cashubtc/nutshell:0.20.2|35004"
  "ns-2003|nutshell|cashubtc/nutshell:0.20.3|35005"
  "ns-1910|nutshell|cashubtc/nutshell:0.19.1|35006"
  "ns-1820|nutshell|cashubtc/nutshell:0.18.2|35007"
  "ns-1650|nutshell|cashubtc/nutshell:0.16.5|35008"
)
MNEMONIC="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"

up() {
  for mint in "${MINTS[@]}"; do
    IFS='|' read -r name family image port <<< "$mint"
    container="battery-$name"
    dir="$DATA_DIR/$name"
    if docker ps --format '{{.Names}}' | grep -q "^$container$"; then
      echo "  :$port $name already running"
      continue
    fi
    mkdir -p "$dir"
    if [ "$family" = "nutshell" ]; then
      key=$(echo "$name" | sha256sum | cut -c1-64)
      docker run -d --name "$container" --network host \
        -e MINT_BACKEND_BOLT11_SAT=FakeWallet \
        -e MINT_LISTEN_HOST=127.0.0.1 \
        -e "MINT_LISTEN_PORT=$port" \
        -e MINT_RATE_LIMIT=FALSE \
        -e "MINT_PRIVATE_KEY=$key" \
        "$image" poetry run mint >/dev/null 2>&1 \
        && echo "  :$port $name UP" \
        || echo "  :$port $name FAILED"
    else
      if [[ "$image" == *"0.18"* ]]; then
        if [ ! -f "$dir/config.toml" ]; then
          printf '[info]\nurl = "http://127.0.0.1:%s/"\nlisten_host = "127.0.0.1"\nlisten_port = %s\nmnemonic = "env:BAT_MN"\n[database]\nengine = "sqlite"\n[payment_backend]\nbackend = "fakewallet"\n[onchain]\nonchain_backend = "fakewallet"\n[fake_wallet]\nsupported_units = ["sat"]\n' "$port" "$port" > "$dir/config.toml"
          docker run --rm -v "$dir:/data" -e "BAT_MN=$MNEMONIC" "$image" cdk-mintd -w /data config init --new-mint --file /data/config.toml >/dev/null 2>&1
        fi
        docker run -d --name "$container" --network host \
          -v "$dir:/data" \
          -e "BAT_MN=$MNEMONIC" \
          "$image" cdk-mintd -w /data >/dev/null 2>&1 \
        && echo "  :$port $name UP" \
        || echo "  :$port $name FAILED"
      else
        docker run -d --name "$container" --network host \
          -e CDK_MINTD_LN_BACKEND=FakeWallet \
          -e CDK_MINTD_FAKE_WALLET_SUPPORTED_UNITS=sat \
          -e CDK_MINTD_LISTEN_HOST=127.0.0.1 \
          -e "CDK_MINTD_LISTEN_PORT=$port" \
          -e "CDK_MINTD_URL=http://127.0.0.1:$port/" \
          -e "CDK_MINTD_MINT_NAME=battery-$name" \
          -e "CDK_MINTD_MNEMONIC=$MNEMONIC" \
          "$image" >/dev/null 2>&1 \
        && echo "  :$port $name UP" \
        || echo "  :$port $name FAILED"
      fi
    fi
  done
}

down() {
  docker ps -aq --filter name=battery- | xargs -r docker rm -f
  echo "battery down"
}

list() {
  echo "=== Mint Battery ==="
  for mint in "${MINTS[@]}"; do
    IFS='|' read -r name family image port <<< "$mint"
    container="battery-$name"
    if docker ps --format '{{.Names}}' | grep -q "^$container$"; then
      version=$(timeout 5 curl -s "http://127.0.0.1:$port/v1/info" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
      echo "  :$port $name UP v=$version"
    else
      echo "  :$port $name DOWN"
    fi
  done
}

case "$COMMAND" in
  up) up ;;
  down) down ;;
  list) list ;;
  *) echo "Usage: $0 up|down|list" ;;
esac
