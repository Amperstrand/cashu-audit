# Smite Lessons for cashu-audit — Applying Lightning Fuzzing Methodology to Cashu

## What smite does (from the lightning-playground)

Smite (lnfuzz/smite) is a **grammar-based fuzzer** for Lightning implementations:
- **IR (Intermediate Representation)**: protocol operations are declarative "programs" (Send/Recv act-ops with typed variables) that a VM executes against a real implementation
- **Generators**: composable "valid traffic baselines" (channel_ops_flow, htlc_hold_then_fail, mpp_same_hash) that produce protocol-legal sequences
- **Mutators**: structural transforms (instruction_delete, instruction_reorder, input_swap) that mechanically derive invalid variants from the valid baselines
- **Coverage-guided**: Nyx hypervisor snapshots track coverage deltas; the fuzzer explores paths that reach new code
- **Artifacts**: findings are banked as JSON with a strict schema (input_raw, input_min, coverage_delta, oracle_verdict, repro) — validated by a contract checker before triage

## What cashu-audit has today

- **miniflare-spend-matrix**: 9 fixed scenarios (forged proof, missing witness, overspend, etc.) — hand-written, no mutation
- **shadow-proxy**: two-implementation comparison (cf vs ns/cdk) — byte-level diffing of responses
- **wallet-mint-interop**: N×N matrix — wallet×mint×flow grid testing
- **edge-soak**: unstructured random load against deployed mints

## The gap: no grammar-based fuzzing

The scenarios in the spend-matrix are **hand-choreographed** — each one tests a specific known attack shape. Smite's insight is that with a grammar + mutators, you mechanically derive **unknown** attack shapes from valid baselines.

## Concrete lessons to apply

### 1. Declarative scenario IR (smite's "programs")

Instead of hardcoded test functions, define scenarios as data:

```yaml
# Today (miniflare-spend-matrix): each scenario is a JS function
# Proposed: scenarios as declarative sequences
scenario: double_spend_race
steps:
  - {op: mint, amount: 100}
  - {op: swap, amount: 50, repeat: 2, concurrent: true}
  - {assert: exactly_one_succeeds}
```

This makes scenarios composable, mutable (lesson 2), and shareable.

### 2. Structural mutators (smite's core insight)

Given a valid swap sequence, mechanically derive:
- **input_delete**: remove one input proof → insufficient_inputs
- **input_reorder**: reorder inputs → should still work (test invariance)
- **input_swap**: swap one proof's secret with another's → signature mismatch
- **amount_mutate**: change one input's amount → balance violation
- **output_duplicate**: duplicate one output → double-signing attempt

These are to the spend-matrix what smite's mutators are to its generators: a force multiplier. 9 hand-written scenarios → 9 × 6 mutators = 54 derived test cases.

### 3. Coverage tracking (smite's Nyx approach, adapted)

We can't use a hypervisor, but we CAN track which code paths are exercised:
- Miniflare's `--coverage` flag or vitest coverage
- Per-scenario coverage maps: "this scenario exercised lines X-Y in verifyProofs"
- A coverage-gap report: "no scenario reaches the HTLC refund path"

### 4. Finding artifacts (smite's strict schema)

Every finding should be a self-contained JSON artifact:
```json
{
  "schema": "cashu-fuzz/1",
  "scenario": "swap_input_delete",
  "input": {"raw": "...", "minimal": "..."},
  "response": {"status": 200, "body": "..."},
  "oracle": "should_have_rejected",
  "invariant": "NUT-03 no_double_sign",
  "coverage_delta": {...},
  "repro": "node scripts/repro.mjs <artifact.json>"
}
```

This makes findings triageable, shareable, and automatically re-verifiable.

### 5. Multi-connection programs (smite's "triangle")

Smite's payer/payee/router triangle → our equivalent is the wallet/mint/upstream triangle:
- wallet creates a melt request with proofs from an OLD keyset
- mint forwards to upstream (CashuBackend/spark)
- upstream settles differently than expected

This tests the era-mixing and fund-ambiguity classes that have been our hardest bugs.

## Recommended implementation order

1. **Mutator engine** (highest ROI): wrap the existing 9 spend-matrix scenarios with 6 structural mutators = 54 derived cases, each automatically checked against the same oracle. No new scenario writing needed.

2. **Coverage map**: add vitest coverage to the miniflare runs; identify which code paths are never exercised by any scenario. This is the "unknown unknowns" finder.

3. **Declarative IR**: migrate scenarios from JS functions to YAML data (enables composition + mutation). Can be incremental — start with the mutator engine operating on the existing JS scenarios.

4. **Finding schema**: adopt a strict artifact format for any fuzz finding, with a validation gate (like smite-artifact-validate.py).

5. **Multi-party scenarios**: model the wallet/mint/upstream triangle for era-mixing and fund-ambiguity testing.

## What NOT to copy

- **Hypervisor snapshots**: we don't need Nyx — miniflare gives us deterministic execution and vitest coverage is sufficient
- **Coverage-guided loop**: we don't have the volume to justify a coverage-guided fuzzer; mutation-based (dumb but structured) is sufficient for the mint surface
- **BOLT message builders**: our protocol is HTTP/JSON, not binary wire format — the grammar is simpler
