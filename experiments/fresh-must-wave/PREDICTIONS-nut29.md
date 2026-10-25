# FROZEN PREDICTIONS — NUT-29 batch atomicity (written BEFORE run, 2026-10-25)

Arms: ns-0.21.0, cdk-0.18.2 (docker FakeWallet), testnut (cashu-cf).
Endpoint: POST /v1/mint/bolt11/batch
{quotes, outputs[, quote_amounts][, signatures]}.
Setup per arm: two PAID bolt11 mint quotes (64 + 32 sat), valid blinded
outputs prepared for the batch. Spec: 8 pre-validation checks, all-or-
nothing ("MUST reject the entire batch... without minting any quotes"),
duplicate-quote error code **11016** named in the spec.

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| R route exists | yes (declares NUT-29) | yes | yes |
| 0 control: 2 paid quotes, 3 valid outputs summing 96 | 200, 3 sigs | 200, 3 sigs | 200, 3 sigs |
| A one corrupted B_ (garbage hex, same length) in a balanced batch | **unknown — the probe's question**; cf is saga-per-item (ISSUE-051 history) → candidate for partial/no-sigs 200 or 4xx | 422 pydantic/secp whole reject | 422 whole reject (secp parse) |
| B unknown quote id among valid | 4xx whole (MUST) — code fork expected | 4xx | 4xx |
| C duplicate quote ids | 4xx — code? | 4xx | 4xx **11016** (spec-named) |
| D empty quotes array | 4xx | 4xx | 4xx |

Secondary observations: error identities (code + message) per leg; sig
count on any 200; whether quote states get consumed on a rejected
batch (re-submit control after a rejected leg — if the quotes still
mint, rejection was clean; if spent/pending, the batch burned them —
FUND-LOSS CLASS if a rejected batch consumes paid quotes).

Prediction on the re-submit leg: all arms leave quotes mintable after
rejection (spec's "without minting any quotes" honored); any arm that
burns a quote on rejection is a finding.
