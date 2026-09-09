# Issue draft: V1 and V2 keyset ids both live; v4 tokens cannot encode V1


## Why a developer or LLM gets confused

Two valid formats with migration left as an exercise; tooling fails late (at encode time) rather than at receipt.

## The lesson

Document the compatibility matrix in NUT-02 (which formats can appear in which token versions), and require wallets to degrade gracefully (v3 encode fallback) rather than throw.

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*
