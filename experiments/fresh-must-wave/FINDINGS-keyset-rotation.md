# FINDINGS — keyset-rotation rung, cdk 0.18.2 (2026-10-29)

Frozen predictions: `PREDICTIONS-keyset-rotation.md`. Driver:
`keyset_rotation.py` (management RPC via generated gRPC stubs in
`out/grpc_stubs/` — proto extracted from cdk v0.18.2). Tollgate #818
is the motivating incident.

## Verdict: rotation surface is CONFORMANT and wallet-friendly

| Leg | Result |
|---|---|
| R1 `/v1/keys` post-rotation | new keyset B only ✓ |
| R2 `/v1/keysets` | BOTH listed; A `active=false` (no expiry set) ✓ |
| R3 retired keys fetchable | **`GET /v1/keys/{A}` → 200 with keys** (NUT-02's required rotation flow works) ✓ |
| R4 swap A-proof → B outputs | **200 — old proofs stay spendable (fund safety)** ✓ |
| W1 swap → A-referenced outputs | 400/**12002 "Inactive Keyset"** |
| W2 mint → A-referenced outputs | 400/**12002 "Inactive Keyset"** |
| W3 checkstate of A-proof's Y | 200, correct state ✓ |

## The wallet-facing datum (feeds tollgate #818 self-heal)

Retired-keyset OUTPUTS get a DISTINCT identity — **12002 Inactive
Keyset** — vs 12001 Unknown Keyset for never-seen ids. A wallet can
therefore distinguish "keyset retired, re-fetch /v1/keys and re-keyset
my outputs" (12002) from "garbage id" (12001) and self-heal. Old-keyset
INPUTS remain spendable indefinitely (spec: take-out-of-circulation is
wallet-driven via swaps; mint verified internally). Wallet rule from
NUT-02: prioritize swapping inactive-keyset proofs.

## Corrections (house discipline)

- R3 first probed `/v1/keysets/{id}/keys` — 404 on ALL families —
  but that path is NOT in NUT-02; the spec endpoint is
  `GET /v1/keys/{keyset_id}` (02.md line 184), which works on
  cdk (incl. retired keysets), ns-0.21.0, and testnut. No divergence:
  retraction of the initial "endpoint unimplemented" read.
- cdk-mintd 0.18.2 management RPC needs the TOML section
  `[mint_management_rpc]` at `config init` time (env vars alone are
  ignored once settings are DB-backed) + `x-cdk-protocol-version: 1.0.0`
  gRPC metadata on every call.

## Not covered

- ns/cf rotation mechanics (no management RPC equivalent probed; ns
  rotation is operator-side).
- Multi-rotation ladders (A→B→C) and expiry-driven retirement
  (final_expiry) — same harness, one more rung each.
