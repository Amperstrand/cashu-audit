# CAMPAIGN-SUMMARY-2026-09-12: Vector Campaign Session Log

*Autonomous session, 2026-09-12 ~06:00–08:00 Europe/Oslo. All work
committed to cashu-audit main (917d26a and earlier); upstream drafts
updated in private/ per keep-internal policy.*

## Session goals (from prior turn)

1. Design + run additional experiments (compute-heavy, token-light)
2. Pin drift boundaries across the full release line
3. Answer "is the HTLC bug fixed upstream?" definitively

## What ran

| Experiment | Scale | Result |
|---|---|---|
| NUT-14 + refund vectors (H1-H6, P1-P2) | 16 mint versions | F6/F7/F8/F9 (d6 root cause) |
| Version gap-fill ephemerals | 0.16.0/0.17.0/0.18.0/0.18.1/0.19.2/0.20.1 | exact drift boundaries |
| Wallet-mint boundary sweep | 6 wallet versions × 4 mint types | F10 (NUT-20 divergence) |
| Wallet-level HTLC refund + wire tap | 0.20.3 + 0.20.2 wallets | null-preimage wire evidence |
| SIG_ALL melt vectors (M1-M3) | 8 mints | F11 + F5 narrowed to swap-path |
| cdk upstream HEAD build + vectors | cargo build on ai-legion | F6 confirmed live upstream |
| Nightly vector regression | cron 03:17 + drift diff | standing infra |
| Auditor port/500 fix | nemo-lab displacement | #193 closed |

## Findings added this session (F6–F11, on top of F1–F5)

- **F6** d6 root cause: cdk `HTLCWitness.preimage: String` required;
  wallet sends `"preimage":null` (wire-captured); empty-string works.
  **Still present in upstream HEAD built today.**
- **F7** nutshell HTLC refund branch sawtooth: missing ≤0.16.0 and
  0.17.0–0.18.2; present 0.16.5 and 0.19.0+.
- **F8** hash-case: all 16 mints digest-compare (cashu-cf was the lone
  outlier — delay-mode addressed a real bug).
- **F9** P2PK refund path healthy everywhere.
- **F10** NUT-20 mint-auth scheme divergence: wallet 0.20.3 signs
  new-scheme; cdk 0.17.x legacy-only; nutshell mints <0.20.3 reject →
  **current wallet mints on 2/9 battery mints**.
- **F11** SIG_ALL melt message conformant on cdk 0.17–0.18 + nutshell
  0.20.3 only; family flipped at the 0.20.3 boundary (same as swaps).

## Precise boundaries table (nutshell)

| drift | window |
|---|---|
| sigflag validation lost | 0.17.0 – 0.19.2 |
| HTLC refund branch missing | ≤0.16.0 and 0.17.0 – 0.18.2 |
| SIG_ALL message old format | ≤ 0.20.2 |
| duplicate-key MUST regressed | 0.20.2 – 0.20.3 |
| NUT-20 new-scheme mint verify | 0.20.3 only |
| uncompressed pubkey accepted | all versions tested |

## Infrastructure state at session end

- Battery: 9 mints UP; nightly vector cron 03:17; drift log
  `~/must-gap-runs/nightly.log`
- Auditor: **:8100** (8000 belongs to nemo-lab), keepalive cron */5*,
  /mints/ 200
- CLN tunnel + signet mints: unchanged
- Ephemeral containers + cdk HEAD build artifacts: cleaned (binary at
  /tmp/cdk-head-test/target/release/cdk-mintd preserved until reboot)

## Open threads for next session

1. Upstream filings (F6/F10 strongest; drafts in private/) — owner go
   required
2. P2PK wire capture (#192) — still open, 4 approaches documented
3. CLN auto-payer quote-list mismatch (#195)
4. Docker bridge root cause (#194)
5. Optional: 0.14/0.15 pre-v1 API driver variant (low value)
