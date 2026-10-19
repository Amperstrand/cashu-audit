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
