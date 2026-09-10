# d5 — HTLC hash hex case: the spec binds producers and verifiers differently

**Status:** INTERNAL RESEARCH (overview build, 2026-09-09). Nothing filed.
**Upstream novelty:** PARTIAL — known as a divergence (cdk#2252 item 5);
our addition is that both implementations converged on the byte-equality
reading, which exposes the two-clause tension in NUT-14 itself.

## What we found (measured 2026-09-09)

An HTLC secret whose `data` hash is 64-char **UPPERCASE** hex spends with
the correct preimage at BOTH cdk-mintd/0.18.0 and Nutshell 0.20.3.
NUT-14 contains two differently-binding statements:

- Producer rule: `hash_hex` "is … encoded as a 64-character **lowercase**
  hexadecimal string" (and the preimage likewise).
- Verifier MUST: "Mints and wallets **must verify**
  `SHA256(hex_to_bytes(Proof.witness.preimage)) == hex_to_bytes(Proof.secret.data)`"
  — byte-wise, therefore case-blind.

Both implementations enforce the second and ignore the first on the mint
side — consistent, defensible, and now uniform (nutshell-branch rejection
per cdk#2252 never shipped; cashu-cf normalizes case at construction).

## How we tested

- Probe cell `d5_htlc_uppercase_hash` (`build_htlc_secret(hash_hex.upper())`,
  preimage-only witness).
- Same arms/lifecycle/evidence as d1; stable ×2.

## Community discussion (summary)

- nuts#315 (2026-01-08, "NUT-11 + NUT-14: New P2PK/HTLC rules") introduced
  both the lowercase producer rule and the byte-equality verifier equation
  in the same PR — the tension is original to the section, not later drift.
- nutshell#1009 lists incomplete #315 implementation among its failure
  causes; the #1008 merge chose the byte-equality half.
- No thread we found adjudicates "must mints reject non-lowercase data?"
  (census checked; the question is subtle enough nobody has asked it).

## Historic context

- 2026-01-08: #315 lands both clauses.
- 2026-07-23: cdk#2252 item 5 records cdk=any-case vs nutshell=lowercase.
- 2026-08-11: #1008 merges; nutshell drops lowercase-only.
- 2026-09-09: both-accept measured.

## Links (internal reference; no upstream engagement)

- cashubtc/nuts#315 — both clauses' origin
- cashubtc/nutshell#1009, #1008 — the implementation choice
- cashubtc/cdk#2252 (item 5) — prior state, reference-only
- Census: `research/CENSUS-nut10-11-14-correct-behaviour.md`

## Direction (our read)

Low urgency (interoperable, uniform). One clarifying sentence in NUT-14 —
"the mint's obligation is the byte equality above; the lowercase encoding
is a producer requirement" — would close it. Fold into any future nuts PR
of ours rather than standalone.
