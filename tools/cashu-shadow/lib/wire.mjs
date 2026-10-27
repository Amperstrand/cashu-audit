// cashu-shadow wire helpers — the cross-implementation knowledge extracted
// from the 2026-10-22..24 three-way study (cf/ns 0.20.3/cdk 0.18.1).
// Every rule here is empirically locked; see the study README for evidence.
import { createHash } from 'node:crypto';

export function pointToHex(p) {
  return Buffer.from(p.toRawBytes ? p.toRawBytes(true) : p.toBytes(true)).toString('hex');
}

// Blinded mint with an explicit secret; verifies the mint's blind signature
// via NUT-12 DLEQ (dleq: {e,s} hex on the wire → bytes).
export function makeMinter(cashuTs, noble) {
  const { blindMessage, unblindSignature, pointFromHex, verifyDLEQProof } = cashuTs;
  const { randomBytes, bytesToHex, hexToBytes } = noble;
  return {
    async mintWithSecret(t, sats, secret) {
      const keys = await t('/v1/keys', 'GET');
      const ks = keys.body.keysets.find(k => k.unit === 'sat' && k.active) ?? keys.body.keysets[0];
      const keysetId = ks.id;
      const pubKeys = ks.keys;
      const mq = await t('/v1/mint/quote/bolt11', 'POST', { amount: sats, unit: 'sat' });
      if (mq.status !== 200) throw new Error('quote create failed: ' + String(mq.text).slice(0, 120));
      let quote = mq.body.quote, state = mq.body.state;
      for (let i = 0; i < 80 && state !== 'PAID'; i++) {
        await new Promise(r => setTimeout(r, 300));
        const s = await t(`/v1/mint/quote/bolt11/${quote}`, 'GET');
        state = s.body?.state;
        if (!state) break;
        if (state !== 'UNPAID' && state !== 'PENDING' && state !== 'PAID') break;
      }
      if (state !== 'PAID') throw new Error('quote never PAID (state=' + state + ')');
      const bm = blindMessage(new TextEncoder().encode(secret));
      const minted = await t('/v1/mint/bolt11', 'POST', { quote, outputs: [{ amount: sats, B_: pointToHex(bm.B_), id: keysetId }] });
      if (minted.status !== 200) throw new Error('mint failed: ' + String(minted.text).slice(0, 160));
      const sig = minted.body.signatures[0];
      const A = pointFromHex(pubKeys[String(sats)]);
      const C = unblindSignature(pointFromHex(sig.C_), bm.r, A);
      let dleqOk = null;
      if (sig.dleq) {
        try { dleqOk = verifyDLEQProof({ e: hexToBytes(sig.dleq.e), s: hexToBytes(sig.dleq.s) }, bm.B_, pointFromHex(sig.C_), A); }
        catch (e) { dleqOk = 'error:' + String(e.message ?? e).slice(0, 50); }
      }
      return { keysetId, pubKeys, dleqOk, proof: { amount: sats, secret, C: pointToHex(C), id: keysetId }, ppk: Number(ks.input_fee_ppk ?? 0) };
    },
    async meltQuote(t, sats) {
      const mq = await t('/v1/mint/quote/bolt11', 'POST', { amount: sats, unit: 'sat' });
      return await t('/v1/melt/quote/bolt11', 'POST', { request: mq.body.request, unit: 'sat' });
    },
    // SIG_ALL canonical melt message: concat(secret_i‖C_i) ‖ quoteId —
    // IDENTICAL across cf/ns 0.20.3/cdk 0.18.1; schnorr over sha256(msg).
    sigAllMeltMessage(proofs, outputs, quoteId) {
      let msg = '';
      for (const p of proofs) msg += p.secret + p.C;
      for (const o of outputs ?? []) msg += String(o.amount) + o.B_;
      return msg + (quoteId ?? '');
    },
    // NUT-02 denominations for an amount (powers of two); ns rejects
    // single non-denomination outputs with opaque code-0 detail.
    denominations(amount) {
      const out = [];
      let rem = amount;
      for (let d = 1; rem > 0; d *= 2) { if (rem & d) { out.push(d); rem -= d; } }
      return out;
    },
    sha256Hex(bytes) { return createHash('sha256').update(bytes).digest('hex'); },
    randomBytes, bytesToHex
  };
}

export const identity = (r) => ({
  status: r.status,
  code: r.body?.code ?? null,
  error: r.body?.error ?? r.body?.detail ?? null,
  detail: typeof r.body?.detail === 'string' ? r.body.detail.slice(0, 90) : (typeof r.body?.detail === 'number' ? r.body.detail : undefined)
});
