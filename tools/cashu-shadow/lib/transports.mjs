// cashu-shadow transports: plain HTTP, cashu-cf-in-miniflare (the engine),
// and cashu-cf-as-proxy (SHADOW_MODE passthrough — the proxy-faithful leg).
import { readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

export function httpTransport(base) {
  return async (path, method, body) => {
    const res = await fetch(base + path, {
      method, headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const text = await res.text();
    let json; try { json = text ? JSON.parse(text) : undefined; } catch {}
    return { status: res.status, body: json, text, headers: res.headers };
  };
}

export async function cfTransport(cfRoot, { shadow = false, backendUrl = null, persistDir } = {}) {
  const { Miniflare } = await import(join(cfRoot, 'node_modules/miniflare/dist/src/index.js'));
  const buildDir = resolve(cfRoot, '.tmp-wrangler-build');
  const modules = { 'index.js': { type: 'esm', contents: readFileSync(join(buildDir, 'index.js'), 'utf8') } };
  for (const f of readdirSync(buildDir)) {
    if (f.endsWith('.wasm')) modules[f] = { type: 'wasm', contents: new Uint8Array(readFileSync(join(buildDir, f))) };
  }
  const mkdtemp = (await import('node:fs')).mkdtempSync;
  const tmpdir = (await import('node:os')).tmpdir;
  const persist = persistDir ?? mkdtemp(join(tmpdir(), 'cashu-shadow-'));
  const name = shadow ? 'shadow-proxy' : 'local-engine';
  const env = {};
  for (const [k, v] of Object.entries({
    MINT_PRIVATE_KEY: '1'.repeat(64), MINT_UNIT: 'sat', LIGHTNING_BACKEND: 'fakewallet',
    KEYSETS: '{"sat":{"1":{"input_fee_ppk":0,"max_order":10}}}', WEBSOCKETS_ENABLED: 'false',
    MELT_SAGA_V2: 'true', ...(shadow && backendUrl ? { SHADOW_MODE: 'true', SHADOW_BACKEND_URL: backendUrl } : {})
  })) env[k] = { type: 'text', value: v };
  for (const [b, c] of Object.entries({ MINT_DO: 'MintDO', MINT_COORDINATOR: 'MintCoordinatorDO', MELT_QUOTE: 'QuoteDO' })) {
    env[b] = { type: 'durable-object', worker: name, exportName: c };
  }
  const mf = new Miniflare({
    resourcePersistencePath: persist,
    workers: [{
      config: {
        type: 'worker', name, compatibilityDate: '2024-10-21',
        manifest: { mainModule: 'index.js', modulesRoot: buildDir, modules }, env,
        exports: {
          MintDO: { type: 'durable-object', storage: 'sqlite' },
          MintCoordinatorDO: { type: 'durable-object', storage: 'sqlite' },
          QuoteDO: { type: 'durable-object', storage: 'sqlite' }
        }
      }
    }]
  });
  const transport = async (path, method, body) => {
    const res = await mf.dispatchFetch('https://mint.test' + path, {
      method, headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const text = await res.text();
    let json; try { json = text ? JSON.parse(text) : undefined; } catch {}
    return { status: res.status, body: json, text, headers: res.headers };
  };
  return { transport, dispose: () => mf.dispose(), persistDir: persist, purgeCache: () => mf.purgeCache() };
}
