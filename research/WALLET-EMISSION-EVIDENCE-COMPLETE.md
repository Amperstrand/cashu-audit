# Wallet emission evidence complete (filing 1 support)

## cashu-ts v4.10.1 HTLC refund witness — captured on the wire (new)

`experiments/must-gap-vectors/ts4_refund_capture.mjs`:

- emission: `{"signatures":["25809150baaf41cf..."]}` — preimage OMITTED
- vs stock cdk 0.17.6: `400 {"code":50000,"detail":"Secret is not a HTLC secret"}`
- vs nutshell 0.20.3 (control): refund spent (5 new proofs)

Both major wallet families now have live wire evidence (nutshell:
`{"preimage":null,...}`; cashu-ts: omission).

## nutshell wallet version sweep vs stock cdk 0.17.6 (new)

0.19.0 / 0.19.2 / 0.20.0 / 0.20.2 — all fail identically with the
misleading 50000 error.

## gonuts

`AddWitnessHTLC` always sets `Preimage` (receiver-side helper); no
refund-path spend emission exists — unaffected, not a data point.

## Research: related ecosystem work (2026-09-13)

- **SatsAndSports nut-10-checker**: built ON CDK (its wallet side
  constructs witnesses via cdk's types → preimage always present → the
  wallet-natural encodings are never exercised). Self-described
  obsolete (pre-SIG_ALL update). Its "CDK 58/58" result is consistent
  with our findings — the checker cannot see this bug class.
- **nutshell #848** ("NUT-14 HTLC refund path incorrectly requires
  preimage (spec violation)") fixed via **PR #803** — the nutshell-side
  mirror of our cdk finding was already recognized as a spec
  violation. cdk has the inverse shape of the same problem.
- **nutshell #1009 + PR #1008**: active SIG_ALL/P2PK/HTLC refactor
  wave (SatsAndSports, following the CDK architecture — introduced the
  SpendingRequirements class). #1008 contains the open error-handling
  question our soft-failure proposal answers ("reject and log? what
  error do we return?").
- **cashu_spilman_channels**: Spillman-style channels on Cashu
  (SatsAndSports) — funding is P2PK 2-of-2 + time-locked refund
  (P2PK-family refund works on cdk today; the HTLC-family refund is
  the broken one). Refund paths are safety-critical there.
- **NUT-14 spec**: has a "Witness format" section showing both fields;
  the Sender Pathway text requires only signatures. Issue draft
  updated to cite this precisely.
- SatsAndSports' checker announcement (nostr, 2025-10) tags TollGate,
  calle, vnprc — existing public relationship.
