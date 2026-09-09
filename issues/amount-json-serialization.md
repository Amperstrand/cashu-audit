# Issue draft: Amount fields: int in examples, string in the wild


## Why a developer or LLM gets confused

JSON number vs string for u64 is a classic cross-language trap (JS precision); the spec text never pins the wire type, so each impl resolves it privately.

## The lesson

NUT-00 should pin: amounts are JSON integers in all request/response bodies (or explicitly strings — either, but ONE), and the vector suite should include a round-trip blob per endpoint.

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*
