# gonuts-tollgate v0.15.0 mint — first conformance-v2 run (2026-10-28)

Target: OpenTollGate/gonuts-tollgate **mint** at tag `v0.15.0` (current main,
`53d9773`), built from `cmd/mint` with `LIGHTNING_BACKEND=FAKEBACKEND`,
port 18498, sqlite under /tmp, input fee 0. Runner: `conformance/run_matrix.py`
(116 scenarios; same lane as the four reference arms). Full matrix:
`reports/matrix-gonuts-20261028.md` (copy in this run's evidence bundle).

## Headline

**28 failures: 19 gonuts-unique, 9 sharing scenario names with reference
expected-fail sets** (recomputed 2026-10-30 after review — the original
"zero overlap" claim was wrong). Shared names and how the identities
compare: `mint_quote_zero_amount_fails` — ns arms REJECT with a 422
pydantic shape (wrong identity), gonuts ACCEPTS the zero-amount quote
outright (opposite defect); `melt_replay_returns_cached_response` — ns
arms fail on cached-response identity, gonuts answers 20006
"quote already paid" instead of the cached 200 (same class, different
error); the six `htlc_sigall_*`/`p2pk_sigall_locktime_*` family names —
ns-0.20.3 also rejects these (its positioned witness split, expected-fail),
and gonuts' rejections are the same defect class (SIG_ALL verification
broken) plus MORE of the family; `batch_mint_rejects_too_many_outputs` —
cdk arms fail on strict-parse shape (422), gonuts has no endpoint (404).
The remaining 19 (incl. all of grade A and the quote-hygiene pair) fail on
NO reference arm. Grades:

### A — quote-settlement race (mint-operator loss vector)

- **`concurrent_double_melt_rejected` FAILED: BOTH concurrent melts paid
  (A=200, B=200).** Trigger (per the scenario source,
  `security_concurrent_melt.py:55–63`): ONE melt quote, TWO DISJOINT
  proof sets submitted concurrently — this exercises quote-level
  double-settlement, NOT proof reuse (each proof set is spent once).
  The observed defect is duplicate PAID for a single quote/invoice;
  with FAKEBACKEND this does not by itself establish double Lightning
  settlement — settlement evidence needs a real or simulated backend
  leg. The sequential control IS rejected (400), so the quote-state
  serialization that guards the sequential case does not span the
  concurrent window. Remedy: the cashu-cf #41 pattern — a single
  conditional UNPAID→PENDING transition (CAS) on the quote BEFORE
  settle, under a lock spanning check→settle; note that proof
  spend-marking alone would NOT close this variant (the proofs are
  disjoint — the race is on the quote, not the Ys).

### B — NUT-11/14 spending-condition enforcement on MELT (19 scenarios)

The signed-melt family is broadly broken while the swap-side mostly
holds; two distinct shapes:

1. `pubkeys tag cannot be empty if n_sigs tag is present` (melt_p2pk_signed,
   sigall_transaction, before_locktime_correct_key): the mint rejects
   well-formed P2PK melts — witness/tags parsing on the melt path
   disagrees with the swap path's (working) parsing of the same secrets.
2. `not enough valid signatures provided` (all SIG_ALL melts + several
   locktime/refund shapes): SIG_ALL verification on melts fails even with
   valid signatures — and `p2pk_sigall_locktime_after_expiry_no_refund_
   anyone_can_spend` answered `invalid witness` where ANY witness must be
   accepted after locktime.

Also `p2pk_swap_signed_succeeds` fails (swap-side P2PK not fully clean
either). These are enforcement gaps the whole reference field closes.

### C — quote hygiene (3)

- `mint_quote_uuid_v7`: quote ids are hex hashes, not UUIDv7 (NUT-04).
- `mint_quote_accounting_after_mint`: `amount_issued` stays 0 after a
  mint (NUT-04 accounting fields).
- `mint_quote_zero_amount_fails`: a zero-amount mint quote is ACCEPTED
  (200) — validation gap.

### D — NUT-19/29 (3)

- `melt_replay_returns_cached_response`: melt replay answers 20006
  "quote already paid" instead of the cached 200 response (swap replay
  IS byte-identical cached). cdk/cf behavior: cached.
- `batch_check_returns_quotes`: 400 quote-does-not-exist (NUT-29 shape).
- `batch_mint_rejects_too_many_outputs`: endpoint absent (404).

### Skips (1)

`melt_p2pk_sigall_transaction_signature_succeeds`-family hang is
run_filtered on other arms too — not gonuts-specific.

## Verdict vs the ecosystem

The fork's **wallet** side (the TollGate-consumed half) is now
converged with the field's fund-safety practices (v0.15.0: intent
journal + replay + NUT-09 restore + response binding + fee refusal —
all cdk-shaped, most live-verified). The **mint** side is NOT at
reference-arm conformance: 28 failures (19 unique to gonuts, 9
shared-name with reference expected-fail sets — identities compared in
the headline), one of them a concurrent quote double-pay. Operational
guidance until A is fixed: do not
expose the gonuts mint to untrusted melt traffic; it remains fit for
test/lab mints (its current TollGate role — the deployed mints are
cashu-cf/cdk).

## Follow-ups (tracked in OpenTollGate repos; fork issues disabled)

1. [P0] melt: single conditional UNPAID→PENDING transition (CAS) on the
   quote before settle, spanning check→settle; concurrent melts on one
   quote must leave exactly one PAID. Repro: this lane's scenario, one
   command. Follow-up repro EXECUTED 2026-10-29 (local arm, FAKEBACKEND):
   **same-proofs/two-quotes concurrent -> exactly one settles (B=400)** —
   the proof-level guard holds across quotes, confirming the defect is
   precisely quote-level double-settlement (the CAS remedy is the right
   target). Still open: a settlement-evidencing backend leg for the
   Lightning-loss picture (FAKEBACKEND auto-pays everything).
2. [P1] melt-path NUT-11/14 verification: same parser as swap; SIG_ALL
   counts; anyone-can-spend after locktime.
3. [P2] quote ids → UUIDv7; amount_issued accounting; zero-amount
   refusal.
4. [P3] melt replay cache (NUT-19) + NUT-29 batch endpoints.
