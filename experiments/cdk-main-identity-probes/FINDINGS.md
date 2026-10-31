# cdk-main identity probes — FINDINGS (2026-10-31)

Target: **cdk main @ 3523c8a9** (unreleased 0.19-candidate; workspace version
string still 0.18.0 — provenance proven behaviorally: C1 exists only
post-`0b225c9b` Oct 1, and C2 only post-`cd8c84d9` Oct 3). Binary from the
shared ai-legion cargo cache (`/root/.cargo-target`, fingerprints identical to
a fresh export of FETCH_HEAD). mintd + FakeWallet bolt11/onchain, :8739,
sqlite in `/tmp/opencode/cdk-main-rig/data`. Frozen predictions in
PREDICTIONS.md. **Result: 5/5 PASS + one identity discovery (C2b).**

| # | Scenario | Observed (wire) | 0.18.x contrast | Status |
|---|---|---|---|---|
| C0 | control: mint 2-sat + swap | 200 / 200 | same | PASS |
| C1 | POST /v1/restore `{"outputs":[]}` | **200 `{"outputs":[],"signatures":[]}`** | errors (fell through empty-DB path) | PASS |
| C2 | HTLC refund, PAST locktime, sig-ONLY witness (no preimage) | **200 ACCEPT** — `cd8c84d9` fix wire-verified | **20008** `IncorrectSecretKind` (registry #2252 item 6) | PASS |
| C2b | control: FUTURE locktime, same sig-only witness | 400 `{"code":50000,"detail":"Secret is not a HTLC secret"}` | 20008 | PASS (reject) + identity discovery |
| C5 | unlocked bolt11 quote create | 200; `method:"bolt11"`, `state:"UNPAID"`, **no `pubkey` key** | — | PASS |

## Boot-time wire facts (C3, captured before probes)

- **NUT-19:** `{ttl:60, cached_endpoints: [POST /v1/swap, /v1/mint/bolt11,
  /v1/melt/bolt11, /v1/mint/bolt12, /v1/melt/bolt12, /v1/mint/onchain,
  /v1/melt/onchain]}` — 7 endpoints (all enabled methods). cashu-cf advertises
  5 (bolt11 family + aliases) — subset, fine.
- **NUT-29:** `max_batch_size:100` alongside top-level `max_array_length:1000`
  — **the advertised-1000 / enforced-100 fork, now wire-captured on main**
  (strengthens the staged registry row; cashu-cf's 50/50 is the honest shape).

## Identity discovery: C2b error misdirection on the blocked refund path

Future-locktime HTLC refund attempt (sig-only witness) returns
`{"code":50000,"detail":"Secret is not a HTLC secret"}` — the secret IS a
well-formed HTLC secret; the 50000 generic code + misdirected detail fire when
the refund path is blocked by locktime. Post-`cd8c84d9` code path: the
P2PKWitness→empty-preimage conversion puts verification on the refund branch,
and the unexpired-locktime failure surfaces as a wrong-kind error. Hygiene
note only (reject is correct; identity is misleading). Not filed — owner-gated,
adjacent to #2252.

## Probe-bug log (method rule 1)

1. Run 1: C0/C2 → 422 `outputs[0].id: NUT02: ID length invalid, expected 8
   bytes (short/v1) or 33 bytes (v2)` — `keyset_id_ref[0]` never set → outputs
   carried `id:""`; cdk's strict serde rejects at deserialization (ns-main
   tolerated `""` further in — same trap, earlier failure point). Fix: set ref.
2. mintd v0.18 config flow: `-c` startup flag removed — `config init --new-mint
   --file` + `CDK_MINTD_WORK_DIR` + `CDK_MINTD_MNEMONIC` env, then bare
   `cdk-mintd --enable-logging`. Failed boots leave DB state → wipe data dir
   before re-init.

## Rig notes

- keyset: V2 id (`01df…`, 0x01 prefix), amounts power-of-2, input_fee_ppk 0 —
  single-output swaps fine (per-amount keys on demand; **no ns-main S5
  KeyError class on cdk** — tried implicitly via try_swap single output C0).
- RESULTS.json holds raw evidence rows. Boot recipe in PREDICTIONS.md header
  + this file.
