# CDK mint error identity: duplicate signed outputs reported as InvoiceAlreadyPaid instead of NUT-19 11003

Date: 2026-10-29
Status: CONFIRMED (end-to-end reproduction) — fixed on Amperstrand/cdk, upstream unfixed as of cdk 0.18.2
Class: error-identity divergence (wallet-visible behavior)
Affected: cdk-mintd (all versions through 0.18.2), issue path

## Summary

When a wallet re-derives blinded messages the mint has already signed
(seed reuse after store loss, NUT-09 restore gone wrong, a restored
backup colliding with a burned derivation range), the mint's issue
path hits a UNIQUE violation on the blind-message/signature inserts.
cdk-mintd propagates the raw `Database::Duplicate`, which the
ErrorResponse mapping turns into **InvoiceAlreadyPaid** — a QUOTE-level
refusal. The correct identity is NUT-19 **11003 BlindedMessageAlreadySigned**
(the code exists in cdk-common; the swap path already maps `Duplicate`
correctly to `DuplicateOutputs` — only the issue path diverges).

## Why it matters (measured, not hypothesized)

Wallets key error identity to pick a recovery strategy. With
InvoiceAlreadyPaid the wallet concludes "this quote was already paid"
and takes a quote-failure path that ROLLS BACK the derivation counter;
every future mint then re-derives the same burned range and is refused
again — the wallet is **permanently bricked against that mint**. This
is precisely the tollgate #257/#266/#480 incident class (gonuts
history), reproduced end-to-end on cdk 0.18.2:

1. W1 mints 1000 sat → keyset counter range [0..54) exposed to the mint.
2. W2 (same seed, fresh store) mints 500 → InvoiceAlreadyPaid (wrong identity).
3. W2 restart + FRESH quote → refused again, and again, forever. Balance 0.
   (mint-side log shows the refusal; wallet-side keyset_counter stuck.)

With the corrected 11003 identity the wallet's saga compensation KEEPS
counter increments, so the wallet **walks past the burn** in
ceil(burn_depth / secrets_per_mint) attempts: measured 27 secrets per
500-sat mint, attempts 1–2 refused, attempt 3 SUCCEEDED (counter 54→81,
balance 500).

## Fix

Amperstrand/cdk branch `fix/duplicate-outputs-error-identity`
(b9444ab9 + EVIDENCE.md 340423d3): map the issue path's duplicate
inserts to `Error::BlindedMessageAlreadySigned`. One-site fix; the
swap path was already correct. Upstream submission is human-gated
(fork-first doctrine) after audit + dogfood.

## Assertion guidance for parity suites

- A same-seed collision case must assert the ERROR IDENTITY, not just
  refusal: unpatched mint ⇒ "Request already paid"; patched ⇒ 11003
  text ("Blinded Message is already signed").
- The flip detector pattern: pin the unpatched behavior; the assertion
  goes red when a fixed mint lands, then flips to assert the walk-past
  heal. Reference implementation: OpenTollGate/tollgate-module-basic-go
  `tests/cloud-lab/parity/test_parity.py` case 40 (PR #1137).
- Wallets have NO skip-ahead 11003 handler in cdk 0.18.2 — recovery is
  walk-past, not single-step. Optional hardening: advance the counter
  past the signed range in one step (restore-style).

## Cross-references

- tollgate incident class: OpenTollGate/tollgate-module-basic-go #257, #266, #480
- Harness lineage: killerproxy.py (#497) → killproxy.py (deterministic
  swallow-at-acceptance placement used to isolate the boundary)
- Related class in this directory: melt-quote stage witness validation
  (2026-09-16) — same lesson: the wire-visible error shape is the contract.
