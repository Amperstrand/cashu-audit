# Issue draft: 'active' conflates mintable and redeemable


## Why a developer or LLM gets confused

NUT-02's flag semantics don't distinguish the mint window from the redeem window of a keyset's life.

## The lesson

Either split the flag (mintable/redeemable) or define 'active' as redeem-inclusive and document that issuance uses the newest keyset for a unit.

## Improvement



*Source: cashu-audit confusion inventory 2026-09-08; full evidence in research/.*
