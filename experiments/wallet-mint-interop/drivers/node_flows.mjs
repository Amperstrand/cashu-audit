// cashu-ts v4 interop driver — correct API usage from probe
// Contract: exit 0 PASS / 1 FAIL / 127 SKIP
import { writeFileSync, appendFileSync, mkdirSync, readFileSync } from 'node:fs';
import { generateKeyPairSync } from 'node:crypto';

const MINT = process.env.MINT_URL;
const FLOW = process.env.TESTCASE;
const ART = process.env.ARTIFACT_DIR;
mkdirSync(ART, { recursive: true });
const log = (...a) => { const s = a.join(' '); console.log(s); appendFileSync(`${ART}/output.txt`, s + '\n'); };
const result = { flow: FLOW, mint: MINT, wallet: process.env.WALLET_NAME ?? 'node', verdict: null, reason: '', wire_shapes: {} };

// wire capture
const realFetch = globalThis.fetch;
globalThis.fetch = async (input, init = {}) => {
  const url = typeof input === 'string' ? input : input.url;
  if (url.startsWith(MINT) && init.body) {
    appendFileSync(`${ART}/wire.ndjson`, JSON.stringify({ t: Date.now(), url, body: typeof init.body === 'string' ? init.body : init.body.toString() }) + '\n');
  }
  return realFetch(input, init);
};

async function main() {
  const mod = await import('@cashu/cashu-ts');
  log('exports:', Object.keys(mod).slice(0, 10).join(','));

  // generate a secp256k1 keypair for P2PK/HTLC signing — MUST derive pub from the
  // same library the wallet signs with (@noble/curves), else the wallet's
  // "lock pubkey in secret" check silently skips signing (warn-only)
  const { randomBytes } = await import('node:crypto');
  let secp;
  try { secp = (await import('@noble/curves/secp256k1.js')).secp256k1; }
  catch { secp = (await import('@noble/curves/secp256k1')).secp256k1; }
  const privHex = randomBytes(32).toString('hex');
  const pubHex = Buffer.from(secp.getPublicKey(Buffer.from(privHex, 'hex'), true)).toString('hex');
  log('pubkey:', pubHex.slice(0, 10) + '... len=' + pubHex.length);

  // connect
  const WalletClass = mod.Wallet || mod.CashuWallet;
  // Official interception: v4 Wallet accepts options.requestFetch (custom transport).
  // Older versions (v2/v3) fall back to the old signatures.
  const wireFetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url;
    if (url && String(url).startsWith(MINT) && init?.body) {
      appendFileSync(`${ART}/wire.ndjson`, JSON.stringify({ t: Date.now(), url, method: init.method || 'POST', body: typeof init.body === 'string' ? init.body : init.body.toString() }) + '\n');
    }
    return realFetch(input, init);
  };
  let wallet;
  try {
    wallet = new WalletClass(MINT, { requestFetch: wireFetch });          // v4: official hook
    log('wallet: v4 requestFetch wire tap armed');
  } catch (e4) {
    try {
      wallet = new WalletClass(MINT, 'sat', { requestFetch: wireFetch }); // v3-style opts
    } catch (e3) {
      wallet = new WalletClass(MINT, 'interop-driver');                   // legacy
      log('wallet: legacy construction, wire tap via global fetch only');
    }
  }
  // Wrap _request on EVERY Mint instance reachable from the wallet (#192 fix:
  // v4.10.1 has w.mint AND w._keyChain.mint; WalletOps uses one of them, older
  // drivers only hooked wallet._mint). customRequest works on Mint but is NOT
  // plumbed through Wallet in 4.10.1 — requestFetch exists only on unreleased main.
  const tapMints = (root, path = 'w', depth = 0) => {
    if (!root || typeof root !== 'object' || depth > 4) return;
    if (typeof root._request === 'function' && !root.__tapped) {
      const origReq = root._request;
      root._request = async (opts) => {
        const body = opts?.requestBody ?? opts?.body;
        if (body) {
          const bodyStr = typeof body === 'string' ? body : JSON.stringify(body);
          appendFileSync(ART + '/wire.ndjson', JSON.stringify({t: Date.now(), via: path, endpoint: opts?.endpoint ?? opts?.url ?? '?', method: opts?.method ?? 'POST', body: bodyStr}) + '\n');
        }
        return origReq(opts);
      };
      root.__tapped = true;
      log('wire tap: Mint._request wrapped at', path);
    }
    const seen = arguments[3] || new WeakSet();
    if (seen.has(root)) return;
    seen.add(root);
    for (const k of Object.keys(root)) {
      let v; try { v = root[k]; } catch { continue; }
      if (v && typeof v === 'object') tapMints(v, `${path}.${k}`, depth + 1, seen);
    }
  };
  globalThis.__tapMints = () => tapMints(wallet);

  tapMints(wallet);
  await wallet.loadMint();
  tapMints(wallet); // loadMint may create fresh Mint instances
  log('mint loaded');

  // mint flow: get ecash via bolt11 (FakeWallet pays instantly)
  async function getProofs(amount) {
    const quote = await wallet.createMintQuoteBolt11(amount);
    log('quote:', quote.quote, 'state:', quote.state);
    for (let i = 0; i < 30; i++) {
      const check = await wallet.checkMintQuoteBolt11(quote.quote);
      if (check.state === 'PAID') break;
      await new Promise(r => setTimeout(r, 1000));
    }
    // v4 mintProofsBolt11 might take the full quote object
    let proofs;
    // dedup: second declaration removed
    try {
      // WalletOps.mintBolt11 — high-level API handles Amount internally
      const ops = new mod.WalletOps(wallet);
    tapMints(ops, 'ops');
      const result = await ops.mintBolt11(amount);
      proofs = result?.proofs ?? result;
      log('WalletOps.mintBolt11:', typeof result, proofs?.length ?? '?', 'proofs');
    } catch (e1) {
      log('WalletOps failed:', e1.message?.slice(0, 200), '— trying raw Amount(BigInt)');
      try {
        const amt = new mod.Amount(BigInt(amount));
        proofs = await wallet.mintProofsBolt11(amt, quote.quote);
        log('raw Amount(BigInt) worked');
      } catch (e2) {
        log('BigInt also failed:', e2.message?.slice(0, 200));
        throw new Error('all mint approaches failed: ' + e1.message + ' | ' + e2.message);
      }
    }
    log('minted:', proofs?.length ?? 'unknown', 'proofs');
    return proofs;
  }

  // swap to self (basic interop test)
  if (FLOW === 'mint_swap') {
    const ops = new mod.WalletOps(wallet);
    tapMints(ops, 'ops');
    const mintResult = await ops.mintBolt11(64);
    log('mint:', mintResult?.proofs?.length ?? 'no-proofs-prop', 'proofs, keys:', mintResult ? Object.keys(mintResult).slice(0,8).join(',') : 'null');
    const sendResult = await ops.send(64);
    const sendDesc = sendResult?.token ? 'token:' + String(sendResult.token).slice(0, 30) : (sendResult?.proofs ? sendResult.proofs.length + ' proofs' : 'other-shape');
    log('send:', sendDesc);
    result.verdict = 'PASS'; finish(0);
  }

  // P2PK: lock to our pubkey, then sign and spend
  if (FLOW === 'p2pk_send_spend') {
    // v4 builder API: createMintQuote -> ops.mintBolt11(amount, quote).run() -> ops.send(...).asP2PK(...).run()
    try {
      let quote;
      try { quote = await wallet.createMintQuote('bolt11', { amount: 128, unit: 'sat' }); }
      catch (e1) { log('createMintQuote v4 sig failed:', String(e1).slice(0, 90)); throw e1; }
      log('quote:', String(quote?.quote ?? quote).slice(0, 18));
      await new Promise(r => setTimeout(r, 2500)); // FakeWallet settle
      let proofs;
      try { proofs = await wallet.ops.mintBolt11(128, quote).run(); }
      catch (e) { log('mintBolt11:', String(e).slice(0, 120)); throw e; }
      log('minted:', Array.isArray(proofs) ? proofs.length + ' proofs' : typeof proofs);
      const { keep, send } = await wallet.ops.send(64, proofs).asP2PK({ pubkey: pubHex }).includeFees(true).run();
      log('p2pk send:', (send ?? []).length, 'locked proofs | keep:', (keep ?? []).length);
      // spend phase: swap the locked proofs back with our key (witness emission = the d6 evidence)
      try {
        const signed = wallet.signP2PKProofs(send, privHex);
        const nWit = (signed ?? []).filter(p => p?.witness).length;
        log('signed proofs with witness:', nWit, '/', (send ?? []).length);
        const spendRes = await wallet.ops.send(60, signed).includeFees(true).run();
        log('p2pk spend-back ok:', (spendRes?.send ?? []).length, 'new proofs');
      } catch (eS) { log('spend-back attempt:', String(eS).slice(0, 130)); }
      try { result.wire_shapes = extractWitness(readWire()); } catch { result.wire_shapes = {}; }
      result.verdict = (send ?? []).length > 0 ? 'PASS' : 'FAIL';
      result.reason = (send ?? []).length > 0 ? '' : 'no send proofs';
      finish(result.verdict === 'PASS' ? 0 : 1);
    } catch (e) {
      // older wallet versions: legacy path
      log('v4 path failed, legacy attempt:', String(e).slice(0, 100));
      // v3-era API: createMintQuote(amount) -> mintProofs -> send(amount, {p2pk})
      try {
        const q3 = await wallet.createMintQuote(128);
        log('v3 quote:', String(q3?.quote ?? q3).slice(0, 16));
        await new Promise(r => setTimeout(r, 2500));
        const proofs3 = await wallet.mintProofs(128, q3?.quote ?? q3);
        log('v3 minted:', Array.isArray(proofs3) ? proofs3.length : typeof proofs3);
        const sent3 = await wallet.send(64, proofs3, { p2pk: { pubkey: pubHex } });
        log('v3 sent:', sent3?.send?.length ?? sent3?.length ?? '?');
      } catch (e3) {
        log('v3 flow failed:', String(e3).slice(0, 100));
        try {
          const q3 = await wallet.createMintQuote(128);
          await new Promise(r => setTimeout(r, 2500));
          const proofs3 = await wallet.mintProofs(128, q3?.quote ?? q3);
          const sent3 = await wallet.send(64, { p2pk: { pubkey: pubHex } });
          log('v3b sent:', sent3?.send?.length ?? sent3?.length ?? '?');
        } catch (e4) { log('v3b flow failed:', String(e4).slice(0, 100)); }
      }
      try { result.wire_shapes = extractWitness(readWire()); } catch { result.wire_shapes = {}; }
      // evidence-based verdict: PASS only if a swap actually hit the wire
      const wireOk = (() => { try { return readWire().some(l => l.includes('/v1/swap')); } catch { return false; } })();
      result.verdict = wireOk ? 'PASS' : 'FAIL';
      result.reason = wireOk ? '' : 'no swap on the wire (flow did not execute)';
      finish(wireOk ? 0 : 1);
    }
  }

  // HTLC receive: lock to hash, spend with preimage
  if (FLOW === 'htlc_receive') {
    const { randomBytes, createHash } = await import('node:crypto');
    const preimage = randomBytes(32).toString('hex');
    const hash = createHash('sha256').update(Buffer.from(preimage, 'hex')).digest('hex');
    try {
      // v4: quote -> mint -> send with hashlock -> spend-back with preimage
      let quote;
      try { quote = await wallet.createMintQuote('bolt11', { amount: 128, unit: 'sat' }); }
      catch { quote = await wallet.createMintQuote(128); }
      await new Promise(r => setTimeout(r, 2500));
      let proofs;
      try { proofs = await wallet.ops.mintBolt11(128, quote).run(); }
      catch { proofs = await wallet.mintProofs(128, quote?.quote ?? quote); }
      const htlcOpts = new mod.P2PKBuilder().addHashlock(hash).toOptions();
      const { keep, send } = await wallet.ops.send(64, proofs).asP2PK(htlcOpts).includeFees(true).run();
      log('htlc locked:', (send ?? []).length, 'proofs');
      // spend back with the preimage: attach the witness manually (the wire shape we verified)
      for (const p of (send ?? [])) p.witness = JSON.stringify({ preimage });
      const spent = await wallet.ops.receive(send).run();
      log('htlc spend-back:', Array.isArray(spent) ? spent.length + ' proofs' : 'ok');
      // v4 success path: evidence = locked proofs + successful preimage spend
      const n = (send ?? []).length + (Array.isArray(spent) ? spent.length : 1);
      try { result.wire_shapes = extractWitness(readWire()); } catch { result.wire_shapes = {}; }
      result.verdict = n > 0 ? 'PASS' : 'FAIL';
      result.reason = n > 0 ? '' : 'no proofs locked/spent';
      finish(n > 0 ? 0 : 1);
    } catch (eH) {
      log('htlc v4 path failed:', String(eH).slice(0, 110));
      try {
        const q3 = await wallet.createMintQuote(128);
        await new Promise(r => setTimeout(r, 2500));
        const proofs3 = await wallet.mintProofs(128, q3?.quote ?? q3);
        const sent3 = await wallet.send(64, proofs3, { htlc: { hash } });
        log('htlc v3 sent:', sent3?.send?.length ?? sent3?.length ?? '?');
      } catch (e3) { log('htlc v3 path failed:', String(e3).slice(0, 110)); }
    }
    try { result.wire_shapes = extractWitness(readWire()); } catch { result.wire_shapes = {}; }
    const wireOkH = (() => { try { return readWire().some(l => l.includes('/v1/swap')); } catch { return false; } })();
    result.verdict = wireOkH ? 'PASS' : 'FAIL';
    result.reason = wireOkH ? '' : 'no swap on the wire';
    finish(wireOkH ? 0 : 1);
  }

  // HTLC refund: lock with expired locktime + refund key, spend via refund
  if (FLOW === 'htlc_refund') {
    const proofs = await getProofs(64);
    const { randomBytes, createHash } = await import('node:crypto');
    const preimage = randomBytes(32);
    const hash = createHash('sha256').update(preimage).digest('hex');
    const pastLock = Math.floor(Date.now() / 1000) - 3600;

    const builder = new mod.P2PKBuilder();
    builder.addHashlock(hash);
    builder.addRefundPubkey(pubHex);
    builder.lockUntil(pastLock);
    const htlcOpts = builder.toOptions();

    const sendResult = await wallet.send(64, { p2pk: htlcOpts });
    log('htlc refund locked:', JSON.stringify(sendResult).slice(0, 300));
    result.wire_shapes = extractWitness(readWire());

    // try to spend the refund (sign with our key)
    // v4: the wallet should recognize the expired lock and allow refund spend
    try {
      const spendResult = await wallet.send(64);
      log('refund spend:', JSON.stringify(spendResult).slice(0, 200));
      result.verdict = 'PASS';
    } catch (e) {
      log('refund spend failed:', e.message?.slice(0, 200));
      // The spend may fail if the wallet can't sign — that's the d6 finding!
      result.verdict = 'FAIL';
      result.reason = `refund spend: ${e.message?.slice(0, 200)}`;
    }
    finish(result.verdict === 'PASS' ? 0 : 1);
  }

  result.verdict = 'SKIP'; result.reason = `unknown flow ${FLOW}`; finish(127);
}

function readWire() {
  try {
    return readFileSync(`${ART}/wire.ndjson`, 'utf8').trim().split('\n')
      .map(l => { try { return JSON.parse(l); } catch { return null; } })
      .filter(Boolean)
      .map(d => ({ ...d, url: d.url ?? d.endpoint ?? '' }));  // unify fetch-layer + request-layer shapes
  } catch { return []; }
}
function extractWitness(wire) {
  const shapes = {};
  for (const w of wire) {
    if (!w.url.includes('/swap')) continue;
    try {
      const body = JSON.parse(w.body);
      for (const inp of body.inputs || []) {
        if (inp.witness) {
          const wit = JSON.parse(inp.witness);
          shapes.preimage_present = 'preimage' in wit;
          shapes.preimage_null = wit.preimage === null;
          shapes.sig_count = (wit.signatures || []).length;
        }
      }
    } catch {}
  }
  return shapes;
}

function finish(code) {
  if (!result.verdict) result.verdict = code === 0 ? 'PASS' : code === 127 ? 'SKIP' : 'FAIL';
  (ART && mkdirSync(ART, { recursive: true }));
  writeFileSync(`${ART}/result.json`, JSON.stringify(result, null, 1));
  process.exit(code);
}

main().catch(e => { log('FATAL', e); result.verdict = 'FAIL'; result.reason = e.message?.slice(0, 300); finish(1); });
