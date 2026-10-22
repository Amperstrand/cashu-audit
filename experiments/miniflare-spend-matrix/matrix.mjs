#!/usr/bin/env node
// miniflare-spend-matrix — adversarial + race inputs at cashu-cf spend
// endpoints against a REAL local worker (wrangler bundle + DOs, miniflare@5
// workers[].config shape). Frozen predictions: see README.md.
import { readdirSync, readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir, homedir } from 'node:os';

const CF_ROOT = process.env.CASHU_CF_ROOT || resolve(homedir(), 'src/cashu-cf');
const BUILD_DIR = resolve(CF_ROOT, '.tmp-wrangler-build');

const { Miniflare } = await import(join(CF_ROOT, 'node_modules/miniflare/dist/src/index.js'));
const cashuTs = await import(join(CF_ROOT, 'node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js'));
const { Wallet, Mint, blindMessage, unblindSignature, hashToCurve, pointFromHex } = cashuTs;
const { secp256k1, schnorr } = await import(join(CF_ROOT, 'node_modules/@noble/curves/secp256k1.js'));
const { randomBytes, bytesToHex } = await import(join(CF_ROOT, 'node_modules/@noble/hashes/utils.js'));

const pointToHex = (p) => bytesToHex(p.toRawBytes ? p.toRawBytes(true) : p.toBytes(true));

const BASE = 'https://mint.test';
const BASE_BINDINGS = {
  MINT_PRIVATE_KEY: '1'.repeat(64),
  MINT_UNIT: 'sat',
  LIGHTNING_BACKEND: 'fakewallet',
  KEYSETS: '{"sat":{"1":{"input_fee_ppk":0,"max_order":10}}}',
  WEBSOCKETS_ENABLED: 'false',
  MELT_SAGA_V2: 'true'
};

function bootWorker(name, bindings = {}) {
  const persistDir = mkdtempSync(join(tmpdir(), `matrix-${name}-`));
  const modules = { 'index.js': { type: 'esm', contents: readFileSync(join(BUILD_DIR, 'index.js'), 'utf8') } };
  for (const f of readdirSync(BUILD_DIR)) {
    if (f.endsWith('.wasm')) modules[f] = { type: 'wasm', contents: new Uint8Array(readFileSync(join(BUILD_DIR, f))) };
  }
  const env = {};
  for (const [k, v] of Object.entries({ ...BASE_BINDINGS, ...bindings })) env[k] = { type: 'text', value: v };
  for (const [b, c] of Object.entries({ MINT_DO: 'MintDO', MINT_COORDINATOR: 'MintCoordinatorDO', MELT_QUOTE: 'QuoteDO' })) {
    env[b] = { type: 'durable-object', worker: name, exportName: c };
  }
  const mf = new Miniflare({
    resourcePersistencePath: persistDir,
    workers: [{
      config: {
        type: 'worker', name, compatibilityDate: '2024-10-21',
        manifest: { mainModule: 'index.js', modulesRoot: BUILD_DIR, modules },
        env,
        exports: {
          MintDO: { type: 'durable-object', storage: 'sqlite' },
          MintCoordinatorDO: { type: 'durable-object', storage: 'sqlite' },
          QuoteDO: { type: 'durable-object', storage: 'sqlite' }
        }
      }
    }]
  });
  return { mf, persistDir };
}

const jsonSafe = (v) => (v === undefined ? undefined : JSON.stringify(v, (_, x) => (typeof x === 'bigint' ? Number(x) : x)));

async function raw(mf, path, body, method = 'POST') {
  const res = await mf.dispatchFetch(BASE + path, {
    method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  });
  const text = await res.text();
  let json; try { json = text ? JSON.parse(text) : undefined; } catch { json = undefined; }
  return { status: res.status, body: json, text };
}

function walletOn(mf) {
  const customRequest = async ({ endpoint, method, requestBody }) => {
    const res = await mf.dispatchFetch(endpoint, {
      method: method ?? 'GET', headers: { 'Content-Type': 'application/json' }, body: jsonSafe(requestBody)
    });
    const text = await res.text();
    let json; try { json = text ? JSON.parse(text) : undefined; } catch { json = undefined; }
    if (!res.ok) throw new Error(String(json?.detail ?? json?.error ?? text));
    return json;
  };
  return new Wallet(new Mint(BASE, { customRequest }), { unit: 'sat' });
}

async function mintReal(mf, sats) {
  const wallet = walletOn(mf);
  await wallet.loadMint(true);
  const quote = await wallet.createMintQuoteBolt11(sats);
  let paid = quote;
  const dl = Date.now() + 8000;
  while (paid.state !== 'PAID' && Date.now() < dl) {
    paid = { ...quote, ...(await wallet.checkMintQuoteBolt11(quote)) };
    await new Promise(r => setTimeout(r, 50));
  }
  if (paid.state !== 'PAID') throw new Error('quote never PAID');
  const proofs = await wallet.mintProofsBolt11(sats, paid);
  return { wallet, proofs: proofs.map(p => ({ amount: Number(p.amount), secret: p.secret, C: p.C, id: String(p.id) })), keysetId: String(proofs[0].id) };
}

// self-blinded swap output for `sats` with an explicit secret is NOT needed —
// the mint signs any valid point; scenarios construct their own B_.

const results = [];
const check = (name, pass, detail) => { results.push({ name, pass, detail }); console.log(`${pass ? 'PASS' : 'FAIL'}  ${name}  ${detail}`); };

async function meltQuoteFor(mf, sats) {
  const mq = await raw(mf, '/v1/mint/quote/bolt11', { amount: sats, unit: 'sat' });
  const q = await raw(mf, '/v1/melt/quote/bolt11', { request: mq.body.request, unit: 'sat' });
  if (q.status !== 200) throw new Error('melt quote failed: ' + q.text);
  return q.body;
}

// ── Control ──
{
  const { mf, persistDir } = bootWorker('ctl');
  try {
    const { proofs } = await mintReal(mf, 8);
    check('CONTROL mint real proofs', proofs.length > 0, `${proofs.length} proof(s), ${proofs.map(p => p.amount).join('+')}`);
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S1: swap forged off-curve C ──
{
  const { mf, persistDir } = bootWorker('s1');
  try {
    const { proofs, keysetId } = await mintReal(mf, 8);
    const dummyOut = { amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: keysetId };
    const forged = { amount: 8, secret: bytesToHex(randomBytes(32)), C: '02' + 'ab'.repeat(32), id: keysetId };
    const r = await raw(mf, '/v1/swap', { inputs: [forged], outputs: [dummyOut] });
    const ok = r.status === 400 && r.body?.error === 'invalid_request' && String(r.body?.code) === '14005' && /Proof verification failed at index 0/i.test(String(r.body?.detail));
    check('S1 swap off-curve C rejected', ok, `status=${r.status} error=${r.body?.error} code=${r.body?.code} detail=${r.body?.detail}`);
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S2: swap ON-CURVE but wrong-signature C ──
{
  const { mf, persistDir } = bootWorker('s2');
  try {
    const { proofs, keysetId } = await mintReal(mf, 8);
    const wrongC = bytesToHex(secp256k1.getPublicKey(randomBytes(32), true));
    const input = { amount: 8, secret: bytesToHex(randomBytes(32)), C: wrongC, id: keysetId };
    const dummyOut = { amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: keysetId };
    const r = await raw(mf, '/v1/swap', { inputs: [input], outputs: [dummyOut] });
    const ok = r.status === 400 && r.body?.error === 'invalid_request' && String(r.body?.code) === '14005' && /Proof verification failed at index 0/i.test(String(r.body?.detail));
    check('S2 swap wrong-signature C rejected (swap identity 14005; 30003 is melt-only)', ok, `status=${r.status} error=${r.body?.error} code=${r.body?.code} detail=${r.body?.detail}`);
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S3: melt P2PK SIG_ALL witness over WRONG message ──
{
  const { mf, persistDir } = bootWorker('s3');
  try {
    const { proofs, keysetId } = await mintReal(mf, 8);
    const witnessKey = randomBytes(32);
    const witnessPub = bytesToHex(secp256k1.getPublicKey(witnessKey, true));
    const p2pkSecret = JSON.stringify(['P2PK', { nonce: bytesToHex(randomBytes(32)), data: witnessPub, tags: [['sigflag', 'SIG_ALL'], ['n_sigs', '1']] }]);
    const bm = blindMessage(new TextEncoder().encode(p2pkSecret));
    const sr = await raw(mf, '/v1/swap', {
      inputs: proofs.map(p => ({ amount: p.amount, secret: p.secret, C: p.C, id: p.id })),
      outputs: [{ amount: 8, B_: pointToHex(bm.B_), id: keysetId }]
    });
    if (sr.status !== 200) { check('S3 setup swap', false, sr.text.slice(0, 120)); }
    else {
      const sig = sr.body.signatures[0];
      const keysResp = await (await mf.dispatchFetch(`${BASE}/v1/keys/${keysetId}`)).json();
      const pubKeys = keysResp.keysets?.[0]?.keys ?? keysResp.keys;
      const A = pointFromHex(pubKeys[String(8)]);
      const C = unblindSignature(pointFromHex(sig.C_), bm.r, A);
      // schnorr witness over a WRONG message (not the quote-bound SIG_ALL message)
      const p2pkInput = { amount: 8, secret: p2pkSecret, C: pointToHex(C), id: keysetId, witness: { signatures: [bytesToHex(schnorr.sign(randomBytes(32), witnessKey))] } };
      const q = await meltQuoteFor(mf, 4);
      const r = await raw(mf, '/v1/melt', { quote: q.quote, inputs: [p2pkInput], outputs: [] });
      const ok = r.status === 403 && r.body?.code === '30006';
      check('S3 SIG_ALL wrong-message witness → 403/30006', ok, `status=${r.status} error=${r.body?.error} code=${r.body?.code} detail=${r.body?.detail}`);
    }
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S4: concurrent identical swaps (TOCTOU) ──
{
  const { mf, persistDir } = bootWorker('s4');
  try {
    const { proofs, keysetId } = await mintReal(mf, 8);
    const Y = bytesToHex(secp256k1.getPublicKey(randomBytes(32), true));
    const body = { inputs: proofs.map(p => ({ amount: p.amount, secret: p.secret, C: p.C, id: p.id })), outputs: [{ amount: 8, B_: Y, id: keysetId }] };
    const N = 16;
    const rs = await Promise.all(Array.from({ length: N }, () => raw(mf, '/v1/swap', body)));
    const oks = rs.filter(r => r.status === 200);
    const states = new Set(rs.filter(r => r.status !== 200).map(r => `${r.status}/${r.body?.code ?? r.body?.error}`));
    const sigSets = new Set(oks.map(r => JSON.stringify(r.body?.signatures)));
    const ok = oks.length === 1 && sigSets.size === 1;
    check('S4 race: exactly one swap succeeds', ok, `200s=${oks.length}/${N} err-identities=[${[...states].join('; ')}] distinct-sigs=${sigSets.size}`);
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S5: NUT-08 melt change accounting ──
{
  const { mf, persistDir } = bootWorker('s5');
  try {
    const { proofs, keysetId } = await mintReal(mf, 8);
    const q = await meltQuoteFor(mf, 4);
    const feeReserve = Number(q.fee_reserve ?? 0);
    // TWO blinded change outputs: refund 3 splits [2,1] — one blank per part
    // (settle.ts dust-truncates parts beyond the supplied blanks, with a
    // logged 'melt change truncated' warning)
    const blanks = ['matrix-change-a-', 'matrix-change-b-'].map(p => {
      const bm = blindMessage(new TextEncoder().encode(p + bytesToHex(randomBytes(8))));
      return { amount: 4, B_: pointToHex(bm.B_), id: keysetId };
    });
    const r = await raw(mf, '/v1/melt', {
      quote: q.quote,
      inputs: proofs.map(p => ({ amount: p.amount, secret: p.secret, C: p.C, id: p.id })),
      outputs: blanks
    });
    const changeSum = (r.body?.change ?? []).reduce((a, c) => a + Number(c.amount), 0);
    const paid = r.body?.state === 'PAID';
    const neverRed = paid && changeSum >= 8 - 4 - feeReserve && changeSum <= 8 - 4;
    check('S5 NUT-08 change never-red', r.status === 200 && neverRed, `status=${r.status} state=${r.body?.state} fee_reserve=${feeReserve} change_sum=${changeSum} change_len=${r.body?.change?.length} detail=${r.body?.detail}`);
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S6: concurrent identical MELTs (TOCTOU, ISSUE-049/080 class) ──
{
  const { mf, persistDir } = bootWorker('s6');
  try {
    const { proofs, keysetId } = await mintReal(mf, 8);
    const q = await meltQuoteFor(mf, 4);
    const blanks = ['s6-a-', 's6-b-'].map(p => {
      const bm = blindMessage(new TextEncoder().encode(p + bytesToHex(randomBytes(8))));
      return { amount: 4, B_: pointToHex(bm.B_), id: keysetId };
    });
    const body = { quote: q.quote, inputs: proofs.map(p => ({ amount: p.amount, secret: p.secret, C: p.C, id: p.id })), outputs: blanks };
    const N = 16;
    const rs = await Promise.all(Array.from({ length: N }, () => raw(mf, '/v1/melt', body)));
    const paid = rs.filter(r => r.status === 200 && r.body?.state === 'PAID');
    const preimages = new Set(paid.map(r => r.body?.preimage));
    const errIds = new Set(rs.filter(r => !(r.status === 200 && r.body?.state === 'PAID')).map(r => `${r.status}/${r.body?.code ?? r.body?.error}`));
    const ok = paid.length === 1 && preimages.size === 1;
    check('S6 race: exactly one melt PAID', ok, `PAID=${paid.length}/${N} preimages=${preimages.size} err-identities=[${[...errIds].join('; ')}]`);
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S7: checkstate SPENT after successful swap (ISSUE-067 class) ──
{
  const { mf, persistDir } = bootWorker('s7');
  try {
    const { wallet, proofs, keysetId } = await mintReal(mf, 8);
    const Y = bytesToHex(hashToCurve(new TextEncoder().encode(proofs[0].secret)).toBytes(true));
    const out = { amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: keysetId };
    const sr = await raw(mf, '/v1/swap', { inputs: proofs.map(p => ({ amount: p.amount, secret: p.secret, C: p.C, id: p.id })), outputs: [out] });
    if (sr.status !== 200) { check('S7 setup swap', false, sr.text.slice(0, 120)); }
    else {
      const r = await raw(mf, '/v1/checkstate', { Ys: [Y] });
      const state = r.body?.states?.[0]?.state;
      check('S7 checkstate SPENT after swap-burn', r.status === 200 && state === 'SPENT', `status=${r.status} state=${state} Y=${Y.slice(0, 12)}…`);
    }
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S8: same proof listed twice in one swap ──
{
  const { mf, persistDir } = bootWorker('s8');
  try {
    const { proofs, keysetId } = await mintReal(mf, 8);
    const p = proofs[0];
    const out = { amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: keysetId };
    const r = await raw(mf, '/v1/swap', { inputs: [p, p], outputs: [out] });
    const noSigs = !r.body?.signatures || r.body.signatures.length === 0;
    check('S8 duplicate proof in one swap rejected', r.status >= 400 && noSigs, `status=${r.status} error=${r.body?.error} code=${r.body?.code} detail=${r.body?.detail} sigs=${r.body?.signatures?.length}`);
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S9: mint replay on a consumed quote (double issuance lock) ──
{
  const { mf, persistDir } = bootWorker('s9');
  try {
    const { wallet, keysetId } = await mintReal(mf, 8);
    const q2 = await wallet.createMintQuoteBolt11(8);
    let paid2 = q2;
    const dl = Date.now() + 8000;
    while (paid2.state !== 'PAID' && Date.now() < dl) {
      paid2 = { ...q2, ...(await wallet.checkMintQuoteBolt11(q2)) };
      await new Promise(r => setTimeout(r, 50));
    }
    const bm = blindMessage(new TextEncoder().encode('s9-replay-secret'));
    const body = { quote: paid2.quote, outputs: [{ amount: 8, B_: pointToHex(bm.B_), id: keysetId }] };
    const first = await raw(mf, '/v1/mint/bolt11', body);
    // (a) SAME outputs re-POSTed: restore/idempotency replay — 200 with the
    // IDENTICAL signature (deterministic k·B_; value-neutral by design)
    const second = await raw(mf, '/v1/mint/bolt11', body);
    const sameSigs = JSON.stringify(second.body?.signatures) === JSON.stringify(first.body?.signatures);
    const okA = first.status === 200 && second.status === 200 && sameSigs;
    check('S9a same-output replay → 200 IDENTICAL signatures (no new value)', okA, `first=${first.status} second=${second.status} identical=${sameSigs}`);
    // (b) same quote, DIFFERENT output: re-issuance attempt → must reject
    const bm2 = blindMessage(new TextEncoder().encode('s9-replay-secret-2'));
    const third = await raw(mf, '/v1/mint/bolt11', { quote: paid2.quote, outputs: [{ amount: 8, B_: pointToHex(bm2.B_), id: keysetId }] });
    const okB = third.status === 400 && String(third.body?.code) === '20002';
    check('S9b different-output re-mint on consumed quote → 400/20002', okB, `status=${third.status} error=${third.body?.error} code=${third.body?.code}`);
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

// ── S10: melt HTLC (NUT-14) conditioned proof WITHOUT preimage witness ──
{
  const { mf, persistDir } = bootWorker('s10');
  try {
    const { proofs, keysetId } = await mintReal(mf, 8);
    const { createHash } = await import('node:crypto');
    const preimage = randomBytes(32);
    const hashlock = createHash('sha256').update(preimage).digest('hex');
    const htlcSecret = JSON.stringify(['HTLC', { nonce: bytesToHex(randomBytes(32)), data: hashlock }]);
    const bm = blindMessage(new TextEncoder().encode(htlcSecret));
    const sr = await raw(mf, '/v1/swap', {
      inputs: proofs.map(p => ({ amount: p.amount, secret: p.secret, C: p.C, id: p.id })),
      outputs: [{ amount: 8, B_: pointToHex(bm.B_), id: keysetId }]
    });
    if (sr.status !== 200) { check('S10 setup swap', false, sr.text.slice(0, 120)); }
    else {
      const sig = sr.body.signatures[0];
      const keysResp = await (await mf.dispatchFetch(`${BASE}/v1/keys/${keysetId}`)).json();
      const pubKeys = keysResp.keysets?.[0]?.keys ?? keysResp.keys;
      const A = pointFromHex(pubKeys[String(8)]);
      const C = unblindSignature(pointFromHex(sig.C_), bm.r, A);
      const htlcInput = { amount: 8, secret: htlcSecret, C: pointToHex(C), id: keysetId };
      const q = await meltQuoteFor(mf, 4);
      const r = await raw(mf, '/v1/melt', { quote: q.quote, inputs: [htlcInput], outputs: [] });
      const ok = r.status === 403 && r.body?.code === '30006';
      check('S10 HTLC witness-less melt → 403/30006', ok, `status=${r.status} error=${r.body?.error} code=${r.body?.code} detail=${(r.body?.detail ?? '').slice(0, 80)}`);
    }
  } finally { await mf.dispose(); rmSync(persistDir, { recursive: true, force: true }); }
}

const fails = results.filter(r => !r.pass);
console.log(`\nmatrix: ${results.length - fails.length}/${results.length} PASS`);
process.exit(fails.length ? 1 : 0);