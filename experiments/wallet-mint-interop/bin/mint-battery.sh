#!/bin/bash
# Mint battery: stands up multiple Cashu mints as persistent docker containers
# on ai-legion. Each mint gets a unique port starting from 35000.
# Usage: ~/bin/mint-battery.sh up|down|list

set -e

COMMAND="${1:-list}"
BASE_PORT=35000
DATA_DIR="$HOME/mint-battery"
mkdir -p "$DATA_DIR"

# Mint definitions: name:family:image
MINTS=(
  "cdk-0170:cdk:cashubtc/mintd:0.17.0"
  "cdk-0176:cdk:cashubtc/mintd:0.17.6"
  "cdk-0180:cdk:cashubtc/mintd:0.18.0"
  "ns-2000:nutshell:cashubtc/nutshell:0.20.0"
  "ns-2002:nutshell:cashubtc/nutshell:0.20.2"
  "ns-2003:nutshell:cashubtc/nutshell:0.20.3"
  "ns-1910:nutshell:cashubtc/nutshell:0.19.1"
  "ns-1820:nutshell:cashubtc/nutshell:0.18.2"
  "ns-1650:nutshell:cashubtc/nutshell:0.16.5"
)

port_for() {
  local idx=$1
  echo $((BASE_PORT + idx))
}

up() {
  local idx=0
  for mint in "${MINTS[@]}"; do
    IFS=':' read -r name family image <<< "$mint"
    local port=$(port_for $idx)
    local container="battery-$name"
    local dir="$DATA_DIR/$name"

    # Skip if already running
    if docker ps --format '{{.Names}}' | grep -q "^$container$"; then
      echo "  $name already running on :$port"
      idx=$((idx+1)); continue
    fi

    mkdir -p "$dir"

    if [ "$family" = "nutshell" ]; then
      # Generate a deterministic key per mint for reproducibility
      local key=$(echo "$name" | sha256sum | cut -c1-64)
      docker run -d --name "$container" \
        -p "$port:3338" \
        -e MINT_BACKEND_BOLT11_SAT=FakeWallet \
        -e MINT_LISTEN_HOST=0.0.0.0 \
        -e MINT_LISTEN_PORT=3338 \
        -e MINT_RATE_LIMIT=FALSE \
        -e "MINT_PRIVATE_KEY=$key" \
        "$image" poetry run mint >/dev/null 2>&1 && \
        echo "  $name up on :$port" || echo "  $name FAILED"
    elif [ "$family" = "cdk" ]; then
      local mnemonic_file="$dir/mnemonic"
      if [ ! -f "$mnemonic_file" ]; then
        python3 -c "from mnemonic import Mnemonic; print(Mnemonic('english').generate(strength=256))" > "$mnemonic_file" 2>/dev/null || \
        echo "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about" > "$mnemonic_file"
      fi
      local mnemonic=$(cat "$mnemonic_file")

      if [[ "$image" == *"0.18"* ]]; then
        # 0.18+ needs config init
        if [ ! -f "$dir/config.toml" ]; then
          cat > "$dir/config.toml" << EOF
[info]
url = "http://127.0.0.1:$port/"
listen_host = "0.0.0.0"
listen_port = 3338
mnemonic = "env:BATTERY_MNEMONIC"

[database]
engine = "sqlite"

[payment_backend]
backend = "fakewallet"

[onchain]
onchain_backend = "fakewallet"

[fake_wallet]
supported_units = ["sat"]
EOF
          docker run --rm -v "$dir:/data" -e "BATTERY_MNEMONIC=$mnemonic" \
            "$image" cdk-mintd -w /data config init --new-mint --file /data/config.toml >/dev/null 2>&1
        fi
        docker run -d --name "$container" \
          -p "$port:3338" \
          -v "$dir:/data" \
          -e "BATTERY_MNEMONIC=$mnemonic" \
          "$image" cdk-mintd -w /data >/dev/null 2>&1 && \
          echo "  $name up on :$port" || echo "  $name FAILED"
      else
        # 0.17.x legacy env vars
        docker run -d --name "$container" \
          -p "$port:3338" \
          -e CDK_MINTD_LN_BACKEND=FakeWallet \
          -e CDK_MINTD_FAKE_WALLET_SUPPORTED_UNITS=sat \
          -e CDK_MINTD_LISTEN_HOST=0.0.0.0 \
          -e CDK_MINTD_LISTEN_PORT=3338 \
          -e "CDK_MINTD_URL=http://127.0.0.1:$port/" \
          -e CDK_MINTD_MINT_NAME="battery-$name" \
          -e "CDK_MINTD_MNEMONIC=$mnemonic" \
          "$image" >/dev/null 2>&1 && \
          echo "  $name up on :$port" || echo "  $name FAILED"
      fi
    fi
    idx=$((idx+1))
  done
}

down() {
  docker ps -aq --filter name=battery- | xargs -r docker rm -f
  echo "battery down"
}

list() {
  echo "=== Mint Battery ==="
  local idx=0
  for mint in "${MINTS[@]}"; do
    IFS=':' read -r name family image <<< "$mint"
    local port=$(port_for $idx)
    local container="battery-$name"
    if docker ps --format '{{.Names}}' | grep -q "^$container$"; then
      local status="UP"
      local version=$(timeout 3 curl -s "http://127.0.0.1:$port/v1/info" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
      echo "  :$port  $name ($family) $status v=$version"
    else
      echo "  :$port  $name ($family) DOWN"
    fi
    idx=$((idx+1))
  done
}

case "$COMMAND" in
  up) up ;;
  down) down ;;
  list) list ;;
  *) echo "Usage: $0 up|down|list" ;;
esac
