// ts4_refund_capture.mjs — capture cashu-ts v4's HTLC refund witness on the wire.
// Lock: P2PKBuilder().addHashlock().lockUntil(past).addRefundPubkey() -> send
// Spend: wallet.signP2PKProofs(locked, refundPriv) -> swap
// Prints the exact witness bytes + mint response.
import { randomBytes, createHash } from 'node:crypto';
import { appendFileSync, writeFileSync } from 'node:fs';

const MINT = process.env.MINT_URL;
const ART = process.env.ARTIFACT_DIR ?? '/tmp/art';
const log = (...a) => console.log(...a);

// wire tap (request-layer)
const mod = await import('@cashu/cashu-ts');
let secp;
try { secp = (await import('@noble/curves/secp256k1.js')).secp256k1; }
catch { secp = (await import('@noble/curves/secp256k1')).secp256k1; }

const privHex = randomBytes(32).toString('hex');
const pubHex = Buffer.from(secp.getPublicKey(Buffer.from(privHex, 'hex'), true)).toString('hex');

const wallet = new mod.Wallet(MINT, {});
await wallet.loadMint();
// tap AFTER load (fresh mints may appear)
const seen = new WeakSet();
const tap = (root, path, depth = 0) => {
  if (!root || typeof root !== 'object' || depth > 4 || seen.has(root)) return;
  seen.add(root);
  if (typeof root._request === 'function' && !root.__tapped) {
    const orig = root._request;
    root._request = async (opts) => {
      if (opts?.requestBody) {
        appendFileSync(`${ART}/wire.ndjson`, JSON.stringify({ via: path, endpoint: opts.endpoint, method: opts.method, body: String(typeof opts.requestBody === 'string' ? opts.requestBody : JSON.stringify(opts.requestBody)) }) + '\n');
      }
      return orig(opts);
    };
    root.__tapped = true;
  }
  for (const k of Object.keys(root)) {
    let v; try { v = root[k]; } catch { continue; }
    if (v && typeof v === 'object') tap(v, `${path}.${k}`, depth + 1);
  }
};
tap(wallet, 'w');

// 1. mint
let quote;
try { quote = await wallet.createMintQuote('bolt11', { amount: 64, unit: 'sat' }); }
catch { quote = await wallet.createMintQuote(64); }
await new Promise(r => setTimeout(r, 2500));
const proofs = await wallet.ops.mintBolt11(64, quote).run();
log('minted:', proofs.length);

// 2. HTLC lock with PAST locktime + our refund key
const preimage = randomBytes(32).toString('hex');
const hash = createHash('sha256').update(Buffer.from(preimage, 'hex')).digest('hex');
const past = Math.floor(Date.now() / 1000) - 1000;
const b = new mod.P2PKBuilder()
  .addHashlock(hash)
  .lockUntil(past)
  .addRefundPubkey(pubHex);
const opts = b.toOptions();
const { keep, send } = await wallet.ops.send(32, proofs).asP2PK(opts).includeFees(true).run();
log('locked:', (send ?? []).length, 'proofs');

// 3. refund spend: sign with our key, swap
const signed = wallet.signP2PKProofs(send, privHex);
log('signed with witness:', (signed ?? []).filter(p => p?.witness).length, '/', (send ?? []).length);
for (const p of (signed ?? [])) {
  log('witness bytes:', JSON.stringify(p.witness).slice(0, 120));
}
try {
  const res = await wallet.ops.send(30, signed).includeFees(true).run();
  log('REFUND SPENT:', (res?.send ?? []).length, 'new proofs');
} catch (e) {
  log('REFUND SPEND FAILED:', String(e).slice(0, 140));
}
tap(wallet, 'w'); // catch any fresh mint instances
