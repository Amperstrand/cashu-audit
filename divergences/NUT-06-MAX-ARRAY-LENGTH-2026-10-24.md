# NUT-06: `max_array_length` — advertisement matrix + non-enforcement (2026-10-24)

NUT row: NUT-06 (tracker card updated). Source: first tracker-priority
probe. Method: `/v1/info` capture across 6 arms (research/
mint-nut-support.json, 2026-10-24) + live enforcement probe on testnut.

## Spec (06.md:102, after #425 landed 2026-08-15)

`max_array_length` is **(optional)**: "the maximum length the mint
accepts for any array in a request, such as `inputs`, `outputs` or
`Ys`. Wallets **SHOULD** split larger requests into batches no bigger
than this."

## Advertisement (wire, all arms)

| Arm | max_array_length |
|---|---|
| testnut (cashu-cf) | **50** |
| rugs (cashu-cf) | **50** |
| nutshell 0.20.3 | *(absent)* |
| nutshell 0.21.0 | 1000 |
| cdk 0.18.1 | 1000 |
| cdk 0.18.2 | 1000 |

- ns 0.20.3 predates the field — spec-legal (optional) but leaves
  wallets without a discoverable limit.
- cashu-cf advertises 50 = **20× tighter** than both references. A
  wallet that batches to the spec-example value (1000) fails on
  testnut/rugs wherever the limit IS enforced downstream.

## Enforcement (probe, testnut, 2026-10-24)

`POST /v1/checkstate` `{"Ys": [...]}` with distinct placeholder Ys:

| Array size | Verdict |
|---|---|
| 10 / 50 / 51 / **60** | all **200**, full `states` array returned |

**testnut does not enforce its advertised limit** on checkstate.
Error-identity note: the first probe attempt used the `outputs` request
shape and got `400 invalid_request "Missing Ys, proofs, or secrets"` —
cashu-cf's checkstate accepts several request shapes (`Ys` or `proofs`
or `secrets`), wider than NUT-07's example; related: issues/
nut07-checkstate-shape.md.

## Impact

Low severity, but two-sided:

1. A wallet honoring the advertised 50 on testnut is over-conservative
   (harmless); a wallet ignoring it works on testnut today and breaks
   on any enforcing mint.
2. The 50-vs-1000 advertisement fork means a batch size that works
   against every reference mint can still fail on cashu-cf mints once
   enforcement exists — or, conversely, cashu-cf's unenforced 50
   currently misleads nobody but teaches wallets nothing.

Follow-up in cashu-cf (our repo, owner-gated like all changes): decide
enforce-or-correct-the-value; the probe stays as the regression vector.
