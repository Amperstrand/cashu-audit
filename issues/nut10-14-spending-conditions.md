# Issue draft: NUT-10/11/14 — references converged on violating NUT-11 MUSTs; two redemption divergences survive

> **Umbrella + measured matrix.** Per-thing breakdown (each with finding,
> test method, community discussion, history, links, and a known-vs-novel
> upstream flag) lives in the per-divergence drafts:
> d1 `nut10-d1-unknown-kind-secrets.md` ·
> d2 `nut11-d2-duplicate-tags-must-unenforced.md` ·
> d3 `nut11-d3-nsigs-exceeds-pubkeys-must-unenforced.md` ·
> d4 `nut10-d4-empty-pubkeys-tag-spec-contradiction.md` ·
> d5 `nut14-d5-hash-hex-case.md` ·
> d6 `nut14-d6-htlc-refund-witness-shape.md` ·
> d7 `nut11-d7-duplicate-signatures.md` ·
> d8 `nut11-d8-witness-on-plain-secret.md`
> Filing candidates (NOVEL only): d2+d3 (one bundled nuts amendment), d4
> (one-line reconciliation). Everything else is tracked or settled — link
> for reference only, never re-file (spam rule).

## Finding (measured 2026-09-09, A/B probe, both arms stable ×2, controls green)

`conformance/ab_probe_p2pk_htlc.py` against **cdk-mintd/0.18.0** and
**Nutshell/0.20.3** (both FakeWallet, fresh keysets, identity-verified).
Probe: mint regular proofs → blind-swap into divergence-triggering secrets →
attempt the discriminating spend. Matrix + journal:
`conformance/reports/ab-p2pk-htlc-2026-09-09.{json,log}`.

Of the 8 divergences cdk#2252 documents, only **#1 and #6 survive** between
these releases. The other six converged — but **convergence ≠ conformance**:

| # | Cell | Spec text | cdk 0.18.0 | nutshell 0.20.3 | Verdict |
|---|---|---|---|---|---|
| d1 | unknown kind `["MBS",…]`, no witness | NUT-10 Caution: "**may** be treated as regular anyone-can-spend" | ACCEPT | REJECT | Spec-permissive vs stricter-than-spec. **LIVE divergence** — cdk-minted token bricked at nutshell |
| d2 | duplicate `n_sigs` tags | NUT-11: tags appear "exactly **ONCE** … the P2PK secret is malformed and the Proof **MUST** be rejected as unspendable" | ACCEPT | ACCEPT | **Both violate a MUST.** Converged the wrong way |
| d3 | `n_sigs`=3 > 2-key pool, refund after expiry | NUT-11: "exceeds the total number of keys in its pathway … **MUST** be rejected as unspendable" | ACCEPT | ACCEPT | **Both violate a MUST** (the malformed secret is never rejected; refund path spends) |
| d4 | empty `["pubkeys"]` tag | NUT-10: tags are "ONE or more strings", `["pubkeys"]` listed as a **valid** example — but NUT-11: "arrays with two or more strings" | ACCEPT | ACCEPT | **NUT-10 and NUT-11 contradict each other**; both impls follow NUT-10 |
| d5 | HTLC hash in UPPERCASE | NUT-14: hash_hex "64-character **lowercase** hexadecimal string" (producer rule) vs mint MUST "SHA256(hex_to_bytes(preimage)) == hex_to_bytes(data)" (byte-wise, case-blind) | ACCEPT | ACCEPT | Spec-ambiguous; both take the byte-equality reading |
| d6 | HTLC refund, SIG_INPUTS witness with signatures only (no `preimage` field) | NUT-14 Sender Pathway: sender spends "by providing signature(s) as per … Refund MultiSig" — preimage not involved | REJECT (code 50000, "Secret is not a HTLC secret") | ACCEPT | **LIVE divergence.** cdk arguably spec-wrong: rejects the documented Sender Pathway because a signatures-only JSON shape deserializes as `P2PKWitness` and `verify_htlc` demands `HTLCWitness`. Error text misleads (the *secret* IS HTLC; the *witness shape* isn't) — see issue 6 (error-code registry). Nutshell-spendable refund bricked at cdk |
| d7 | same valid signature twice from the required key | NUT-11 CAUTION (non-normative): count "unique public keys", not signatures | REJECT | REJECT (11000 "signatures must be unique.") | Both stricter than guidance; converged. Defensible hygiene |
| d8 | witness on plain (non-NUT-10) secret | silent | REJECT | REJECT (11000 "witness data not allowed without a spending condition.") | Spec-silent; converged. Fine |

## Why this matters (the receipt-incident pattern, inverted)

d2/d3 mean money whose validity is **mint-dependent** for spec-literal reasons:
a third implementation (or an LLM-generated client) that enforces the printed
MUSTs will reject tokens both references accept — the mirror image of our
NUT-00 incident, where the strict mint stranded tokens lenient mints honored.
NUT-11's MUSTs existing on paper while both references fail them is the same
"verification theater" class the framework hunts: the clause has no vectors,
so no suite pins it.

d1/d6 are bricking risks for **Spilman channels (nuts#296)**, which build on
exactly these mechanisms: an unknown/future `kind` is bricked at nutshell
today; a nutshell-style HTLC refund is bricked at cdk today.

## Why a developer or LLM gets confused

- Witness JSON has **two plausible shapes** for an HTLC refund spend
  (`{"signatures":[…]}` vs `{"preimage":null,"signatures":[…]}`); only the
  envelope differs, and only cdk cares. Classic dual-representation boundary.
- NUT-10 vs NUT-11 disagree on tag arity, so "is `["pubkeys"]` valid?" has
  two spec-correct answers depending on which file you read.
- cdk's d6 error names the wrong object ("Secret is not a HTLC secret" when
  the secret is fine) — the failed spend is the only contact, and it lies.

## The lesson

Divergence-counting is the wrong KPI: six of eight divergences "closed", two
of them by jointly abandoning a MUST. Equalization must be audited against
the spec text, not celebrated as convergence.

## Improvement

1. cdk#2252 comment with our measured matrix (table went stale vs 0.20.3) —
   one artifact, no new repo issue.
2. nuts: (a) vectors + negatives for the two existing NUT-11 MUSTs (duplicate
   tags; n_sigs>pool) so suites can pin them; (b) resolve the NUT-10/NUT-11
   tag-arity contradiction; (c) state whether `HTLCWitness.preimage` is
   optional (decides d6); (d) decide fail-open vs fail-closed for unknown
   kinds (decides d1).
3. cdk: accept signatures-only HTLC refund witness (or at minimum fix the
   error text/code — 50000 "Secret is not a HTLC secret" → a witness-kind
   error).
4. Probe is permanent: `conformance/ab_probe_p2pk_htlc.py` re-runs the full
   matrix in ~5 min against any two mint URLs.

## Security triage (added 2026-09-09)

| cell | theft vector | funds-loss vector | assessment |
|---|---|---|---|
| d1 unknown kind | **YES, conditional — unknown-kind only** (revised 2026-09-09): the malformed-pubkey lock-voiding half was measured DEAD on cdk 0.18.0 (cell d1b: REJECT 20008 — cdk#2252's fallback claim is stale). Residual exposure: future locking kinds (channels/nuts#296, new NUT-28-style extensions) — lock void at any lenient mint that doesn't know the kind | no — leniency *rescues* the holder | the real question upstream hasn't engaged: fail-open vs fail-closed for *unknown locks*, not malformed secrets generally |
| d2 duplicate tags | indirect — wallet-vs-mint parse ambiguity (wallet's receive-time lock check could read a different tag than the mint enforces); unverified, research item | mint-dependent validity (DotNet rejects) | needs the wallet-side differential probe |
| d3 n_sigs>pool | no | primary path unsatisfiable by construction | low |
| d4 empty tag | no | no | docs-only |
| d5 hash case | no | no | encoding-only |
| d6 refund witness | no over-acceptance found (cdk's dummy-preimage acceptance is spec-defensible; nutshell verifies-when-present) | **YES, proven total** — no witness shape spends an HTLC refund on both mints (empty intersection, measured d6/d6b/d6c); channel failure-recovery is mint-dependent | lead upstream candidate |
| d7 dup sigs | defensive (forecloses naive signature-counting in other impls) | no — cannot strand a correct spend | settled, safely strict |
| d8 witness-on-plain | closes a smuggling surface | no | settled |

No cell lets an attacker spend *validly locked* money under today's two
kinds. The exposure classes are: lock-voiding on malformed/future locks
(d1, theft-shaped) and refund-path incompatibility (d6, loss-shaped).

## Provenance

- Upstream: cashubtc/cdk#2252 (table), nutshell PR #1008 (reviewed branch ≠
  shipped 0.20.3 subset — strict on d1/d7/d8, lenient on d2/d3/d4/d5).
- Census + timeline + community correct-behaviour evidence (incl. the
  a1denvalu3 split-handling quote and DotNut#42):
  `research/CENSUS-nut10-11-14-correct-behaviour.md`.
- Ours: prior measurements in `conformance/CROSS-IMPLEMENTATION-GUIDE.md`
  §6.4/§6.5 — §6.5 ("nutshell rejects n_sigs>pool upfront") is now STALE,
  superseded by this matrix; `reference-reports/cdk.json` measured d6=ACCEPT
  on an older cdk (softfork-by-upgrade in action).
