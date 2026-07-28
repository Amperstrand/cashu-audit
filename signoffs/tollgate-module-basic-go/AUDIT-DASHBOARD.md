# TollGate Audit Dashboard — 2026-07-28

## Layer 3 AI Audit Results

| NUT Group | Signoff | Verdict | Key Finding |
|---|---|---|---|
| NUT-00 (Token Format) | [NUT-00-20260728-glm52.md](NUT-00-20260728-glm52.md) | **FAIL** | V4 token decoding broken in gonuts; V3 works |
| NUT-04/05 (Mint API) | [NUT-04-05-20260728-glm52.md](NUT-04-05-20260728-glm52.md) | **PASS (WARN)** | Fragile string-based spent token detection |
| NUT-10/11/14 (Spending) | [NUT-10-11-14-20260728-glm52.md](NUT-10-11-14-20260728-glm52.md) | **WARN** | No TollGate-level validation; inherits 2 gonuts FAILs |

## Findings Summary

| ID | Severity | Finding | Location | Status |
|---|---|---|---|---|
| TG-NUT00-F1 | **HIGH** | V4 token decoding fails on valid V4 tokens from modern wallets | gonuts/cashu.go:401 | Open |
| TG-NUT00-F2 | MEDIUM | V4 decode error masked by V3 fallback in DecodeToken | gonuts/cashu.go:175 | Open |
| TG-NUT00-F3 | MEDIUM | Fund() uses V4-only decode (no V3 fallback) | merchant.go:1101 | Open |
| TG-NUT00-F4 | LOW | Stale comment "cashu tokens start with cashuA" | merchant.go:1089 | Open |
| TG-NUT05-W1 | MEDIUM | String matching for spent token detection (fragile) | tollwallet.go:139 | Open |
| TG-NUT11-F1 | **HIGH** | No spending condition validation before crediting user | tollwallet.go:132 | Open |
| TG-NUT11-F2 | **HIGH** | Inherited: duplicate P2PK tags silently overwritten | gonuts (NUT-11) | Inherited |
| TG-NUT14-F1 | **HIGH** | Inherited: HTLC signature bypass with pubkeys/no n_sigs | gonuts (NUT-14) | Inherited |

## Attack Surface

### P2PK/HTLC Token Attack (HIGH)
A malicious user can POST a P2PK-locked token as payment. TollGate credits internet access. Later, TollGate can't spend the locked token. Result: free internet for attacker, worthless tokens for gateway.

### V4 Token Rejection (HIGH)
Any user with Cashu wallet ≥ 0.20.0 (defaulting to V4 tokens) cannot pay a TollGate router. Must use `--legacy` flag to produce V3 tokens.

## Dependency Chain
```
tollgate-module-basic-go
  └── gonuts-tollgate (5 signoffs, WARN overall)
       ├── NUT-00: PASS (but V4 decode broken — found in TollGate QA)
       ├── NUT-04/05: WARN (accounting fields missing)
       └── NUT-10/11/14: WARN (duplicate tags + HTLC bypass)
```

## Recommendations
1. **Fix V4 decoding** in gonuts (CBOR struct tags)
2. **Add spendability check** after Receive() — reject locked tokens
3. **Migrate to CDK** (#305) — native V4 + proper spending condition validation
4. **Use generic DecodeToken** in Fund() instead of DecodeTokenV4
