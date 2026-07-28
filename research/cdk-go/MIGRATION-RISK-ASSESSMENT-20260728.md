# CDK-Go Migration Risk Assessment

**Researched**: 2026-07-28 by GLM-5.2 librarian agent
**CDK version**: 0.17.3 | **cdk-go version**: 0.17.1
**Full report**: see background_output(bg_e80b395b) session log

## Key Findings Summary

| Area | gonuts | cdk-go | Risk |
|---|---|---|---|
| NUT coverage | 16 NUTs | 28/29 NUTs | CDK superior |
| V4 support | ✅ works | ✅ native | Parity |
| Spending conditions | Partial (NUT-14 open) | Full (P2PK+HTLC+P2BK) | CDK fixes #324, #328 |
| Error handling | String matching | Typed + protocol codes | CDK superior |
| MIPS support | ✅ pure Go | ❌ not in CI | **CRITICAL BLOCKER** |
| Binary size | ~17MB | ~30MB+ (Go+Rust) | Medium concern |
| API stability | Stable fork | ALPHA (unstable) | HIGH risk |
| Architecture | Sync | Async (Tokio) | Medium refactoring |

## Critical Blocker: MIPS

cdk-go has NO MIPS targets in CI/CD. Prebuilt libraries only for x86_64, aarch64, macOS, Windows.
OpenWrt routers (mips_24kc) require custom Rust cross-compilation.

## Recommendation: DO NOT MIGRATE yet
1. Fix gonuts issues independently (simpler, no arch risk)
2. Contribute MIPS support upstream to CDK
3. Plan migration for when MIPS is available (6-12 month project)
