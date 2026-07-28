# NUT-11 P2PK Violations in cashu-cf (2026-07-27)

Source: LLM spec audit of cashu-cf against NUT-11 spec + Nutshell Python reference.
Auditor: GLM-5.2 via opencode audit prompt system.
Full report: [NUT-11-result.md](../signoffs/cashu-cf/NUT-11-result-20260727.md)

## Summary

5 spec violations found in `src/mint/spending-conditions.ts`. 3 are security-relevant.

## Violations

| # | Requirement | Spec | cashu-cf behavior | Severity |
|---|------------|------|-------------------|----------|
| 1 | Invalid sigflag MUST be rejected | L104: "Proof **MUST** be rejected as unspendable" | `getSigFlag()` silently falls back to SIG_INPUTS | HIGH — allows malformed proofs |
| 2 | Duplicate keys detected by x-coordinate | L268: "compared using their lowercase x-coordinate" | Uses full string comparison; `02..` and `03..` bypass check | HIGH — allows duplicate keys |
| 3 | Locktime Multisig conditions continue after expiry | L215: "continue to apply" | Main pubkeys excluded after locktime — only refund path checked | MEDIUM — limits spending flexibility |
| 4 | SIG_ALL witness MUST be in first input only | L133: "first input of the transaction" | `proofs.find()` accepts witness on ANY input | LOW — overly permissive |
| 5 | SIG_ALL message format | L146: single defined format | Tries 11 message format variants | LOW — compat hack |

## Cross-implementation comparison

| Behavior | Nutshell (Python) | CDK (Rust) | cashu-cf (TypeScript) |
|----------|-------------------|------------|----------------------|
| Invalid sigflag | ❌ rejects | ❌ rejects | ✅ accepts (BUG) |
| Duplicate key by x-coord | ✅ x-coord comparison | ✅ x-coord comparison | ❌ string comparison (BUG) |
| Locktime: main + refund | ✅ both available | ? | ❌ refund only (BUG) |
| SIG_ALL witness location | ✅ first input | ? | ❌ any input |

## Resolution

Filed as [ISSUE-030](https://github.com/Amperstrand/cashu-cf/blob/main/docs/issues/ISSUE-030-nut11-p2pk-spec-violations.md).
✅ **Fixed** (commit `1d1e401`, 2026-07-27).
