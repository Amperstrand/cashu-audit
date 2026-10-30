# FINDINGS — cashu-cf#102 decision-bundle facts (2026-10-30)

Frozen predictions: `PREDICTIONS-cf102-facts.md`. Arms: testnut (cf),
ns-0.21.0, cdk-0.18.3 (all live). Facts only — no decisions.

## Item 2: POST /v1/restore with outputs:[] (3-family, wire)

| Arm | Result |
|---|---|
| cf (testnut) | 400 `at least one output is required` / 14005 |
| ns-0.21.0 | 400 `no outputs provided.` / code 0 |
| cdk-0.18.3 | 400 / **50000 "Empty IN clause for placeholder: b"** |

CORRECTION to the issue text: current cdk does NOT return the 200-empty
— that is cdk MAIN (0b225c9b, unreleased). All three CURRENT arms
reject; the live fork is error-identity only. Bonus datum: cdk 0.18.3
leaks SQL internals in the detail string — a hygiene finding on cdk's
side (their generic 50000 wrapping a SQL error message).

## Item 4: /v1/checkstate with Ys:[Y,Y] (3-family, wire)

| Arm | Result |
|---|---|
| cf (testnut) | 400 `Duplicate Y values not allowed` |
| ns-0.21.0 | 200 — BOTH copies answered (same state) |
| cdk-0.18.3 | 200 — BOTH copies answered (same state) |

Minor correction to the issue's "cdk dedupes": cdk 0.18.3 returns one
state entry per submitted copy (repeat, not dedupe-to-one). Net wallet
semantics identical. cf is the strict arm (reject) — document-only as
the issue says.

## Item 3: HTLC uppercase-data 60s delay (source-verified, NOT wire-measured)

DELAY_MODE_ENABLED=true busy-wait confirmed in source
(spending-conditions.ts); a live probe would pin a testnut DO thread
for 60s and requires full HTLC proof machinery — skipped as
low-value/high-nuisance for a source-certain fact. Cell stays
"source-verified, unmeasured" in the tracker.

## Item 1: melt Paid-before-change ordering

Not externally triggerable without forcing a finalize failure
mid-payment (both sides are source-cited). Remains a pure decision
item: keep+document vs mirror cdk-main's PENDING-until-change-committed
gate.

Ledger rows added for items 2 and 4 (three-family values).
