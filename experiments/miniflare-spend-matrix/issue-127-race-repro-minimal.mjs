// ISSUE-127 lazy-boot ordering race — repro harness.
// Per iteration: fresh persist; boot A (legacy v1, minimal); boot B with
// KEYSET_VERSION=2; FIRST request = GET /v1/keysets. Record:
//   stale   = listing shows v1-active (pre-rotation incarnation won)
//   correct = listing shows v2-active (rotation ran before serving)
// plus whether listing #2 self-heals.
import { readdirSync, readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const CF = '/root/src/cashu-cf';
const { Miniflare } = await import(CF + '/node_modules/miniflare/dist/src/index.js');
const BUILD = resolve(CF, '.tmp-wrangler-build');

function opts(bindings, persist) {
  const modules = { 'index.js': { type: 'esm', contents: readFileSync(join(BUILD, 'index.js'), 'utf8') } };
  for (const f of readdirSync(BUILD)) {
    if (f.endsWith('.wasm')) modules[f] = { type: 'wasm', contents: new Uint8Array(readFileSync(join(BUILD, f))) };
  }
  const env = {};
  for (const [k, v] of Object.entries(bindings)) env[k] = { type: 'text', value: v };
  for (const [b, c] of Object.entries({ MINT_DO: 'MintDO', MINT_COORDINATOR: 'MintCoordinatorDO', MELT_QUOTE: 'QuoteDO' })) {
    env[b] = { type: 'durable-object', worker: 'w1', exportName: c };
  }
  return {
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
  };
}

const BASE = { MINT_PRIVATE_KEY: '1'.repeat(64), MINT_UNIT: 'sat', LIGHTNING_BACKEND: 'fakewallet', WEBSOCKETS_ENABLED: 'false' };
const A = { ...BASE, KEYSET_INPUT_FEE_PPK_BY_VERSION: '{"1":0}', KEYSET_DEFAULT_MAX_ORDER: '10' };
const B = { ...BASE, KEYSET_INPUT_FEE_PPK_BY_VERSION: '{"1":0,"2":10}', KEYSET_DEFAULT_MAX_ORDER: '10', KEYSET_VERSION: '2' };

const N = Number(process.env.N ?? 10);
let stale = 0, correct = 0, healed = 0;
for (let i = 0; i < N; i++) {
  const persist = mkdtempSync(join(tmpdir(), `race-${i}-`));
  try {
    const mf1 = new Miniflare(opts(A, persist));
    await (await mf1.dispatchFetch('https://x/v1/keys')).text();
    await mf1.dispose();

    const mf2 = new Miniflare(opts(B, persist));
    const l1 = await (await mf2.dispatchFetch('https://x/v1/keysets')).json();
    const l2 = await (await mf2.dispatchFetch('https://x/v1/keysets')).json();
    await mf2.dispose();
    const first = l1.keysets?.find(k => k.active)?.id;
    const second = l2.keysets?.find(k => k.active)?.id;
    const v1 = l1.keysets?.[0]?.id;
    const isStale = first === v1;
    if (isStale) stale++; else correct++;
    if (isStale && second !== v1) healed++;
    console.log(`run ${i + 1}: first-active=${String(first).slice(0, 8)} ${isStale ? 'STALE' : 'correct'}; second-active=${String(second).slice(0, 8)} ${second === v1 ? 'still-stale' : 'healed'}`);
  } finally {
    rmSync(persist, { recursive: true, force: true });
  }
}
console.log(`\nRESULT: ${N} runs — stale-first=${stale} correct-first=${correct} (self-healed-on-2nd=${healed})`);
