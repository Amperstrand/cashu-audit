# PREDICTIONS — signut baseline (frozen 2026-11-11 ~21:30, BEFORE any dependent probing)

Campaign: extensive testnut+signut testing, audited via cashu-audit,
contrasted vs cdk/ns arms (experiments/live-mint-matrix/).

Arm under test: signut.cashu.exchange — cashu-cf, CLNrest backend,
single active sat keyset (00eb682a), pre-#118 deploy (last deploy
predates 2026-11-11; the #118 fix fa62a94c is NOT on signut).

Already-measured recon (before freeze, declared): /v1/info shows 12
NUTs (no 15, no 17 rest-ad... 17 absent from list), version string
"Nutshell-CF/0.0.1", 1 keyset sat active.

Predictions for the legs below. A mismatch is a probe bug until proven
otherwise (AGENTS.md rule 1).

| id | leg | prediction |
|----|-----|------------|
| S1 | check-path NUT-04 fields, UNPAID quote (no funding) | fields ABSENT — the #118 serializer strips state-independently (pre-fix shape {quote,request,amount,unit,state,expiry}) |
| S2 | check-path NUT-04 fields after real payment (lnbits) | still ABSENT; coco 2.0+ unclaimable on signut (bug live on 2nd env) |
| S3 | GET path accounting after full mint | PRE-fix testnut shape: fields PRESENT but STALE (amount_issued stays 0, updated_at unmoved, state PAID) — #119-class residue |
| S4 | restore-empty | 200 {"outputs":[],"signatures":[]} (B2 identity, same code) |
| S5 | NUT-15 advertisement | absent |
| S6 | batch-fetch cap | 400 code 11014 on 51 ids |
| S7 | malformed-B_ mint on UNPAID quote | payment-state identity wins before B_ validation (cf ordering: quote-existence/payment before signing) — exact body recorded either way |
| S8 | swap legs (funded) | balanced fee-correct swap 200; byte-identical replay cached 200; keyless-amount 400 invalid_amount |
| S9 | self-payment detection | melt quote for the mint's OWN invoice: fee_reserve == 1 (2026-09-04 internal settlement fee) |
| S10 | updated_at monotonicity across mint | NOT bumped (same #119 residue as testnut; pre-dates #118) |
| S11 | funding rail | lnbits (creds in cashu-cf test/live/lightning/credentials.json) pays a 21-sat signut invoice from the audit box |

Verdict rules:
- S1/S2 RED = #118 live on signut -> fleet decision input (natural
  differential: testnut post-fix vs signut pre-fix, same family).
- S3/S10 RED = #119-class residue confirmed on a second env (strengthens
  "live-on-main, not testnut-specific").
- Any GREEN where RED predicted (or vice versa) -> read the wire body
  before recording; probe bug first.

## OUTCOMES (2026-11-11 ~21:45 — run log: signut-baseline-2026-11-11.log)

12/14. Two predictions WRONG, both informative:

- S1/S2 predicted fields ABSENT (assumed signut pre-#118): fields
  PRESENT, states UNPAID and PAID — signut runs post-#118 code (the
  laptop deploy covered signut as well as testnut; wire-conclusive).
  The planned testnut-vs-signut pre/post differential is therefore off
  the table; instead #119 residues are now measured on TWO envs.
- S7 predicted payment-state identity first: WRONG — malformed-B_
  yields the B_-shape identity (400 invalid_request "Invalid B_: must
  be a 66-character hex compressed sec..." ) on an UNPAID quote. cf
  validates B_ shape BEFORE payment state on this path. Contrast cell
  for the 6-arm matrix (cdk checks payment first — skill pitfall).

RED (both = cf#119 class, now env-independent):
- S3 GET accounting stale after full mint (ai=0, ua unmoved, state=PAID;
  first run additionally caught cross-path updated_at NON-monotonicity:
  check-path 6552 > GET-path 6551).
- S10 updated_at not bumped on issuance (check path: ai 0->21, ua same).

GREEN of note: S9 self-payment fee_reserve=1 (signut/CLNrest-specific
feature, absent on fakewallet envs); S8b replay caching (cf family
property) confirmed on signut; CLN ssh rail funds signut from the hub.
