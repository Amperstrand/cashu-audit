# Finding: CDK #2252 Divergence Table Partially Outdated

> **Date**: 2026-07-26
> **Source**: Cross-implementation audit of NUT-10/11/14 (cashu-cf, CDK, Nutshell)
> **CDK issue**: https://github.com/cashubtc/cdk/issues/2252
> **Status**: Internal finding (not filed on CDK repo per project decision)

## Summary

The CDK #2252 issue documents 8 behavioral divergences between CDK and Nutshell on NUT-10/11/14 (spending conditions). Our independent Layer 3 AI audit of both implementations found that **6 of the 8 documented Nutshell behaviors are inaccurate** — they don't match the current Nutshell codebase.

This means CDK and Nutshell are **more aligned than CDK #2252 suggests**. The real divergences are narrower.

## Detailed Findings

### Accurate (2/8)

| # | Divergence | Status |
|---|---|---|
| 1 | Malformed/unknown-kind secrets: CDK=anyone-can-spend, Nutshell=fail-closed | ✅ Confirmed accurate |
| 6 | HTLC refund via SIG_INPUTS: CDK=rejects non-HTLCWitness, Nutshell=accepts | ✅ Confirmed accurate |

### Outdated/Wrong (6/8)

| # | CDK #2252 claims Nutshell... | Actual Nutshell behavior (code evidence) | Impact |
|---|---|---|---|
| 2 | rejects duplicate tags | **Uses first-match** — `get_tag()` returns first occurrence silently (secret.py:35-39). Only pubkey x-coordinate uniqueness is checked (conditions.py:136-138). | CDK and Nutshell AGREE — both use first-match |
| 3 | rejects n_sigs > pubkeys upfront | **Validates at verify time, not upfront** — `len(pubkeys) < n_sigs_required` check (conditions.py:158-161) is in `_verify_p2pk_signatures`, not at parse time. Refund path remains usable. | CDK and Nutshell are SIMILAR — both defer to verify time |
| 4 | rejects empty ["pubkeys"] | **Accepts** — `get_tag_all("pubkeys")` returns empty list (conditions.py:63). Handled gracefully — primary key from `secret.data` still provides security. | CDK and Nutshell AGREE — both accept |
| 5 | requires lowercase HTLC hash hex | **Accepts mixed case** — Python's `bytes.fromhex()` is case-insensitive (nut14.py:31-34). Byte-level comparison works regardless of hex case. | CDK and Nutshell AGREE — both accept mixed case. Only cashu-cf enforces lowercase. |
| 7 | ignores duplicate signatures | **Rejects** — explicit check: `if len(set(signatures)) != len(signatures): raise TransactionError("signatures must be unique.")` (conditions.py:148-149) | CDK and Nutshell AGREE — both reject duplicate sigs |
| 8 | accepts witness on plain secret | **Rejects** — explicit check: `if proof.witness is not None: raise TransactionError("witness data not allowed without a spending condition.")` (conditions.py:210-213) | CDK and Nutshell AGREE — both reject. Only cashu-cf accepts/ignores. |

## Corrected Divergence Table

Based on independent code audit (not CDK #2252's documentation):

| # | Issue | CDK (actual) | Nutshell (actual) | cashu-cf | Real divergence? |
|---|---|---|---|---|---|
| 1 | Malformed secrets | anyone-can-spend | fail-closed (unknown kind only) | anyone-can-spend | **YES** |
| 2 | Duplicate tags | first-match | first-match | **rejects all** (strictest) | **YES** — cashu-cf diverges |
| 3 | n_sigs > pubkeys | not on verify path | at verify time | rejects upfront | **PARTIAL** |
| 4 | Empty ["pubkeys"] | accepted | accepted | accepted | **NO** — all agree |
| 5 | HTLC hash case | mixed accepted | mixed accepted | lowercase enforced | **YES** — cashu-cf strictest |
| 6 | HTLC refund SIG_INPUTS | rejects non-HTLCWitness | accepts | accepts | **YES** — CDK diverges |
| 7 | Duplicate sigs | errors | errors | errors | **NO** — all agree |
| 8 | Witness on plain secret | rejects | rejects | accepts/ignores | **YES** — cashu-cf most lenient |

## Possible Explanations for the Discrepancy

1. **Nutshell code changed since CDK #2252 was filed** (Jul 23, 2026) — the PR referenced (nutshell #1008) may have been merged, changing behavior
2. **CDK #2252 was based on PR branch, not main** — the divergence table compares CDK main vs Nutshell PR branch, not Nutshell main
3. **Interpretation differences** — some behaviors are emergent from implementation details (like Python's `bytes.fromhex` being case-insensitive) rather than explicit design choices

## Recommendation

This finding should be shared with the Cashu community when appropriate (e.g., as a comment on CDK #2252 or a new issue). For now, it's documented internally in the cashu-audit project. The corrected divergence table above should be used as the reference for future audits.
