# Cashu Conformance Suite

## Running Tests

```bash
pip3 install requests coincurve pyyaml --break-system-packages
python3 run_matrix.py --mint https://testnut.cashu.exchange
```

## Current Coverage

| NUT | Scenarios | Description |
|-----|-----------|-------------|
| NUT-01/06 | 6 | Info endpoint, keysets, mint metadata |
| NUT-02 | 6 | Keyset validation, fees, units |
| NUT-03 | 3 | Swap (split tokens) |
| NUT-04 | 5 | Mint quote accounting (amount_paid, amount_issued, updated_at) |
| NUT-05 | 3 | Melt quote lifecycle |
| NUT-07 | 2 | Checkstate (UNSPENT/PENDING/SPENT) |
| NUT-08 | 6 | Fee calculation and validation |
| NUT-09 | 1 | Restore signatures |
| NUT-11 | 20+ | P2PK SIG_INPUTS + SIG_ALL (swap + melt) |
| NUT-13 | 3 | Deterministic secrets (BIP32 derivation, restore) |
| NUT-14 | 10+ | HTLC spending conditions (swap + melt) |
| NUT-18 | 2 | Payment request CBOR decode |
| NUT-19 | 1 | Cache headers |
| NUT-20 | 4 | Quote signature validation |
| NUT-26 | 2 | Bech32m payment request encoding |
| NUT-29 | 3 | Batch mint/check operations |
| **Total** | **107** | |

## Adding Scenarios

See `scenarios/` directory for examples. Use the `@scenario` decorator.

## Consumer conformance lane (TollGate token corpus)

`consumer_conformance.py` executes the TollGate protocol repo's token
conformance corpus (OpenTollGate/tollgate `corpus/`, PR #30) against
real consumers. The corpus is the frozen prediction set — every
expected verdict was recorded before the run, and a surprising FAIL is
triaged against the corpus/source before being believed.

```bash
python3 consumer_conformance.py \
  --corpus /path/to/tollgate/corpus \
  --gateway http://192.168.13.1:2121 \
  --mint http://192.168.13.221:8383 \
  --cdk-cli ~/.cargo-target/release/cdk-cli \
  --cashu /opt/cashu-venv/bin/cashu \
  --portal /path/to/tollgate-captive-portal-site \
  --report-out reports/consumer-conformance-<date>.json
```

Lanes: `lifecycle` (decode/verify/checkstate per fixture per consumer;
verify spends only regen'd siblings — committed fixtures are never
consumed), `http` (replays corpus vectors against the gateway,
matcher vocabulary from the corpus manifest, mode-aware preconditions,
rate-limiter-polite pacing), `portal` (the portal checkout's
vendored-corpus vitest suite). Rows are PASS / FAIL / SKIP (unmet
precondition, never silent) / FILL (corpus cell was `unknown` — the
runner fills the matrix). First live runs 2026-10-16 against the
degraded rig: 79 rows — every FAIL ultimately triaged to a corpus bug
(including one wrong content-type assertion initially misread as a rig
anomaly; the error format prints want != actual — read it before
believing a ghost) or a runner bug. Zero unexplained FAILs (report JSONs
and OpenTollGate/tollgate#30).

## Nightly corpus workflow (ops)

`.github/workflows/nightly-corpus.yml` (cron `17 3 * * *` UTC + dispatch):

- **Coverage**: the offline surface — corpus self-validation, the
  consumer-conformance decode lanes (cdk-cli v0.18.1 cargo-cached,
  nutshell **0.21.0 via docker** (`conformance/docker-nutshell` wrapper —
  2026-10-23: PyPI fully deleted breez-sdk-spark <0.18 making cashu
  0.20.3+ uninstallable; the image restores the original reference and is
  PyPI-immune; issue #54)
  the environs breakage), and the portal's vendored-corpus suite (9
  tests). GH runners cannot reach the lab rig/fakewallet, so the
  http/checkstate legs SKIP — those stay on the in-lab runner.
- **Divergence gate** (`nightly_diff.py`): each run diffs its report
  against `conformance/nightly-baseline.json`; NEW or CHANGED
  divergence rows file one issue each (title carries the key verbatim).
  Dedupe matches the key against open-issue TITLES by direct list —
  GitHub search cannot phrase-match the slash-laden keys (proven the
  hard way: issues #44–#46). Bootstrap (missing baseline) records and
  files nothing.
- **State**: baseline + `conformance/NIGHTLY-STATUS.md` are committed
  back by the workflow's bot identity; `reports/` stays untracked
  (house gitignore) and ships as the run artifact.
- **Pipeline health**: a workflow-level failure (infra, not verdicts)
  files/keeps a single open `pipeline-health` issue, deduped the same
  way; close it when a nightly passes again.
- Tag `nightly-corpus-v1` marks the first steady-state green run
  (39115159562).
- The permanent cron fires unattended: run 39195559901 (2026-10-19
  03:37 UTC, success — ~20 min scheduler jitter past the 03:17 target;
  the TEMP evidence cron was removed after it fired once, PR #52).

## Weekly conformance-v2 lane (ops)

`.github/workflows/conformance-v2.yml` (Mondays 06:00 UTC + dispatch): the
deterministic live-verdict lane on LOCAL docker arms — #33's rebuild of
the delisted public-test-mint lane, #34's closed design (deterministic,
artifact-only). Three arms: nutshell 0.20.3 / nutshell 0.21.0 / cdk 0.18.1,
each booted by `run_arm_lane.py` together with an **invoice-oracle** arm
(a scratch mint whose only job is issuing invoices the target has never
seen — FakeWallet mints auto-settle their own invoices, which raced every
melt-success scenario before this).

- **Per-arm seeds** (`expected-fail-*.json`): documented divergences with
  justifications (registry-linked where positioned). Expected fails do not
  gate; every unlisted FAIL does.
- **Divergence gate** (`v2_diff.py`): compares the run's verdicts against
  `v2-baseline/<arm>.json`; red on NEW or PASS→FAIL/TIMEOUT flips only.
  `EXPECTED_FAIL → PASS` is reported as a RESOLUTION — the cue to update
  the seed and the registry entry. Mutation-checked (a planted FAIL
  refuses).
- **Local runs**: `python3 conformance/run_arm_lane.py --target
  ns=nutshell:cashubtc/nutshell:0.20.3 --host-network --expected-fail
  conformance/expected-fail-nutshell-0.20.3.json` (`--host-network` for
  hosts with a broken docker bridge hairpin — ai-legion; GH runners don't
  need it).
- Reference verdicts: ns-0.20.3 98P/8EF/6S · ns-0.21.0 104P/2EF/6S ·
  cdk-0.18.1 102P/4EF/5S+1 non-gating TIMEOUT. Note 0.21.0 passes all six
  0.20.3 SIG_ALL/HTLC positioned divergences — the lane reproduces the
  registry's convergence data deterministically.
