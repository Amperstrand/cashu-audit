# cdk fix branch validated (filing 1 staged)

Branch: **Amperstrand/cdk `htlc-refund-witness`** (owner-review stage).

- Fix: `verify_htlc` extracts witness components variant-agnostically
  (same accessors `verify_sig_all_htlc` already uses). One file.
- Tests: nut14 18/18, cdk htlc 14/14 (2 new), nut11 P2PK 65/65.
- External 17-vector suite: exactly one delta vs stock HEAD — natural
  refund witness accepted (H3); locktime gate and all controls intact.
- Melt regression M1-M3 200/200/200.
- Wallet-level: nutshell 0.20.2 refund spend PASS on patched (FAIL on
  stock with the misleading 50000 error).
- Naive `preimage: Option<String>` was rejected in design: it would
  break P2PK (untagged enum discriminator). Documented in the branch
  commit message.

Evidence pack + issue draft: `private/EVIDENCE-cdk-filing1.md`,
`private/DRAFT-ISSUE-cdk-htlc-refund-witness.md` (staged, not filed).

## Repro test verified on both trees (final staging)

Self-contained unit repro (`test_verify_htlc_refund_signature_only_witness_repro`,
on the branch) — paste-able into main:

- stock main @ 8077e501: `Err(IncorrectSecretKind)` ← the wire error, reproduced
- branch: `test result: ok. 1 passed`

Final filing draft with collapsibles: `private/FINAL-DRAFT-cdk-issue.md`.
