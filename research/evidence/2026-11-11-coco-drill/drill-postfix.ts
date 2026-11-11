/**
 * Live crash drill for coco post-#613 recovery against testnut (cashu-cf FakeWallet).
 * Phase 1: mint 21 sat, send-prepare 10, execute (swap#1), rollback — the proxy
 *          refuses the reclaim swap (#2) -> rollback rejects; driver exits with
 *          the op persisted in rolling_back (simulated crash aftermath).
 * Phase 2: fresh process, same sqlite + seed; expect rolling_back; run
 *          ops.send.recovery.run(); expect rolled_back, balance restored to 21,
 *          and (asserted afterwards from wire.jsonl) the replayed reclaim
 *          byte-identical to the interrupted one.
 */
import { initializeCoco } from '../coco-sync/packages/core/index.ts';
import { SqliteRepositories } from '../coco-sync/packages/sqlite-bun/src/index.ts';
import { Database } from 'bun:sqlite';

const MINT = 'http://127.0.0.1:8907';
const phase = process.argv[2] ?? 'phase1';
const dbFile = 'drill-wallet.db';

async function seed(): Promise<Uint8Array> {
  // Random-once, then persisted: phase2 must reuse phase1's seed, but
  // re-running the drill pair from a fresh db must NOT re-derive the same
  // secrets (deterministic derivation + fixed seed = "spent proof" 400s
  // against the live mint from earlier runs' spends).
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
  // Post-#118-fix driver: execute() returns while the op may still be pending —
  // the background watcher performs the claim. Wait for a terminal state.
  const deadline = Date.now() + 60_000;
  let opState = executed.state;
  while (opState !== 'completed' && opState !== 'failed' && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 1000));
    // execute() is idempotent for pending/executing ops: re-polls the quote,
    // claims when claimable, recovers executing ops, returns current state.
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
