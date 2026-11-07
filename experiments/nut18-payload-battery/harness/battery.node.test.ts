import { readFileSync, existsSync } from 'fs';
import { describe, it, expect } from 'vitest';

import { Mint, PaymentRequest, PaymentRequest as PR, Wallet } from '../../src';

// Battery cells: cashu-ts decodePayload + isPaymentRequestSatisfied vs ../../expected.json
// Env: BATTERY_MINT_URL (settlement cells; decode cells are offline).

const BATTERY_DIR = process.env.BATTERY_DIR || new URL('../../../..', import.meta.url).pathname;
const D = `${BATTERY_DIR}/fixtures`;
const EXPECTED = JSON.parse(readFileSync(`${BATTERY_DIR}/expected.json`, 'utf8'));
const MINT_URL = process.env.BATTERY_MINT_URL || '';
const load = (f: string) => readFileSync(`${D}/${f}`, 'utf8');

const tsMatrix = EXPECTED.payload_parse_matrix.cashu_ts_decodePayload as Record<string, string>;

describe('battery: cashu-ts decodePayload (exact identities)', () => {
  for (const [fixture, exp] of Object.entries(tsMatrix)) {
    it(`${fixture}: ${exp.slice(0, 60)}`, () => {
      if (exp.startsWith('PASS')) {
        expect(() => PR.decodePayload(load(fixture))).not.toThrow();
      } else {
        const detail = exp.replace(/^FAIL /, '').replace(/\s*\(.*\)$/, '');
        expect(() => PR.decodePayload(load(fixture))).toThrowError(detail);
      }
    });
  }
});

const settlement = EXPECTED.settlement_matrix.cashu_ts_isPaymentRequestSatisfied as Record<string, string>;

describe('battery: cashu-ts settlement (needs live arm)', () => {
  it.skipIf(!MINT_URL)('short16 throws unrecognised-keyset identity', async () => {
    const wallet = new Wallet(new Mint(MINT_URL), { unit: 'sat' });
    await wallet.loadMint();
    const p = PR.decodePayload(load('payload_short16.json'));
    const pr = new PaymentRequest({ amount: 5, unit: 'sat' });
    expect(() => wallet.isPaymentRequestSatisfied(pr, p.proofs)).toThrowError(
      /Proof has unrecognised keyset\. '[0-9a-f]{16}' is not a sat keyset from this mint/,
    );
  });
  it.skipIf(!MINT_URL)('full66 settles true', async () => {
    const wallet = new Wallet(new Mint(MINT_URL), { unit: 'sat' });
    await wallet.loadMint();
    const p = PR.decodePayload(load('payload_full66.json'));
    const pr = new PaymentRequest({ amount: 5, unit: 'sat' });
    expect(wallet.isPaymentRequestSatisfied(pr, p.proofs)).toBe(true);
  });
  it.skipIf(!MINT_URL)('nutshell wire captures: decode OK, settlement throws unrecognised', async () => {
    const wallet = new Wallet(new Mint(MINT_URL), { unit: 'sat' });
    await wallet.loadMint();
    const pr = new PaymentRequest({ amount: 5, unit: 'sat' });
    for (const f of ['capture_nutshell_wire_0210.json', 'capture_nutshell_wire_0221.json']) {
      if (!existsSync(`${D}/${f}`)) continue;
      const p = PR.decodePayload(load(f));
      expect(() => wallet.isPaymentRequestSatisfied(pr, p.proofs)).toThrowError(
        /Proof has unrecognised keyset\. '[0-9a-f]{16}' is not a sat keyset from this mint/,
      );
    }
  });
  it.skipIf(!MINT_URL)('cdk wire capture: decodePayload rejects memo:null', () => {
    expect(() => PR.decodePayload(load('capture_cdk_wire.json'))).toThrowError(
      'invalid payment payload: memo must be a string',
    );
  });
});
