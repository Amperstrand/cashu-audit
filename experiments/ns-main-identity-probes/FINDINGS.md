# ns-main identity probes — FINDINGS (2026-10-31)

Target: **nutshell main @ ac1c2e0** (unreleased, 0.21.0+70), FakeWallet, :8738,
venv `pip install -e` (no patches needed on main — spark wheel resolves,
`limits>=4.8,<5` fixed upstream). Purpose: upgrade UPSTREAM-AUDIT-2026-10.md
§2.2–2.5 source-verified claims to **wire-verified**. Frozen predictions in
PREDICTIONS.md (written pre-run). **Result: 7/7 PASS, exact error-identity.**

| # | Scenario | Observed (wire) | 0.21.0 contrast | Status |
|---|---|---|---|---|
| S0 | control: plain mint + denom-split swap | 200 | same | PASS |
| S1a | P2PK swap (tagged-array secret), witness ABSENT | 400 `{"detail":"no signatures in proof.","code":11000}` | same identity | PASS |
| S1b | P2PK swap, witness `{"foo":"bar"}` | 400 `{"detail":"witness could not be parsed.","code":11000}` | `"no signatures in proof."` (identical to absent — parse errors were swallowed) | PASS — the fork is real on the wire |
| S2 | `keysets.balance` forced to 0 via sqlite, swap VALID proofs | 400 `{"detail":"keyset balance is insufficient for redemption","code":11000}` | no balance enforcement; swap succeeds | PASS |
| S3 | swap input secret = 2000 chars | 422 `{"detail":[{"type":"string_too_long","loc":["body","inputs",0,"secret"],"msg":"String should have at most 1024 characters","ctx":{"max_length":1024}}]}` — **no `code` field** (framework-layer, bypasses spec error registry) | no pydantic bound; hash_to_curve runs | PASS |
| S4 | unlocked NUT-04 bolt11 quote create | 200, **`pubkey` key ABSENT** from response | `"pubkey": ""` present | PASS |
| S5 | single NON-denomination swap output (64-sat input, 1-sat keyset fee → one 63-sat output) | 400 `{"detail":"63","code":0}` | (untested on 0.21.0; same code path likely) | PASS (post-hoc; see below) |

## New finding: S5 — opaque KeyError leak on non-denomination swap outputs

`_sign_blinded_messages` does `keyset.private_keys[output.amount]`
(cashu/mint/ledger.py ~:1767); keysets hold keys only for the power-of-2
denomination list, so a spec-legal single output of e.g. 63 sats raises
`KeyError(63)`, which the db session wrapper re-raises and the app handler
serializes as `{"detail":"63","code":0}`. Trigger is trivial: any raw-protocol
client that nets a fee-adjusted swap into ONE output (wallets split into
denominations, so deployed wallets never hit it — same invisibility class as
the registry's F5 `detail:"3"`). Severity: hygiene/error-identity only — mint
stays up, txn rolls back, no fund impact. Not filed upstream (owner-gated;
minor, adjacent to the #1008/#1009 error-handling venue). cashu-cf signs
arbitrary amounts (HMAC per-amount on demand) → unaffected; cdk derives
per-amount keys too (unaffected — verify on next cdk arm if desired).

## Probe-bug log (method rule 1: surprising FAIL = probe bug until proven)

1. Run 1: S0/S1/S2 → `"keyset id unknown."` — `fresh_output` reads
   `must_gap_vectors.keyset_id_ref[0]`, never set by this driver → outputs had
   `id:""`. Fix: set the ref.
2. Run 2: `"inputs (64) - fees (1) vs outputs (64) are not balanced."` — keyset
   `input_fee_ppk=100` (1-sat fee); my swap lacked the fee retry that
   `try_swap` has. Fix: fee-aware outputs.
3. Run 3: `{"detail":"63","code":0}` on S0/S1 — TWO causes: (a) single 63-sat
   output → S5 (real mint behavior, kept as scenario); (b) S1a/S1b never
   reached the witness check because my secret used the dict form
   `{"kind":"P2PK",...}` — NOT parsed as a conditioned secret (treated as
   plain). Fix: canonical tagged-array form `["P2PK",{"nonce":...,"data":...}]`.
   Side observation: dict-form "P2PK" secrets are accepted as PLAIN spendable
   proofs on ns-main (fail-open parse, same class as cdk's registry note).

## Rig notes

- Boot: see probe.py header; mint at /tmp/opencode/ns-main-mint (data:
  `data/mint/mint.sqlite3` — new path+name on main), log
  /tmp/opencode/ns-main-mint.log. `setsid` required — tool timeouts reap the
  process group otherwise (bit me twice).
- Main's schema seen live: keysets table has `balance`, `encrypted_seed`,
  `seed_encryption_method` (§2.8 wave), `final_expiry`, `input_fee_ppk=100`
  default nonzero (testnut runs ppk=0 — fee semantics differ between rigs).
- RESULTS.json holds the raw evidence rows (status/body/verdict per scenario).
