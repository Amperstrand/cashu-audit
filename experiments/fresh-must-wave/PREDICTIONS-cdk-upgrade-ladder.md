# FROZEN PREDICTIONS — cdk closed-loop upgrade ladder (2026-10-26, before run)

Setup: ONE persistent workdir (/data: sqlite + TOML), ONE mnemonic,
sequential cdk-mintd containers 0.17.6 → 0.17.7 → 0.18.0 → 0.18.1 →
0.18.2, fakewallet sat. Before each stop: mint proof P (unspent,
must stay redeemable), spend a proof (must stay spent), create+pay a
quote Q WITHOUT minting (must stay mintable).

Legs at every rung:
- K: /v1/keys keyset ids unchanged from rung 1 (mnemonic-derived)
- R: pre-ladder proof P swaps (redeemable across upgrade)
- S: spent proof re-swap fails (spent ledger survives upgrade)
- Q: paid-unminted quote mints after upgrade

| Boundary | K | R | S | Q | Notes |
|---|---|---|---|---|---|
| 0.17.6 → 0.17.7 | = | ok | spent | ok | backport: same schema, same config (env) |
| 0.17.7 → 0.18.0 | = | ok | spent | ok? | config era breaks (env→TOML, operator step); sqlx migrations expected to run forward on the 0.17 DB |
| 0.18.0 → 0.18.1 | = | ok | spent | ok | 11017 cap lands (irrelevant to legs) |
| 0.18.1 → 0.18.2 | = | ok | spent | ok | |

Failure modes that would matter:
- 0.18 refuses the 0.17 sqlite (no migration path): operators must
  re-init — keysets re-derive, but the SPENT ledger vanishes → the
  double-spend window REOPENS on upgrade (fund-class hazard).
- Q lost at any rung: paid invoices mintable pre-upgrade become dead
  (burned money for the wallet).
- Keyset ids change: every pre-upgrade token needs wallet-side
  re-keyset handling (tollgate #818's brick class).
- Any leg flipping = probe bug first (per house rule) — re-read the
  container logs before claiming a cdk defect.
