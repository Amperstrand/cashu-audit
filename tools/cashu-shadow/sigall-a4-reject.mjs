#!/usr/bin/env node
// A4 regen (2026-11-04): SIG_ALL melt REJECTION — witness signed over the
// wrong message (legacy pre-0.20.3 form: concat(secret‖C) WITHOUT quoteId).
// Complement to the corpus's sigall-unlock row: together they complete the
// SIG_ALL row of the three-way spending-condition matrix per arm.
// Arms: cashu-cf (miniflare, 6cd249e bundle), gonuts v0.16.0 :4470,
//       nutshell 0.20.3 :4472, cdk 0.18.1 :4474 — /v1/info asserted first.
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

const CF = '/root/src/cashu-cf';
const { cfTransport, httpTransport } = await import('./lib/transports.mjs');
const { makeMinter, identity } = await import('./lib/wire.mjs');

process.env.CASHU_TS_PATH = join(CF, 'node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js');
const cashuTs = await import(join(CF, 'node_modules/@cashu/cashu-ts/lib/cashu-ts.es.js'));
const noble = await import(join(CF, 'node_modules/@noble/hashes/utils.js'));
const { secp256k1, schnorr } = await import(join(CF, 'node_modules/@noble/curves/secp256k1.js'));
const { sha256: nobleSha256 } = await import(join(CF, 'node_modules/@noble/hashes/sha256.js'));
const w = makeMinter(cashuTs, noble);

const arms = [];
const cf = await cfTransport(CF, {});
arms.push({ name: 'cashu-cf@6cd249e', t: cf.transport, dispose: cf.dispose });
for (const [name, url] of [['gonuts-v0.16.0', 'http://127.0.0.1:4470'], ['nutshell-0.20.3', 'http://127.0.0.1:4472'], ['cdk-0.18.1', 'http://127.0.0.1:4474']]) {
  arms.push({ name, t: httpTransport(url), dispose: async () => {} });
}

const rows = [];
try {
  for (const arm of arms) {
    // identity FIRST (#40 rule): refuse to attribute results to an unverified arm
    const info = await arm.t('/v1/info', 'GET');
    const version = info.body?.version;
    const expected = { 'cashu-cf@6cd249e': null, 'gonuts-v0.16.0': 'gonuts/0.4.0', 'nutshell-0.20.3': 'Nutshell/0.20.3', 'cdk-0.18.1': 'cdk-mintd/0.18.1' }[arm.name];
    if (expected && version !== expected) throw new Error(`${arm.name}: identity mismatch — /v1/info says "${version}", expected "${expected}" — ABORT (wrong-mint rule)`);

    const priv = noble.randomBytes(32);
    const secret = JSON.stringify(['P2PK', { nonce: noble.bytesToHex(noble.randomBytes(16)), data: noble.bytesToHex(secp256k1.getPublicKey(priv, true)), tags: [['sigflag', 'SIG_ALL'], ['n_sigs', '1']] }]);
    const m = await w.mintWithSecret(arm.t, 8, secret);
    const q = await w.meltQuote(arm.t, 4);
    const canonical = w.sigAllMeltMessage([m.proof], [], q.body.quote);
    const variants = {
      // documented-lenience probe: legacy pre-0.20.3 form (no quoteId) —
      // cashu-cf's compat window (UPSTREAM-AUDIT 3.22) is EXPECTED to accept.
      legacy_no_quote: canonical.slice(0, -q.body.quote.length),
      garbage_suffix: w.sigAllMeltMessage([m.proof], [], 'deadbeef'),
      quote_first: q.body.quote + m.proof.secret + m.proof.C
    };
    const row = { arm: arm.name, identity: version ?? 'cashu-cf (no version field)', a4_wrong_message: {} };
    for (const [vname, msg] of Object.entries(variants)) {
      const sig = noble.bytesToHex(schnorr.sign(nobleSha256(new TextEncoder().encode(msg)), priv));
      let mm; let melt;
      if (vname === 'legacy_no_quote') {
        // one fresh conditioned proof + quote per variant (each melt consumes)
        mm = await w.mintWithSecret(arm.t, 8, secret);
        const qq = await w.meltQuote(arm.t, 4);
        melt = await arm.t('/v1/melt/bolt11', 'POST', { quote: qq.body.quote, inputs: [{ ...mm.proof, witness: JSON.stringify({ signatures: [sig] }) }], outputs: [] });
      } else {
        melt = await arm.t('/v1/melt/bolt11', 'POST', { quote: q.body.quote, inputs: [{ ...m.proof, witness: JSON.stringify({ signatures: [sig] }) }], outputs: [] });
      }
      row.a4_wrong_message[vname] = identity(melt);
    }
    rows.push(row);
    console.log(`${arm.name} [${row.identity}] -> ${JSON.stringify(row.a4_wrong_message)}`);
  }
} finally {
  for (const a of arms) await a.dispose();
}
const ts = new Date().toISOString().replace(/[:.]/g, '-');
writeFileSync(join('out', `sigall-a4-rejection-${ts}.json`), JSON.stringify({ probe: 'A4 SIG_ALL melt, witness over wrong (legacy no-quoteId) message', rows }, null, 2));
console.log(`capture: out/sigall-a4-rejection-${ts}.json`);
