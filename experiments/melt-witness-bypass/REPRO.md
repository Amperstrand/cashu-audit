# testnut melt-pathway witness bypass — reproduction capture

Probe: `probe_melt22.py` (scenario 22's exact flow, instrumented:
full bodies + quote state before the melt).

- Date: 2026-10-19 (UTC)
- Mint: https://testnut.cashu.exchange — "Testnut mint", `Nutshell-CF/0.0.1`
- Also observed: weekly run 39208407672 (2026-10-19, scenarios
  #22/#24/#27/#28/#32 — same `got 200 {quote…}` bodies, truncated);
  matrix-2026-09-16-postPR1PR2.md on signut AND testnut (same shape).

## Captured flow (2026-10-19, local)

1. Minted 8 sat (regular secrets).
2. Swapped to P2PK-conditioned secrets — `["P2PK",{"nonce":…,"data":<pubkey>,"tags":[["sigflag","SIG_INPUTS"],["n_sigs","1"]]}]` — amounts 1+2+4.
3. Melt quote for 4 sat via the suite's self-loop helper
   (invoice = the mint's own mint_quote request):
   `state: UNPAID` at creation.
4. **Control (confound eliminated):** `GET /v1/melt/quote/{id}` immediately
   before the melt → `200 {"state":"UNPAID", …}` — the quote was NOT
   pre-settled by the self-loop.
5. `POST /v1/melt` with the three P2PK proofs as inputs, **no `witness`
   field on any input**, change outputs supplied →
   `HTTP 200`, `state: PAID`, `paid: true`,
   `preimage: 3ac138d3dc5a532ef2008e7d4c5b7250edeff0b40cea2652cac9108c4dccf3c6`
   (real Lightning payment evidence), change output returned.

## Interpretation

The mint executed payment against inputs whose secrets demand a
SIG_INPUTS signature (`n_sigs: 1`) that was never supplied. On the same
mint and same morning run, the **swap**-pathway witness scenarios
(#34/#35/#37/#38) all PASS ("rejected") — enforcement exists on swap,
is absent on melt. Fund-safety class: P2PK-locked tokens are bearer-
spendable via melt on this software.

Controls on record: scenario #23 (signed melt) PASSes on the same
flow — witness verification *with* a witness works; the morning run's
matrix shows the mint-side split (melt ✗ / swap ✓) within one run.

## 2026-10-19 escalation + root cause + fix

**Escalation (owner-sanctioned fix):** the hole is bigger than the
witness bypass. `probe_forged.py` (captured: `probe-out-forged-melt.txt`)
— a completely fabricated proof (random secret, off-curve C hex, never
minted) melted and **PAID** a 4-sat invoice. Control `probe_forged_swap.py`
(`probe-out-forged-swap.txt`): the same fabrication through /v1/swap is
**rejected** with full cryptographic verification.

**Root cause** (Amperstrand/cashu-audit #53 → cashu-cf ISSUE-124): the
ISSUE-051 melt saga performs NO input verification — both checks the
deleted legacy melt path had (proof signatures via
`verifyProofSignatureWithPrivateKey`; spending conditions via
`verifySpendingConditions`) were lost in cashu-cf's 2114eb6 big deletion.
The proof ledger has no issuance record (unknown Y reads UNSPENT), so
nothing else rejects fabricated proofs.

**Fix:** Amperstrand/cashu-cf `aba6cd6` — `src/melt/verify-inputs.ts`,
saga Phase 0.5, swap-path ordering parity (verify before claiming).
Unit battery 2380/2380 incl. real-crypto negatives/positives. Deployed
status: testnut deploy pending owner Cloudflare token (no credentials on
ai-legion); live re-probes after deploy should flip all three probe
verdicts (forged→400, unsigned witness→403, control melt→200).

