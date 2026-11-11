/**
 * Logging proxy for the testnut coco drill: 127.0.0.1:8898 -> testnut.cashu.exchange
 * - Logs every request/response (method, path, status, bodies) to wire.jsonl
 * - INJECT_AT_SWAP=n (default 2): the n-th POST /v1/swap is NOT forwarded —
 *   the proxy returns 502. With n=2: swap#1 = send execute, swap#2 = the
 *   rollback reclaim. Simulates a crash mid-rollback before the mint saw
 *   the reclaim (the mint never executes it).
 */

const UPSTREAM = 'https://testnut.cashu.exchange';
// INJECT_FROM_SWAP=n: inject a 502 on every swap numbered >= n (send execute
// is swap #1; the reclaim path retries internally, so a single-shot injection
// at #2 lets the retry through — inject ALL reclaim attempts for a persisted
// rolling_back). INJECT_OFF=1 disables injection entirely (phase 2 recovery).
const INJECT_FROM = Number(process.env.INJECT_FROM_SWAP ?? '2');
const INJECT_OFF = process.env.INJECT_OFF === '1';
let swapCount = 0;
const log = { write: (s: string) => { require('fs').appendFileSync('wire.jsonl', s); } };

Bun.serve({
  port: 8907,
  idleTimeout: 30,
  async fetch(req) {
    const url = new URL(req.url);
    const reqBody = await req.text();
    const isSwap = req.method === 'POST' && url.pathname === '/v1/swap';
    if (isSwap) {
      swapCount += 1;
      if (!INJECT_OFF && swapCount >= INJECT_FROM) {
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
console.log(`[proxy] listening on 127.0.0.1:8907 -> ${UPSTREAM} (inject swaps >= ${INJECT_OFF ? 'OFF' : INJECT_FROM})`);
