/**
 * STANDING coco crash-drill proxy — logging + crash injection.
 * Port via DRILL_PORT (default 8907); upstream via DRILL_UPSTREAM
 * (default testnut). INJECT_FROM_SWAP=n: 502 every swap numbered >= n
 * (send execute is swap #1; the reclaim path retries internally, so
 * inject ALL reclaim attempts for a persisted rolling_back).
 * INJECT_OFF=1 disables injection (phase 2 recovery). The swap counter
 * is PER-PROCESS: restart between phases/runs.
 */
const UPSTREAM = process.env.DRILL_UPSTREAM ?? 'https://testnut.cashu.exchange';
const INJECT_FROM = Number(process.env.INJECT_FROM_SWAP ?? '2');
const INJECT_OFF = process.env.INJECT_OFF === '1';
let swapCount = 0;
const log = { write: (s: string) => { require('fs').appendFileSync('wire.jsonl', s); } };

Bun.serve({
  port: Number(process.env.DRILL_PORT ?? '8907'),
  idleTimeout: 30,
  async fetch(req) {
    const url = new URL(req.url);
    const reqBody = await req.text();
    const isSwap = req.method === 'POST' && url.pathname === '/v1/swap';
    if (isSwap) {
      swapCount += 1;
      if (!INJECT_OFF && swapCount >= INJECT_FROM) {
        log.write(JSON.stringify({ t: Date.now(), method: req.method, path: url.pathname, injected: true, note: 'reclaim NOT forwarded — simulated crash mid-rollback', reqBody }) + '\n');
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
console.log(`[proxy] listening on 127.0.0.1:${process.env.DRILL_PORT ?? '8907'} -> ${UPSTREAM} (inject swaps >= ${INJECT_OFF ? 'OFF' : INJECT_FROM})`);
