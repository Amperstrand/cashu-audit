#!/usr/bin/env node
/**
 * Minimal, self-contained demonstration of the NUT-00 secret-encoding trap,
 * discovered while building custom low-level mint tooling during testing.
 *
 * Prereq: local cdk-mintd 0.17.6 fakewallet on 127.0.0.1:18085
 *   (docker run -d --name cdk-mint-0176 ... cashubtc/mintd:0.17.6)
 *
 * Run: node demo-bug.mjs
 *
 * What it shows, in ~20 seconds:
 *   1. the same 32 bytes of entropy blinded two ways produce two valid-looking
 *      blinded points — the mint happily signs either (blindness!)
 *   2. the proof built the "convenient" way (hash the raw bytes, publish the
 *      hex string) fails verification with 10001 "Token not verified"
 *   3. the proof built the spec way (hash the utf8 bytes of the hex string)
 *      spends fine
 *   4. a 3-line client-side guard catches the bug BEFORE anything is submitted
 */
import { blindMessage, constructUnblindedSignature, hashToCurve } from '@cashu/cashu-ts';
import { secp256k1 } from '@noble/curves/secp256k1.js';
import { randomBytes } from 'node:crypto';

const MINT = 'http://127.0.0.1:18085';
const AMOUNT = 64;
const G = secp256k1.Point.BASE;
const api = async (path, body) => {
  const r = await fetch(MINT + path, {
    method: body !== undefined ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return { status: r.status, json: await r.json().catch(() => null) };
};

const entropy = randomBytes(32);
const secretString = entropy.toString('hex');            // what a Proof.secret holds
const Y_spec = hashToCurve(Buffer.from(secretString, 'utf8')); // NUT-00: utf8 of the STRING
const Y_trap = hashToCurve(entropy);                     // the trap: hashing the entropy

console.log('entropy          :', entropy.toString('hex'));
console.log('secret (string)  :', secretString);
console.log('Y  spec (utf8)   :', Y_spec.toHex(true));
console.log('Y  trap (raw)    :', Y_trap.toHex(true), ' <- both are perfectly valid points\n');

const ks = (await api('/v1/keys')).json.keysets.find(k => k.active && k.unit === 'sat');
const A = secp256k1.Point.fromHex(ks.keys[String(AMOUNT)]);

async function mintAndTry(label, blindInput, secretForProof) {
  const q = (await api('/v1/mint/quote/bolt11', { amount: AMOUNT, unit: 'sat' })).json;
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 400));
    if ((await api(`/v1/mint/quote/bolt11/${q.quote}`)).json.state === 'PAID') break;
  }
  const bm = blindMessage(blindInput);
  // the guard: B_ must equal H(utf8(published secret)) + rG
  const guardOk = bm.B_.equals(hashToCurve(Buffer.from(secretForProof, 'utf8')).add(G.multiply(bm.r)));
  const mr = await api('/v1/mint/bolt11', { quote: q.quote, outputs: [{ amount: AMOUNT, B_: bm.B_.toHex(true), id: ks.id }] });
  console.log(`${label}: mint -> HTTP ${mr.status}   guard(B_ == H(utf8(secret))+rG): ${guardOk ? 'PASS' : 'FAIL  <-- bug detectable HERE, pre-submission'}`);
  const unb = constructUnblindedSignature({ C_: secp256k1.Point.fromHex(mr.json.signatures[0].C_), id: mr.json.signatures[0].id }, bm.r, blindInput, A);
  const proof = { id: ks.id, amount: AMOUNT, secret: secretForProof, C: unb.C.toHex(true) };
  const nb = blindMessage(Buffer.from(randomBytes(32).toString('hex'), 'utf8'));
  const sw = await api('/v1/swap', { inputs: [proof], outputs: [{ amount: AMOUNT, B_: nb.B_.toHex(true), id: ks.id }] });
  console.log(`${label}: swap  -> HTTP ${sw.status} ${sw.json?.code ? JSON.stringify(sw.json) : '(spendable!)'}`);
  return sw.status;
}

console.log('--- A) spec-conformant: blind utf8(hexString), publish hexString ---');
const ok = await mintAndTry('A  ', Buffer.from(secretString, 'utf8'), secretString);

console.log('\n--- B) the trap: blind raw entropy bytes, publish hexString ---');
const bad = await mintAndTry('B  ', entropy, secretString);

console.log(`
=====================================================================
 A (spec)  : mint OK, guard PASS, swap OK          -> money is spendable
 B (trap)  : mint OK (!), guard FAIL, swap 10001   -> money is LOCKED FOREVER

 The mint signed BOTH without complaint - a blind signature cannot know
 how B_ was derived. The secret<->point coupling is only checked at spend:
     C == a * hash_to_curve(utf8_bytes(proof.secret))
 The guard (3 lines, client-side, before the POST) is the only place the
 bug is detectable before funds are committed.
=====================================================================`);
process.exit(ok === 200 && bad === 400 ? 0 : 1);
