# Issue draft: checkstate request body shape differs across implementations


## Why a developer or LLM gets confused

NUT-07 names the field conceptually but implementations serialized different keys during evolution.

## The lesson

Pin the exact key in NUT-07 (and accept both on read during a deprecation window). Add a request/response pair to the vector suite.

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*
