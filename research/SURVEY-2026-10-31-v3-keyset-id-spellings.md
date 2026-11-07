# SURVEY 2026-10-31 — V3 proof keyset-id spelling: emission × acceptance × mint-side (consolidated, #43 item 1)

Consolidates the 2026-10-21..23 arc (FINDINGS-2026-10-22 §1,
FINDINGS-2026-10-23) with the legs closed tonight (2026-11-01
window D): nutshell mint-side (live), cashu-cf (src), cdk 0.18.3 +
main region rechecks (src diff), NUT-02 upstream drift check
(negative). Evidence classes: `live` (local docker nutshell 0.21.0
arm — runners stopped tonight, all gates local), `src` (pinned
tags), `spec` (cashubtc/NUTs @ 1363de4, 2026-10-23). Full probe
record: private mirror `private/nut18-live/` (mint_shortid_probe.py
+ PREDICTIONS-mint-shortid.md + out/mint_shortid_results.json).

## Spec state (frozen)

NUT-00's short-or-full MUST is written for the V4 `i` field only
(00.md:289-300); the V3 JSON `id` spelling is unpinned. Upstream
NUTs main is FROZEN at 1363de4 (2026-10-23) — no 02.md/00.md/tests
drift since the arc's spec pin ("input_fee_list" in circulation is
a garble of `input_fee_ppk`; nothing new to probe).

## Emission (wallet product surfaces; V3 `id` in `cashuA` tokens)

| Family | V3 emission | Evidence |
|---|---|---|
| cdk 0.18.x → 0.18.3 | SHORT 16-hex (`ShortKeysetId` Display = version byte + 7 bytes) | arc src nut02.rs:383-408 + corpus; 0.18.2→0.18.3 nut02.rs/token.rs/mod.rs byte-identical (diff-checked this session); main `Id` serde unchanged |
| nutshell 0.20.3/0.21.0 | FULL 66-hex (`Proof.to_dict` verbatim on the V3 path) | arc src base.py:165 |
| cashu-ts 4.11.0 / rc.9 | none — V4-only encoder | arc src core.ts:231→239 |
| cashu-cf | none — no product wallet-emission surface (mint); tools/token-formats.ts `encodeCashuTokenV3` copies `p.id` VERBATIM (full in practice — ids originate from mint listings) | src this session; consumers = scripts/validation + tests only |

Adjacent (same id-spelling axis, this session's NUT-18 work): the
nutshell NUT-18 payload path emits SHORT ids (V4-token round-trip
`TokenV4Token.proofs` → `to_dict`), while its V3 token path emits
full — one wallet, two surfaces, opposite spellings; cdk's payload
parse rejects short. See FINDINGS-2026-10-31-nut18-payload-spelling.md.

## Acceptance (V3 token in)

All three wallet families accept BOTH spellings when the mint's
keysets are known (arc, live). Unresolvable-short failure
identities diverge (error-identity class): cdk-cli intermittent
silent deadlock (audit#41; retest 0/39+ on 0.18.2 — mitigated, not
explained), nutshell `KeyError`, cashu-ts `CTSError`. cashu-cf
tooling acceptance = cashu-ts semantics verbatim
(`decodeCashuToken` delegates to `getDecodedToken`).

## Mint-side (NEW tonight: nutshell leg; live, frozen predictions PN1–PN5)

Uniform across all three reference mints: **swap/melt inputs must
carry FULL ids; no mint expands short ids** (in cdk, short-id
resolution is wallet-side at token decode, token.rs:319/455).

| Mint | inputs (short) | outputs (short) | Evidence |
|---|---|---|---|
| cdk-mintd | 400 (exact `HashSet<Id>` lookup, verification.rs) | 400 (12002-class family for inactive; unknown-id 4xx) | arc src |
| cashu-cf | 404 (fee-resolver → keyset registry exact match) | n/a (signs on listed keysets) | arc live/src; 404-vs-400 outlier noted in registry |
| nutshell 0.21.0 | **400 `{"detail":"keyset <id> unknown","code":0}`** | **400 `{"detail":"keyset id unknown.","code":11000}`** | live this session, PN1–PN5 below |

### Nutshell mint run (PN1–PN5, predictions frozen before run)

- PN1 CONTROL inputs full66 → **200** (fresh 2+4 sat proofs,
  same-run control).
- PN2 inputs short16 → **400 `keyset 0115f753f486af11 unknown`
  code 0** — the input chain hits an internal `assert proof.id in
  self.keysets` (verification.py:285 via `_verify_proof_bdhke`);
  the assert-derived error is served UNREGISTERED (code 0 — the
  ns framework class from the registry). Prediction was the F5
  opaque-KeyError shape; verdict class matched (non-200, keyset
  echo, code 0), the handler caught it before an F5 crash —
  no triage owed beyond the mechanism, source-pinned.
- PN3 checkstate → **200** both bodies (Y-only wire shape; a
  `proofs` field with short ids is ignored) — the id spelling is
  not consultable on this endpoint (wire-shape fact).
- PN5 outputs short16 (valid full inputs) → **400 `keyset id
  unknown.` code 11000** — the outputs chain raises a registered
  `TransactionError` (verification.py:196; errors.py:11000).
- **Input/output identity asymmetry**: same missing keyset, two
  chains, `code 0` vs `code 11000` — one-line survey pin; wallet
  authors keying on error codes see two identities for one
  condition. Folded into the staged 00-tests/error-registry work.

## cdk version-generality (this session)

- v0.18.2 → v0.18.3: `nut02.rs`, `nut00/token.rs`, `nut00/mod.rs`,
  `wallet/metadata_cache.rs` byte-identical (release was
  sqlite/ffi-only) — every V3-spelling verdict above carries to
  0.18.3 unchanged.
- main (8006cc30): `Id`/serde region unchanged.

## nutshell 0.22.1 checkpoint (2026-11-07, live)

New-release re-verification (frozen PR-A–D, all confirmed; two probe
artifacts triaged, one non-finding): same mnemonic → same boot keyset
id; short-id INPUTS still 400 `keyset <id> unknown` code 0; short-id
OUTPUTS still 400 `keyset id unknown.` code 11000 (earlier
divergent-looking identities were probe artifacts — garbage-C inputs
hit the input pubkey-parse first, and a sig-pairing slip; real-Cs
redo reproduces the 0.21.0 identity exactly); CLI `pay` payload still
carries SHORT 16-hex ids + no dleq on the wire (707B capture). A
rotated keyset's id differing across arms triaged to NON-finding:
`final_expiry` is in the NUT-02 preimage and the two rotations used
different past timestamps (live confirmation the id hashes the
expiry). Past-expiry rotation passthrough persists (listed
`active: true`, fee 0). No payee-side payload consumer added.
Version spans above now read "0.20.3/0.21.0/0.22.1" for every
nutshell row.

## Survey verdicts (what #43 asked, answered)

1. V3 spelling per wallet: cdk short, nutshell full (V3 path) /
  short (V4-derived surfaces), cashu-ts none, cashu-cf no wallet
  surface (tooling verbatim). Done — all four families pinned.
2. Does every wallet accept both spellings in V3? **Yes** (when
  keysets known), with three distinct failure identities when not —
  the divergence is in the FAILURE identity, not acceptance.
3. Mint-side uniformity: all three reference mints require full
  ids; nutshell joins with a code-0/11000 asymmetry (new).
4. Spec gap stands: V3 JSON `id` spelling unpinned upstream (nuts
  frozen since 2026-10-23) — staged 00-tests contribution (D5,
  #62) remains the vehicle; tonight adds no new spec drift.
