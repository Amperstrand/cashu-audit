#!/usr/bin/env bash
# Battery cell: cdk payload-parse column vs expected.json (exact identities).
# Env: CDK_CHECKOUT (default /root/src/upstream-cache/cdk @ v0.18.2),
#      CDK_TARGET (default /tmp/opencode/cdk-target-dbg), FIXTURES dir.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
CDK_CHECKOUT="${CDK_CHECKOUT:-/root/src/upstream-cache/cdk}"
CDK_TARGET="${CDK_TARGET:-/tmp/opencode/cdk-target-dbg}"
FIXTURES="${FIXTURES:-$HERE/fixtures}"

cp "$HERE/harness/nut18_payload_probe.rs" "$CDK_CHECKOUT/crates/cashu/examples/"
(cd "$CDK_CHECKOUT" && nice -n 10 cargo build -p cashu --example nut18_payload_probe -j 2 \
  --target-dir "$CDK_TARGET") >/dev/null

"$CDK_TARGET/debug/examples/nut18_payload_probe" "$FIXTURES"/payload_*.json \
  | tee /tmp/opencode/cdk_parse_out.txt || true   # intended FAILs exit 1

python3 "$HERE/runners/check_expected.py" cdk /tmp/opencode/cdk_parse_out.txt \
  "$HERE/expected.json"
