# Issue draft: Mint error codes are de facto per-implementation


## Why a developer or LLM gets confused

The NUT error tables exist but don't cover all classes (parse vs semantic vs verification) and implementations extended privately.

## The lesson

Extend the NUT error registry: reserve ranges, require distinct codes for parse vs verification failures, and recommend one JSON body shape. Cheap, huge UX payoff (see our cashu.me error-UX draft).

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*
