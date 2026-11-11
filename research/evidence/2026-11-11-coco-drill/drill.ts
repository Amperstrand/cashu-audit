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

const MINT = 'http://127.0.0.1:8899';
const phase = process.argv[2] ?? 'phase1';
const dbFile = 'drill-wallet.db';

async function seed(): Promise<Uint8Array> {
  await Bun.write('drill.seed', 'drill-seed-fixed-for-reproducibility-0001');
  return new TextEncoder().encode('drill-seed-fixed-for-reproducibility-0001');
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
  console.log('[phase1] mint op:', executed.state);
  const total = await manager.wallet.balances.total();
  console.log('[phase1] balance after mint:', JSON.stringify(total));

  const prepared = await sendOps.prepare({ mintUrl: MINT, amount: 10 });
  console.log('[phase1] send prepared:', prepared.operationId ?? prepared.id);
  const opId = (prepared as { operationId?: string; id?: string }).operationId ?? (prepared as { id: string }).id;
  const exec = await sendOps.execute(opId);
  console.log('[phase1] send state after execute:', exec.state);

  try {
    await sendOps.rollback(opId);
    console.log('[phase1] UNEXPECTED: rollback succeeded');
  } catch (e) {
    console.log('[phase1] rollback rejected as expected:', (e as Error).message);
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
