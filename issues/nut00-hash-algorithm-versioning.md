# Issue draft: NUT-00 hash_to_curve has two live algorithms and no version story


## Why a developer or LLM gets confused

The spec tightened the algorithm without a migration story; implementations carry private shims (nutshell's permanent verify_deprecated fallback, ordered new-first; the lnbits fork's, ordered legacy-first — same shim, opposite order, no guidance).

## The lesson

NUT-00 should name exactly one normative algorithm, mark the other as legacy with a defined compat posture, and ship vectors for both derivations of one input. Cross-impl consensus: both algorithms' outputs for a canonical secret should be in the vector table.

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*

## Corollary: migrations are softforks

nutshell honors algorithm-legacy tokens permanently (`verify_deprecated`);
cdk never did. Migrating a nutshell mint to cdk silently strands every
pre-0.15.1 token — redemption rules tightened by software choice, not spec
change. See position doc closing corollary and the A/B matrix in
`research/AB-TEST-redemption-rules.md`.
