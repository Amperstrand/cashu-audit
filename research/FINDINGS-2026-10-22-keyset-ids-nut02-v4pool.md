# FINDINGS 2026-10-22 — V3 keyset-ID spellings, NUT-02 rotation identity, nuts/tests alignment, V4 CBOR pool

Research sessions 2026-10-21/22 against agenda #43 (items 1–4).
Evidence classes: `live` (local docker arms / LAN rig, FakeWallet
only), `src` (cited source lines), `vec` (crafted vectors +
three-family decoder verdicts, held in `private/v4-pool/`), `spec`
(cashubtc/nuts @ 2026-10-22). Upstream drafts and the registry
additions below are staged in `private/` pending owner approval;
nothing has been filed or posted.

## 1. V3 proof `id` spelling (emission × acceptance × mint-side)

Emission, by wallet family:

| Wallet | V3 `id` spelling | Evidence |
|---|---|---|
| cdk 0.18.x | short 16-hex (`ShortKeysetId`, ver byte + 8-byte prefix) | src nut02.rs:383-408; corpus fixtures |
| Nutshell 0.20.3/0.21.0 | full 66-hex (`Proof.to_dict` verbatim) | src base.py:165 |
| cashu-ts 4.11.0 / 5.0.0-rc.9 | **no V3 emission** — encoder is V4-only | src core.ts:231→239 |

Acceptance of both spellings (V3): all three wallets accept both when
the mint's keysets are known. Unresolvable-short-id failure identities
diverge: cdk-cli intermittent silent deadlock (audit#41; release
builds OOM-killed by earlyoom on this host — debug build works),
Nutshell `KeyError`, cashu-ts `CTSError`. Spec: NUT-00's
short-or-full MUST is written for V4 `i` only; the V3 spelling is
unpinned and official `tests/00-tests.md` covers only a V1-era id.

Mint-side: NUT-00 "the mint is unaware of the s_id" holds — cdk-mintd
(`verification.rs` exact `HashSet<Id>` lookup) and cashu-cf
(`fee-resolver.ts` → registry exact match) both require full ids in
swap/melt inputs. The tollgate corpus manifest's "mints natively
resolve them" is imprecise: in cdk, resolution is wallet-side at token
decode (`token.rs:319/455`).

tmbg full66 verdict (corpus `unknown`): **unfillable on the current
rig** — full-service stage order puts `client-not-registered` before
token processing (mode-dependent order; degraded era was
media-type→body→identity→refusal), and the advertised mint
(10.99.99.2:8383) offers only the V1 keyset `0016f5fb…`, for which the
full66 spelling cannot exist. Rig drift recorded: full-service now
(capture era: degraded), advertised mint moved from 192.168.13.221.

## 2. NUT-02 `final_expiry` / `input_fee_ppk` as keyset identity

Spec: preimage omits `|final_expiry:0` (and fee 0); `final_expiry`
permits the mint to stop honoring and prune nullifiers; no wallet duty
stated.

Live results (docker arms, frozen predictions P1–P4 + wallet legs):

- **P1 (listing)**: neither reference mint flips `active` on expiry —
  both list expired keysets as `active: true` indefinitely (nutshell:
  no expiry evaluation exists, startup rotation task commented out;
  cdk: boot-time warn + continue only).
- **P2 (signing)**: cdk 0.18.2 refuses expired-keyset outputs — HTTP
  400 `12003 "Keyset has expired"`; Nutshell 0.21.0 signs (HTTP 200 +
  signatures). Contrast: inactive keysets refused by both (12002).
- **P2-wallet legs**: Nutshell wallet minted on an expired-active
  keyset (no awareness end-to-end); cdk wallet surfaced the mint's
  `Keyset has expired` and could not mint — the expiry analog of
  cdk#2702's delisted-keyset lockout.
- **Inputs (src)**: cdk `verification.rs:145` refuses expired-keyset
  INPUT redemption too — post-expiry swap-out is refused (stranded
  late swappers); Nutshell redeems forever.
- **P3 (zero-expiry)**: Nutshell mint rotation with `final_expiry=0`
  (management RPC passes it through) advertises a **noncanonical id**
  (`012095f3…` = zero-hashed preimage; canonical derivation of its own
  published keys is `016d8e82…`) and lists `"final_expiry": 0` — both
  contra NUT-02. Verified offline against the official 02-tests
  vectors (canonical derivation reproduced exactly first).
- **P4 (wallet impact)**: cdk wallet keyset refresh verifies every
  listed keyset (`mint_metadata_cache.rs:748 verify_id()`) → the one
  noncanonical keyset fails the ENTIRE mint fetch: `Error: Keyset id
  incorrect`, mint-wide lockout. Control arm: clean mint succeeds
  end-to-end. cdk 0.18.2's `verify_id_for_legacy_nutshell_migration`
  (mint feature) accepts the zero-hashed id for migration imports
  only; wallets still reject.

Fee-change = rotation: cdk-mintd rotates on fee mismatch (builder log
line, source-verified); Nutshell's sanctioned path derives new keys
(new id). **cashu-cf re-prices existing ids via env overrides**
(`resolveFeeForKeysetMeta`, listing + charge both flow through it) —
NUT-02 identity binding broken by design; fix shapes staged in the
report (rotation-on-override preferred + boot-time id/fee assertion).

## 3. Official cashubtc/nuts `tests/` alignment

tests/ grew to 12 files (+README); still **no NUT-07/14/08/03/04/05
files** — our checkstate/HTLC/fee corpora fill real gaps. Official
00-tests V3 vectors use a V1-era id only (both-spellings dimension
untested upstream); 02-tests lacks the `final_expiry=0` case. Three
owner-filed contribution texts staged (`private/UPSTREAM-*.md`, prior
art checked — no covering PRs/issues; #200/#402/#452 are other
surfaces).

## 4. V4 CBOR vector pool — CLOSED at 18 vectors

`private/v4-pool/` (+manifest, sidecars): full-33-byte-`i` twins
(spec-MUST, no vector existed anywhere), memo+DLEQ, both-i-spellings
single token, malformed battery (truncated / text-`i` / text-`c` /
short-`c` / unknown-field / empty-`t` / `cashuC` prefix), non-sat V3
(first anywhere) + V4 pair, direction pins (V4→V3: short ids, unit,
DLEQ; V3→V4: 8-byte `i`, unit, memo), real BIP340 witness (observed
wire shape: `data`=pubkey + separate `nonce`), live C-bound P2PK
locked proof (full lifecycle: locked-send → witnessed swap).

Three-family decoder matrix (cdk-cli 0.18.2 / Nutshell 0.21.0 /
cashu-ts 4.11.0), headline splits:

| Vector | cdk | Nutshell | cashu-ts |
|---|---|---|---|
| text-typed `i` | reject | **coerces to garbage bytes** | reject |
| text `c` | reject | accept | reject |
| 10-byte `c` | **reject (point check at parse)** | accept | accept |
| empty `t` | accept | accept | accept (uniform gap) |
| mixed-unit/mixed-realm | accept | accept | accept (tx-time check only) |
| `cashuC` prefix | Unsupported token | AssertionError | Token version not supported |

**New divergence (spec-adjudicated)**: NUT-28 (28.md:113) mandates
`pe` as a 33-byte CBOR bstr; Nutshell and cashu-ts conform; cdk
0.18.2 `ProofV4.pe` (nut00/mod.rs:457) parses hex-string serde →
**spec-conformant P2BK tokens are undecodable by cdk wallets**
(repro: `v4_v2_pe_kg181.cashu`; same struct uses a bytes (de)serializer
for `c`, fix is local). Version generality (2026-10-23): `ProofV4` is
byte-identical in cdk 0.18.1 and 0.18.2 (serde attrs included) — the
defect ships in both, so the nightly's frozen 0.18.1 reference rejects
the pe vector identically. Rechecked 2026-10-30 against v0.18.3
(sqlite/ffi-only release): `ProofV4` and the `pe` serde unchanged —
defect spans 0.18.1–0.18.3.

## Next actions

1. **Owner review gate (blocking all external motion)**:
   `private/RESEARCH-2026-10-21-agenda.md` + `private/REGISTRY-UPDATE-2026-10-22.md`.
2. Upstream filings (owner files, agents never post):
   cashubtc/cdk issue — `pe` serde vs NUT-28 bstr (vector + verdicts
   ready); cashubtc/nuts tests additions — V3 both-spellings twins,
   02-tests `final_expiry=0` negative vector, 07-test.md checkstate
   proposal (texts staged).
3. OpenTollGate corpus (owner files): pool → corpus v1.2; QA nit
   (`v3_v2_kg181.json` `c_encoding`); full66-blocked verdict row +
   rig-drift facts.
4. cashu-cf lane: fee-override-without-rotation fix (handoff section
   in the report; coordinate with NUT-00 leniency work).
5. Rig follow-ups: full66 tmbg verdict needs a V2-keyset verification
   mint behind the gateway + a registered portal session; rig drift
   (advertised mint V1-only) is itself worth an owner note to the rig
   operators.
6. Candidate probes for the weekly lane (frozen-predictions ready):
   expired-keyset P2/PW pair as scenarios; `pe` decode as a pool
   vector in the nightly decode reference (post 0.18.2 re-pin, which
   remains owner-deliberate per #43).

Evidence index: `private/RESEARCH-2026-10-21-agenda.md` (full session
log incl. all probe transcripts and addenda 1–5),
`private/v4-pool/manifest.json` (per-vector three-family verdicts),
registry rows added in this commit.
