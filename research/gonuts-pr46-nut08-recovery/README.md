# gonuts-tollgate PR #46 — hostile NUT-08 recovery repro (declassified)

Published from the private mirror (`Amperstrand/cashu-audit-private`
commit `471327d`, dir `private/gonuts-pr46-nut08-recovery/`) after the
owner's 2026-11-03 declassification (cashu-audit #67): gonuts-tollgate
findings are PUBLIC; anything touching cdk or other maintained Cashu
projects stays in the private mirror.

Contents (verbatim at the audited commit):
- FINDINGS-2026-11-03-gonuts-pr46-nut08-recovery.md — the write-up
- PREDICTIONS-2026-11-03.md — frozen predictions (written before any run)
- hostile_nut08_recovery_test.go — wire-level hostile proxy harness,
  V1-V6; PASS = the gap is PRESENT (vulnerable-behavior assertions)
- run-log-2026-11-03.txt — 7/7 hostile PASS + full battery + -race clean

The flipped (post-fix) assertions live in #67 §11 — that table is the
acceptance criteria for the PR #46 guards.
