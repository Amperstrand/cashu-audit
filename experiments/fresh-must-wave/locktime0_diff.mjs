// Locktime-0 differential: same proof shapes, run under 4.11.0 and 4.13.0
import { createP2PKsecret, signP2PKProof, verifyP2PKSpendingConditions, createRandomSecretKey } from '@cashu/cashu-ts';


const lockPriv = createRandomSecretKey();
const refundPriv = createRandomSecretKey();
// compressed pubkeys via noble secp256k1

import { secp256k1 } from '@noble/curves/secp256k1.js';
import { bytesToHex } from '@noble/curves/utils.js';
const lockPub = bytesToHex(secp256k1.getPublicKey(lockPriv, true));
const refundPub = bytesToHex(secp256k1.getPublicKey(refundPriv, true));

const C = bytesToHex(secp256k1.getPublicKey(createRandomSecretKey(), true));
const now = Math.floor(Date.now() / 1000);
const shapes = {
  lt0:      [["locktime", "0"]],
  ltFuture: [["locktime", String(now + 3600)]],
  ltPast:   [["locktime", String(now - 3600)]],
  lt0refund: [["locktime", "0"], ["refund", refundPub]],
  ltFutureRefund: [["locktime", String(now + 3600)], ["refund", refundPub]],
};

for (const [name, tags] of Object.entries(shapes)) {
  for (const signer of ["lock", "refund"]) {
    if (signer === "refund" && !tags.some(t => t[0] === "refund")) continue;
    const secret = createP2PKsecret(lockPub, tags);
    const proof = { amount: 1, id: "00".repeat(8), secret, C };
    try {
      const signed = signP2PKProof(proof, signer === "lock" ? lockPriv : refundPriv);
      const v = verifyP2PKSpendingConditions(signed);
      console.log(`${name}\t${signer}\t${JSON.stringify(v).slice(0, 90)}`);
    } catch (e) {
      console.log(`${name}\t${signer}\tTHROWS ${String(e.message).slice(0, 80)}`);
    }
  }
}
