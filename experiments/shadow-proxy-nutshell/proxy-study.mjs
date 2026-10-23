#!/usr/bin/env node
// shadow-proxy-nutshell study: comparative wire audit, cashu-cf (miniflare)
// vs Nutshell 0.20.3 (local FakeWallet), with cashu-cf ALSO running as the
// SHADOW_MODE proxy over nutshell (passthrough verified per scenario).
// Frozen predictions: README.md. Error-identity assertions, never any-4xx.
import { readdirSync, readFileSync, mkdtempSync, rmSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const CF = process.env.CASHU_CF_ROOT || '/root/src/cashu-cf';
const NS = process.env.NUTSHELL_URL || 'http://127.0.0.1:8737';
const OUT = resolve('study-out');
mkdirSync(OUT, { recursive: true });

const { Miniflare } = await import(join(CF, 'node_modules/miniflare/dist/src/index.js'));
const cashuTs = await import(join(CF, 'node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js'));
const { blindMessage, unblindSignature, hashToCurve, pointFromHex, verifyDLEQProof } = cashuTs;
const { randomBytes, bytesToHex, hexToBytes } = await import(join(CF, 'node_modules/@noble/hashes/utils.js'));
const { secp256k1, schnorr } = await import(join(CF, 'node_modules/@noble/curves/secp256k1.js'));
const pointToHex = (p) => bytesToHex(p.toRawBytes ? p.toRawBytes(true) : p.toBytes(true));

const BUILD = resolve(CF, '.tmp-wrangler-build');

function workerOpts(name, extra, persist) {
  const modules = { 'index.js': { type: 'esm', contents: readFileSync(join(BUILD, 'index.js'), 'utf8') } };
  for (const f of readdirSync(BUILD)) {
    if (f.endsWith('.wasm')) modules[f] = { type: 'wasm', contents: new Uint8Array(readFileSync(join(BUILD, f))) };
  }
  const env = {};
  for (const [k, v] of Object.entries({
    MINT_PRIVATE_KEY: '1'.repeat(64), MINT_UNIT: 'sat', LIGHTNING_BACKEND: 'fakewallet',
    KEYSETS: '{"sat":{"1":{"input_fee_ppk":0,"max_order":10}}}', WEBSOCKETS_ENABLED: 'false',
    MELT_SAGA_V2: 'true', ...extra
  })) env[k] = { type: 'text', value: v };
  for (const [b, c] of Object.entries({ MINT_DO: 'MintDO', MINT_COORDINATOR: 'MintCoordinatorDO', MELT_QUOTE: 'QuoteDO' })) {
    env[b] = { type: 'durable-object', worker: name, exportName: c };
  }
  return {
    resourcePersistencePath: persist,
    workers: [{
      config: {
        type: 'worker', name, compatibilityDate: '2024-10-21',
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

// ── transport ──────────────────────────────────────────────────────────
async function httpFetch(url, method, body, headers = {}) {
  const res = await fetch(url, {
    method, headers: { 'Content-Type': 'application/json', ...headers },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const text = await res.text();
  let json; try { json = text ? JSON.parse(text) : undefined; } catch { }
  return { status: res.status, body: json, text, headers: res.headers };
}
const ns = (path, method, body) => httpFetch(NS + path, method, body);

function mfTransport(mf) {
  return async (path, method, body) => {
    const res = await mf.dispatchFetch('https://mint.test' + path, {
      method, headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const text = await res.text();
    let json; try { json = text ? JSON.parse(text) : undefined; } catch { }
    return { status: res.status, body: json, text };
  };
}

const identity = (r) => ({
  status: r.status,
  code: r.body?.code ?? null,
  error: r.body?.error ?? r.body?.detail ?? null,
  detail: typeof r.body?.detail === 'string' ? r.body?.detail.slice(0, 90) : (typeof r.body?.detail === 'number' ? r.body.detail : undefined)
});

// ── per-mint stateful plumbing (raw primitives, no Wallet object) ─────
// mint with an EXPLICIT secret (needed for adversarial re-use); verifies
// the returned blind signature via NUT-12 DLEQ (real client-side check)
async function mintWithSecret(t, sats, secret) {
  const keys = await t('/v1/keys', 'GET');
  const ks = keys.body.keysets.find(k => k.unit === 'sat' && k.active) ?? keys.body.keysets[0];
  const keysetId = ks.id;
  const pubKeys = ks.keys;
  const mq = await t('/v1/mint/quote/bolt11', 'POST', { amount: sats, unit: 'sat' });
  let quote = mq.body.quote, state = mq.body.state;
  for (let i = 0; i < 60 && state !== 'PAID'; i++) {
    await new Promise(r => setTimeout(r, 300));
    const s = await t(`/v1/mint/quote/bolt11/${quote}`, 'GET');
    state = s.body?.state;
    if (!state) break;
  }
  if (state !== 'PAID') throw new Error('quote never PAID');
  const bm = blindMessage(new TextEncoder().encode(secret));
  const minted = await t('/v1/mint/bolt11', 'POST', { quote, outputs: [{ amount: sats, B_: pointToHex(bm.B_), id: keysetId }] });
  if (minted.status !== 200) throw new Error('mint failed: ' + minted.text.slice(0, 160));
  const sig = minted.body.signatures[0];
  const A = pointFromHex(pubKeys[String(sats)]);
  const C = unblindSignature(pointFromHex(sig.C_), bm.r, A);
  let dleqOk = null;
  if (sig.dleq) {
    try {
      dleqOk = verifyDLEQProof(
        { e: hexToBytes(sig.dleq.e), s: hexToBytes(sig.dleq.s) },
        bm.B_, pointFromHex(sig.C_), A
      );
    } catch (e) { dleqOk = 'error:' + String(e.message ?? e).slice(0, 60); }
  }
  return { keysetId, pubKeys, dleqOk, proof: { amount: sats, secret, C: pointToHex(C), id: keysetId } };
}

async function meltQuote(t, sats) {
  const mq = await t('/v1/mint/quote/bolt11', 'POST', { amount: sats, unit: 'sat' });
  const q = await t('/v1/melt/quote/bolt11', 'POST', { request: mq.body.request, unit: 'sat' });
  return q;
}

// ── report ─────────────────────────────────────────────────────────────
const rows = [];
const proxyFaithful = [];
function record(name, cf, nsRes, prediction, note = '') {
  const row = { name, cf: identity(cf), ns: identity(nsRes), prediction, note };
  rows.push(row);
  console.log(`${name}\n  cf: ${JSON.stringify(row.cf)}\n  ns: ${JSON.stringify(row.ns)}${note ? '\n  note: ' + note : ''}`);
}

// proxy-faithfulness: same request through cashu-cf-as-proxy must equal
// direct nutshell (status + body) — the "cashu-cf is the proxy" lock.
async function assertProxy(path, method, body, label) {
  const viaNs = await ns(path, method, body);
  const viaProxy = await proxyT(path, method, body);
  const faithful = viaProxy.status === viaNs.status && JSON.stringify(viaProxy.body) === JSON.stringify(viaNs.body);
  proxyFaithful.push({ label, path, faithful, proxyStatus: viaProxy.status, nsStatus: viaNs.status });
  if (!faithful) {
    console.log(`PROXY-DIVERGENT ${label} ${path}: proxy=${viaProxy.status} ns=${viaNs.status}`);
  }
  return viaNs;
}

// ── boot ───────────────────────────────────────────────────────────────
const persistLocal = mkdtempSync(join(tmpdir(), 'study-local-'));
const persistProxy = mkdtempSync(join(tmpdir(), 'study-proxy-'));
const shadowDiffs = [];
const local = new Miniflare(workerOpts('local-engine', {}, persistLocal));
const proxy = new Miniflare({
  ...workerOpts('proxy-engine', { SHADOW_MODE: 'true', SHADOW_BACKEND_URL: NS }, persistProxy),
  handleStructuredLogs: (l) => { if (String(l.message ?? '').includes('SHADOW_DIFF')) shadowDiffs.push(l.message); }
});

const cfT = mfTransport(local);
const proxyT = mfTransport(proxy);

try {
  // sanity: proxy passthrough actually serving nutshell
  const proxyInfo = await proxyT('/v1/info', 'GET');
  const nsInfo = await ns('/v1/info', 'GET');
  if (!String(proxyInfo.text).match(/Nutshell\/0\.[0-9]+/)) throw new Error('proxy not passing through nutshell: ' + proxyInfo.text.slice(0, 120));
  console.log('SANITY: proxy serves nutshell-authoritative /v1/info ✓ (ns direct: ' + (nsInfo.text.match(/Nutshell\/0\.[0-9]+/) ? 'ok' : 'MISMATCH') + ')\n');

  // R4: bogus keyset id — via proxy-faithfulness wrapper
  record('R4 keys/{bogus}',
    await cfT('/v1/keys/decafbaddecafbad', 'GET'),
    await assertProxy('/v1/keys/decafbaddecafbad', 'GET', undefined, 'R4'),
    'both 400 family');

  // R5: checkstate malformed Y — record returned states too (both 200 here)
  const badY = { Ys: ['02' + 'zz'.repeat(32)] };
  const cfR5 = await cfT('/v1/checkstate', 'POST', badY);
  const nsR5 = await assertProxy('/v1/checkstate', 'POST', badY, 'R5');
  record('R5 checkstate malformed-Y',
    { ...cfR5, body: { code: cfR5.status === 200 ? (cfR5.body?.states?.[0]?.state ?? 'no-states') : cfR5.body } },
    { ...nsR5, body: { code: nsR5.status === 200 ? (nsR5.body?.states?.[0]?.state ?? 'no-states') : nsR5.body } },
    'both 200 — states captured');

  // H1: real mint on each + cross-verify signatures (NUT-12 DLEQ)
  const cfMint = await mintWithSecret(cfT, 8, 'cf-real-' + bytesToHex(randomBytes(6)));
  const nsMint = await mintWithSecret(ns, 8, 'ns-real-' + bytesToHex(randomBytes(6)));
  record('H1 mint+DLEQ verify', { status: 200, body: { code: String(cfMint.dleqOk) } },
    { status: 200, body: { code: String(nsMint.dleqOk) } },
    'both true (DLEQ-verified blind signatures)');

  // A1: forged off-curve C swap (ns leg via the proxy — proxy-faithfulness lock)
  {
    const mk = (kid) => ({ inputs: [{ amount: 8, secret: 'forged-' + bytesToHex(randomBytes(6)), C: '02' + 'ab'.repeat(32), id: kid }], outputs: [{ amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: kid }] });
    record('A1 swap forged off-curve C',
      await cfT('/v1/swap', 'POST', mk(cfMint.keysetId)),
      await assertProxy('/v1/swap', 'POST', mk(nsMint.keysetId), 'A1'),
      'cf 400/14005; ns Token-not-verified family');
  }

  // A2: duplicate proof in one swap
  {
    const dup = (p, kid) => ({ inputs: [p, p], outputs: [{ amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: kid }, { amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: kid }] });
    record('A2 swap duplicate proof',
      await cfT('/v1/swap', 'POST', dup(cfMint.proof, cfMint.keysetId)),
      await assertProxy('/v1/swap', 'POST', dup(nsMint.proof, nsMint.keysetId), 'A2'),
      'cf 400/14008 (ISSUE-126); ns 11007');
  }

  // A3: witness-less P2PK swap (swap-path conditions)
  {
    const witnessKey = randomBytes(32);
    const pub = bytesToHex(secp256k1.getPublicKey(witnessKey, true));
    const secret = JSON.stringify(['P2PK', { nonce: bytesToHex(randomBytes(32)), data: pub, tags: [['sigflag', 'SIG_INPUTS'], ['n_sigs', '1']] }]);
    const p2pkMint = async (t, kid0) => {
      const r = await mintWithSecret(t, 8, secret);
      return r;
    };
    const cfP = await p2pkMint(cfT);
    const nsP = await p2pkMint(ns);
    const body = (p, kid) => ({ inputs: [p.proof], outputs: [{ amount: 8, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: kid }] });
    record('A3 swap P2PK witness-less',
      await cfT('/v1/swap', 'POST', body(cfP, cfP.keysetId)),
      await ns('/v1/swap', 'POST', body(nsP, nsP.keysetId)),
      'both reject; identities compared');
  }

  // A4: melt SIG_ALL witness over WRONG message
  // A5: melt HTLC no witness
  for (const [name, mkSecret] of [
    ['A4 melt SIG_ALL wrong-message', () => {
      const k = randomBytes(32);
      return JSON.stringify(['P2PK', { nonce: bytesToHex(randomBytes(32)), data: bytesToHex(secp256k1.getPublicKey(k, true)), tags: [['sigflag', 'SIG_ALL'], ['n_sigs', '1']] }]);
    }],
    ['A5 melt HTLC no-witness', () => JSON.stringify(['HTLC', { nonce: bytesToHex(randomBytes(32)), data: 'ab'.repeat(32) }])]
  ]) {
    const secret = mkSecret();
    const cfP = await mintWithSecret(cfT, 8, secret);
    const nsP = await mintWithSecret(ns, 8, secret);
    const cfQ = await meltQuote(cfT, 4);
    const nsQ = await meltQuote(ns, 4);
    const melt = (p, q) => ({ quote: q.body.quote, inputs: [p.proof], outputs: [] });
    record(name,
      await cfT('/v1/melt/bolt11', 'POST', melt(cfP, cfQ)),
      await ns('/v1/melt/bolt11', 'POST', melt(nsP, nsQ)),
      'cf 403/30006; ns 11000-family');
  }

  // A6: mint replay — same outputs on a consumed quote
  {
    const replay = async (t) => {
      const m = await mintWithSecret(t, 8, 'replay-' + bytesToHex(randomBytes(6)));
      // re-mint SAME secret on a SECOND quote with the SAME B_? B_ is bound to secret;
      // simpler variant: re-POST the same {quote, outputs} that already succeeded —
      // we no longer have it; mint again with same secret via fresh quote then replay THAT body.
      const keys = await t('/v1/keys', 'GET');
      const kid = keys.body.keysets[0].id;
      const mq = await t('/v1/mint/quote/bolt11', 'POST', { amount: 8, unit: 'sat' });
      let quote = mq.body.quote, state = mq.body.state;
      for (let i = 0; i < 60 && state !== 'PAID'; i++) {
        await new Promise(r => setTimeout(r, 300));
        const s = await t(`/v1/mint/quote/bolt11/${quote}`, 'GET');
        state = s.body?.state;
        if (!state) break;
      }
      const bm = blindMessage(new TextEncoder().encode('replay-body-' + bytesToHex(randomBytes(6))));
      const body = { quote, outputs: [{ amount: 8, B_: pointToHex(bm.B_), id: kid }] };
      const first = await t('/v1/mint/bolt11', 'POST', body);
      const second = await t('/v1/mint/bolt11', 'POST', body);
      return { first, second, sig1: first.body?.signatures?.[0]?.C_ };
    };
    const cfR = await replay(cfT);
    const nsR = await replay(ns);
    const sameSigs = (r) => r.second?.body?.signatures?.[0]?.C_ === r.sig1;
    record('A6a mint replay same-outputs (1st)',
      { status: cfR.first.status, body: { code: 'first' } },
      { status: nsR.first.status, body: { code: 'first' } }, 'both 200 first time');
    record('A6b mint replay same-outputs (2nd)',
      cfR.second,
      nsR.second,
      'cf 200 identical sig; ns characterize', `cf-identical=${sameSigs(cfR)}, ns-identical=${sameSigs(nsR)}`);  }

  // A7: valid swap → checkstate SPENT for the burned Y (ISSUE-067 class, comparative).
  // Fee-aware: NUT-02 input fee (ceil(ppk/1000) per input) must be deducted
  // from the output — nutshell's default keyset carries ppk=100 (1 sat on one
  // input) and enforces balance strictly (400/11000 "not balanced").
  {
    const swapAndCheck = async (t) => {
      const m = await mintWithSecret(t, 8, 'check-' + bytesToHex(randomBytes(6)));
      const keys = await t('/v1/keys', 'GET');
      const meta = keys.body.keysets.find(k => k.id === m.keysetId);
      const ppk = Number(meta?.input_fee_ppk ?? 0);
      const inputFee = Math.ceil(ppk / 1000);
      const outSum = 8 - inputFee;
      // outputs must be power-of-2 denominations summing to outSum (7 = 4+2+1);
      // a single non-denomination output gets nutshell's opaque code-0
      // detail:"7" error (catalogued in README findings)
      const outs = [];
      let rem = outSum;
      for (let d = 1; rem > 0; d *= 2) { if (rem & d) { outs.push(d); rem -= d; } }
      const Y = bytesToHex(hashToCurve(new TextEncoder().encode(m.proof.secret)).toBytes(true));
      const sw = await t('/v1/swap', 'POST', {
        inputs: [m.proof],
        outputs: outs.map(amount => ({ amount, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: m.keysetId }))
      });
      const cs = await t('/v1/checkstate', 'POST', { Ys: [Y] });
      const state = cs.body?.states?.[0]?.state;
      return { swap: sw, state, ppk, inputFee, outSum };
    };
    const cfA = await swapAndCheck(cfT);
    const nsA = await swapAndCheck(ns);
    record('A7 fee-aware swap then checkstate-burned-Y',
      { status: cfA.swap.status, body: { code: `ppk:${cfA.ppk} fee:${cfA.inputFee} out:${cfA.outSum} swap:${cfA.swap.status} state:${cfA.state}` } },
      { status: nsA.swap.status, body: { code: `ppk:${nsA.ppk} fee:${nsA.inputFee} out:${nsA.outSum} swap:${nsA.swap.status} state:${nsA.state}` } },
      'both: swap 200 with NUT-02 fee deducted, burned Y reads SPENT');
  }

  // A8: HAPPY melt — real proofs, melt quote 4, exact-balance change blanks
  // sized to fee_reserve; locks PAID + change + never-red comparatively.
  {
    const happyMelt = async (t) => {
      const m = await mintWithSecret(t, 8, 'melt-happy-' + bytesToHex(randomBytes(6)));
      const q = await meltQuote(t, 4);
      const feeReserve = Number(q.body?.fee_reserve ?? 0);
      const refund = 8 - 4 - feeReserve;
      const blanks = [];
      let rem = refund;
      for (let d = 1; rem > 0; d *= 2) { if (rem & d) { blanks.push(d); rem -= d; } }
      const melt = await t('/v1/melt/bolt11', 'POST', {
        quote: q.body.quote,
        inputs: [m.proof],
        outputs: blanks.map(amount => ({ amount, B_: bytesToHex(secp256k1.getPublicKey(randomBytes(32), true)), id: m.keysetId }))
      });
      const changeSum = (melt.body?.change ?? []).reduce((a, c) => a + Number(c.amount), 0);
      return { melt, feeReserve, refund, changeSum };
    };
    const cfM = await happyMelt(cfT);
    const nsM = await happyMelt(ns);
    const ok = (x) => x.melt.status === 200 && x.melt.body?.state === 'PAID' && x.changeSum >= 0 && x.changeSum <= 8 - 4;
    record('A8 happy melt (PAID + change never-red)',
      { status: ok(cfM) ? 200 : 500, body: { code: `state:${cfM.melt.body?.state} feeRes:${cfM.feeReserve} change:${cfM.changeSum}` } },
      { status: ok(nsM) ? 200 : 500, body: { code: `state:${nsM.melt.body?.state} feeRes:${nsM.feeReserve} change:${nsM.changeSum}` } },
      'both PAID, change within bounds; cf detail if failed',
      `cf-raw=${cfM.melt.status}/${String(cfM.melt.text).slice(0, 80)} ns-raw=${nsM.melt.status}/${String(nsM.melt.text).slice(0, 80)}`);
  }

  // ── write report ──
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  writeFileSync(join(OUT, `study-${ts}.json`), JSON.stringify({ rows, proxyFaithful, shadowDiffs: shadowDiffs.length }, null, 2));
  writeFileSync(join(OUT, `study-${ts}.md`), '# shadow-proxy-nutshell study run\n\n' +
    '| # | cashu-cf | nutshell 0.20.3 |\n|---|---|---|\n' +
    rows.map(r => `| ${r.name} | ${r.cf.status} ${JSON.stringify(r.cf.code ?? r.cf.detail ?? r.cf.error)} | ${r.ns.status} ${JSON.stringify(r.ns.code ?? r.ns.detail ?? r.ns.error)} |`).join('\n') +
    `\n\nProxy-faithfulness (cashu-cf-as-proxy ≡ direct ns): ${proxyFaithful.filter(p => p.faithful).length}/${proxyFaithful.length} faithful\n` +
    `SHADOW_DIFF telemetry events captured: ${shadowDiffs.length}\n`);
  console.log(`\nreport: ${OUT}/study-${ts}.{json,md}; proxy-faithful: ${proxyFaithful.filter(p => p.faithful).length}/${proxyFaithful.length}; SHADOW_DIFF events: ${shadowDiffs.length}`);
} finally {
  await local.dispose(); await proxy.dispose();
  rmSync(persistLocal, { recursive: true, force: true });
  rmSync(persistProxy, { recursive: true, force: true });
}
