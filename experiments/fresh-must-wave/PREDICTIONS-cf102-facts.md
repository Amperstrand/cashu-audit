# FROZEN PREDICTIONS — #102 decision-bundle facts (2026-10-30, before run)

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.3 |
|---|---|---|---|
| POST /v1/restore outputs:[] | 400 "at least one output" (issue-cited) | 400/422 (ns validates arrays; likely pydantic 422) | 200 {"outputs":[],"signatures":[]} (cdk 0b225c9b) |
| /v1/checkstate Ys:[Y,Y] duplicate | 400 duplicate-reject (issue-cited) | dedupe-or-reject unknown (predict reject or 200-both) | 200 with both entries same state (cdk 70654052) |
| HTLC uppercase-data spend | ~60s stall then result (source: DELAY_MODE 60s busy-wait) | n/m (no delay mode) | n/m (case-insensitive, no delay) |

HTLC leg on testnut: ONE request only (it pins a DO thread for 60s on
the live test mint — single-shot, then stop).
