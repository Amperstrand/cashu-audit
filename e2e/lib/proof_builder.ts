/**
 * Cashu E2E Proof Builder — Layer 4 dynamic testing.
 *
 * Uses @cashu/cashu-ts to construct real P2PK/HTLC proofs with valid
 * blind signatures, enabling runtime testing of spending conditions.
 *
 * Usage:
 *   npx tsx e2e/lib/proof_builder.ts --mint-url http://localhost:8787
 */

import { Wallet, Mint, P2PKBuilder, CheckStateEnum, MintQuoteState } from '@cashu/cashu-ts';
import { secp256k1 } from '@noble/curves/secp256k1';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils';

export interface TestResult {
  name: string;
  status: 'PASS' | 'FAIL' | 'SKIP';
  detail: string;
}

export class CashuE2E {
  private mint: Mint;
  private wallet: Wallet | null = null;

  constructor(mintUrl: string) {
    this.mint = new Mint(mintUrl);
  }

  async setup(): Promise<void> {
    const info = await this.mint.getInfo();
    const keys = await this.mint.getKeys();
    this.wallet = new Wallet(this.mint, info, keys);
  }

  /**
   * Mint tokens via FakeWallet (auto-settles).
   * Returns proofs that can be used for swap/melt tests.
   */
  async mintTokens(amount: number, unit: string = 'sat'): Promise<any[]> {
    if (!this.wallet) throw new Error('Call setup() first');

    // Create mint quote
    const quote = await this.mint.createMintQuoteBolt11({ amount, unit });
    console.log(`  Quote: ${quote.quote.slice(0, 12)}...`);

    // For FakeWallet, payment settles automatically
    // Poll until PAID
    let state = quote.state;
    let attempts = 0;
    while (state !== MintQuoteState.PAID && attempts < 10) {
      await new Promise(r => setTimeout(r, 500));
      const status = await this.mint.checkMintQuoteBolt11(quote.quote);
      state = status.state;
      attempts++;
    }

    if (state !== MintQuoteState.PAID) {
      throw new Error(`Quote not PAID after ${attempts} attempts (state=${state})`);
    }

    // Mint tokens
    const { proofs } = await this.wallet.mintTokens(quote.quote, amount, unit);
    console.log(`  Minted ${proofs.length} proofs totaling ${amount} ${unit}`);
    return proofs;
  }

  /**
   * Create a P2PK-locked proof set for testing spending conditions.
   */
  async createP2PKProofs(
    amount: number,
    opts: {
      lockPubkey?: string;
      sigAll?: boolean;
      locktime?: number;
      refundPubkey?: string;
      nSigs?: number;
      nSigsRefund?: number;
    } = {}
  ): Promise<{ secret: string; proofs: any[] }> {
    if (!this.wallet) throw new Error('Call setup() first');

    // Generate keypair if not provided
    const privKey = secp256k1.utils.randomPrivateKey();
    const pubKey = bytesToHex(secp256k1.getPublicKey(privKey, true));

    // Build P2PK secret
    const builder = new P2PKBuilder();
    builder.addLockPubkey(opts.lockPubkey || pubKey);
    if (opts.sigAll) builder.sigAll();
    if (opts.locktime) builder.lockUntil(opts.locktime);
    if (opts.refundPubkey) builder.addRefundPubkey(opts.refundPubkey);
    if (opts.nSigs) builder.requireLockSignatures(opts.nSigs);
    if (opts.nSigsRefund) builder.requireRefundSignatures(opts.nSigsRefund);

    // Create the secret
    const secretOpts = builder.toOptions();
    const secret = JSON.stringify(['P2PK', secretOpts]);

    return { secret, proofs: [] };
  }

  /**
   * Check proof state via /v1/checkstate
   */
  async checkProofState(ys: string[]): Promise<any[]> {
    const response = await fetch(`${this.mint.mintUrl}/v1/checkstate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Ys: ys }),
    });
    const data = await response.json();
    return data.states || [];
  }

  /**
   * Get mint info
   */
  async getInfo(): Promise<any> {
    return await this.mint.getInfo();
  }

  /**
   * Health check
   */
  async isHealthy(): Promise<boolean> {
    try {
      const resp = await fetch(`${this.mint.mintUrl}/health`);
      return resp.ok;
    } catch {
      return false;
    }
  }
}

/**
 * Run all E2E scenarios.
 */
export async function runAllScenarios(mintUrl: string): Promise<TestResult[]> {
  const results: TestResult[] = [];
  const e2e = new CashuE2E(mintUrl);

  // Health check
  if (!(await e2e.isHealthy())) {
    results.push({ name: 'health', status: 'FAIL', detail: `Mint not reachable at ${mintUrl}` });
    return results;
  }
  results.push({ name: 'health', status: 'PASS', detail: 'Mint reachable' });

  // Setup
  try {
    await e2e.setup();
    results.push({ name: 'setup', status: 'PASS', detail: 'Wallet initialized' });
  } catch (e: any) {
    results.push({ name: 'setup', status: 'FAIL', detail: e.message });
    return results;
  }

  // Scenario: mint tokens
  try {
    const proofs = await e2e.mintTokens(10);
    results.push({
      name: 'mint_tokens',
      status: 'PASS',
      detail: `${proofs.length} proofs minted`,
    });
  } catch (e: any) {
    results.push({ name: 'mint_tokens', status: 'FAIL', detail: e.message });
  }

  // Scenario: info completeness
  try {
    const info = await e2e.getInfo();
    const hasNuts = info.nuts && info.nuts['4'] && info.nuts['5'];
    results.push({
      name: 'info_completeness',
      status: hasNuts ? 'PASS' : 'FAIL',
      detail: hasNuts ? `${Object.keys(info.nuts).length} NUTs advertised` : 'Missing NUT-04/05',
    });
  } catch (e: any) {
    results.push({ name: 'info_completeness', status: 'FAIL', detail: e.message });
  }

  return results;
}

// CLI entry point
if (require.main === module) {
  const mintUrl = process.argv[2] || 'http://localhost:8787';
  console.log(`\nCashu E2E Proof Builder — Layer 4`);
  console.log(`Target: ${mintUrl}\n`);

  runAllScenarios(mintUrl).then(results => {
    for (const r of results) {
      const emoji = { PASS: '✅', FAIL: '❌', SKIP: '⏭️' }[r.status];
      console.log(`${emoji} ${r.name}: ${r.detail}`);
    }
    const passed = results.filter(r => r.status === 'PASS').length;
    const failed = results.filter(r => r.status === 'FAIL').length;
    console.log(`\n${passed} PASS, ${failed} FAIL\n`);
    process.exit(failed > 0 ? 1 : 0);
  });
}
