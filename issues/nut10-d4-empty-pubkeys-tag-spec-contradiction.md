# d4 — Empty `["pubkeys"]` tag: NUT-10 and NUT-11 contradict each other

**Status:** INTERNAL RESEARCH (overview build, 2026-09-09). Nothing filed.
**Upstream novelty:** NOVEL — we found no upstream tracker for the
intra-spec contradiction itself. Both implementations converged on the
NUT-10 reading, so nothing is broken in practice today; this is a
documentation bug and a trap for the next implementer (especially
LLM-generated ones reading one file only). Cleanest possible nuts PR:
one-line reconciliation in 11.md.

## What we found (measured 2026-09-09)

A secret containing the bare tag `["pubkeys"]` (key, no values) plus
`n_sigs=1` spends with a data-key signature at BOTH cdk-mintd/0.18.0
(parses to empty key list; pool = data key) and Nutshell 0.20.3. But the
two spec documents disagree about whether that tag is even well-formed:

- **NUT-10** (since #320, 2025-12-16): "Each individual tag is an array of
  **ONE or more strings**" — and lists `["pubkeys"]` — "a tag with the key,
  `\"pubkeys\"`, and no tag values" — as an **example of a valid tag**.
- **NUT-11** (since 2023-10-13, never touched): "Tags are arrays with **two
  or more strings**".

## How we tested

- Probe cell `d4_empty_pubkeys_tag` (raw-tag secret builder, data-key
  SIG_INPUTS witness).
- Same arms/lifecycle/evidence as d1; stable ×2.
- Spec archaeology: `git log -S` in the nuts clone — "two or more strings"
  traces to the original NUT-11 PR (#40, 2023-10-13); "ONE or more" +
  the valid example trace to #320 (2025-12-16). Nobody reconciled 11.md.

## Community discussion (summary)

- #320's clarification was a NUT-10-side edit; NUT-11's tag-format sentence
  is stale since that day. No issue/PR discusses the conflict (census
  checked nuts/cdk/nutshell trackers).
- cdk#2252 item 4 framed it as cdk-accepts vs nutshell-branch-rejects —
  the rejection never shipped; both now accept, silently taking NUT-10's
  side of the contradiction.

## Historic context

- 2023-10-13: NUT-11 original wording ("two or more").
- 2025-12-16: nuts#320 clarifies NUT-10 the other way; contradiction born.
- 2026-09-09: measured — both implementations follow NUT-10.

## Links (internal reference; no upstream engagement)

- cashubtc/nuts 10.md (Tag format section) vs 11.md (Tags section)
- nuts#320 — the 2025 clarification
- nuts#40 (2023) — the stale sentence's origin
- cashubtc/cdk#2252 (item 4) — prior divergence state, reference-only
- Census: `research/CENSUS-nut10-11-14-correct-behaviour.md`

## Direction (our read)

One-line nuts PR: align NUT-11's tag-format sentence with NUT-10's "ONE or
more strings" (or move the whole tag grammar to NUT-10 and reference it).
Zero behavioral change anywhere — the definition of a safe spec PR, and a
good first contribution vehicle if we want one.
