# Issue draft: Melt change outputs are blank — pairing is by index, declared amounts are ignored


## Why a developer or LLM gets confused

Two reasonable models (amounts-matter vs blank-outputs) with zero normative text; the wallet-side mental model (I declared denominations) is the natural one and it is wrong.

## The lesson

NUT-05/NUT-08 should state: melt/swap change outputs are blank (amounts ignored), signatures pair positionally, take amounts from the returned signature. One sentence + a two-denomination test vector kills this class.

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*
