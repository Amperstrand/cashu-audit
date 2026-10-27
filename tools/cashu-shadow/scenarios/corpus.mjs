// cashu-shadow scenario corpus — the three-way-locked matrix as data-driven
// steps. Each scenario gets {A, B} transports (the two mints under
// comparison) + the shared wire helpers, and returns rows of identities.
export const corpus = [
  {
    name: 'R4 keys/{bogus}',
    run: async ({ A, B }) => {
      const a = await A.t('/v1/keys/decafbaddecafbad', 'GET');
      const b = await B.t('/v1/keys/decafbaddecafbad', 'GET');
      return [{ label: 'keys-bogus', a, b }];
    }
  },
  {
    name: 'R5 checkstate malformed-Y',
    run: async ({ A, B }) => {
      const badY = { Ys: ['02' + 'zz'.repeat(32)] };
      return [{ label: 'checkstate-malformed', a: await A.t('/v1/checkstate', 'POST', badY), b: await B.t('/v1/checkstate', 'POST', badY) }];
    }
  },
  {
    name: 'H1 mint + DLEQ',
    run: async ({ A, B, w, randomBytes, bytesToHex }) => {
      const a = await w.mintWithSecret(A.t, 8, 'shadow-a-' + bytesToHex(randomBytes(6)));
      const b = await w.mintWithSecret(B.t, 8, 'shadow-b-' + bytesToHex(randomBytes(6)));
      return [{ label: 'mint-dleq', a: { status: 200, body: { code: String(a.dleqOk) } }, b: { status: 200, body: { code: String(b.dleqOk) } } }, { __state: { a, b } }];
    }
  },
  {
    name: 'A1 swap forged off-curve C',
    run: async ({ A, B, secp, state, randomBytes, bytesToHex }) => {
      const mk = (kid) => ({ inputs: [{ amount: 8, secret: 'forged-' + bytesToHex(randomBytes(6)), C: '02' + 'ab'.repeat(32), id: kid }], outputs: [{ amount: 8, B_: bytesToHex(secp.getPublicKey(randomBytes(32), true)), id: kid }] });
      return [{ label: 'swap-forged', a: await A.t('/v1/swap', 'POST', mk(state.a.keysetId)), b: await B.t('/v1/swap', 'POST', mk(state.b.keysetId)) }];
    }
  },
  {
    name: 'A2 swap duplicate proof',
    run: async ({ A, B, secp, state, randomBytes, bytesToHex }) => {
      const dup = (p, kid) => ({ inputs: [p, p], outputs: [{ amount: 8, B_: bytesToHex(secp.getPublicKey(randomBytes(32), true)), id: kid }, { amount: 8, B_: bytesToHex(secp.getPublicKey(randomBytes(32), true)), id: kid }] });
      return [{ label: 'swap-duplicate', a: await A.t('/v1/swap', 'POST', dup(state.a.proof, state.a.keysetId)), b: await B.t('/v1/swap', 'POST', dup(state.b.proof, state.b.keysetId)) }];
    }
  },
  {
    name: 'A3 swap P2PK witness-less',
    run: async ({ A, B, secp, w, randomBytes, bytesToHex }) => {
      const mkSecret = () => JSON.stringify(['P2PK', { nonce: bytesToHex(randomBytes(16)), data: bytesToHex(secp.getPublicKey(randomBytes(32), true)), tags: [['sigflag', 'SIG_INPUTS'], ['n_sigs', '1']] }]);
      const a = await w.mintWithSecret(A.t, 8, mkSecret());
      const b = await w.mintWithSecret(B.t, 8, mkSecret());
      const body = (m) => ({ inputs: [m.proof], outputs: [{ amount: Math.max(1, 8 - Math.ceil(m.ppk / 1000)), B_: bytesToHex(secp.getPublicKey(randomBytes(32), true)), id: m.keysetId }] });
      return [{ label: 'swap-p2pk-witnessless', a: await A.t('/v1/swap', 'POST', body(a)), b: await B.t('/v1/swap', 'POST', body(b)) }];
    }
  },
  {
    name: 'A6b mint replay same-outputs',
    run: async ({ A, B, w, randomBytes, bytesToHex }) => {
      const replay = async (t) => {
        const keys = await t('/v1/keys', 'GET');
        const kid = keys.body.keysets[0].id;
        const mq = await t('/v1/mint/quote/bolt11', 'POST', { amount: 8, unit: 'sat' });
        let state = mq.body.state;
        for (let i = 0; i < 80 && state !== 'PAID'; i++) {
          await new Promise(r => setTimeout(r, 300));
          state = (await t('/v1/mint/quote/bolt11/' + mq.body.quote, 'GET')).body?.state;
          if (!state || (state !== 'UNPAID' && state !== 'PENDING' && state !== 'PAID')) break;
        }
        const bm = (await import('file://' + process.env.CASHU_TS_PATH)).blindMessage(new TextEncoder().encode('replay-' + bytesToHex(randomBytes(6))));
        const body = { quote: mq.body.quote, outputs: [{ amount: 8, B_: Buffer.from(bm.B_.toRawBytes ? bm.B_.toRawBytes(true) : bm.B_.toBytes(true)).toString('hex'), id: kid }] };
        const first = await t('/v1/mint/bolt11', 'POST', body);
        const second = await t('/v1/mint/bolt11', 'POST', body);
        return { second, sig1: first.body?.signatures?.[0]?.C_, firstStatus: first.status };
      };
      const a = await replay(A.t);
      const b = await replay(B.t);
      const identical = (r) => r.second?.body?.signatures?.[0]?.C_ === r.sig1;
      return [{ label: 'mint-replay', a: a.second, b: b.second, note: `a-identical=${identical(a)} b-identical=${identical(b)}` }];
    }
  },
  {
    name: 'A7 fee-aware swap + checkstate SPENT',
    run: async ({ A, B, secp, w, randomBytes, bytesToHex, cashuTs }) => {
      const step = async (t) => {
        const m = await w.mintWithSecret(t, 8, 'check-' + bytesToHex(randomBytes(6)));
        const fee = Math.ceil(m.ppk / 1000);
        const outs = w.denominations(8 - fee).map(amount => ({ amount, B_: bytesToHex(secp.getPublicKey(randomBytes(32), true)), id: m.keysetId }));
        const sw = await t('/v1/swap', 'POST', { inputs: [m.proof], outputs: outs });
        const Y = bytesToHex(cashuTs.hashToCurve(new TextEncoder().encode(m.proof.secret)).toBytes(true));
        const cs = await t('/v1/checkstate', 'POST', { Ys: [Y] });
        return { status: sw.status, body: { code: `ppk:${m.ppk} swap:${sw.status} state:${cs.body?.states?.[0]?.state}` } };
      };
      return [{ label: 'swap-checkstate', a: await step(A.t), b: await step(B.t) }];
    }
  },
  {
    name: 'A8 happy melt + HTLC unlock (PAID paths)',
    run: async ({ A, B, secp, w, randomBytes, bytesToHex, nodeCrypto }) => {
      const happyMelt = async (t) => {
        const m = await w.mintWithSecret(t, 8, 'melt-' + bytesToHex(randomBytes(6)));
        const q = await w.meltQuote(t, 4);
        const melt = await t('/v1/melt/bolt11', 'POST', { quote: q.body.quote, inputs: [m.proof], outputs: [] });
        return { status: melt.status, body: { code: `state:${melt.body?.state}` } };
      };
      const htlcUnlock = async (t) => {
        const preimage = randomBytes(32);
        const hash = nodeCrypto.createHash('sha256').update(preimage).digest('hex');
        const secret = JSON.stringify(['HTLC', { nonce: bytesToHex(randomBytes(16)), data: hash }]);
        const m = await w.mintWithSecret(t, 8, secret);
        const q = await w.meltQuote(t, 4);
        const melt = await t('/v1/melt/bolt11', 'POST', { quote: q.body.quote, inputs: [{ ...m.proof, witness: JSON.stringify({ preimage: bytesToHex(preimage) }) }], outputs: [] });
        return { status: melt.status, body: { code: `state:${melt.body?.state}` } };
      };
      return [
        { label: 'happy-melt', a: await happyMelt(A.t), b: await happyMelt(B.t) },
        { label: 'htlc-unlock', a: await htlcUnlock(A.t), b: await htlcUnlock(B.t) }
      ];
    }
  },
  {
    name: 'SIG_ALL unlock (canonical message)',
    run: async ({ A, B, secp, schnorr, w, randomBytes, bytesToHex, nobleSha256 }) => {
      const sigallUnlock = async (t, priv) => {
        const secret = JSON.stringify(['P2PK', { nonce: bytesToHex(randomBytes(16)), data: bytesToHex(secp.getPublicKey(priv, true)), tags: [['sigflag', 'SIG_ALL'], ['n_sigs', '1']] }]);
        const m = await w.mintWithSecret(t, 8, secret);
        const q = await w.meltQuote(t, 4);
        const msg = w.sigAllMeltMessage([m.proof], [], q.body.quote);
        const sig = bytesToHex(schnorr.sign(nobleSha256(new TextEncoder().encode(msg)), priv));
        const melt = await t('/v1/melt/bolt11', 'POST', { quote: q.body.quote, inputs: [{ ...m.proof, witness: JSON.stringify({ signatures: [sig] }) }], outputs: [] });
        return { status: melt.status, body: { code: `state:${melt.body?.state}` } };
      };
      return [{ label: 'sigall-unlock', a: await sigallUnlock(A.t, randomBytes(32)), b: await sigallUnlock(B.t, randomBytes(32)) }];
    }
  }
];
