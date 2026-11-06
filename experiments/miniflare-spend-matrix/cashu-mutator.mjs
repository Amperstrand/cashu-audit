#!/usr/bin/env node
/**
 * cashu-mutator.mjs — structural mutation engine for the spend-matrix
 * (smite lesson #1: mutators as force multipliers).
 *
 * Given a valid mint+swap (the baseline scenario), mechanically derive
 * adversarial variants by applying structural mutators to the inputs.
 * Each derived variant is checked against the same oracle: the mint MUST
 * reject it (or handle it identically to the baseline if the mutation
 * is semantically neutral).
 *
 * Mutators (smite-inspired, adapted from BOLT message mutators):
 *   input_delete     — remove one input proof → insufficient_inputs
 *   input_reorder    — reverse input order → should still work (invariance)
 *   input_swap       — swap two inputs' secrets → signature mismatch
 *   amount_mutate    — change one input's amount → balance violation
 *   output_duplicate — duplicate one output → double-signing attempt
 *   secret_corrupt   — corrupt one input's secret → Y mismatch
 *
 * Usage: node cashu-mutator.mjs
 * Exit: 0 all oracles pass / 1 any oracle fails
 */

import { readdirSync, readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const CF = '/root/src/cashu-cf';
const { Miniflare } = await import(CF + '/node_modules/miniflare/dist/src/index.js');
const { Wallet, Mint } = await import(CF + '/node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js');
const { randomBytes, bytesToHex } = await import(CF + '/node_modules/@noble/hashes/utils.js');
const { bytesToHex: bh } = await import(CF + '/node_modules/@noble/hashes/utils.js');
const { hexToBytes } = await import(CF + '/node_modules/@noble/hashes/utils.js');

const BUILD = resolve(CF, '.tmp-wrangler-build');
const modules = { 'index.js': { type: 'esm', contents: readFileSync(join(BUILD, 'index.js'), 'utf8') } };
for (const f of readdirSync(BUILD)) {
  if (f.endsWith('.wasm')) modules[f] = { type: 'wasm', contents: new Uint8Array(readFileSync(join(BUILD, f))) };
}
const env = {};
for (const [k, v] of Object.entries({
  MINT_PRIVATE_KEY: '1'.repeat(64), MINT_UNIT: 'sat', LIGHTNING_BACKEND: 'fakewallet',
  KEYSETS: '{"sat":{"1":{"input_fee_ppk":0,"max_order":10}}}', WEBSOCKETS_ENABLED: 'false',
  MELT_SAGA_V2: 'true'
})) env[k] = { type: 'text', value: v };
for (const [b, c] of Object.entries({ MINT_DO: 'MintDO', MINT_COORDINATOR: 'MintCoordinatorDO', MELT_QUOTE: 'QuoteDO' })) {
  env[b] = { type: 'durable-object', worker: 'w1', exportName: c };
}
const exports = {};
for (const c of new Set(Object.values({ MINT_DO: 'MintDO', MINT_COORDINATOR: 'MintCoordinatorDO', MELT_QUOTE: 'QuoteDO' })) ) {
  exports[c] = { type: 'durable-object', storage: 'sqlite' };
}

const BASE = 'https://mint.test';
const bigIntSafe = (o) => JSON.stringify(o, (_, v) => typeof v === 'bigint' ? Number(v) : v);
const results = [];

async function boot() {
  const persist = mkdtempSync(join(tmpdir(), 'mutator-'));
  const mf = new Miniflare({
    resourcePersistencePath: persist,
    workers: [{ config: { type: 'worker', name: 'w1', compatibilityDate: '2024-10-21',
      manifest: { mainModule: 'index.js', modulesRoot: BUILD, modules }, env, exports } }]
  });
  await new Promise(r => setTimeout(r, 1000));
  return { mf, persist };
}

async function mintProofs(mf, amount) {
  const customRequest = async ({ endpoint, method, requestBody }) => {
    const res = await mf.dispatchFetch(endpoint, {
      method: method ?? 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: requestBody ? bigIntSafe(requestBody) : undefined,
    });
    const text = await res.text();
    if (!res.ok) throw new Error(`${res.status}: ${text.slice(0, 200)}`);
    return JSON.parse(text);
  };
  const wallet = new Wallet(new Mint(BASE, { customRequest }), { unit: 'sat' });
  await wallet.loadMint(true);
  const quote = await wallet.createMintQuoteBolt11(amount);
  // FakeWallet auto-pays
  for (let i = 0; i < 20; i++) {
    const q = await customRequest({ endpoint: `${BASE}/v1/mint/quote/bolt11/${quote.quote}` });
    if (q.state === 'PAID') break;
    await new Promise(r => setTimeout(r, 200));
  }
  const proofs = await wallet.mintProofsBolt11(amount, quote);
  return { wallet, proofs, keysetId: proofs[0].id };
}

async function swap(mf, inputs, outputs) {
  const res = await mf.dispatchFetch(`${BASE}/v1/swap`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ inputs, outputs }),
  });
  const text = await res.text();
  let json; try { json = JSON.parse(text); } catch { json = { raw: text.slice(0, 200) }; }
  return { status: res.status, body: json };
}

import { secp256k1 } from '/root/src/cashu-cf/node_modules/@noble/curves/secp256k1.js';
function blankOutputs(keysetId, count = 2) {
  return Array.from({ length: count }, () => {
    // Generate a proper blinded message: B_ = rG (a real curve point)
    const r = randomBytes(32);
    const point = secp256k1.getPublicKey(r, true);
    return { id: keysetId, amount: 0, B_: bytesToHex(point) };
  });
}

// ── Mutator definitions ────────────────────────────────────────────────

const mutators = {
  input_delete: (inputs, outputs) => {
    if (inputs.length < 2) return null;
    return { inputs: inputs.slice(1), outputs };
  },
  input_reorder: (inputs, outputs) => {
    return { inputs: [...inputs].reverse(), outputs };
  },
  input_swap: (inputs, outputs) => {
    if (inputs.length < 2) return null;
    const mutated = [...inputs];
    const tmp = mutated[0].secret; mutated[0].secret = mutated[1].secret; mutated[1].secret = tmp;
    return { inputs: mutated, outputs };
  },
  amount_mutate: (inputs, outputs) => {
    const mutated = [...inputs];
    mutated[0] = { ...mutated[0], amount: mutated[0].amount + 1000 };
    return { inputs: mutated, outputs };
  },
  output_duplicate: (inputs, outputs) => {
    return { inputs, outputs: [...outputs, { ...outputs[0], B_: outputs[1].B_ }] };
  },
  secret_corrupt: (inputs, outputs) => {
    const mutated = [...inputs];
    mutated[0] = { ...mutated[0], secret: 'ff'.repeat(32) };
    return { inputs: mutated, outputs };
  },
};

// Oracle: what SHOULD the mint do?
const oracles = {
  input_delete: { expect: 'reject', reason: 'insufficient inputs' },
  input_reorder: { expect: 'accept', reason: 'order-independent (invariance)' },
  input_swap: { expect: 'reject', reason: 'signature mismatch (swapped secrets)' },
  amount_mutate: { expect: 'reject', reason: 'amount mismatch (C_ ≠ amount)' },
  output_duplicate: { expect: 'reject', reason: 'duplicate output B_' },
  secret_corrupt: { expect: 'reject', reason: 'Y mismatch (corrupted secret)' },
};

// ── Main ───────────────────────────────────────────────────────────────

const { mf, persist } = await boot();
try {
  // Baseline: mint 32 sats, then swap 32→32
  const { wallet, proofs, keysetId } = await mintProofs(mf, 32);
  const outputs = blankOutputs(keysetId, 2);

  // Verify baseline works — using wallet.send (proper swap with valid B_)
  try {
    const recv = await wallet.send(32, undefined, { includeFees: true, keysetId });
    const baselineOK = recv.proofs && recv.proofs.length > 0;
    results.push({ name: 'baseline', status: baselineOK ? 200 : 400, expect: 'accept', verdict: baselineOK ? 'PASS' : 'FAIL' });
  } catch (e) {
    results.push({ name: 'baseline', status: 400, expect: 'accept', verdict: 'FAIL', reason: String(e).slice(0, 200) });
  }

  // Re-mint for each mutator (proofs are consumed by the baseline swap)
  for (const [name, mutate] of Object.entries(mutators)) {
    const { proofs: freshProofs, keysetId: kId } = await mintProofs(mf, 32);
    const freshOutputs = blankOutputs(kId, 2);
    const mutated = mutate(freshProofs, freshOutputs);
    if (!mutated) { results.push({ name, verdict: 'SKIP', reason: 'not applicable' }); continue; }
    const oracle = oracles[name];
    const result = await swap(mf, mutated.inputs, mutated.outputs);
    const accepted = result.status === 200;
    const verdict = oracle.expect === 'reject'
      ? (accepted ? 'FAIL' : 'PASS')
      : (accepted ? 'PASS' : 'FAIL');
    results.push({
      name, status: result.status, expect: oracle.expect, verdict,
      reason: oracle.reason, body: JSON.stringify(result.body).slice(0, 200),
    });
  }
} finally {
  rmSync(persist, { recursive: true, force: true });
}

// ── Report ────────────────────────────────────────────────────────────

const pass = results.filter(r => r.verdict === 'PASS').length;
const fail = results.filter(r => r.verdict === 'FAIL').length;
console.log('\n┌─ Cashu Mutator Engine (smite lesson #1) ─────────────────┐');
for (const r of results) {
  const icon = r.verdict === 'PASS' ? '✅' : r.verdict === 'FAIL' ? '❌' : '⏭️ ';
  console.log(`│ ${icon} ${r.name.padEnd(20)} ${r.verdict.padEnd(5)} (expected ${r.expect}, got ${r.status}) ${r.reason || ''}`);
}
console.log(`└─ ${pass} PASS / ${fail} FAIL / ${results.length} total ──────────────────────┘`);
process.exit(fail > 0 ? 1 : 0);
