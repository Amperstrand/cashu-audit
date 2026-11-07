# Expiry cells recipe (needs a live nutshell arm with mgmt-RPC)

Arm (restart-safe, mnemonic-deterministic):

```sh
docker run -d --name battery-arm --network host \
  -e MINT_BACKEND_BOLT11_SAT=FakeWallet -e MINT_LISTEN_HOST=127.0.0.1 \
  -e MINT_LISTEN_PORT=28086 -e MINT_RATE_LIMIT=FALSE \
  -e MINT_PRIVATE_KEY=<hex> \
  -e MINT_RPC_SERVER_ENABLE=true -e MINT_RPC_SERVER_MUTUAL_TLS=false \
  -e MINT_RPC_SERVER_ADDR=127.0.0.1 -e MINT_RPC_SERVER_PORT=28096 \
  cashubtc/nutshell:0.21.0 poetry run mint   # 0.22.1 also verified
```

## Cells (frozen expectations in ../expected.json → expiry_cells)

1. **rotation_past_expiry**:
   `docker exec battery-arm poetry run mint-cli -h 127.0.0.1 -p 28096 -i next-keyset sat 0 8 $(date -d '1 hour ago' +%s)`
   → rotation accepted; `GET /v1/keysets` lists the new keyset `active: true`,
   `input_fee_ppk: 0`, `final_expiry` in the past. NOTE: the rotated id
   depends on the timestamp — `final_expiry` is in the NUT-02 id preimage.
2. **mint_signs_expired_active**: POST /v1/mint/bolt11 with outputs `id` =
   the expired keyset → 200 + signatures.
3. **cashu_ts_bound_mint**: `wallet.withKeyset(<expired>)` +
   `createMintQuoteBolt11` + `ops.mintBolt11` → proofs on the expired id
   (harness: private mirror nut18-live/harness/nut02-expiry.node.test.ts).
4. **cdk_cli_unprompted_mint**: `cdk-cli mint <url> 8 --unit sat` then
   `send -a 8 -u sat` → decode token, assert `i` == expired short id
   (cdk selection prefers the 0-ppk keyset). Covered upstream:
   cashubtc/cdk#2755 + PR #2800 (we stay silent; see registry row).

Frozen predictions of record: private mirror `private/nut18-live/`
PREDICTIONS-expiry-wallets.md (PE1–PE4) and
PREDICTIONS-ns0221-checkpoint.md (PR-A–D).
