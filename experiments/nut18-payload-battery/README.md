# NUT-18 payload battery (#63)

Repeatable cells for the NUT-18 `PaymentRequestPayload` surface and the
adjacent id-spelling/expiry axes, distilled from the 2026-10-31..11-07
research arc. Every verdict is an **exact error-identity assertion**
(status + detail + code) against `expected.json` — family regexes are
forbidden by house method; `expected.json` changes only with a
frozen-prediction probe run recorded in the private mirror.

Findings of record: `research/FINDINGS-2026-10-31-nut18-payload-spelling.md`,
`research/SURVEY-2026-10-31-v3-keyset-id-spellings.md`,
`research/FINDINGS-2026-11-01-nut02-expiry-wallets.md` (+ 0.22.1
checkpoint notes inside each).

## Layout

- `fixtures/` — crafted payload variants (from real local-test-mint
  proofs; no live value) + captured WIRE bodies (nutshell 0.21.0 and
  0.22.1 CLI emissions, cdk 0.18.2 emission). The captures caught both
  divergences the crafted variants missed — replay them, don't skip them.
- `expected.json` — the frozen verdict matrix.
- `harness/` — cdk example (the wallet's own serde call) + cashu-ts
  vitest battery.
- `runners/` — per-cell entrypoints:
  - `run_cdk_parse.sh` — cdk parse column (builds the example at the
    pinned checkout; `CDK_CHECKOUT`/`CDK_TARGET` overridable).
  - `run_ts.sh` — cashu-ts decode+settlement columns (`TS_WORKTREE` at
    v5.0.0-rc.9; `BATTERY_MINT_URL` enables settlement cells).
  - `mint_side_probe.py` — mint-side spelling identities (self-minting
    control proofs; env `MINT`).
  - `expiry_recipe.md` — expiry cells (arm + rotation + wallet legs).
  - `check_expected.py` — verdict comparator used by the shell runners.

## Conda/venm note

The python runners use the host venv (`/opt/cashu-venv`) for nutshell
crypto helpers; on a clean host `pip install cashu==0.21.0 httpx bolt11`
reproduces it.

## Provenance

Predictions of record: P1–P12 (payload), PN1–PN5 (mint-side), PE1–PE4
(expiry), PR-A–D (0.22.1 checkpoint) — all in the private mirror
`private/nut18-live/`. Fixture regeneration + full transcripts live
there; this directory holds the public, lane-runnable subset.
