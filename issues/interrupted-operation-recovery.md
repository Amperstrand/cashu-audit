# Issue draft: Recovery from interrupted operations is unspecified


## Why a developer or LLM gets confused

This is the largest underspecified area after encoding — and the most expensive, since every implementation solves it privately and differently (interoperable wallets cannot make the same recovery assumptions).

## The lesson

A NUT for operation recovery semantics: state machines for melt/mint/swap across crash points, idempotency keys, and restore obligations (NUT-09 exists for outputs; nothing covers mint-side obligations).

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*
