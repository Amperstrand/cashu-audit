# Cashu Conformance Matrix — 2026-11-13 22:39 UTC

**Targets** (identity captured at run start):
- `https://signut.cashu.exchange` — Signet Cashu Mint / Nutshell-CF/0.0.1

**Summary**: 0 passed, 2 failed, 0 skipped (2 total)

## Post-Deploy Boundary Wave 2

| Scenario | `Signet Cashu Mint@Nutshell-CF/0.0.1` |
|---|---|
| `mpp_subsat_partial_boundary` | ❌ |
| `melt_change_outputs_cap` | ❌ |

> ❌ `mpp_subsat_partial_boundary` @ `https://signut.cashu.exchange`: sub-sat partial accepted pre-fix (amount=2, Math.ceil overcharge live) — cashu-cf 92da59a6 not deployed (issue #49)

> ❌ `melt_change_outputs_cap` @ `https://signut.cashu.exchange`: 101 outputs passed validation (400: {"error": "payment_failed", "detail": "HTTP status: 500 Destination said it doesn't know invoice: Ma) — cashu-cf b473a00d not deployed (issue #100)
