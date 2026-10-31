# FINDINGS — melt-path error identities, pre-deploy baseline (2026-10-31)

Frozen predictions: `PREDICTIONS-melt-identities.md`. Purpose: the
pre-deploy cells for cashu-cf so the post-deploy diff against
fix/saga-error-codes (@5aaf50b) is mechanical.

## Baseline cells (testnut, deployed = OLD saga codes)

| Leg | Result |
|---|---|
| M4 unknown melt quote + garbage proof | 400 `invalid_proof`/30003 — cf verifies PROOF SIGNATURES before quote lookup (ordering datum; the quote_not_found saga arm exists but is shadowed) |
| M5 inputs from unknown keyset | 400 `unknown_keyset`/**10009** — the exact code the fix remaps to 12001 |
| M7 witness-less P2PK (garbage C) | 400 `invalid_proof`/30003 — C-signature check precedes the witness path; the 30006→30007 split is only reachable with a genuinely-signed P2PK proof (pool's live-minted tokens cover this post-deploy) |
| invoice shape at melt-quote create (malformed bolt11) | **cf ACCEPTS (fakewallet), ns rejects "Bech32 string is not valid", cdk rejects 50000 "Invalid payment request"** — 3-way fork at the quote layer; cf is the lenient one |

## Family comparison (partial — real invoices needed for deep melt legs)

Melt-quote create with a malformed invoice: cf lenient / ns 400
bech32 / cdk 400 50000. Deep melt error legs (insufficient,
witness-class) against ns/cdk need payable invoices = oracle/regtest
tier (kali); recorded as the next corpus pass.

## Post-deploy expectations (the diff to run)
- M5 cell: 10009 → 12001 (string `unknown_keyset` unchanged)
- M7-class with REAL signed P2PK proofs: 30006 → 30007 on the
  witness-less shape
- M4: potentially re-ordered if the saga remap touches verification
  order (it should not — only numeric codes changed)
