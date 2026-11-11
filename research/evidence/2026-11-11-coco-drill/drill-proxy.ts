/**
 * Logging proxy for the testnut coco drill: 127.0.0.1:8898 -> testnut.cashu.exchange
 * - Logs every request/response (method, path, status, bodies) to wire.jsonl
 * - INJECT_AT_SWAP=n (default 2): the n-th POST /v1/swap is NOT forwarded —
 *   the proxy returns 502. With n=2: swap#1 = send execute, swap#2 = the
 *   rollback reclaim. Simulates a crash mid-rollback before the mint saw
 *   the reclaim (the mint never executes it).
 */

const UPSTREAM = 'https://testnut.cashu.exchange';
const INJECT_AT = Number(process.env.INJECT_AT_SWAP ?? '2');
let swapCount = 0;
const log = { write: (s: string) => { require('fs').appendFileSync('wire.jsonl', s); } };

Bun.serve({
  port: 8898,
  idleTimeout: 30,
  async fetch(req) {
    const url = new URL(req.url);
    const reqBody = await req.text();
    const isSwap = req.method === 'POST' && url.pathname === '/v1/swap';
    if (isSwap) {
      swapCount += 1;
      if (swapCount === INJECT_AT) {
        const rec = { t: Date.now(), method: req.method, path: url.pathname, injected: true, note: 'reclaim NOT forwarded — simulated crash mid-rollback', reqBody };
        log.write(JSON.stringify(rec) + '\n');
        console.log(`[proxy] INJECTED failure at swap #${swapCount} (502, not forwarded)`);
        return new Response('proxy-injected interruption', { status: 502 });
      }
    }
    const upstream = new URL(url.pathname + url.search, UPSTREAM);
    const resp = await fetch(upstream, {
      method: req.method,
      headers: { 'content-type': req.headers.get('content-type') ?? 'application/json', accept: req.headers.get('accept') ?? 'application/json' },
      body: ['GET', 'HEAD'].includes(req.method) ? undefined : reqBody,
    });
    const respBody = await resp.text();
    log.write(JSON.stringify({ t: Date.now(), method: req.method, path: url.pathname, status: resp.status, reqBody, respBody }) + '\n');
    return new Response(respBody, { status: resp.status, headers: { 'content-type': resp.headers.get('content-type') ?? 'application/json' } });
  },
});
console.log(`[proxy] listening on 127.0.0.1:8898 -> ${UPSTREAM} (inject at swap #${INJECT_AT})`);
