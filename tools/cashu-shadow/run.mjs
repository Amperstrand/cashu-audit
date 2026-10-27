#!/usr/bin/env node
// cashu-shadow — Diffy-style cross-implementation audit runner (ISSUE-129).
// Config: { cashu_cf_root, backends: {A, B}, proxy?: bool }
//   backend: { kind: "http"|"cf", url? } — cf = cashu-cf engine in miniflare.
// When proxy:true, an extra cashu-cf SHADOW worker fronts backend B and
// every B request is ALSO asserted byte-faithful through the proxy.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import * as nodeCrypto from 'node:crypto';

const cfgPath = process.argv[2];
if (!cfgPath) { console.error('usage: node run.mjs <config.json>'); process.exit(2); }
const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
const CF = cfg.cashu_cf_root;

const { cfTransport, httpTransport } = await import('./lib/transports.mjs');
const { makeMinter, identity } = await import('./lib/wire.mjs');
const { corpus } = await import('./scenarios/corpus.mjs');

process.env.CASHU_TS_PATH = join(CF, 'node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js');
const cashuTs = await import(join(CF, 'node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js'));
const noble = await import(join(CF, 'node_modules/@noble/hashes/utils.js'));
const { secp256k1, schnorr } = await import(join(CF, 'node_modules/@noble/curves/secp256k1.js'));
const { sha256: nobleSha256 } = await import(join(CF, 'node_modules/@noble/hashes/sha256.js'));
const w = makeMinter(cashuTs, noble);

async function backendTransport(def) {
  if (def.kind === 'http') return { t: httpTransport(def.url), dispose: async () => {}, name: def.name ?? def.url };
  const cf = await cfTransport(CF, def.options ?? {});
  return { t: cf.transport, dispose: cf.dispose, name: def.name ?? 'cashu-cf' };
}

const A = await backendTransport(cfg.backends.A);
const B0 = await backendTransport(cfg.backends.B);
const B = B0;
let proxy = null;
if (cfg.proxy) {
  const backendUrl = cfg.backends.B.kind === 'http' ? cfg.backends.B.url : null;
  if (!backendUrl) throw new Error('proxy mode requires backend B of kind http (the authoritative mint the proxy fronts)');
  const p = await cfTransport(CF, { shadow: true, backendUrl });
  proxy = { t: p.transport, dispose: p.dispose };
  // per-request faithfulness for PURE READS: every GET through B is
  // dual-sent via the proxy and asserted byte-identical. POSTs are NOT
  // dual-sent (double execution risk on stateful paths).
  const directGet = B0.t.bind(B0);
  B.t = async (path, method, body) => {
    const direct = await directGet(path, method, body);
    if ((method ?? 'GET') === 'GET') {
      try {
        const viaProxy = await proxy.t(path, method, body);
        const ok = viaProxy.status === direct.status && JSON.stringify(viaProxy.body) === JSON.stringify(direct.body);
        faithful.push({ label: 'dual-send', path, faithful: ok, proxyStatus: viaProxy.status, directStatus: direct.status });
      } catch (e) {
        faithful.push({ label: 'dual-send', path, faithful: 'error', error: String(e.message ?? e).slice(0, 60) });
      }
    }
    return direct;
  };
}

const rows = [];
const faithful = [];
if (proxy) {
  // proxy-faithfulness pass: deterministic probes must be byte-identical
  // through cashu-cf-as-proxy vs direct to the authoritative backend.
  const probes = [
    ['GET', '/v1/keys/decafbaddecafbad', undefined, 'keys-bogus'],
    ['POST', '/v1/checkstate', { Ys: ['02' + 'zz'.repeat(32)] }, 'checkstate-malformed'],
    ['GET', '/v1/info', undefined, 'info']
  ];
  for (const [method, path, body, label] of probes) {
    const direct = await B.t(path, method, body);
    const viaProxy = await proxy.t(path, method, body);
    const ok = viaProxy.status === direct.status && JSON.stringify(viaProxy.body) === JSON.stringify(direct.body);
    faithful.push({ label, path, faithful: ok, proxyStatus: viaProxy.status, directStatus: direct.status });
    console.log(`proxy-faithful ${label}: ${ok ? 'OK' : `DIVERGENT proxy=${viaProxy.status} direct=${direct.status}`}`);
  }
}
let state = {};
try {
  for (const scenario of corpus) {
    try {
      const results = await scenario.run({
        A, B, w, secp: secp256k1, schnorr, cashuTs, randomBytes: noble.randomBytes, bytesToHex: noble.bytesToHex,
        nobleSha256, nodeCrypto, state
      });
      for (const r of results) {
        if (r.__state) { state = { a: r.__state.a, b: r.__state.b }; continue; }
        rows.push({ scenario: scenario.name, label: r.label, a: identity(r.a), b: identity(r.b), note: r.note ?? '' });
        console.log(`${scenario.name} / ${r.label}\n  A: ${JSON.stringify(rows[rows.length - 1].a)}\n  B: ${JSON.stringify(rows[rows.length - 1].b)}${r.note ? '\n  note: ' + r.note : ''}`);
      }
    } catch (e) {
      rows.push({ scenario: scenario.name, label: 'ERROR', a: { status: 0, code: String(e.message).slice(0, 120) }, b: null });
      console.log(`${scenario.name} ERROR: ${String(e.message).slice(0, 140)}`);
    }
  }
} finally {
  await A.dispose(); await B.dispose(); if (proxy) await proxy.dispose();
}

// drift vs baseline (ISSUE-129): compare identity triples per scenario/label
const baselinePath = process.argv[3];
let drift = null;
if (baselinePath) {
  try {
    const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'));
    const bmap = new Map(baseline.rows.map(r => [r.scenario + '|' + r.label, r]));
    const drifts = [];
    for (const r of rows) {
      const b = bmap.get(r.scenario + '|' + r.label);
      if (!b) { drifts.push({ ...r, kind: 'NEW' }); continue; }
      const norm = (x) => x ? { status: x.status, code: x.code, error: x.error } : x;
      if (JSON.stringify(norm(b.a)) !== JSON.stringify(norm(r.a)) || JSON.stringify(norm(b.b)) !== JSON.stringify(norm(r.b))) {
        drifts.push({ scenario: r.scenario, label: r.label, kind: 'DRIFT', was: { a: b.a, b: b.b }, now: { a: r.a, b: r.b } });
      }
    }
    for (const b of baseline.rows) {
      if (!rows.some(r => r.scenario + '|' + r.label === b.scenario + '|' + b.label)) drifts.push({ ...b, kind: 'GONE' });
    }
    drift = drifts;
    console.log(`\ndrift vs baseline: ${drifts.length === 0 ? 'NONE — no drift' : drifts.length + ' finding(s)'}`);
    for (const d of drifts) console.log(`  ${d.kind}: ${d.scenario} / ${d.label}`);
  } catch (e) { console.log('baseline unavailable: ' + String(e.message ?? e).slice(0, 80)); }
}

const OUT = resolve('out');
mkdirSync(OUT, { recursive: true });
const ts = new Date().toISOString().replace(/[:.]/g, '-');
writeFileSync(join(OUT, `shadow-${ts}.json`), JSON.stringify({ config: cfg, rows, proxyFaithful: faithful, drift }, null, 2));
writeFileSync(join(OUT, 'latest-baseline.json'), JSON.stringify({ rows }, null, 2));
writeFileSync(join(OUT, `shadow-${ts}.md`), '# cashu-shadow run\n\n| scenario | label | A | B |\n|---|---|---|---|\n' +
  rows.map(r => `| ${r.scenario} | ${r.label} | ${r.a.status} ${JSON.stringify(r.a.code ?? r.a.error)} | ${r.b ? r.b.status + ' ' + JSON.stringify(r.b.code ?? r.b.error) : '-'} |`).join('\n') + '\n');
console.log(`\nreport: out/shadow-${ts}.{json,md}`);
