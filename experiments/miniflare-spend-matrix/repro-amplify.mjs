// S8 characterization: duplicate proof in one swap — amplification probe.
// Question: does the mint CREDIT the duplicated input twice (unbacked issuance)
// or dedup by Y (benign)? Inputs [p,p] (one 8-sat proof), outputs [8,8].
import { readdirSync, readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const CF = '/root/src/cashu-cf';
const { Miniflare } = await import(CF + '/node_modules/miniflare/dist/src/index.js');
const { Wallet, Mint, hashToCurve } = await import(CF + '/node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js');
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
const persist = mkdtempSync(join(tmpdir(), 's8d-'));
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
  const Y = bytesToHex(hashToCurve(new TextEncoder().encode(p.secret)).toBytes(true));

  // variant (a): inputs [p,p], outputs [8,8] — amplification probe
  const outsA = [1, 2].map(i => ({ amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: keysetId }));
  const a = await raw(mf_dispatch_path('/v1/swap'), { inputs: [p, p], outputs: outsA });
  const aSigs = (a.body?.signatures ?? []).map(s => Number(s.amount));
  console.log('VARIANT-A (inputs x2, outputs 8+8):', a.status, 'sigs:', JSON.stringify(aSigs), 'total:', aSigs.reduce((x, y) => x + y, 0));

  // checkstate of the duplicated proof's Y after variant A
  const cs = await raw('/v1/checkstate', { Ys: [Y] });
  console.log('CHECKSTATE Y after A:', JSON.stringify(cs.body?.states));
} finally {
  await mf.dispose();
  rmSync(persist, { recursive: true, force: true });
}

function mf_dispatch_path(p) { return p; }
