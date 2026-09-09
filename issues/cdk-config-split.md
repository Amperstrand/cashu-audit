# Issue draft: cdk-mintd: env vars silently don't apply on the database-backed config path


## Why a developer or LLM gets confused

Split config systems with different precedence rules; the doc describes one path universally.

## The lesson

Either apply from_env() on the database path too (one call), or document the precedence per path. We flagged this in our cdk branch commit message; trivial upstream fix.

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*
