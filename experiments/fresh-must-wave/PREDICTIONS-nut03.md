# FROZEN PREDICTIONS — NUT-03 unit consistency on testnut (2026-10-25, before run)

testnut is the only multi-unit arm (sat + usd keysets). #406 made unit
consistency normative (2026-09-15). Legs:

| Leg | Prediction |
|---|---|
| U1 usd quote → mint 1-usd outputs (usd keyset) | 200 (usd advertised; full lifecycle works) |
| U2 swap: sat-keyset inputs → usd-keyset output | reject — identity? (unit/keyset mismatch class) |
| U3 swap: mixed inputs (sat proof + usd proof) | reject — identity? |
| U4 swap: sat inputs → sat output with usd keyset ID on the output | reject (keyset-unit mismatch) |

Any acceptance in U2-U4 = a unit-consistency violation (#406's exact
target). Identities recorded per leg.
