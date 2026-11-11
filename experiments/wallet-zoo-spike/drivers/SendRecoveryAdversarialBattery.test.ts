/**
 * ADVERSARIAL RECOVERY BATTERY — Amperstrand cashu-audit lane A
 * Target: cashubtc/coco @ 2d6aa5834bf261749b2453ef64f2b3cd89c0e8c4 (post-#613 master)
 * Written 2026-11-11. Frozen predictions below BEFORE any run (method rule 1).
 *
 * Upstream suite already covers the sequential decision table
 * (replay/restore/claimed/pending/unreachable/legacy/no-request). This
 * battery targets what it does NOT: concurrent cross-session recovery,
 * re-run idempotence through the public API, and full request-replay
 * identity (upstream asserts outputData equality only, not inputs).
 *
 * FROZEN PREDICTIONS
 *  P1 (concurrent, two Coco Sessions share one wallet, same rolling_back op):
 *     a. final state == 'rolled_back' (terminal exactly once)
 *     b. exactly ONE 'send:rolled-back' event
 *     c. reclaimed value available exactly once — available proofs hold the
 *        reclaim output, total available amount == 10, no secret duplicated
 *     d. remote.reclaim total calls == 2 if the operation lock is shared
 *        across service instances (second session skips 'in progress'),
 *        == 3 if per-instance (both replay; transaction layer must then
 *        make one commit lose). Either topology passes the invariants;
 *        the observed count is recorded as lock-topology evidence.
 *  P2 (second full recovery pass after settlement): zero new mint calls,
 *     zero new events, state still 'rolled_back'.
 *  P3 (replay identity): the replayed reclaim call's INPUTS argument
 *     deep-equals the original call's inputs (upstream asserted only the
 *     outputs arg); outputs equal too.
 *  P4 (public on-demand api.recovery.run()): second sequential run() is a
 *     no-op (no new mint calls, no events); run() over a repository with
 *     only terminal states is a clean no-op.
 */
import { Amount } from '@cashu/cashu-ts';
import { beforeEach, describe, expect, it } from 'bun:test';
import { createSendEnvironment } from '../fixtures/SendEnvironment.ts';
import { deserializeOutputData } from '../../utils.ts';
import { SendOpsApi } from '../../api/SendOpsApi.ts';
import { testMintKeysetId } from '../fixtures/MintMetadata.ts';
import type { CoreProof } from '../../types.ts';

const mintUrl = 'https://mint.test';
const keysetId = testMintKeysetId();

type Environment = Awaited<ReturnType<typeof createSendEnvironment>>;

describe('adversarial rolling_back recovery battery', () => {
  let environment: Environment;
  let repositories: Environment['repositories'];
  let sendOpRepo: Environment['repositories']['sendOperationRepository'];
  let proofRepo: Environment['repositories']['proofRepository'];
  let remote: Environment['remote'];
  let eventBus: Environment['eventBus'];
  let logger: Environment['logger'];
  let service: Environment['service'];

  const makeProof = (secret: string, amount: number): CoreProof =>
    ({
      amount: Amount.from(amount),
      C: `C_${secret}`,
      id: keysetId,
      secret,
      mintUrl,
      unit: 'sat',
      state: 'ready',
    }) as CoreProof;

  const unitAmount = (amount: number) => ({ amount: Amount.from(amount), unit: 'sat' });

  const reclaimOutputs = (outputData: Parameters<typeof deserializeOutputData>[0]) =>
    deserializeOutputData(outputData).keep.map((output) => ({
      id: output.blindedMessage.id,
      amount: output.blindedMessage.amount,
      secret: new TextDecoder().decode(output.secret),
      C: 'reclaimed-signature',
    }));

  const reportStates = (state: 'UNSPENT' | 'PENDING' | 'SPENT') =>
    remote.checkProofStates.mockImplementation(async (proofs: Array<{ secret: string }>) =>
      proofs.map((proof) => ({ Y: `Y-${proof.secret}`, state, witness: null })),
    );

  /** A Send whose reclaim request is stored and whose mint call failed. */
  async function interruptedReclaim(inputSecret: string) {
    await proofRepo.saveProofs(mintUrl, [makeProof(inputSecret, 10)]);
    const prepared = await service.prepare(await service.init(mintUrl, unitAmount(10)));
    await service.execute(prepared);
    remote.reclaim.mockRejectedValueOnce(new Error('connection lost'));
    await expect(service.rollback(prepared.id)).rejects.toThrow('connection lost');
    expect((await sendOpRepo.getById(prepared.id))?.state).toBe('rolling_back');
    return prepared.id;
  }

  beforeEach(async () => {
    environment = await createSendEnvironment();
    repositories = environment.repositories;
    sendOpRepo = repositories.sendOperationRepository;
    proofRepo = repositories.proofRepository;
    remote = environment.remote;
    eventBus = environment.eventBus;
    logger = environment.logger;
    service = environment.service;
  });

  it('P1+P3: two Coco Sessions recovering the same rolling_back Send settle it exactly once, replaying the identical request', async () => {
    const id = await interruptedReclaim('battery-concurrent');
    reportStates('UNSPENT');
    remote.reclaim.mockImplementation(async (_inputs, outputData) => reclaimOutputs(outputData));

    const rolledBack: string[] = [];
    eventBus.on('send:rolled-back', ({ operationId }) => {
      rolledBack.push(operationId);
    });

    const secondSession = environment.buildService();
    const outcomes = await Promise.allSettled([
      service.recoverPendingOperations(),
      secondSession.recoverPendingOperations(),
    ]);
    outcomes.forEach((o) => {
      if (o.status === 'rejected') throw new Error(`concurrent recovery rejected: ${o.reason}`);
    });

    // P1a: terminal exactly once
    expect((await sendOpRepo.getById(id))?.state).toBe('rolled_back');
    // P1b: one event
    expect(rolledBack).toEqual([id]);
    // P3: replay identity — BOTH arguments of the replay call equal the original
    const calls = remote.reclaim.mock.calls as unknown as Array<
      [{ secret: string }[], unknown]
    >;
    expect(calls.length).toBeGreaterThanOrEqual(2);
    const [origInputs, origOutputs] = calls[0]!;
    const [replayInputs, replayOutputs] = calls[calls.length - 1]!;
    expect(replayInputs).toEqual(origInputs);
    expect(replayOutputs).toEqual(origOutputs);
    // P1c: reclaimed value available exactly once, no duplicated secret
    const available = await proofRepo.getAvailableProofs(mintUrl);
    const secrets = available.map((p) => p.secret);
    expect(new Set(secrets).size).toBe(secrets.length);
    const total = available.reduce((sum, p) => sum + p.amount.toNumber(), 0);
    expect(total).toBe(10);
    // P1d: lock-topology evidence (asserted as invariant-compatible range)
    expect([2, 3]).toContain(calls.length);
    // eslint-disable-next-line no-console
    console.log(
      `[battery] P1 lock topology: reclaim calls total=${calls.length} (2=shared op lock, 3=per-instance lock + transaction-layer single winner)`,
    );
  });

  it('P2: a second full recovery pass after settlement is a no-op', async () => {
    const id = await interruptedReclaim('battery-idempotent');
    reportStates('UNSPENT');
    remote.reclaim.mockImplementation(async (_inputs, outputData) => reclaimOutputs(outputData));

    const rolledBack: string[] = [];
    eventBus.on('send:rolled-back', ({ operationId }) => {
      rolledBack.push(operationId);
    });

    await service.recoverPendingOperations();
    expect((await sendOpRepo.getById(id))?.state).toBe('rolled_back');
    const reclaimCallsAfterFirst = remote.reclaim.mock.calls.length;
    const stateCallsAfterFirst = remote.checkProofStates.mock.calls.length;
    expect(rolledBack).toEqual([id]);

    await service.recoverPendingOperations();

    expect(remote.reclaim.mock.calls.length).toBe(reclaimCallsAfterFirst);
    expect(remote.checkProofStates.mock.calls.length).toBe(stateCallsAfterFirst);
    expect(rolledBack).toEqual([id]);
    expect((await sendOpRepo.getById(id))?.state).toBe('rolled_back');
  });

  it('P4: on-demand api.recovery.run() settles and a second run() is a no-op', async () => {
    const id = await interruptedReclaim('battery-ondemand');
    reportStates('UNSPENT');
    remote.reclaim.mockImplementation(async (_inputs, outputData) => reclaimOutputs(outputData));

    const api = new SendOpsApi(service);
    const rolledBack: string[] = [];
    eventBus.on('send:rolled-back', ({ operationId }) => {
      rolledBack.push(operationId);
    });

    await api.recovery.run();
    expect((await sendOpRepo.getById(id))?.state).toBe('rolled_back');
    expect(rolledBack).toEqual([id]);
    const callsAfterRun = remote.reclaim.mock.calls.length;

    await api.recovery.run();
    expect(remote.reclaim.mock.calls.length).toBe(callsAfterRun);
    expect(rolledBack).toEqual([id]);
  });
});
