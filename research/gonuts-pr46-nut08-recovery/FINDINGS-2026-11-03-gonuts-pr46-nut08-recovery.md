# FINDINGS — gonuts-tollgate PR #46 NUT-08 change recovery: both review guards absent, reproduced end-to-end

- **Target:** OpenTollGate/gonuts-tollgate PR #46
  `fix(wallet): recover NUT-08 change without resubmitting paid melts`,
  head `74254915bb17e70e2ec11183e903cb6bc1946aa5` (branch
  `murdawkmedia:fix/nut08-change-recovery`, parent `53d9773` =
  origin/main 2026-11-03).
- **Trigger:** author follow-up
  [issuecomment-6586603833](https://github.com/OpenTollGate/gonuts-tollgate/pull/46#issuecomment-6586603833)
  conceding that Amperstrand's first-pass fund-safety questions 1 and 2
  (issuecomment-6585277379) remain unresolved at head.
- **Method:** frozen predictions (PREDICTIONS-2026-11-03.md) → hostile
  wire-level reproduction → verdicts below. Evidence:
  `hostile_nut08_recovery_test.go` + `run-log-2026-11-03.txt`.
- **Date:** 2026-11-03. Go 1.25.8 linux/amd64, `-count=1`, plus `-race`
  on the hostile set; full repo battery green.
- **Classification:** fund-safety class, other implementation, vendor
  AWARE (the gaps are the author's own public statements; the PR is
  UNMERGED and `resumeOneMelt` does not exist in upstream
  elnosh/gonuts main). Held private per the 2026-10-27 rule; the owner
  (the PR reviewer of record) decides any follow-up on the thread.

## Verdict in one paragraph

The author's two concessions are correct, and they are worse than
"missing validation": with the quote-id binding absent, a wrong-quote
PAID answer does not merely get *accepted* — it drives the wallet's
entire post-settlement teardown (mark quote paid, delete intent, delete
the melt's reserved inputs), and because melt inputs are deleted from
the main proofs table at selection time, the pending table is their
only wallet record, so a state answer for someone else's quote can
silently erase live money from the wallet (V1b: 22 sats destroyed,
`err=nil`, invoice never paid, 0 melt POSTs). With the fee-reserve
ceiling absent, the mint-attested change amount flows into balance
unbounded (V3: 64 sats accepted against fee_reserve 1) and — since
`constructProofs` on this path compares the signature amount against a
value `constructMeltChangeProofs` just copied from the same signature,
and unblinding performs no validity check — change signatures over
points that are not our outputs store as phantom balance (V2: 64 sats
credited, `C ≠ k·H(secret)` proven offline). The whole PR battery plus
all seven hostile tests passes simultaneously: the suite cannot see
either gap, exactly as the author stated.

## The two conceded gaps, source-confirmed

**GAP-A — recovery GET answer never bound to our quote id.**
`wallet/client/client.go:334` `GetMeltQuoteState` unmarshals
`nut05.PostMeltQuoteBolt11Response` (which carries a `quote` field,
`cashu/nuts/nut05/nut05.go:59`) and returns it; nothing anywhere in
non-test wallet code compares `response.Quote` to the requested id
(only assignment, `wallet.go:1461`). `wallet/pending_swaps.go:146`
`resumeOneMelt` branches on `state.State` alone; `finishMeltResume`
(:189) marks OUR quote PAID from the REQUEST id and proceeds to proof
construction / teardown. Pre-existing adjacent surfaces with the same
hole: `CheckMeltQuoteState` (`wallet.go:1128`, interactive path — on
origin/main, not introduced by this PR) and the direct `Melt()` POST
response (`wallet.go:1286+`), whose `Quote` field is never checked
either.

**GAP-B — no total-change ceiling vs the stored fee reserve.**
`wallet/wallet.go:2180` `constructMeltChangeProofs` checks count
(`n ≤ len(messages)`), blankness (`messages[i].Amount == 0`), and
positivity (`sig.Amount != 0`), then assigns
`assigned[i].Amount = sig.Amount` — the amount is mint-attested. It
never receives the quote or `fee_reserve`. NUT-08's invariant is
explicit: blank outputs "will contain the overpaid fees that will be
returned", the wallet supplies proofs covering `amount + fee_reserve`,
so `sum(change) ≤ fee_reserve` is the spec bound (nuts 08.md:15,29,37;
05.md:78). The excess-signature test in the PR covers COUNT only, as
the author said.

Aggravator (ours, not in the thread): on this path the #831
amount-binding in `constructProofs` (`wallet.go:2220`) compares the
signature's amount against a number just copied from that signature —
the binding is neutralized by construction — and `unblindSignature`
(:2268) accepts any parseable point; without DLEQ (optional) nothing
cryptographically ties an accepted change signature to our blinded
output. Amount-key lookup (`keyset.PublicKeys[sig.Amount]`) merely
requires the amount to be a denomination of the keyset.

## Threat model

Not limited to a fully malicious mint (which can steal by refusing
cooperation anyway). The realistic drivers this class guards against:

1. **Buggy/misrouted state answers** — quote-lookup bugs, load-balanced
   nodes with divergent state, an id-normalization mismatch (echoing a
   canonicalized uuid where the wallet asked by another spelling), a
   caching layer keyed wrongly. None require malice; all produce
   PAID-for-the-wrong-quote answers.
2. **Transparent response mutation** — proxies, gateways, MTM on http.
3. **Malicious or compromised mint fronts** — can also forge amounts
   (phantom balance) or inflate "change" (V3 shape).

## Reproduction

`hostile_nut08_recovery_test.go` (this directory) runs the PR's own
`signingMint` stub unmodified behind `hostileProxy` — a reverse proxy
that rewrites only `GET /v1/melt/quote/bolt11/*` answers (and, for V6,
the melt POST response state) on the wire. The wallet's request bytes
pass through untouched; only mint answers mutate. Wallet funded 64
sats; melt quote amount 21, fee_reserve 1 → exactly 1 blank output
(`calculateBlankOutputs(1)==1`, matching NUT-08); melt inputs 22 sats
exist only in the pending table (`getProofsForAmount` deletes from
main at selection, `wallet.go:1943-1947`). Drop-in: copy into
`wallet/` of a pr-46 worktree, `go test ./wallet -run TestHostile
-count=1 -v`. Tests assert the VULNERABLE behavior — a failing test
means the guard landed.

### Verdicts (frozen in PREDICTIONS-2026-11-03.md before the run)

| ID | Hostile answer (wire) | Observed wallet behavior | Verdict |
|---|---|---|---|
| V1 | GET for our quote answered `{quote: <foreign>, state: PAID}`, change omitted; honest NUT-09 restore holds the real 1-sat signature | Foreign id silently discarded; our quote marked PAID, 1 sat credited, intent retired, `err=nil`, no resubmission (1 melt POST) | **CONFIRMED as predicted** |
| V1b | Same foreign PAID, but our melt never reached the mint (pre-POST failure; stub state honestly UNPAID; restore honestly empty) | Our quote marked PAID, 22 sats of *unspent* melt inputs deleted (pending table was their only record), intent deleted, `err=nil`, 0 melt POSTs — invoice never paid, wallet forgets live money with no error | **CONFIRMED as predicted** |
| V2 | Foreign PAID + `change: [{amount:64, id:<our keyset>, C_: valid sig over a FOREIGN point}]` | 64 sats credited (42→106); stored proof C `020a0b…` ≠ expected `k·H(secret)` `03dd9c…` — unspendable at any verifying mint; restore never consulted | **CONFIRMED as predicted** |
| V3 | OUR quote id, PAID, `change: [{amount:64, C_: cryptographically valid sig over OUR blank}]`, stored fee_reserve 1 | 64 sats accepted, no bound anywhere (spec bound: ≤ 1) | **CONFIRMED as predicted** |
| V4 | OUR id, PAID, explicit `"change": []` while restore memory holds a real 1-sat signature | Non-nil empty slice bypasses the `Change == nil` restore branch: intent retired, `recovered=0`, restore never called — real change silently dropped (the "absence as zero change" bug survives via the empty-array spelling) | **CONFIRMED as predicted** |
| V5 | Honest control (our id, PAID, real 1-sat change) | recovered=1, balance 43, 1 melt POST — harness valid | **CONFIRMED (control)** |
| V6 | Interactive path: PENDING melt, then `CheckMeltQuoteState` GET answered foreign-id PAID (+1-sat change passthrough) | Foreign PAID accepted: SettledAt+Preimage persisted, pending inputs deleted, response returned as-is. **Correction to prediction:** quote `State` stays `PENDING` — the interactive PAID branch never persists the state transition at all (pre-existing, on origin/main too) | **CONFIRMED with correction** (probe surfaced an extra defect) |

Harness quirk, recorded for reproducibility: the stub's ServeMux
subtree pattern 301-redirects the quote POST to the GET handler, so
quote ids in tests literally are `"bolt11"`. Ids are opaque to the
wallet; irrelevant to the verdicts.

## New facts beyond the PR thread

The thread (author + our own review) already concedes the two missing
guards. What the reproduction adds:

1. **V1b teardown mechanics** — the wrong-quote PAID does not just
   mislabel state; it triggers deletion of the melt inputs whose only
   wallet record is the pending table → silent loss of live, unspent
   ecash with `err=nil`. Severity anchor for question 1 (PONR).
2. **V2 phantom-balance mechanics** — the #831 binding is structurally
   neutralized on the melt-change path and unblinding validates
   nothing, so change value is 100% mint-attested with no ceiling and
   (without DLEQ) no cryptographic tie to our outputs; proven
   unspendable offline via `C ≠ k·H(secret)`.
3. **V4 empty-array spelling** — the PR's "absence is not evidence of
   zero change" fix only handles `change` omitted/`null`; `"change":
   []` on a PAID answer still retires the intent without consulting
   NUT-09 while real change exists.
4. **V6 + persistence defect** — same missing binding on the
   interactive `CheckMeltQuoteState` path (pre-existing on main), and
   that path additionally never persists `State=Paid` (writes only
   Preimage/SettledAt), leaving settled quotes recorded PENDING
   forever.
5. **Direct Melt() POST response quote id unchecked** — same class on
   the non-recovery path (`meltBolt11Response.Quote` never compared).
6. **Regression vectors V1–V6** below, usable as-is once guards land
   (each becomes an expected-refusal test).

## Test vectors (wire-level)

All against quote `amount=21, fee_reserve=1, unit=sat`, keyset id `K`
(the wallet's active keyset), blank output `B0` (the wallet's single
journaled blank), `Fr = "e771b3ac-1234-4000-8000-00000000046x"`.
Wallet pre-state: balance 42, pending 22, one melt intent, quote
UNPAID→(crashed melt). A fixed wallet MUST refuse or bound each
answer as noted.

- **V1** `GET /v1/melt/quote/bolt11/<ours>` →
  `{"quote":Fr,"state":"PAID"}` (no `change`) — must be REJECTED as a
  quote-id mismatch before any state acceptance (currently: accepted;
  recovery proceeds via NUT-09).
- **V1b** same answer while the mint holds no melt for us — must be
  REJECTED (currently: inputs destroyed, `err=nil`).
- **V2** `{"quote":Fr,"state":"PAID","change":[{"amount":64,"id":K,
  "C_":"02ccbad…","id" spelling = K}]}` where `C_ = k64·B_foreign`,
  `B_foreign ≠ B0` — must be REJECTED (id mismatch; and even with the
  right id, a signature that does not answer `B0` must not credit)
  (currently: 64 phantom sats stored).
- **V3** `{"quote":<ours>,"state":"PAID","change":[{"amount":64,"id":K,
  "C_": k64·B0}]}` — signature valid, total 64 > fee_reserve 1 — must
  be REJECTED/CLAMPED by the fee-reserve ceiling (currently: credited).
- **V4** `{"quote":<ours>,"state":"PAID","change":[]}` with journaled
  outputs and a mint that actually signed change — must consult NUT-09
  before retiring the intent (currently: retires silently).
- **V6** same as V1 delivered to `CheckMeltQuoteState` — same
  requirement (currently: settles + destroys pending; also State never
  persisted as PAID).
- **V5** control — honest answer must keep working (guards must not
  over-block: this is the anti-over-blocking fixture).

## Fix shape (for the maintainer's questions 1–2)

1. `GetMeltQuoteState` (and the melt POST response parse) must reject
   `resp.Quote != requestedID` — one client-level check covers
   recovery GET, interactive GET, and direct POST paths. Case policy:
   mints echo the id verbatim; compare exactly, not EqualFold.
2. `finishMeltResume` and `Melt()`'s Paid branch must enforce
   `sum(sig.Amount) ≤ stored.Quote.FeeReserve` (the LOCAL quote, per
   the review's "sourced from the quote (not the response)").
3. Treat `change` present-but-empty on a PAID answer like absence when
   journaled outputs exist (consult NUT-09 before retiring).
4. `CheckMeltQuoteState` must persist `quote.State = Paid` when it
   settles a quote.
5. Regression: convert V1–V6 into expected-refusal tests (V5 stays a
   pass-through control).

## Venue status (registry row)

The PR thread is the open venue and already contains both concessions
(author's comment). Our new facts (items 1–6 above) are exactly the
"impact, blind spot" class the protocol permits adding — but posting
is owner-gated (draft → owner approval → post). Nothing posted by this
work; GitHub was read-only. Registry row added (public repo,
uncommitted; owner decides): points here for detail.
