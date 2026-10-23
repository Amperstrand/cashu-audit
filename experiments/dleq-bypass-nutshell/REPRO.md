# Nutshell 0.21.0 mixed-proof DLEQ bypass — runnable repro

Finding: `research/FINDINGS-2026-10-23-item6-nut18.md` §6b (root cause:
`cashu/wallet/wallet.py:998-1002` `verify_proofs_dleq` — `return` where
`continue` belongs; the first dleq-less proof aborts verification for the
whole list).

`repro_dleq_bypass.sh`: boots a local FakeWallet nutshell arm
(cashubtc/nutshell:0.21.0, host networking), wallet-1 sends a real V3
token (JSON, editable), a garbage DLEQ `{e,s,r}` is injected into
proof[1], wallet-2 receives.

Frozen verdicts — **independently reproduced 2026-10-23** (capture:
`repro-capture-*.txt`):

- BYPASS `[no-dleq, GARBAGE, no-dleq]` → `Received 4 sat` (5 net of 1
  input fee) — the garbage proof is never verified
- CONTROL `[GARbage]` alone → `Exception: DLEQ proof invalid.`

NUT-12 threat: a malicious mint can pair an honest-looking dleq-less
first proof with invalid-dleq followers; receive/redeem AND mint paths
are gated by the same function. Upstream filing is owner-gated
(registry row 6b; staged text in the findings doc).
