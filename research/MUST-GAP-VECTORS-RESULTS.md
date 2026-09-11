# MUST-Gap Vector Results: NUT-11 Enforcement Across 9 Mints

*2026-09-12. Driver: `experiments/must-gap-vectors/must_gap_vectors.py`
(raw protocol: controlled secrets at blinding time — the mint cannot see the
secret it signs, so we can mint proofs with malformed P2PK secrets and
observe enforcement at spend time). Raw runs: `artifacts/mgv-run{3,4,5}.txt`.*

## Method

For each mint: mint proofs whose secrets carry a specific malformation
(the blind-signature protocol lets the CLIENT choose the secret), then
attempt a swap and record accept/reject **plus the error identity**.
SANITY (plain secret) and CTRL (valid P2PK + proper witness) passed on
all 9 mints before any vector was counted — the probe itself is proven.

Frozen predictions were written into the driver before the first run
(see docstring). Two probe bugs were caught and fixed by this discipline:
pubkey placed in `nonce` instead of `data` (secrets became
anyone-can-spend; old mints silently ignored the witness), and
comma-joined `pubkeys` tag instead of the spec's multi-element array.

## The matrix

| Mint | V2 invalid sigflag<br>(11.md:104) | V3 SIG_ALL mixed<br>(11.md:130) | V3B valid multi-input<br>SIG_ALL (11.md:141) | V5 uncompressed<br>pubkey (11.md:264) | V6 duplicate keys<br>(11.md:295) |
|---|---|---|---|---|---|
| cdk 0.17.0 | REJECT¹ | REJECT | **ACCEPT ✓** | REJECT¹ | REJECT (explicit) |
| cdk 0.17.6 | REJECT¹ | REJECT | **ACCEPT ✓** | REJECT¹ | REJECT (explicit) |
| cdk 0.18.0 | REJECT¹ | REJECT | **ACCEPT ✓** | REJECT¹ | REJECT (explicit) |
| nutshell 0.20.0 | REJECT | REJECT | REJECT² | **ACCEPT (!)** | REJECT |
| nutshell 0.20.2 | REJECT | REJECT | REJECT² | **ACCEPT (!)** | **ACCEPT (!)** |
| nutshell 0.20.3 | REJECT | REJECT | REJECT³ | **ACCEPT (!)** | **ACCEPT (!)** |
| nutshell 0.19.0 | **ACCEPT (!)** | REJECT | REJECT² | **ACCEPT (!)** | REJECT |
| nutshell 0.18.2 | **ACCEPT (!)** | REJECT | REJECT² | **ACCEPT (!)** | REJECT |
| nutshell 0.16.5 | REJECT | REJECT | REJECT² | **ACCEPT (!)** | REJECT |

¹ cdk rejects via secret-parse failure surfacing as opaque
`{"code":20008,"detail":"Witness is not a p2pk witness"}` — outcome
compliant, reason not attributable by the client.
² old SIG_ALL message format (see below) — signature never verifies.
³ opaque internal error `{"detail":"3","code":0}` — see below.

## Findings

### F1 — V5: uncompressed pubkey accepted by EVERY nutshell tested (0.16.5→0.20.3)

11.md:264 ("Public keys MUST use the compressed Secp256k1 public key
format") is enforced by no nutshell release we tested. The signature
verifies because the key library normalizes 65-byte keys on parse.
cdk rejects (via parse failure). A token locked to an uncompressed key
is spendable on nutshell mints but dead on cdk mints — recoverable by
swapping through a lenient mint, but opaque to the user.

### F2 — V6: duplicate-key enforcement REGRESSED in nutshell 0.20.2/0.20.3

0.16.5–0.20.1 reject duplicates ("pubkeys must be unique."). cdk rejects
with an explicit "Duplicate public key in multisig (same x-coordinate)".
**0.20.2 and 0.20.3 accept a `["pubkeys", pkA, pkA]` pathway with
n_sigs=1** — the MUST at 11.md:295 is violated by the two most recent
nutshell releases. Upstream main has re-added the check (as "pubkeys
must have unique x-coordinates") — the regression window is the
released 0.20.2/0.20.3.

### F3 — V2: invalid sigflag drift across nutshell versions

`"sigflag": "SIG_Voodoo"` is rejected by 0.16.5/0.20.x (explicit enum
validation) **but accepted by 0.18.2 and 0.19.0** (the tag is ignored,
secret behaves as SIG_INPUTS). Cross-version trap: a token minted via a
lenient-era wallet that emits a bad sigflag is spendable on 0.18.2/0.19.0
mints and permanently rejected by 0.20.x mints and wallets.

### F4 — V3: the SIG_ALL consistency MUST (11.md:130) is enforced everywhere

Mixed SIG_ALL/differing inputs rejected on all 9 mints (nutshell: "not
all secrets are equal."; cdk: "Spend conditions are not met"). The one
MUST from our gap list that everyone enforces.

### F5 — V3B: spec-conformant multi-input SIG_ALL works ONLY on cdk

The spec normatively defines the swap SIG_ALL message (11.md:141-149):
`secret₁‖C₁‖…‖secretₙ‖Cₙ‖amount₁‖B₁‖…‖amountₘ‖Bₘ`.

- cdk 0.17.0/0.17.6/0.18.0: **ACCEPT** — conformant.
- nutshell 0.16.5–0.20.2: compute the OLD message `secrets‖B_` (no C,
  no amounts) — the conformant signature never verifies
  ("no valid signature" / "signature threshold not met. 0 < 1").
- nutshell 0.20.3: source computes the NEW (conformant) message and
  single-input SIG_ALL works — but the multi-input path fails with an
  opaque internal error `{"detail":"3"}` (an exception whose str is
  literally "3", escaping through the DB-session retry handler).
  Single-input SIG_ALL (V3D) is accepted; the witness covers both
  message formats, isolating the defect to the multi-input path.

**Net effect: a spec-conformant wallet cannot spend multi-input SIG_ALL
tokens on ANY released nutshell mint — only on cdk.** And a wallet
emitting the old-format message cannot spend on cdk. The message format
changed in the spec without a migration path; nutshell's own releases
straddle the change (0.20.2 old, 0.20.3 new-but-broken for >1 input).

## Scorecard (vs SPECTATE-COVERAGE-REPORT.md gap list)

| Gap | Spec line | cdk | nutshell |
|---|---|---|---|
| unescaped-secret signing | 11.md:58 | wallet-side, untested | wallet-side, untested |
| invalid sigflag rejection | 11.md:104 | enforced (opaque) | 0.18.2/0.19.0 VIOLATE |
| SIG_ALL mixed inputs | 11.md:130 | enforced | enforced |
| SIG_ALL message | 11.md:141 | conformant | 0.16.5–0.20.2 NON-conformant; 0.20.3 conformant but multi-input crashes |
| compressed pubkeys | 11.md:264 | enforced (opaque) | ALL VERSIONS VIOLATE |
| duplicate keys | 11.md:295 | enforced (explicit) | 0.20.2/0.20.3 REGRESSED |

## Upstream draft material (internal per policy)

- nutshell: F2 (0.20.2/0.20.3 regression) + F5 (multi-input SIG_ALL "3"
  crash + old-format releases) — both attachable to released versions
  with reproducible vectors.
- cdk: opaque error identity for secret-parse failures (20008 for a
  malformed secret is misleading).
- spec: SIG_ALL message migration has no compat story (same family as
  the d6 amendment argument).

## Reproduce

```bash
scp experiments/must-gap-vectors/must_gap_vectors.py ai-legion:/tmp/mgv-drv/mgv.py
ssh ai-legion 'docker run --rm --network host -v /tmp/mgv-drv:/drv:ro \
  cashubtc/nutshell:0.20.3 python3 /drv/mgv.py \
  http://127.0.0.1:3500{0,1,2,3,4,5,6,7,8}'
```
