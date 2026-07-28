/**
 * Cashu E2E Proof Builder — Layer 4 dynamic testing.
 *
 * Uses @cashu/cashu-ts crypto + raw HTTP to construct real proofs.
 * Run from cashu-cf directory:
 *   npx tsx ../cashu-audit/e2e/lib/proof_builder.ts https://testnut.cashu.exchange
 */

import { schnorr, secp256k1 } from '@noble/curves/secp256k1.js';
const Point = secp256k1.Point;
import { bytesToHex, hexToBytes, randomBytes } from '@noble/hashes/utils';
import { blindMessage } from '@cashu/cashu-ts';

export interface Proof { amount: number; secret: string; C: string; id: string; }

function decomposeAmount(amount: number): number[] {
  const amounts: number[] = [];
  let remaining = amount;
  let power = 0;
  while (remaining > 0) {
    if (remaining & 1) amounts.push(2 ** power);
    remaining >>= 1;
    power++;
  }
  return amounts.length > 0 ? amounts : [0];
}

export class CashuE2E {
  constructor(private mintUrl: string) {
    this.mintUrl = mintUrl.replace(/\/+$/, '');
  }

  private async http(method: string, path: string, body?: any): Promise<{ status: number; data: any }> {
    const resp = await fetch(`${this.mintUrl}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', 'Accept-Encoding': 'identity' },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await resp.text();
    try { return { status: resp.status, data: JSON.parse(text) }; }
    catch { return { status: resp.status, data: { raw: text } }; }
  }

  async isHealthy(): Promise<boolean> {
    try { return (await this.http('GET', '/health')).status === 200; }
    catch { return false; }
  }

  async getInfo(): Promise<any> { return (await this.http('GET', '/v1/info')).data; }
  async getKeys(): Promise<any> { return (await this.http('GET', '/v1/keys')).data; }
  async getKeysets(): Promise<any> { return (await this.http('GET', '/v1/keysets')).data; }

  async mintTokens(amount: number, unit: string = 'sat'): Promise<{ proofs: Proof[]; quoteId: string }> {
    // 1. Get active keyset + keys
    const keysetsResp = await this.getKeysets();
    const keyset = keysetsResp.keysets.find((k: any) => k.unit === unit && k.active);
    if (!keyset) throw new Error(`No active ${unit} keyset`);
    const keysetId = keyset.id;

    const keysResp = await this.getKeys();
    const keysEntry = keysResp.keysets?.find((k: any) => k.id === keysetId);
    if (!keysEntry) throw new Error(`No keys for ${keysetId}`);

    // keysEntry.keys is { "1": "<hex>", "2": "<hex>", ... } per amount
    const keysMap = keysEntry.keys;

    // 2. Create quote
    const quoteResp = await this.http('POST', '/v1/mint/quote/bolt11', { unit, amount });
    if (quoteResp.status !== 200) throw new Error(`Quote failed: ${quoteResp.status}`);
    const quoteId = quoteResp.data.quote;

    // 3. Wait for payment
    let state = quoteResp.data.state;
    let attempts = 0;
    while (state !== 'PAID' && attempts < 20) {
      await new Promise(r => setTimeout(r, 500));
      const status = await this.http('GET', `/v1/mint/quote/bolt11/${quoteId}`);
      state = status.data.state;
      attempts++;
    }
    if (state !== 'PAID') throw new Error(`Not PAID after ${attempts} tries`);

    // 4. Create blinded messages
    const amounts = decomposeAmount(amount);
    const outputs: any[] = [];
    const blindData: { r: bigint; secret: string }[] = [];

    for (const amt of amounts) {
      const secret = bytesToHex(randomBytes(32));
      const { B_: BPoint, r } = blindMessage(secret);
      outputs.push({ amount: amt, id: keysetId, B_: bytesToHex(BPoint.toBytes(true)) });
      blindData.push({ r, secret });
    }

    // 5. Mint
    const mintResp = await this.http('POST', '/v1/mint/bolt11', { quote: quoteId, outputs });
    if (mintResp.status !== 200) throw new Error(`Mint failed: ${mintResp.status} ${JSON.stringify(mintResp.data).slice(0, 200)}`);

    // 6. Unblind
    const signatures = mintResp.data.signatures;
    const proofs: Proof[] = [];
    for (let i = 0; i < signatures.length; i++) {
      const sig = signatures[i];
      const K = keysMap[String(sig.amount)];
      const C_Blinded = Point.fromHex(sig.C_);
      const K_Point = Point.fromHex(K);
      const C_Point = C_Blinded.subtract(K_Point.multiply(blindData[i].r));
      const C = bytesToHex(C_Point.toBytes(true));
      proofs.push({ amount: sig.amount, secret: blindData[i].secret, C, id: keysetId });
    }

    return { proofs, quoteId };
  }

  async swap(inputs: Proof[], outputAmounts: number[], keysetId: string): Promise<{ status: number; data: any }> {
    const outputs: any[] = [];
    for (const amt of outputAmounts) {
      const secret = bytesToHex(randomBytes(32));
      const { B_: BPoint } = blindMessage(secret);
      outputs.push({ amount: amt, id: keysetId, B_: bytesToHex(BPoint.toBytes(true)) });
    }
    const swapInputs = inputs.map(p => ({ amount: p.amount, secret: p.secret, C: p.C, id: p.id }));
    return await this.http('POST', '/v1/swap', { inputs: swapInputs, outputs });
  }

  async checkState(ys: string[]): Promise<any> {
    return (await this.http('POST', '/v1/checkstate', { Ys: ys })).data;
  }
}

export async function runAllScenarios(mintUrl: string) {
  const e2e = new CashuE2E(mintUrl);
  const results: { name: string; status: string; detail: string }[] = [];

  if (!(await e2e.isHealthy())) {
    console.log(`❌ Mint not reachable: ${mintUrl}`);
    return;
  }
  console.log(`✅ Mint reachable\n`);

  try {
    const { proofs, quoteId } = await e2e.mintTokens(10);
    const total = proofs.reduce((s, p) => s + p.amount, 0);
    console.log(`✅ mint_tokens: ${proofs.length} proofs, total=${total}, quote=${quoteId.slice(0, 8)}...`);

    const keysets = await e2e.getKeysets();
    const ks = keysets.keysets.find((k: any) => k.unit === 'sat' && k.active);
    const swapResp = await e2e.swap(proofs, decomposeAmount(total), ks.id);
    console.log(swapResp.status === 200
      ? `✅ swap: ${swapResp.data.signatures?.length || 0} signatures returned`
      : `❌ swap: ${swapResp.status} ${JSON.stringify(swapResp.data).slice(0, 100)}`);
  } catch (e: any) {
    console.log(`❌ mint_tokens: ${e.message}`);
  }
}

if (require.main === module) {
  const url = process.argv[2] || 'http://localhost:8787';
  console.log(`\nCashu E2E Proof Builder — Layer 4`);
  console.log(`Target: ${url}\n`);
  runAllScenarios(url);
}
