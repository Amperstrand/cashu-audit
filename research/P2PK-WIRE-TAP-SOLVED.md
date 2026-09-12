# #192 P2PK Wire Capture: tap solved, spend-witness plumbing remains

*2026-09-12. Driver: experiments/wallet-mint-interop/drivers/node_flows.mjs*

## What was wrong (three stacked issues)

1. **v4.10.1 Wallet does NOT plumb `customRequest`** to its internal
   Mint (only the standalone `Mint` class accepts it). `requestFetch`
   exists only on unreleased main. The old driver hooked
   `wallet._mint._request` — an attribute that doesn't exist in v4
   (it's `wallet.mint` / `wallet._keyChain.mint`).
2. **The v4 API is builder-based**: `ops.mintBolt11(64)` without a
   quote and without `.run()` silently no-ops (no HTTP, no throw) —
   every "PASS" cell in historical v4 p2pk rows was a no-op.
3. The wire tap needed a graph-scan: mints live at `w.mint`,
   `w._keyChain.mint`, and inside `w.ops`.

## The fix (in the driver)

- Adaptive construction: try `{requestFetch}` (v5 future), then wrap
  `_request` on every Mint instance reachable from the wallet
  (deep scan with per-call cycle guard, `__tapped` marker).
- Correct v4 flow: `createMintQuote('bolt11', {amount, unit})` →
  `ops.mintBolt11(128, quote).run()` → `ops.send(64, proofs)
  .asP2PK({pubkey}).includeFees(true).run()`.
- Global `fetch` patch retained as a second capture layer.

## Proven capture (ns 0.20.3 mint, wire.ndjson)

```
POST /v1/mint/quote/bolt11  {"amount":128,"unit":"sat"}
POST /v1/mint/bolt11        {"outputs":[{"amount":"128","B_":...}]}
POST /v1/swap               {"inputs":[...],"outputs":[...7 denoms...]}
p2pk send: 2 locked proofs | keep: 5
```

Note: the P2PK LOCK is invisible on the wire by design (it lives in
the blinded secret). The WITNESS appears only when spending locked
proofs — that phase needs the wallet's P2PK signing plumbing
(`.privkey()` on the receive/spend builder did not attach a witness;
mint responds "Witness is missing for p2pk signature"). Remaining
work: one more pass on v4 KeyChain/privkey format.

## Historical impact

Every historical cashu-ts v4 "p2pk_send_spend PASS" cell was a no-op
pass (the builder was never run). The matrix needs a re-run with this
driver for v4 rows.

## RESOLVED (2026-09-12, later session): full witness capture

The spend-witness phase now works. Two remaining bugs:

1. **Key derivation must use the signer's library** (@noble/curves):
   the wallet's `signP2PKProofs` checks `derived_pubkey ∈ secret.pubkeys`
   and only WARNS on mismatch — a wrong pair silently skips signing
   ("Witness is missing"). Our JWK-based derivation didn't correspond
   to the pkcs8-tail privkey.
2. Call `wallet.signP2PKProofs(proofs, privHex)` directly, then swap
   the signed proofs (the builder's `.privkey()` path is offline-only).

Proven wire output (ns 0.20.3, cashu-ts 4.10.1):

```
swap input[0]:
  secret:  ["P2PK",{"nonce":"4032…","data":"03fc7a…"}]
  witness: "{\"signatures\":[\"b559f3c2…\"]}"   (string-encoded, 64-byte schnorr)
```

cashu-ts v4 emits the standard string-encoded witness (the shape cdk's
serde expects). #192 complete end-to-end: quote → blind mint → P2PK
lock (send) → witness spend — all captured per-cell.
