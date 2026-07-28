/**
 * Cashu E2E Spending Conditions Test Suite — Layer 4
 *
 * Tests P2PK/HTLC/SIG_ALL spending conditions against a live mint.
 * Implements the NUT-10 compatibility checker scenarios from #1009.
 *
 * Run from cashu-cf directory:
 *   node ../cashu-audit/e2e/lib/spending_conditions.js https://testnut.cashu.exchange
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

function now() { return Math.floor(Date.now() / 1000); }

/**
 * Create P2PK proofs locked to specific spending conditions.
 * Returns proofs with the given secret configuration.
 */
async function createP2PKProofs(e2e, amount, config) {
  const { id: keysetId, keys: mintKeys } = await e2e.getActiveKeyset();
  const amounts = decomposeAmount(amount);
  const outputs = [];
  const tokenData = [];

  for (const amt of amounts) {
    const secretStr = typeof config.secret === 'function' ? config.secret() : config.secret;
    const secretBytes = new TextEncoder().encode(secretStr);
    const blinded = blindMessage(secretBytes);
    outputs.push({ amount: amt, id: keysetId, B_: bytesToHex(blinded.B_.toRawBytes(true)) });
    tokenData.push({ secretStr, r: blinded.r, amount: amt });
  }

  // Need a paid quote to mint
  const quoteResp = await e2e.http('POST', '/v1/mint/quote/bolt11', { unit: 'sat', amount });
  if (quoteResp.status !== 200) throw new Error(`Quote failed: ${quoteResp.status}`);
  let state = quoteResp.data.state;
  for (let i = 0; i < 20 && state !== 'PAID'; i++) {
    await new Promise(r => setTimeout(r, 500));
    state = (await e2e.http('GET', `/v1/mint/quote/bolt11/${quoteResp.data.quote}`)).data.state;
  }
  if (state !== 'PAID') throw new Error('Quote not PAID');

  const mintResp = await e2e.http('POST', '/v1/mint/bolt11', { quote: quoteResp.data.quote, outputs });
  if (mintResp.status !== 200) throw new Error(`Mint failed: ${mintResp.status} ${JSON.stringify(mintResp.data).slice(0, 100)}`);

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
      witness: config.witness,
    });
  }
  return { proofs, keysetId };
}

/**
 * Try to swap proofs. Returns { accepted, status, data }.
 */
async function trySwap(e2e, proofs, keysetId) {
  const keysets = await e2e.getKeysets();
  const ksInfo = keysets.keysets.find(k => k.id === keysetId);
  const feePpk = ksInfo?.input_fee_ppk || 0;
  const totalInput = proofs.reduce((s, p) => s + p.amount, 0);
  const fee = Math.ceil((proofs.length * feePpk) / 1000);
  const outputTotal = Math.max(1, totalInput - fee);

  const outputs = [];
  for (const amt of decomposeAmount(outputTotal)) {
    const secret = bytesToHex(randomBytes(32));
    const blinded = blindMessage(new TextEncoder().encode(secret));
    outputs.push({ amount: amt, id: keysetId, B_: bytesToHex(blinded.B_.toRawBytes(true)) });
  }

  // Include witness if present
  const swapInputs = proofs.map(p => {
    const input = { amount: p.amount, secret: p.secret, C: p.C, id: p.id };
    if (p.witness !== undefined) input.witness = p.witness;
    return input;
  });

  const resp = await e2e.http('POST', '/v1/swap', { inputs: swapInputs, outputs });
  return { accepted: resp.status === 200, status: resp.status, data: resp.data };
}

// ===== SCENARIOS =====

async function scenario_unsigned_fails(e2e) {
  const alice = genKeypair();
  const { proofs, keysetId } = await createP2PKProofs(e2e, 8, {
    secret: JSON.stringify(['P2PK', { nonce: 'a'.repeat(16), data: alice.compressed }]),
    witness: undefined, // No witness — should fail
  });
  const result = await trySwap(e2e, proofs, keysetId);
  return {
    name: 'p2pk_swap_unsigned_fails',
    pass: !result.accepted,
    detail: result.accepted ? 'ERROR: unsigned swap accepted!' : `Rejected: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_signed_succeeds(e2e) {
  const alice = genKeypair();
  const secretStr = JSON.stringify(['P2PK', { nonce: 'b'.repeat(16), data: alice.compressed }]);
  const sig = schnorrSign(secretStr, alice.priv);
  const { proofs, keysetId } = await createP2PKProofs(e2e, 8, {
    secret: secretStr,
    witness: JSON.stringify({ signatures: [sig] }),
  });
  const result = await trySwap(e2e, proofs, keysetId);
  return {
    name: 'p2pk_swap_signed_succeeds',
    pass: result.accepted,
    detail: result.accepted ? 'Swap accepted with valid signature' : `Failed: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_wrong_signer_fails(e2e) {
  const alice = genKeypair();
  const bob = genKeypair();
  const secretStr = JSON.stringify(['P2PK', { nonce: 'c'.repeat(16), data: alice.compressed }]);
  const sig = schnorrSign(secretStr, bob.priv); // Wrong key!
  const { proofs, keysetId } = await createP2PKProofs(e2e, 8, {
    secret: secretStr,
    witness: JSON.stringify({ signatures: [sig] }),
  });
  const result = await trySwap(e2e, proofs, keysetId);
  return {
    name: 'p2pk_wrong_signer_fails',
    pass: !result.accepted,
    detail: result.accepted ? 'ERROR: wrong signer accepted!' : `Rejected: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_htlc_preimage_only_succeeds(e2e) {
  const preimage = bytesToHex(randomBytes(32));
  const hashLock = bytesToHex(sha256(hexToBytes(preimage)));
  const secretStr = JSON.stringify(['HTLC', { nonce: 'd'.repeat(16), data: hashLock }]);
  const { proofs, keysetId } = await createP2PKProofs(e2e, 8, {
    secret: secretStr,
    witness: JSON.stringify({ preimage }),
  });
  const result = await trySwap(e2e, proofs, keysetId);
  return {
    name: 'htlc_preimage_only_succeeds',
    pass: result.accepted,
    detail: result.accepted ? 'HTLC preimage-only swap accepted' : `Failed: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_htlc_wrong_preimage_fails(e2e) {
  const preimage = bytesToHex(randomBytes(32));
  const wrongPreimage = bytesToHex(randomBytes(32));
  const hashLock = bytesToHex(sha256(hexToBytes(preimage)));
  const secretStr = JSON.stringify(['HTLC', { nonce: 'e'.repeat(16), data: hashLock }]);
  const { proofs, keysetId } = await createP2PKProofs(e2e, 8, {
    secret: secretStr,
    witness: JSON.stringify({ preimage: wrongPreimage }),
  });
  const result = await trySwap(e2e, proofs, keysetId);
  return {
    name: 'htlc_wrong_preimage_fails',
    pass: !result.accepted,
    detail: result.accepted ? 'ERROR: wrong preimage accepted!' : `Rejected: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_htlc_preimage_and_sig_succeeds(e2e) {
  const alice = genKeypair();
  const preimage = bytesToHex(randomBytes(32));
  const hashLock = bytesToHex(sha256(hexToBytes(preimage)));
  const secretStr = JSON.stringify(['HTLC', {
    nonce: 'f'.repeat(16),
    data: hashLock,
    tags: [['pubkeys', alice.compressed], ['n_sigs', '1']],
  }]);
  const sig = schnorrSign(secretStr, alice.priv);
  const { proofs, keysetId } = await createP2PKProofs(e2e, 8, {
    secret: secretStr,
    witness: JSON.stringify({ preimage, signatures: [sig] }),
  });
  const result = await trySwap(e2e, proofs, keysetId);
  return {
    name: 'htlc_preimage_and_sig_succeeds',
    pass: result.accepted,
    detail: result.accepted ? 'HTLC preimage+sig swap accepted' : `Failed: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_locktime_expired_refund_succeeds(e2e) {
  const alice = genKeypair();
  const refund = genKeypair();
  const secretStr = JSON.stringify(['P2PK', {
    nonce: '10'.repeat(8),
    data: alice.compressed,
    tags: [['locktime', '1'], ['refund', refund.compressed], ['n_sigs_refund', '1']],
  }]);
  const refundSig = schnorrSign(secretStr, refund.priv);
  const { proofs, keysetId } = await createP2PKProofs(e2e, 8, {
    secret: secretStr,
    witness: JSON.stringify({ signatures: [refundSig] }),
  });
  const result = await trySwap(e2e, proofs, keysetId);
  return {
    name: 'p2pk_locktime_expired_refund_succeeds',
    pass: result.accepted,
    detail: result.accepted ? 'Refund path swap accepted after locktime expiry' : `Failed: ${result.data.detail?.slice(0, 60)}`,
  };
}

async function scenario_locktime_expired_primary_still_works(e2e) {
  const alice = genKeypair();
  const refund = genKeypair();
  const secretStr = JSON.stringify(['P2PK', {
    nonce: '11'.repeat(8),
    data: alice.compressed,
    tags: [['locktime', '1'], ['refund', refund.compressed], ['n_sigs_refund', '1']],
  }]);
  const aliceSig = schnorrSign(secretStr, alice.priv);
  const { proofs, keysetId } = await createP2PKProofs(e2e, 8, {
    secret: secretStr,
    witness: JSON.stringify({ signatures: [aliceSig] }),
  });
  const result = await trySwap(e2e, proofs, keysetId);
  return {
    name: 'p2pk_locktime_expired_primary_still_works',
    pass: result.accepted,
    detail: result.accepted
      ? 'Primary path works after locktime expiry (correct)'
      : `Primary path rejected after locktime (potential #1009 bug): ${result.data.detail?.slice(0, 60)}`,
  };
}

const SCENARIOS = [
  scenario_unsigned_fails,
  scenario_signed_succeeds,
  scenario_wrong_signer_fails,
  scenario_htlc_preimage_only_succeeds,
  scenario_htlc_wrong_preimage_fails,
  scenario_htlc_preimage_and_sig_succeeds,
  scenario_locktime_expired_refund_succeeds,
  scenario_locktime_expired_primary_still_works,
];

async function main() {
  const mintUrl = process.argv[2] || 'http://localhost:8787';
  console.log(`\nCashu Spending Conditions E2E — Layer 4`);
  console.log(`Target: ${mintUrl}`);
  console.log(`${'='.repeat(60)}\n`);

  const e2e = new CashuE2E(mintUrl);
  if (!(await e2e.isHealthy())) {
    console.log(`❌ Mint not reachable\n`);
    process.exit(1);
  }

  let passed = 0, failed = 0;
  for (const scenario of SCENARIOS) {
    try {
      const result = await scenario(e2e);
      const emoji = result.pass ? '✅' : '❌';
      console.log(`${emoji} ${result.name}: ${result.detail}`);
      if (result.pass) passed++; else failed++;
    } catch (e) {
      console.log(`⚠️  ${scenario.name}: Exception — ${e.message}`);
      failed++;
    }
    await new Promise(r => setTimeout(r, 300)); // Rate limit
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`Results: ${passed} PASS, ${failed} FAIL out of ${SCENARIOS.length}`);
  console.log(`${'='.repeat(60)}\n`);

  process.exit(failed > 0 ? 1 : 0);
}

if (require.main === module) main();

module.exports = {
  SCENARIOS,
  createP2PKProofs,
  trySwap,
  genKeypair,
  schnorrSign,
};
