/**
 * Cashu E2E Proof Builder — Layer 4 dynamic testing.
 *
 * Uses @cashu/crypto (the same crypto used by cashu-cf's own tests).
 * Run from cashu-cf directory:
 *   npx tsx ../cashu-audit/e2e/lib/proof_builder.ts https://testnut.cashu.exchange
 */

const { bytesToHex, randomBytes } = require('@noble/hashes/utils');
const { blindMessage, unblindSignature } = require('@cashu/crypto/modules/client');
const { pointFromHex, hashToCurve } = require('@cashu/crypto/modules/common');

function decomposeAmount(amount) {
  const amounts = [];
  let remaining = amount;
  const denoms = [64, 32, 16, 8, 4, 2, 1];
  for (const d of denoms) {
    while (remaining >= d) {
      amounts.push(d);
      remaining -= d;
    }
  }
  return amounts.length > 0 ? amounts : [0];
}

class CashuE2E {
  constructor(mintUrl) {
    this.mintUrl = mintUrl.replace(/\/+$/, '');
  }

  async http(method, path, body) {
    const resp = await fetch(`${this.mintUrl}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', 'Accept-Encoding': 'identity' },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await resp.text();
    try { return { status: resp.status, data: JSON.parse(text) }; }
    catch { return { status: resp.status, data: { raw: text } }; }
  }

  async isHealthy() {
    try { return (await this.http('GET', '/health')).status === 200; }
    catch { return false; }
  }

  async getInfo() { return (await this.http('GET', '/v1/info')).data; }
  async getKeys() { return (await this.http('GET', '/v1/keys')).data; }
  async getKeysets() { return (await this.http('GET', '/v1/keysets')).data; }

  async getActiveKeyset(unit = 'sat') {
    const keysets = await this.getKeysets();
    const ks = keysets.keysets.find(k => k.unit === unit && k.active);
    if (!ks) throw new Error(`No active ${unit} keyset`);
    const keysResp = await this.http('GET', `/v1/keys/${ks.id}`);
    return { id: ks.id, keys: keysResp.data.keysets[0].keys };
  }

  async mintTokens(amount, unit = 'sat') {
    const { id: keysetId, keys: mintKeys } = await this.getActiveKeyset(unit);

    // Create quote
    const quoteResp = await this.http('POST', '/v1/mint/quote/bolt11', { unit, amount });
    if (quoteResp.status !== 200) throw new Error(`Quote failed: ${quoteResp.status}`);
    const quoteId = quoteResp.data.quote;

    // Wait for PAID
    let state = quoteResp.data.state;
    for (let i = 0; i < 20 && state !== 'PAID'; i++) {
      await new Promise(r => setTimeout(r, 500));
      state = (await this.http('GET', `/v1/mint/quote/bolt11/${quoteId}`)).data.state;
    }
    if (state !== 'PAID') throw new Error(`Not PAID`);

    // Build blinded outputs
    const amounts = decomposeAmount(amount);
    const outputs = [];
    const tokenDataList = [];

    for (const amt of amounts) {
      const secret = randomBytes(32);
      const blinded = blindMessage(secret);
      outputs.push({ amount: amt, id: keysetId, B_: bytesToHex(blinded.B_.toRawBytes(true)) });
      tokenDataList.push({ secret, r: blinded.r, amount: amt });
    }

    // Mint
    const mintResp = await this.http('POST', '/v1/mint/bolt11', { quote: quoteId, outputs });
    if (mintResp.status !== 200) throw new Error(`Mint failed: ${mintResp.status}`);

    // Unblind
    const proofs = [];
    for (let i = 0; i < mintResp.data.signatures.length; i++) {
      const sig = mintResp.data.signatures[i];
      const td = tokenDataList[i];
      const A = pointFromHex(mintKeys[td.amount.toString()]);
      const C_ = pointFromHex(sig.C_);
      const C = unblindSignature(C_, td.r, A);
      proofs.push({
        amount: td.amount,
        id: keysetId,
        secret: bytesToHex(td.secret),
        C: bytesToHex(C.toRawBytes(true)),
      });
    }

    return { proofs, quoteId };
  }

  async swap(inputs, outputAmounts, keysetId) {
    const outputs = [];
    for (const amt of outputAmounts) {
      const secret = randomBytes(32);
      const blinded = blindMessage(secret);
      outputs.push({ amount: amt, id: keysetId, B_: bytesToHex(blinded.B_.toRawBytes(true)) });
    }
    const swapInputs = inputs.map(p => ({ amount: p.amount, secret: p.secret, C: p.C, id: p.id }));
    return await this.http('POST', '/v1/swap', { inputs: swapInputs, outputs });
  }

  async checkState(ys) {
    return (await this.http('POST', '/v1/checkstate', { Ys: ys })).data;
  }

  deriveY(secret) {
    const secretBytes = new TextEncoder().encode(secret);
    const Y = hashToCurve(secretBytes);
    return bytesToHex(Y.toRawBytes(true));
  }
}

async function main() {
  const mintUrl = process.argv[2] || 'http://localhost:8787';
  console.log(`\nCashu E2E Proof Builder — Layer 4`);
  console.log(`Target: ${mintUrl}\n`);

  const e2e = new CashuE2E(mintUrl);

  if (!(await e2e.isHealthy())) {
    console.log(`❌ Mint not reachable`);
    process.exit(1);
  }
  console.log(`✅ Mint reachable`);

  try {
    const { proofs, quoteId } = await e2e.mintTokens(10);
    const total = proofs.reduce((s, p) => s + p.amount, 0);
    console.log(`✅ mint_tokens: ${proofs.length} proofs, total=${total}, quote=${quoteId.slice(0, 8)}...`);

    const { id: keysetId } = await e2e.getActiveKeyset();
    const keysets = await e2e.getKeysets();
    const ksInfo = keysets.keysets.find(k => k.id === keysetId);
    const feePpk = ksInfo?.input_fee_ppk || 0;
    const fee = Math.ceil((proofs.length * feePpk) / 1000);
    const outputTotal = total - fee;
    console.log(`  Fee: ${fee} sat (${feePpk} ppk × ${proofs.length} proofs), output total: ${outputTotal}`);
    const swapResp = await e2e.swap(proofs, decomposeAmount(outputTotal), keysetId);
    if (swapResp.status === 200) {
      console.log(`✅ swap: ${swapResp.data.signatures?.length || 0} signatures returned`);
    } else {
      console.log(`❌ swap: ${swapResp.status} ${JSON.stringify(swapResp.data).slice(0, 100)}`);
    }

    // Check proof states
    const ys = proofs.map(p => e2e.deriveY(p.secret));
    const states = await e2e.checkState(ys);
    const spent = states.states?.filter(s => s.state === 'SPENT').length || 0;
    console.log(`✅ checkstate: ${spent}/${proofs.length} proofs SPENT (expected ${proofs.length})`);
  } catch (e) {
    console.log(`❌ ${e.message}`);
  }

  console.log();
}

if (require.main === module) main();

module.exports = { CashuE2E, decomposeAmount };
