#!/usr/bin/env bash
# spike-payer.sh — herdr-hosted payment helper for the wallet×zoo spike.
# Watches /tmp/opencode/spike-queue/:
#   <id>.pay      file content = bolt11 invoice to pay from cln-swap-signet
#                 (fallback cln-hub-signet); writes <id>.pay.result
#   <id>.invoice  file content = "<msat> <label>" — creates invoice on
#                 cln-hub-signet; writes <id>.invoice.result = bolt11
#   <id>.check    file content = label — writes <id>.check.result =
#                 PAID|UNPAID|EXPIRED from listinvoices
#   stop          exits the loop
set -uo pipefail
Q=/tmp/opencode/spike-queue
mkdir -p "$Q"
echo "payer up: watching $Q"

inr2() { timeout 60 ssh -o BatchMode=yes -o ConnectTimeout=10 inr2.cashu.exchange "$@"; }

while true; do
    for f in "$Q"/*.pay "$Q"/*.invoice "$Q"/*.check; do
        [ -e "$f" ] || continue
        id=$(basename "$f"); id="${id%%.*}"
        case "$f" in
            *.pay)
                inv=$(cat "$f")
                if inr2 "docker exec cln-swap-signet lightning-cli --network=signet pay $inv" >/dev/null 2>&1 \
                   || inr2 "docker exec cln-hub-signet lightning-cli --network=signet pay $inv" >/dev/null 2>&1; then
                    echo PAY_OK > "$f.result"
                else
                    echo PAY_FAIL > "$f.result"
                fi
                ;;
            *.invoice)
                read -r msat label <<< "$(cat "$f")"
                bolt=$(inr2 "docker exec cln-hub-signet lightning-cli --network=signet invoice $msat spike-$label spike 86400" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["bolt11"])' 2>/dev/null)
                echo "${bolt:-INVOICE_FAIL}" > "$f.result"
                ;;
            *.check)
                label=$(cat "$f")
                st=$(inr2 "docker exec cln-hub-signet lightning-cli --network=signet listinvoices spike-$label" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['invoices'][0]['status'])" 2>/dev/null)
                echo "${st:-CHECK_FAIL}" > "$f.result"
                ;;
        esac
        rm -f "$f"
        echo "$(date +%H:%M:%S) handled $id -> $(cat "$f.result" 2>/dev/null)"
    done
    [ -f "$Q/stop" ] && { echo "payer stopping"; rm -f "$Q/stop"; exit 0; }
    sleep 2
done
