# FROZEN PREDICTIONS — melt-identity family completion M5-M7 (2026-10-31, BEFORE probes)

Context: cf baseline captured earlier tonight (M4/M5 cells). These legs
complete the family matrix on ns-0.21.0 and cdk-0.18.3 using melt quotes
backed by synthetic-but-structurally-valid bech32 invoices (104-word
q-strings + valid checksum — the shape both references' quote-create
accepted per the invoice ladder).

| Leg | ns-0.21.0 | cdk-0.18.3 |
|---|---|---|
| Q0 melt-quote create on synthetic valid-bech32 invoice | 200 (ladder said yes) | 200 (ladder said yes) |
| M5 melt, inputs from UNKNOWN keyset | 400 (detail-quote or keyset error; ns code 0 style) | 400 12001 "Unknown Keyset" |
| M6 melt underfunded (valid keyset, insufficient amount) | 400 fee/balance detail, code 0 | 400 11001-class |
| M7 melt witness-less P2PK proof (genuinely minted+signed, no witness) | 400 (ns spending-condition error, code 0; P2PK depth?) | 400 20006-class or 30006? — cdk witness identity UNKNOWN, this leg pins it |

Probe-bug rules: proofs must LIST-wrapped; fee arithmetic per arm
(ns fee 1, cdk 0); P2PK proof must be MINTED first (locked secret) so
the signature is valid and only the witness is missing.
