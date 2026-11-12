# FINDINGS 2026-11-11 — six-arm comparison: cashu-cf (testnut, signut) vs cdk vs nutshell

Campaign dir: experiments/live-mint-matrix/ (owner direction 2026-11-11:
extensive testnut+signut testing audited via cashu-audit, contrasted vs
cdk/ns). Method: frozen predictions (PREDICTIONS-2026-11-11-signut.md),
error identities verbatim, version matrix not latest-vs-latest. Raw
reports in reports/ (per-arm conformance-v2 JSON + live-matrix.md).

## Arms and totals (130-scenario conformance corpus)

| arm | version | PASS | FAIL | SKIP | notes |
|---|---|---|---|---|---|
| testnut | cashu-cf post-#118 (fa62a94c tree), fakewallet, sat+usd | 92* | 5* | 33* | *run_matrix runner: 36 skips across both live arms are mostly payment-rail/env-shape artifacts, see below |
| signut | cashu-cf post-#118, CLNrest, sat-only | 91* | 4* | 35* | |
| ns | nutshell 0.20.3 | 110 | 14 | 6 | |
| ns | nutshell 0.21.0 | 117 | 7 | 6 | |
| cdk | mintd 0.18.1 | 119 | 6 | 5 | |
| cdk | mintd 0.18.2 | 119 | 6 | 5 | FAIL sets IDENTICAL across 0.18.1→0.18.2 (corpus-level confirmation of the clean upgrade ladder) |

Live-arm SKIP anatomy (36 total): the run_matrix runner has no payment
rail — signut melt/mint/DLEQ/restore legs that need funded quotes skip
or fail on funding (mint_tokens_after_quote "never paid", restore empty;
the signut certifier with the CLN rail covers those paths and passes
them). testnut usd legs partially trip the corpus's sat-only assumption
(errid_mint_quote_unit_unsupported expects usd unsupported — testnut HAS
a usd keyset, so the leg's premise inverts; env-shape mismatch, not a
mint bug). Phase C: wire MUST_GAP_AUTO_PAY into run_matrix + a
multi-unit profile flag.

## Cross-family behavior matrix (the compare/contrast)

Verdict cells measured 2026-11-11; identities verbatim in reports/.

| behavior | ns 0.20.3/0.21.0 | cdk 0.18.1/0.18.2 | cf testnut/signut |
|---|---|---|---|
| swap/melt replay caching (NUT-19) | NONE — replay 400 11001 "proofs already spent" / 20006 "melt quote is not unpaid: paid" | CACHED 200 byte-identical | CACHED 200 byte-identical (both envs) |
| NUT-19 advertisement | absent from /v1/info nuts | present | present |
| unknown keyset error | 11000 "keyset id unknown." (want 12001) | 12001 (spec) | 12001 (spec) |
| underfunded swap error | 11000 (want 11005) | 11005 (spec) | 11005 (spec) |
| duplicate outputs error | 11003 (spec) | **11008 "Duplicate outputs"** (our filed cdk finding, 2026-10-29) | 11003 (spec) |
| request-envelope error shape | 400 {detail,code} (0.21.0) | axum 422 no-code | 400 {error,detail,code} |
| zero-amount quote | pydantic 422 "greater_than" (framework) | spec-coded | spec-coded |
| /v1/info name field | present | **MISSING 'name'** | present |
| ws subscribe unknown quote | ACKED (should reject) | rejected | (ws legs not in live runner — Phase C) |
| malformed-B_ vs payment-state ordering | n/a (fakewallet auto-pays) | payment-state first (skill pitfall) | **B_-shape first** (measured signut S7: UNPAID quote + zz-hex B_ → "Invalid B_" 400) |
| keyless-amount signing (fund-safety) | PASS both | PASS both | **FUNDS-LOSS LIVE both envs** — swap signed [3,12]/[3,13]; staged fix fix/keyless-amount-signing 97a1654 NOT deployed (owner-gated); now two-env-confirmed |
| NUT-12 DLEQ completeness | all-yes | all-yes | all-yes (testnut funded legs) |
| NUT-04 accounting fields | pass | pass | pass post-#118 (both envs; signut confirmed post-fix too) |
| NUT-29 batch caps (11014/11017) | pass | pass (one scenario probe-bug SKIP: AttributeError on cdk) | pass (both envs; 11014 identity confirmed) |
| NUT-04 updated_at-on-issuance / GET freshness | pass | pass | **FAIL both envs (cf#119)** — GET serves pre-mint accounting after full mint; updated_at frozen on issuance; cross-path ua non-monotonicity measured (check 6552 > GET 6551) |

## New findings this run (not previously recorded)

1. **cf lenient at the NUT-00 secret-verification boundary** —
   `secret_encoding_entropy_trap_rejected` FAIL on testnut: mint ACCEPTED
   an entropy-blinded proof where cdk and ns both reject. "Would mask
   buggy wallets" class. Registry-grade candidate AFTER intent-research
   (references/intent-research.md) — not filed yet.
2. **Keyless-amount fund-loss live on signut as well** — the staged fix
   is now blocking TWO production envs; deployment priority input.
3. **cf ordering identity: request-shape validated before payment
   state** on the single-mint path (contrast cdk payment-first) — a
   wallet-visible ordering divergence cell.
4. **testnut melt change arithmetic**: melt_change_returned_for_overpay
   change summed 12 vs scenario-expected [13,14] (total 16 − amount 2 −
   fee ≤ reserve 1 boundary). Untriaged: probe arithmetic vs mint
   rounding cell — Phase C triage before recording.
5. Version-string identity quirk: both cf envs advertise
   "Nutshell-CF/0.0.1" — confusable with actual nutshell in any
   wallet-side fingerprinting; worth a cf issue of its own (honest
   version advertisement).

## Family one-liners (contrasts)

- nutshell = the strict-secret, no-cache, framework-422 family: spec
  codes constructed numerically (11000 umbrella) on 0.20.3, partially
  fixed in 0.21.0 (14→7 corpus fails; sigall/HTLC legs and unit
  error-code fixed).
- cdk = spec-coded identities + axum 422 envelope class + missing info
  name + our filed 11008 duplicate-outputs mis-identity; 0.18.1→0.18.2
  corpus-identical (clean ladder).
- cashu-cf = closest to spec codes + caching + batch caps, but carries
  the fund-safety outlier (keyless, staged) and the #119 read-path
  residues; also the only family with multi-env production presence
  (fakewallet + real-CLN backends behave identically on the corpus).

## Next (Phase C)

1. run_matrix: --auto-pay (CLN rail) + multi-unit profile flag; re-run
   signut to fill the funding-skip cells; funded restore + DLEQ legs.
2. cashu-cf unit/e2e additions: keyless-amount characterization pins
   (RED-on-main, GREEN-with-staged-fix — extend existing pattern),
   entropy-trap verification-boundary lock, #119 characterization pins,
   B_-ordering identity lock.
3. Triage: melt_change overpay arithmetic; entropy-trap intent-research
   → registry row (owner-gated).
4. Tracker: NUT-00 card (entropy trap), NUT-19/03 cards unchanged.
