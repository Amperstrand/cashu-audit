/**
 * STANDING coco crash-drill (certifier harness) — cashu-audit
 * experiments/live-mint-matrix/coco-crash-drill/drill.ts
 *
 * Proven live 2026-11-11/12 (research/evidence/2026-11-11-coco-drill/):
 * coco master @ 2d6aa583 mints from a cf mint, crashes mid-rollback
 * (proxy 502s every reclaim swap), and a FRESH PROCESS auto-recovers at
 * boot. This copy is the portable form of the banked drill-postfix.ts:
 *   - proxy port via DRILL_PORT (default 8907)
 *   - expects a `coco` sibling (symlink) pointing at a checkout of
 *     cashubtc/coco (pinned 2d6aa583; default clone:
 *     ~/src/upstream-cache/coco)
 *   - seed: 64 bytes, random-once-then-persisted (phase2 reuses; fresh
 *     db re-runs never re-derive spent secrets)
 *
 * Driver knowledge (pre-fix drill's back half was never executed — these
 * are the measured API facts): mint terminal state is 'finalized' and
 * needs a wait loop; public API is reclaim()/cancel() (no
 * sendOps.rollback); cancel only works pre-execute; rollback retries the
 * reclaim internally, so the proxy must inject ALL swaps >= 2 for
 * phase1 and run with INJECT_OFF=1 for phase2.
 */
import { initializeCoco } from './coco/packages/core/index.ts';
import { SqliteRepositories } from './coco/packages/sqlite-bun/src/index.ts';
import { Database } from 'bun:sqlite';

const MINT = `http://127.0.0.1:${process.env.DRILL_PORT ?? '8907'}`;
const phase = process.argv[2] ?? 'phase1';
const dbFile = 'drill-wallet.db';

async function seed(): Promise<Uint8Array> {
  const enc = new TextEncoder();
  try {
    const prev = await Bun.file('drill.seed').text();
    if (prev.length === 64) return enc.encode(prev);
  } catch { /* no seed yet */ }
  const s = Array.from(crypto.getRandomValues(new Uint8Array(32)))
    .map((b) => b.toString(16).padStart(2, '0')).join('');
  await Bun.write('drill.seed', s);
  return enc.encode(s);
}

const database = new Database(dbFile);
const repo = new SqliteRepositories({ database });
await repo.init();
const manager = await initializeCoco({
  repo,
  seedGetter: seed,
  logger: { debug: () => {}, info: (...a: unknown[]) => console.log('[coco]', ...a), warn: (...a: unknown[]) => console.log('[coco:warn]', ...a), error: (...a: unknown[]) => console.log('[coco:err]', ...a) } as never,
});

const sendOps = manager.ops.send;
const state = async (id: string) => (await sendOps.get(id))?.state;

if (phase === 'phase1') {
  await manager.mint.addMint(MINT, { trusted: true });
  const quote = await manager.quotes.mint.create({ mintUrl: MINT, amount: 21, method: 'bolt11' });
  const mintOp = await manager.ops.mint.prepare({ quote, amount: 21 });
  const executed = await manager.ops.mint.execute(mintOp);
  console.log('[phase1] mint op after execute():', executed.id ?? mintOp, executed.state);
  const deadline = Date.now() + 60_000;
  let opState = executed.state;
  while (opState !== 'completed' && opState !== 'finalized' && opState !== 'failed' && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 1000));
    opState = (await manager.ops.mint.execute(executed.id)).state ?? opState;
  }
  console.log('[phase1] mint op terminal state:', opState);
  const total = await manager.wallet.balances.total();
  console.log('[phase1] balance after mint:', JSON.stringify(total));
  if (opState !== 'completed' && opState !== 'finalized') throw new Error(`mint did not complete: ${opState}`);

  const prepared = await sendOps.prepare({ mintUrl: MINT, amount: 10 });
  console.log('[phase1] send prepared:', prepared.operationId ?? prepared.id);
  const opId = (prepared as { operationId?: string; id?: string }).operationId ?? (prepared as { id: string }).id;
  const exec = await sendOps.execute(opId);
  console.log('[phase1] send state after execute:', await state(opId));

  try {
    await sendOps.reclaim(opId);
    console.log('[phase1] UNEXPECTED: reclaim/rollback succeeded');
  } catch (e) {
    console.log('[phase1] reclaim rejected as expected:', (e as Error).message);
  }
  console.log('[phase1] persisted send state:', await state(opId));
  console.log('[phase1] SEND_ID=' + opId);
  await manager.dispose?.();
  process.exit(0);
}

if (phase === 'phase2') {
  const opId = process.argv[3];
  console.log('[phase2] state before recovery:', await state(opId));
  await sendOps.recovery.run();
  console.log('[phase2] state after recovery.run():', await state(opId));
  const total = await manager.wallet.balances.total();
  console.log('[phase2] balance after recovery:', JSON.stringify(total));
  await manager.dispose?.();
  process.exit(0);
}
