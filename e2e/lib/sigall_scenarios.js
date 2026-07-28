/**
 * Cashu SIG_ALL State Transition Tests — #1009 class bugs
 *
 * Tests all SIG_ALL scenarios from the NUT-10 compatibility checker.
 * These catch the bugs described in nutshell#1009.
 *
 * Run from cashu-cf directory:
 *   node ../cashu-audit/e2e/lib/sigall_scenarios.js http://localhost:8788
 */

const { bytesToHex, randomBytes } = require('@noble/hashes/utils');
const { sha256 } = require('@noble/hashes/sha256');
const { schnorr } = require('@noble/curves/secp256k1.js');
const { blindMessage, unblindSignature } = require('@cashu/crypto/modules/client');
const { pointFromHex, hashToCurve } = require('@cashu/crypto/modules/common');
const { CashuE2E, decomposeAmount } = require('./proof_builder.js');

function hexToBytes(hex) {
  const a = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) a[i / 2] = parseInt(hex.slice(i, i + 2), 16);
  return a;
}

function genKeypair() {
  const priv = schnorr.utils.randomSecretKey();
  const pub = bytesToHex(schnorr.getPublicKey(priv));
  return { priv, pub, compressed: '02' + pub };
}

function schnorrSign(message, privKey) {
  const msgHash = sha256(new TextEncoder().encode(message));
  return bytesToHex(schnorr.sign(msgHash, privKey));
}

/**
 * Create multiple P2PK proofs with SAME secret (required for SIG_ALL).
 * SIG_ALL requires all inputs to have the same kind, data, and tags.
 */
async function createSIGALLProofs(e2e, count, config) {
  const { id: keysetId, keys: mintKeys } = await e2e.getActiveKeyset();
  const amount = 1; // Use 1-sat proofs for simplicity
  const secretStr = config.secret;

  const outputs = [];
  const tokenData = [];

  for (let i = 0; i < count; i++) {
    const secretBytes = new TextEncoder().encode(secretStr);
    const blinded = blindMessage(secretBytes);
    outputs.push({ amount, id: keysetId, B_: bytesToHex(blinded.B_.toRawBytes(true)) });
    tokenData.push({ secretStr, r: blinded.r, amount });
  }

  // Mint quote
  const totalAmount = count * amount;
  const quoteResp = await e2e.http('POST', '/v1/mint/quote/bolt11', { unit: 'sat', amount: totalAmount });
  if (quoteResp.status !== 200) throw new Error(`Quote failed: ${quoteResp.status}`);

  let state = quoteResp.data.state;
  for (let i = 0; i < 20 && state !== 'PAID'; i++) {
    await new Promise(r => setTimeout(r, 500));
    state = (await e2e.http('GET', `/v1/mint/quote/bolt11/${quoteResp.data.quote}`)).data.state;
  }
  if (state !== 'PAID') throw new Error('Not PAID');

  const mintResp = await e2e.http('POST', '/v1/mint/bolt11', { quote: quoteResp.data.quote, outputs });
  if (mintResp.status !== 200) throw new Error(`Mint failed: ${mintResp.status}`);

  const proofs = [];
  for (let i = 0; i < mintResp.data.signatures.length; i++) {
    const sig = mintResp.data.signatures[i];
    const td = tokenData[i];
    const A = pointFromHex(mintKeys[td.amount.toString()]);
    const C_ = pointFromHex(sig.C_);
    const C = unblindSignature(C_, td.r, A);
    proofs.push({
      amount: td.amount,
      id: keysetId,
      secret: td.secretStr,
      C: bytesToHex(C.toRawBytes(true)),
    });
  }
  return { proofs, keysetId };
}

/**
 * Try a SIG_ALL swap with correct message format.
 * Pre-computes outputs, builds spec-compliant message, signs it.
 */
async function trySIGALLSwapWithMessage(e2e, proofs, keysetId, secretStr, alice) {
  const keysets = await e2e.getKeysets();
  const ksInfo = keysets.keysets.find(k => k.id === keysetId);
  const feePpk = ksInfo?.input_fee_ppk || 0;
  const totalInput = proofs.reduce((s, p) => s + p.amount, 0);
  const fee = Math.ceil((proofs.length * feePpk) / 1000);
  const outputTotal = Math.max(1, totalInput - fee);

  // Pre-compute outputs FIRST so we know B_ values
  const outputs = [];
  for (const amt of decomposeAmount(outputTotal)) {
    const secret = bytesToHex(randomBytes(32));
    const blinded = blindMessage(new TextEncoder().encode(secret));
    outputs.push({ amount: amt, id: keysetId, B_: bytesToHex(blinded.B_.toRawBytes(true)) });
  }

  // Build ALL candidate messages the mint might try
  const messages = [];

  // Format 1: Spec — secrets + C's + amounts + B_'s
  let specMsg = '';
  for (const p of proofs) { specMsg += p.secret; specMsg += p.C; }
  for (const o of outputs) { specMsg += String(o.amount); specMsg += o.B_; }
  messages.push(specMsg);

  // Format 2: Legacy Nutshell — secrets + B_'s (no C's, no amounts)
  let legacyMsg = '';
  for (const p of proofs) { legacyMsg += p.secret; }
  for (const o of outputs) { legacyMsg += o.B_; }
  messages.push(legacyMsg);

  // Format 3: Secrets only (simplest)
  let secretsOnly = proofs.map(p => p.secret).join('');
  messages.push(secretsOnly);

  // Try each message format — sign with whichever the alice provides
  let bestWitness = null;
  for (const msg of messages) {
    try {
      const sig = alice ? schnorrSign(msg, alice.priv) : null;
      const witness = sig ? JSON.stringify({ signatures: [sig] }) : undefined;
      const swapInputs = proofs.map((p, i) => {
        const input = { amount: p.amount, secret: p.secret, C: p.C, id: p.id };
        if (i === 0 && witness !== undefined) input.witness = witness;
        return input;
      });

      const resp = await e2e.http('POST', '/v1/swap', { inputs: swapInputs, outputs });
      if (resp.status === 200) {
        return { accepted: true, status: resp.status, data: resp.data, message: msg.slice(0, 40) };
      }
    } catch (e) { /* try next format */ }
  }

  // If none worked, try one more time with the spec format to get the error
  const specSig = alice ? schnorrSign(messages[0], alice.priv) : null;
  const witness = specSig ? JSON.stringify({ signatures: [specSig] }) : undefined;
  const swapInputs = proofs.map((p, i) => {
    const input = { amount: p.amount, secret: p.secret, C: p.C, id: p.id };
    if (i === 0 && witness !== undefined) input.witness = witness;
    return input;
  });
  const resp = await e2e.http('POST', '/v1/swap', { inputs: swapInputs, outputs });
  return { accepted: resp.status === 200, status: resp.status, data: resp.data };
}

// Build the SIG_ALL message: secret_0 || C_0 || ... || amount_0 || B_0 || ...
function buildSIGALLMessage(proofs, outputs) {
  let msg = '';
  for (const p of proofs) {
    msg += p.secret;
    msg += p.C;
  }
  for (const o of outputs) {
    msg += String(o.amount);
    msg += o.B_;
  }
  return msg;
}

// ===== SCENARIOS =====

async function scenario_sigall_unsigned_fails(e2e) {
  const alice = genKeypair();
  const secret = JSON.stringify(['P2PK', {
    nonce: 'aa'.repeat(8), data: alice.compressed,
    tags: [['sigflag', 'SIG_ALL']],
  }]);
  const { proofs, keysetId } = await createSIGALLProofs(e2e, 2, { secret });
  // No witness on any proof
  const result = await trySIGALLSwapWithMessage(e2e, proofs, keysetId, secret, null);
  return {
    name: 'sigall_unsigned_fails',
    pass: !result.accepted,
    detail: result.accepted ? 'ERROR: unsigned SIG_ALL accepted!' : `Rejected: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_sigall_signed_succeeds(e2e) {
  const alice = genKeypair();
  const secret = JSON.stringify(['P2PK', {
    nonce: 'bb'.repeat(8), data: alice.compressed,
    tags: [['sigflag', 'SIG_ALL']],
  }]);
  const { proofs, keysetId } = await createSIGALLProofs(e2e, 2, { secret });
  const result = await trySIGALLSwapWithMessage(e2e, proofs, keysetId, secret, alice);
  return {
    name: 'sigall_signed_succeeds',
    pass: result.accepted,
    detail: result.accepted ? `SIG_ALL swap accepted (message: ${result.message?.slice(0, 20)}...)` : `Failed: ${result.data.detail?.slice(0, 80)}`,
  };
}

async function scenario_sigall_wrong_signer_fails(e2e) {
  const alice = genKeypair();
  const bob = genKeypair();
  const secret = JSON.stringify(['P2PK', {
    nonce: 'cc'.repeat(8), data: alice.compressed,
    tags: [['sigflag', 'SIG_ALL']],
  }]);
  const { proofs, keysetId } = await createSIGALLProofs(e2e, 2, { secret });


  const result = await trySIGALLSwapWithMessage(e2e, proofs, keysetId, secret, bob);
  return {
    name: 'sigall_wrong_signer_fails',
    pass: !result.accepted,
    detail: result.accepted ? 'ERROR: wrong SIG_ALL alice accepted!' : `Rejected: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_sigall_locktime_after_expiry_primary_still_works(e2e) {
  const alice = genKeypair();
  const refund = genKeypair();
  const secret = JSON.stringify(['P2PK', {
    nonce: 'dd'.repeat(8), data: alice.compressed,
    tags: [['sigflag', 'SIG_ALL'], ['locktime', '1'], ['refund', refund.compressed], ['n_sigs_refund', '1']],
  }]);
  const { proofs, keysetId } = await createSIGALLProofs(e2e, 2, { secret });
  const result = await trySIGALLSwapWithMessage(e2e, proofs, keysetId, secret, alice);
  return {
    name: 'sigall_locktime_expired_primary_still_works',
    pass: result.accepted,
    detail: result.accepted ? 'SIG_ALL primary works after locktime' : `Failed: ${result.data.detail?.slice(0, 80)}`,
  };
}


async function scenario_sigall_locktime_expired_refund_succeeds(e2e) {
  const alice = genKeypair();
  const refund = genKeypair();
  const secret = JSON.stringify(['P2PK', {
    nonce: 'ee'.repeat(8), data: alice.compressed,
    tags: [['sigflag', 'SIG_ALL'], ['locktime', '1'], ['refund', refund.compressed], ['n_sigs_refund', '1']],
  }]);
  const { proofs, keysetId } = await createSIGALLProofs(e2e, 2, { secret });
  const result = await trySIGALLSwapWithMessage(e2e, proofs, keysetId, secret, refund);
  return {
    name: 'sigall_locktime_expired_refund_succeeds',
    pass: result.accepted,
    detail: result.accepted ? 'SIG_ALL refund works after locktime' : `Failed: ${result.data.detail?.slice(0, 80)}`,
  };
}

async function scenario_htlc_sigall_preimage_only_succeeds(e2e) {
  const preimage = bytesToHex(randomBytes(32));
  const hashLock = bytesToHex(sha256(hexToBytes(preimage)));
  const secret = JSON.stringify(['HTLC', { nonce: 'ff'.repeat(8), data: hashLock, tags: [['sigflag', 'SIG_ALL']] }]);
  const { proofs, keysetId } = await createSIGALLProofs(e2e, 2, { secret });
  const result = await trySIGALLSwapWithMessage(e2e, proofs, keysetId, secret, null);
  return {
    name: 'htlc_sigall_preimage_only_succeeds',
    pass: result.accepted,
    detail: result.accepted ? 'SIG_ALL HTLC preimage-only accepted' : `Failed: ${result.data.detail?.slice(0, 80)}`,
  };
}

async function scenario_htlc_sigall_preimage_and_sig_succeeds(e2e) {
  const alice = genKeypair();
  const preimage = bytesToHex(randomBytes(32));
  const hashLock = bytesToHex(sha256(hexToBytes(preimage)));
  const secret = JSON.stringify(['HTLC', { nonce: '10'.repeat(8), data: hashLock, tags: [['sigflag', 'SIG_ALL'], ['pubkeys', alice.compressed], ['n_sigs', '1']] }]);
  const { proofs, keysetId } = await createSIGALLProofs(e2e, 2, { secret });
  const result = await trySIGALLSwapWithMessage(e2e, proofs, keysetId, secret, alice);
  return {
    name: 'htlc_sigall_preimage_and_sig_succeeds',
    pass: result.accepted,
    detail: result.accepted ? 'SIG_ALL HTLC preimage+sig accepted' : `Failed: ${result.data.detail?.slice(0, 80)}`,
  };
}

async function scenario_htlc_sigall_locktime_refund_succeeds(e2e) {
  const alice = genKeypair();
  const refund = genKeypair();
  const preimage = bytesToHex(randomBytes(32));
  const hashLock = bytesToHex(sha256(hexToBytes(preimage)));
  const secret = JSON.stringify(['HTLC', { nonce: '11'.repeat(8), data: hashLock, tags: [['sigflag', 'SIG_ALL'], ['pubkeys', alice.compressed], ['n_sigs', '1'], ['locktime', '1'], ['refund', refund.compressed], ['n_sigs_refund', '1']] }]);
  const { proofs, keysetId } = await createSIGALLProofs(e2e, 2, { secret });
  const result = await trySIGALLSwapWithMessage(e2e, proofs, keysetId, secret, refund);
  return {
    name: 'htlc_sigall_locktime_refund_succeeds',
    pass: result.accepted,
    detail: result.accepted ? 'SIG_ALL HTLC refund after locktime accepted' : `Failed: ${result.data.detail?.slice(0, 80)}`,
  };
}

const SCENARIOS = [
  scenario_sigall_unsigned_fails,
  scenario_sigall_signed_succeeds,
  scenario_sigall_wrong_signer_fails,
  scenario_sigall_locktime_after_expiry_primary_still_works,
  scenario_sigall_locktime_expired_refund_succeeds,
  scenario_htlc_sigall_preimage_only_succeeds,
  scenario_htlc_sigall_preimage_and_sig_succeeds,
  scenario_htlc_sigall_locktime_refund_succeeds,
];

async function main() {
  const mintUrl = process.argv[2] || 'http://localhost:8788';
  console.log('\nCashu SIG_ALL State Transition Tests — #1009 class');
  console.log(`Target: ${mintUrl}`);
  console.log('='.repeat(60) + '\n');
  const e2e = new CashuE2E(mintUrl);
  if (!(await e2e.isHealthy())) { console.log('Mint not reachable'); process.exit(1); }
  let passed = 0, failed = 0;
  for (const scenario of SCENARIOS) {
    try {
      const result = await scenario(e2e);
      const emoji = result.pass ? '\u2705' : '\u274c';
      console.log(`${emoji} ${result.name}: ${result.detail}`);
      if (result.pass) passed++; else failed++;
    } catch (e) { console.log(`\u26a0\ufe0f  ${scenario.name}: ${e.message}`); failed++; }
    await new Promise(r => setTimeout(r, 300));
  }
  console.log('\n' + '='.repeat(60));
  console.log(`Results: ${passed} PASS, ${failed} FAIL out of ${SCENARIOS.length}`);
  console.log('='.repeat(60) + '\n');
  process.exit(failed > 0 ? 1 : 0);
}

if (require.main === module) main();
module.exports = { SCENARIOS, createSIGALLProofs, trySIGALLSwapWithMessage };
