# Spec-Audit Framework — reusable methodology for cross-implementation behavioral audits

**Derived from:** the NUT-00 secret-encoding campaign (2026-09-08/09)
**Tested against:** cdk, nutshell, cashu-cf, nucula, cashu-core-lite
**Tools:** ab_probe.py, demo-bug.mjs, scenario suite in conformance/

## The framework

### 1. Identify a boundary where two valid-looking readings exist

Look for places where:
- The spec uses descriptive language ("checks that X == Y") without RFC-2119 force
- The type system permits multiple encodings (e.g., `bytes` where the canonical form is a string)
- Two implementations made different choices (grep for `deprecated`, `BACKWARDS COMPAT`, `legacy`)
- The failure surfaces only at an external verifier (spend, swap, redeem — never at construction)
- The spec's own examples are ambiguous or incomplete

### 2. Write frozen predictions BEFORE running anything

Predict what each implementation will do for each input class. Write it down.
This is the discipline that makes the results meaningful — mismatch = probe
bug until proven otherwise, never "interesting finding."

### 3. Build the differential probe matrix

| Input class | Implementation A | Implementation B | ... |
|---|---|---|---|
| canonical | predict | predict | |
| divergent reading 1 | predict | predict | |
| divergent reading 2 | predict | predict | |
| garbage/control | predict | predict | |

One probe script that runs the full lifecycle per cell: mint → unblind →
spend. Record /v1/info version + pubkey per arm (environment identity guard).

### 4. Run on pinned versions in isolated environments

- Docker containers per arm (fakewallet for mints)
- Fresh ports, fresh keysets (same mnemonic = same keyset = camouflage hazard)
- Verify /v1/info identity BEFORE trusting any result
- Run each probe at least twice (flake detection)

### 5. Analyze results against frozen predictions

- All match → hypothesis confirmed, document
- Any mismatch → investigate to root cause (probe bug vs real divergence)
- Never adjust predictions after seeing results

### 6. Document as a divergence report

House format: `divergences/NUT-XX-TOPIC-DATE.md` with the measured matrix,
the spec text that permits both readings, and the operational consequence.

## Audit dimensions (from the campaign + community findings)

| Dimension | What to probe | Already audited |
|---|---|---|
| Secret encoding | entropy vs utf8-of-string hashing | ✅ (this campaign) |
| Hash algorithm version | deprecated vs domain-separated | ✅ (this campaign) |
| Blank change outputs | amount-matching vs index-pairing | Partially (Amethyst #3847) |
| Amount JSON serialization | string vs int | ✅ (personal hit) |
| Checkstate request shape | Ys vs outputs keys | ✅ (personal hit) |
| Error code registry | per-impl codes for same failure | ✅ (personal hit) |
| Keyset ID formats | V1 short vs V2 hex, v4 token encoding | ✅ (personal hit) |
| Keyset active semantics | mintable vs redeemable | ✅ (personal hit) |
| Interrupted-op recovery | saga semantics per implementation | Adjacent (our ISSUE-103) |
| **P2PK/HTLC spending conditions** | 8 divergences documented in cdk#2252 | **NEXT — highest value** |
| Deterministic secrets (NUT-13) | derivation path per implementation | Not started |
| DLEQ verification (NUT-12) | deprecated vs current DLEQ format | Not started |
| Token V3/V4 encoding | CBOR details, short keyset IDs | Not started |
| NUT-09 restore semantics | which outputs get signatures back | Not started |
| NUT-20/29 signatures | quote signing differences | Not started |
| Quote TTL semantics | absolute vs relative expiry | Not started |

## P2PK/HTLC: the next high-value audit target

cdk#2252 already documents **8 behavioral divergences** between cdk and
nutshell in NUT-10/11/14 spending-condition verification. These are exactly
the class our framework tests:

1. Malformed NUT-10 secrets: cdk=anyone-can-spend, nutshell=rejected
2. Duplicate tags: cdk=first-wins, nutshell=rejected
3. n_sigs > pubkeys: cdk=refund-only, nutshell=fully-bricked
4. Empty pubkeys tag: cdk=accepted, nutshell=rejected
5. HTLC hash case: cdk=any-case, nutshell=lowercase-only
6. HTLC refund via SIG_INPUTS: cdk=rejected, nutshell=accepted
7. Duplicate signatures: cdk=error, nutshell=ignored
8. Witness on plain secret: cdk=rejected, nutshell=ignored

**A token spendable at a cdk mint can be bricked at a nutshell mint** (and
vice versa for #6). The Spilman channel proposal (nuts#296) builds directly
on these mechanisms — any divergence is a channel-bricking risk.

**Probe design:** craft proofs hitting each divergence, swap them against
both mints, record accept/reject per cell. The frozen prediction matrix
writes itself from the cdk#2252 table.

## Tools committed to this repo

| Tool | What it does | Where |
|---|---|---|
| `conformance/ab_probe.py` | 3-derivation A/B probe (canonical/algolegacy/trap) | committed |
| `conformance/run_filtered.py` | Full matrix with per-scenario timeout + JSON output | committed |
| `conformance/scenarios/nut00_secret_encoding.py` | Permanent conformance scenarios (3) | committed |
| `conformance/reference-vectors/nut00-secret-encoding.json` | Cross-impl vectors incl. negative | committed |
| `conformance/cf_crypto.py` | House crypto helpers (hash_to_curve both variants) | at ai-legion:/tmp (copy to repo) |
| `demo-bug.mjs` | One-minute end-to-end demo (docker + node) | in receipt/recovery/ (copy to repo) |

## Session learnings (condensed from RETROSPECTIVE)

1. **Frozen predictions before runs** — the methodology that makes results meaningful
2. **Environment identity verification** — /v1/info version check before trusting ANY result
3. **Canary spend before scale** — test the smallest unit end-to-end first
4. **Negative vectors in every suite** — a suite that can't fail on the known trap isn't a suite
5. **Ad-hoc scripts are for reproduction only** — write tests as scenarios with house helpers
6. **One environment per purpose** — superseded environments die immediately
7. **Reuse house crypto helpers** — hand-rolled point math produces probe bugs
8. **Powers-of-2 for output splits** — both mints expect denomination-aligned splits
9. **Fee-aware probes** — read input_fee_ppk from /v1/keysets before sizing outputs
10. **The frozen-prediction mismatch discipline** — mismatch = probe bug until proven otherwise
