# Cross-Implementation Testing Guide

How to run the Cashu conformance suite against any mint and compare
results across the three major implementations: **cashu-cf**
(TypeScript), **Nutshell** (Python), and **CDK** (Rust).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Running Against Any Mint](#2-running-against-any-mint)
3. [Local Nutshell Setup](#3-local-nutshell-setup)
4. [Local CDK Setup](#4-local-cdk-setup)
5. [Comparing Results Across Implementations](#5-comparing-results-across-implementations)
6. [Known Divergences](#6-known-divergences)
7. [Scenario Reference](#7-scenario-reference)

---

## 1. Prerequisites

```bash
cd conformance
pip3 install requests coincurve pyyaml --break-system-packages
```

Verify installation:

```bash
python3 -c "from conformance.client import MintClient; print('OK')"
```

---

## 2. Running Against Any Mint

### Single mint

```bash
python3 run_matrix.py --mint https://testnut.cashu.exchange
```

Output is written to `reports/matrix.md`. The exit code is non-zero if
any scenario FAILs.

### Multiple mints (side-by-side comparison)

```bash
python3 run_matrix.py \
  --mint https://testnut.cashu.exchange \
  --mint http://localhost:3338
```

The matrix table renders one column per mint so you can spot
divergences at a glance.

### From a YAML config file

```bash
python3 run_matrix.py --mints-file mints.yaml
```

Example `mints.yaml`:

```yaml
mints:
  - name: testnut
    url: https://testnut.cashu.exchange
    type: cashu-cf
  - name: nutshell-local
    url: http://localhost:3338
    type: nutshell
  - name: cdk-local
    url: http://localhost:3339
    type: cdk
```

### Custom output path

```bash
python3 run_matrix.py --mint https://testnut.cashu.exchange \
  --output reports/comparison-$(date +%Y%m%d).md
```

---

## 3. Local Nutshell Setup

Nutshell is the Python reference implementation. The official Docker
image bundles a FakeWallet backend so you can mint tokens without a
Lightning node.

```bash
# Generate a mint private key (or use a fixed one for reproducibility)
MINT_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

docker run -d -p 3338:3338 --name nutshell \
  -e MINT_LIGHTNING_BACKEND=FakeWallet \
  -e MINT_PRIVATE_KEY=$MINT_KEY \
  -e MINT_HOST=0.0.0.0 \
  -e MINT_PORT=3338 \
  -v nutshell-data:/data \
  cashubtc/nutshell:latest
```

Verify it is running:

```bash
curl -s http://localhost:3338/v1/info | python3 -m json.tool | head -5
```

Run the conformance suite:

```bash
python3 run_matrix.py --mint http://localhost:3338 \
  --output reports/nutshell-local.md
```

**SIG_ALL note:** Nutshell uses a legacy SIG_ALL message format (inputs
secrets only) rather than the standard format (inputs secrets + C +
outputs). The conformance suite auto-detects this via the version string
and switches to legacy mode. If you see SIG_ALL failures, check the
`sigall_mode` field in the reference reports.

Tear down:

```bash
docker stop nutshell && docker rm nutshell
```

---

## 4. Local CDK Setup

CDK is the Rust reference implementation. Use `cdk-mintd` with the
FakeWallet backend for testing without a Lightning node.

```bash
docker run -d -p 3339:3338 --name cdk-mintd \
  -e CDK_MINTD_BACKEND=FakeWallet \
  -e CDK_MINTD_MINT_INFO_NAME="CDK Test Mint" \
  -e CDK_MINTD_SEED=0000000000000000000000000000000000000000000000000000000000000001 \
  -e CDK_MINTD_HOST=0.0.0.0 \
  -e CDK_MINTD_PORT=3338 \
  -v cdk-data:/data \
  ghcr.io/cashubtc/cdk-mintd:latest
```

Verify it is running:

```bash
curl -s http://localhost:3339/v1/info | python3 -m json.tool | head -5
```

Run the conformance suite:

```bash
python3 run_matrix.py --mint http://localhost:3339 \
  --output reports/cdk-local.md
```

Tear down:

```bash
docker stop cdk-mintd && docker rm cdk-mintd
```

---

## 5. Comparing Results Across Implementations

### Three-way comparison

Spin up both local instances (sections 3 and 4), then run:

```bash
python3 run_matrix.py \
  --mint https://testnut.cashu.exchange \
  --mint http://localhost:3338 \
  --mint http://localhost:3339 \
  --output reports/three-way.md
```

The generated matrix shows one row per scenario and one column per mint.
Cells use:

| Icon | Meaning |
|------|---------|
| ✅ | PASS |
| ❌ | FAIL (note appended below the table) |
| ⏭️ | SKIP (feature not supported by this mint) |
| ⚠️ | XFAIL (expected failure) |

### Interpreting divergences

A scenario that PASSES on CDK but FAILs on cashu-cf (or vice versa)
indicates a spec compliance gap in the failing implementation. The
`reports/FINDINGS-*.md` files contain root-cause analysis for each
failure.

### Using reference reports

The `reference-reports/` directory contains pre-generated JSON results
from CDK, Nutshell, and Nutmix. Compare your live results against these
baselines:

```bash
python3 -c "
import json
with open('reference-reports/nutshell.json') as f:
    ref = json.load(f)
for r in ref['results']:
    print(f\"{r['status']:6s} {r['name']}\")
" | head -20
```

---

## 6. Known Divergences

The following behavioral differences have been identified through this
conformance suite. Full details are in the `divergences/` directory.

### 6.1 NUT-11/14: Locktime pathway independence

After locktime expiry, the primary (sig) pathway should remain valid
alongside the refund pathway.

| Implementation | Primary after locktime | Refund after locktime |
|---|---|---|
| **CDK** | ✅ Works | ✅ Works |
| **Nutshell** | ❌ Dropped (SIG_ALL only) | ✅ Works |
| **cashu-cf** | ❌ Dropped | ❌ HTLC refund requires preimage |

**Affected scenarios:** `p2pk_locktime_after_expiry_primary_still_works`,
`htlc_receiver_path_after_locktime`, `htlc_locktime_after_expiry_refund_succeeds`

### 6.2 NUT-14: HTLC + SIG_ALL verification

cashu-cf returns "Signature threshold not met. 0 < 1" for all HTLC +
SIG_ALL scenarios. P2PK + SIG_ALL works correctly. CDK passes all HTLC
SIG_ALL scenarios.

**Affected scenarios:** `htlc_sigall_preimage_only_no_pubkeys_succeeds`,
`htlc_sigall_requires_preimage_and_transaction_signature`,
`htlc_sigall_multisig_2of3`

### 6.3 SIG_ALL message format

Nutshell uses a legacy SIG_ALL format (concatenation of input secrets
only). cashu-cf and CDK use the standard format (input secrets + C +
output amounts + B_). The conformance suite auto-detects and adapts.

### 6.4 NUT-11: Duplicate tag handling

| Implementation | Behavior |
|---|---|
| **CDK** | First occurrence wins (duplicate silently ignored) |
| **Nutshell** | First occurrence wins |
| **cashu-cf** | Rejects all duplicate tags |

Spec (NUT-11 L85): "MUST be rejected as unspendable." All three
implementations technically violate the spec, but cashu-cf is closest.

### 6.5 NUT-11: n_sigs exceeding pubkeys

| Implementation | Behavior |
|---|---|
| **CDK** | Not validated upfront (refund path still usable) |
| **Nutshell** | Rejected upfront |
| **cashu-cf** | Rejected upfront (Nutshell-aligned) |

### 6.6 NUT-20: Quote signature format (cashu-cf, FIXED)

cashu-cf used a naive string concatenation instead of the spec-mandated
format with domain separator, length prefixes, and amounts.
**Fixed** in commit `d295576` (2026-07-27).

### 6.7 NUT-05: UUID v7 + method field (cashu-cf, FIXED)

cashu-cf generated random hex quote IDs instead of UUID v7, and omitted
the `method` field in melt responses. **Fixed** in commit `c1cb6a2`.

### 6.8 NUT-12: DLEQ proof support

All three implementations support DLEQ proofs on BlindSignatures. The
conformance suite verifies DLEQ presence, validity, and rejection of
tampered proofs.

---

## 7. Scenario Reference

| Category | Count | NUTs Covered |
|---|---|---|
| NUT-03 Swap Basics | 3 | NUT-03 |
| NUT-04 Mint Quote Basics | 3 | NUT-04 |
| NUT-05 Melt Basics | 2 | NUT-05 |
| NUT-07 Checkstate Basics | 2 | NUT-07 |
| NUT-09 Restore Basics | 1 | NUT-09 |
| NUT-00 Token Format Basics | 2 | NUT-00 |
| NUT-06 Mint Info Basics | 1 | NUT-06 |
| NUT-19 Cache Basics | 1 | NUT-19 |
| NUT-02 Keysets | 6 | NUT-02 |
| NUT-04 Accounting | 5 | NUT-04 |
| NUT-08 Fees | 6 | NUT-08 |
| NUT-11 P2PK SIG_INPUTS | 10 | NUT-11 |
| NUT-11 P2PK SIG_ALL | 10 | NUT-11 |
| NUT-11 Melt | 8 | NUT-11, NUT-05 |
| NUT-12 DLEQ | 6 | NUT-12 |
| NUT-12 HTLC SIG_INPUTS | 8 | NUT-14 |
| NUT-12 HTLC SIG_ALL | 8 | NUT-14 |
| NUT-20 Quote Sig | 4 | NUT-20 |
| NUT-29 Batch | 3 | NUT-29 |
| **Total** | **~100** | |

---

## Appendix: Adding a New Mint to the Suite

1. Add the mint URL to `mints.yaml`:

```yaml
mints:
  - name: my-mint
    url: https://my-mint.example.com
    type: custom
```

2. Run the suite:

```bash
python3 run_matrix.py --mints-file mints.yaml
```

3. Review `reports/matrix.md` for failures. Any FAIL indicates a
   spec compliance issue — compare with the reference reports to
   determine if the issue is mint-specific or affects multiple
   implementations.
