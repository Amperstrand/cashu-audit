# FROZEN PREDICTIONS — gonuts-tollgate PR #46 NUT-08 recovery guards

Target: OpenTollGate/gonuts-tollgate PR #46 head `74254915bb17e70e2ec11183e903cb6bc1946aa5`
(worktree `/tmp/opencode/gonuts-pr46`, branch `pr-46`).

Source-review basis (read 2026-11-03, before any test run):

- `wallet/client/client.go:334` `GetMeltQuoteState` — returns parsed
  `nut05.PostMeltQuoteBolt11Response`; the response carries a `quote`
  field (nut05.go:59) that is never compared to the requested id.
- `wallet/pending_swaps.go:146` `resumeOneMelt` — accepts
  `state.State == nut05.Paid` from whatever record the GET returned and
  calls `finishMeltResume(intent, request.Quote, state)` with the
  REQUEST id.
- `wallet/pending_swaps.go:189` `finishMeltResume` — marks the local
  quote PAID, then either NUT-09-restores (change omitted) or
  `finishResume(intent, response.Change)`.
- `wallet/wallet.go:2180` `constructMeltChangeProofs` — count-bound and
  blank-output checks only; the amount is taken from the signature
  (`assigned[i].Amount = sig.Amount`); no total-value ceiling vs the
  stored quote's fee reserve is received or enforced.
- `wallet/wallet.go:2220` `constructProofs` — the #831 amount-binding
  compares `sig.Amount` to a value `constructMeltChangeProofs` just
  copied from the same signature (binding neutralized on this path by
  construction); keyset id compared EqualFold; DLEQ verified only if
  present; `unblindSignature` performs no validity check (any parseable
  point succeeds).
- `wallet/wallet.go:1128` `CheckMeltQuoteState` — the INTERACTIVE path
  shares the same missing quote-id binding (pre-existing surface).
- `wallet/wallet.go:1943-1947` `getProofsForAmount` — melt inputs are
  DELETED from the main proofs table at selection; during a melt they
  exist only in the pending table keyed by quote id.
- `wallet/pending_swaps.go:373` recovery tail — `DeletePendingProofsByQuoteId`
  destroys that only record.
- Stub-mint facts: melt quote amount=21, fee_reserve=1;
  `calculateBlankOutputs(1)`=1 blank output; stub assigns 1 sat to the
  blank; mint path mints a single 64-sat proof.

Predictions (each will be marked CONFIRMED / REFUTED after the run):

| ID | Scenario | Frozen prediction |
|---|---|---|
| V1 | Recovery GET answered with a FOREIGN quote id + PAID, change omitted; honest NUT-09 restore returns the real 1-sat signature | Resume succeeds: err=nil, failed=0, recovered=1, OUR quote marked Paid in db, intents=0, melt POSTs=1. Foreign quote id silently discarded — proves PAID state accepted without binding to our quote. |
| V1b | FOREIGN-id PAID accepted while OUR melt never reached the mint (pre-POST network failure; intent journaled; restore honestly empty) | Resume: err=nil, failed=0, recovered=0, quote marked Paid, intents=0, PendingBalance 22→0, mint melt POSTs=0. The 22 sats of melt inputs (unspent at the mint, only record = pending table) are deleted from the wallet with NO error — silent loss of live money via a mint state lie. |
| V2 | FOREIGN-id PAID + injected `change` = one 64-sat signature over a FOREIGN B_ (valid crypto, our keyset id, not our journaled output) | constructMeltChangeProofs zips it with our blank: err=nil, recovered=64, balance 42→106, intents=0. Phantom 64 sats stored (unblinds to garbage C; will fail at spend) — response value accepted with zero binding to our output. |
| V3 | OUR-id PAID + `change` = one cryptographically VALID 64-sat signature over OUR actual blank output; stored quote fee_reserve=1 | err=nil, recovered=64, balance 42→106 — no ceiling check vs quote.FeeReserve anywhere. Claim B (no total-change bound) reproduced with fully valid signatures. |
| V4 | OUR-id PAID + explicit `"change": []` while the mint really signed 1-sat change (restore memory holds it) | Non-nil empty slice bypasses the `Change == nil` restore branch: err=nil, recovered=0, restoreCalls=0, intents=0 — real change silently lost via the empty-array spelling of "absence". |
| V5 | Honest control: OUR-id PAID + 1-sat change passthrough | err=nil, recovered=1, balance=43, melts=1 — harness validity. |
| V6 | Interactive surface: quote pending, `CheckMeltQuoteState` GET answered with FOREIGN-id PAID (+1-sat change) | Response returned as-is; OUR quote marked Paid; pending proofs for OUR quote id deleted. Same missing binding on the pre-existing interactive path. |

All seven predictions frozen 2026-11-03 before `go test` execution.
Surprising results = probe bug until proven otherwise (driver stderr
inspected before any conclusion).
