# FINDINGS — NUT-04/07 quote-state observability matrix (2026-10-31)

Frozen predictions: `PREDICTIONS-nut07-states.md`. Arms: testnut (cf),
ns-0.21.0, cdk-0.18.3 (all fakewallet-backed; docker + live probe).

## The matrix

| Observable | cf (testnut) | ns-0.21.0 | cdk-0.18.3 |
|---|---|---|---|
| UNPAID at creation | **PAID immediately** | **PAID immediately** | UNPAID ✓ |
| PENDING during settle | absent | absent | absent (UNPAID→PAID, no intermediate) |
| State after single mint | **PAID (never ISSUED)** | ISSUED ✓ | ISSUED ✓ |
| State after batch mint | **PAID (never ISSUED)** | ISSUED ✓ | ISSUED ✓ |
| Unknown quote | 404 `quote_not_found`/14005 | 400 detail-only/code 0 | 400 50000 "Unknown quote" |

## Findings

1. **cf never reports ISSUED** (both mint paths). NUT-04: wallets poll
   state to detect already-minted quotes; on cf the ISSUED signal
   never arrives — a spec-conformant wallet concludes "not yet minted"
   forever, retries, and eats 11003 "outputs already signed" instead
   of learning from state. Wallet-side workaround exists (treat 11003
   as ISSUED-equivalent) but the state machine is incomplete vs both
   references. → cf issue (our repo, fix queued behind deploy creds).
2. **PENDING is unobservable on every fakewallet** — cf/ns pay at
   creation (no UNPAID either), cdk pays with no intermediate state.
   The spec's UNPAID→PENDING→PAID middle leg needs a holding backend
   (regtest-LN tier / kali) — cell stays honestly n/m.
3. UNPAID-at-creation exists ONLY on cdk — another quiet family fork:
   wallets that create a quote and immediately poll (pre-payment) see
   PAID on cf/ns fakewallet mints (test mints are always "paid") but
   UNPAID on cdk test mints. Test-suite assumptions diverge by family.
4. Unknown-quote error identity: three-way fork (404/14005 vs
   400/code-0 vs 400/50000) — recorded in the ledger's identity rows.

Probes: this file's table is the evidence (single script, three arms,
rapid-poll during settle).
