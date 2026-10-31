# UPSTREAM AUDIT 2026-10 — cashu-cf vs cdk/nutshell main

**Window:** 2026-08-01 → 2026-10-30 · **Audited target:** Amperstrand/cashu-cf @ `67285b2` (read-only)
**Baselines:** cdk v0.18.1 (local snapshot) → upstream main `3523c8a9` (fetched 2026-10-28); nutshell tag `0.21.0` (`a974914`, 2026-09-16) → main `ac1c2e0` (2026-10-21)
**Method:** commit-log triage + diff reading on both upstream mains (release-status verified against release-branch trees, not dates — the grafted cdk clone makes dates unreliable); cashu-cf source inventory at `67285b2`. **Wire claims upgraded 2026-10-31:** BOTH sides' unreleased claims are now **wire-verified** — ns-main §2.2–2.5 via `experiments/ns-main-identity-probes/` (7/7) and cdk-main §1.2/§1.3 (+ info advertisement §1.4/§1.7) via `experiments/cdk-main-identity-probes/` (5/5, local mintd build of main @3523c8a9). Two new identity discoveries recorded (ns S5 opaque KeyError; cdk C2b 50000 misdirection). Existing three-way corpus findings (DIVERGENCE-REGISTRY, conformance-v2, must-gap) used as the behavioral baseline for released arms.
**Post-window release check:** cdk **v0.18.3** (2026-10-29) landed after the main-side analysis — sqlite/ffi-only, no mint wire changes; the pe-serde recheck against it is commit `329878e` (affected span now 0.16–0.18.3, fix still main-only). cashu-ts v5.0.0-rc.12 appeared on the upstream-watch lane (out of scope here; watch handles it).

---

## 0. Release anatomy (what "latest" means on each side)

| Repo | Latest release | Main delta | Notes |
|---|---|---|---|
| cdk | **v0.18.3** (2026-10-29, sqlite/ffi-only) | ~50 main-only commits since v0.18.2 | v0.18.0 (cut ~09-01) and v0.18.1 (cut ~09-15) are **inside** the audit window but already our conformance baseline. v0.18.2 = 0.18.1 + backports (`d3a7128d` historical-keyset import, LND/BDK/wallet fixes) — **no mint HTTP wire change** (verified by patch-id/tree checks); v0.18.3 likewise. Everything wire-visible and new = **main-only, de-facto 0.19**. |
| nutshell | **0.21.0** (2026-09-16) | 70 commits, **all unreleased** | No 0.22 cut yet; main contains a security fix (hardcoded auth seed), a keyset-balance enforcement feature, and the multi-mint wallet fix. |
| cashu-cf | main `67285b2` | — | ISSUE-094 NUT-19 cache live fleet-wide (body-inclusive key, `2fe524b`); ISSUE-051 melt saga + Phase-0.5 input verification (`aba6cd6` lineage) deployed; ISSUE-124 wire-verified on deployed testnut (`4a25bb4`). |

---

## 1. CDK changes since 0.18.1 (window 2026-08-01→10-28; 318 commits)

Release status per item: **[0.18.0]** = already in our baseline arms, **[0.18.2]** = released, **[main]** = unreleased 0.19-candidate (none of the [main] items are in v0.18.3).

### 1.1 NUT-28/V4 `pe` bstr fix series [main, 2026-10-28]
`17e0553d` `96535ad6` `5bb4af0e` `97b44f7e` `5714e383` — `ProofV4.pe` now serializes as a **33-byte CBOR bstr** (was hex string in 0.16–0.18); decoder accepts legacy hex text (`BytesOrHex` → `PeVisitor` on CBOR type), fixes the UTF-8-valid-bstr corruption case, adds JSON `[u8]` round-trip, pins nuts#402 HTLC/P2BK vectors. CHANGELOG `[Unreleased]`: "P2BK V4 tokens now encode `pe` as CBOR bytes. Wallets using CDK 0.16–0.18 must upgrade…". **This resolves our staged finding "cdk 0.18.2 V4 pe serde violates NUT-28's bstr mandate" (staged 2026-10-22) — fixed upstream pre-filing. v0.18.3 does not carry the fix; registry row updated (affected span 0.16–0.18.3).**

### 1.2 HTLC signature-only refund witnesses [main] — **WIRE-VERIFIED 2026-10-31** (`experiments/cdk-main-identity-probes/` C2: 200 ACCEPT sig-only refund witness after locktime; C2b future-locktime control 400)
`cd8c84d9` — `verify_htlc` now converts a `P2PKWitness` with `refund_path` present into an HTLC witness with empty preimage, falling through to the refund path (locktime + refund-key sigs). Before: `IncorrectSecretKind` → mint HTTP **20008**. **This is cdk#2252 item 6 fixed** (registry: item was UNDECIDED; nutshell accepted, cdk rejected, deployed wallets emit `null`/omitted preimage → could not spend HTLC refunds on cdk). Wallet-side emission fix not yet confirmed on cdk — the *verification* gate is gone. Not in v0.18.3. **Identity discovery (C2b): blocked refund path (future locktime) answers `{"code":50000,"detail":"Secret is not a HTLC secret"}` — misleading detail (secret is well-formed HTLC), generic code; hygiene note, owner-gated.**

### 1.3 Expired-keyset handling [mixed]
- Core unchanged in the whole window: signing on expired keyset → **12003** (`verify_outputs_keyset`, `crates/cdk/src/mint/verification.rs:100-105`); redemption of expired-keyset inputs → **12003** (`verification.rs:145-150`). Identical in 0.18.1/0.18.2/0.18.3/main. Our registry finding ("cdk strands late swappers post-expiry") stands.
- **[main]** `8e0f6365` + `12647e52` — **/v1/restore** now replays stored blind signatures regardless of keyset expiry and even with an empty keyset cache (before: silently dropped expired-keyset sigs). Restore = pure DB replay keyed by blinded message.
- **[main]** `0b225c9b` — `POST /v1/restore` with `outputs: []` → `200 {"outputs":[],"signatures":[]}`. **WIRE-VERIFIED 2026-10-31** (C1).
- **[0.18.2]** `d3a7128d` — operator-side: config import gains historical-Nutshell-keyset verification (noncanonical IDs with explicit-zero expiry importable preserving original IDs). Directly relevant to our `final_expiry=0` nutshell finding — cdk mintd can now absorb those keysets; cdk *wallets* still reject the IDs.

### 1.4 NUT-29 / request limits [0.18.0/0.18.1 — in baseline]
- `2a1167a3`: `/v1/info` gains top-level **`max_array_length`** = `min(max_inputs, max_outputs)` = builder default 1000 (one global figure, not per-endpoint).
- `eafc298c`: batch routes validate **before any DB work**: empty → UnknownQuote; `len > max_batch_size` → **11017** `{actual, max}`; repeated quote IDs → **11016**. mintd default batch = **100** while info advertises max_array_length = **1000** → our staged "advertised 1000 / enforced 100" finding is structural and **still live on main — wire-captured 2026-10-31 (C3): `nut29.max_batch_size:100` alongside `max_array_length:1000` on a live main mintd**.
- `f6f80aa8`: custom melt `request`/`extra` ≤ 1024 bytes; custom method name ≤ 53; NUT-17 kind ≤ 64. Violation → generic 50000 (no dedicated code).
- `d8528fa4`: WS `subId` ≤ 128, kind ≤ 64, filter ≤ 256 at deserialization.

### 1.5 Melt saga state machine [mostly 0.18.0/0.18.1; two main-only]
- Cross-replica coordination (`eb34a228` + PG quote-coordination `7c00aab3`/`80b84644`): DB quote lock held across dispatch/reconciliation/finalization/compensation; concurrent duplicate finalization covered.
- Ambiguity semantics (`46e009eb`): raw payment errors indeterminate; only explicit terminal backend states count; fail closed.
- Compensation (`6a067110`/`971fa867`): `Unpaid`/`Failed` are authoritative-terminal → durable `PaymentFailed` row **before** proofs unreserved; `Pending`/`Unknown` never release proofs.
- Recovery (`076a9ff0`): restart trusts fresh terminal states; stale rollback rejected once finalization started. `0b07cc5f` [0.18.1]: backend status checks bounded 10s.
- **[main]** `71aceca7` — **Paid-melt gating on change finalization**: `load_melt_quote_for_response` answers **`Pending`** on status/subscription/waiter while state=Paid but the melt-request row (change) still exists; finalization deletes it atomically with change persistence (incl. zero-change). A wallet can no longer observe Paid before change is durably committed.
- **[main]** `4fe6f613`: indexed melt-saga lookup by quote id (was a scan per status check).
- Lock discipline `c21c1c43` [0.18.0]; throttle `d5855ad8`; structured lifecycle logs `1fed279e`/`06dda518`/`7ed3816e`/`584a85b9` [0.18.1].

### 1.6 Duplicate-Y / checkstate / mint idempotency
- `70654052` [0.18.0]: `/v1/checkstate` with duplicate Ys in the array — all duplicates now return the same true state (was: later duplicates looked unspent).
- Re-sent mint/swap with identical outputs: **unchanged** in the window (static read says 11003 path exists; our 2026-10-24 wire capture on cdk 0.18.1 showed 200+byte-identical replay — empirical row stands; no new upstream movement).

### 1.7 NUT-19
- Mint side [0.18.0]: mintd advertises `nuts.nut19 = {ttl, cached_endpoints}` for POST /v1/swap, /v1/mint/{m}, /v1/melt/{m}; default TTL/TTI **60s**; in-memory or Redis backend. **WIRE-CAPTURED on main 2026-10-31 (C3): ttl 60 + 7 cached_endpoints (swap, bolt11/bolt12/onchain mint+melt).**
- **Cache policy (decisive for cashu-cf):** the `post_cache_wrapper!` macro (`crates/cdk-axum/src/router_handlers.rs:30-58`) caches **only successful typed responses** — `$handler(...).await?` returns errors before `cache.set`. Errors are never stored, never replayed.
- Key = serialized request payload (`calculate_key` over typed JSON) ≡ cashu-cf's body-inclusive canonical JSON (post-`2fe524b`). **No `GET /v1/cache/{key}` route on cdk** (same as nutshell and cashu-cf — NUT-19 is server-transparent everywhere; not a cashu-cf gap).
- `80906bb7` [0.18.0] wallet-side: replay only after ambiguous Connection/Timeout failures, only on advertised routes, TTL=deadline, bounded backoff. `1842da08` is build caching only; `64b0db09` is GCRA pacing — not NUT-19.

### 1.8 Spending-condition hardening
- `dceb8aab` [0.18.0, authoring side]: duplicate pubkeys (x-only view) rejected at condition-build time (incl. P2BK data key; refund keys separate set).
- **[main]** `c6b5ce96` (test): pins shared P2BK slot ceiling = `MAX_LOCKING_SLOTS` = 11; plain NUT-11/14 locks uncapped.
- `1ef10319` [0.18.0, wallet]: `p2pk_e` stripped from proofs after NUT-28 signing. `220fe7a4`: FFI-only.

### 1.9 Validation / DoS / robustness
- `9ed72a9b` [0.18.0] **mint-side blind-auth double-spend race fixed**: auth-proof insert now `ON CONFLICT DO NOTHING` directly as Spent; loser → **31002** (was: duplicate error swallowed → both requests authenticated).
- `b24558e5`/`54e941c8` [0.18.0]: AmountOverflow instead of panic; checked math. **[main]** `4089d6cf`: DB column range checks (PG INT2/INT4) — refuse instead of truncate. **[main]** `d1db1d4b`/`fe766120`: wallet HTTP response bodies bounded. **[main]** `b76031fa`/`2b2ea99f`: sqlite pool fails on lost in-memory DB instead of silently recreating; poisoned txns discarded.
- `c4aed1e5`/`dab79561` [0.18.0]: log/terminal escaping of untrusted strings. `b033eb34`/`9c8f5d4d` [0.18.1]: PG TLS fail-closed.

### 1.10 Quote/info shapes [all 0.18.0 — in baseline; recap for the matrix]
- `method` field required in all mint/melt quote responses (missing → defaulted for compat). NUT-25 bolt12 `options.description`. NUT-23: bolt11 `description` nested under `options` in /v1/info (legacy top-level still decoded). Bolt12 melt quotes distinct struct.
- **[main]** `75471675`: bolt12 mint offers carry `absolute_expiry = now+mint_ttl` (wallets stop paying dead quotes). **[main]** `4165a487`: NUT-18 `creqA` optional fields omitted instead of CBOR null (nulls still decode). **[main]** `42ef19e2`: WS JSON-RPC — error `id` may be `null`; `jsonrpc:"2.0"` validated both directions. **[main]** NUT-17 subscription **backfill** trio (`c6e76df5`/`30c113ea`/`1c6f683a`): reconnecting subscribers get snapshots incl. persisted melt change signatures.
- **[main despite Sept date]** `752723a6`: legacy `CdkMint` gRPC removed (proto 2.0.0); `bb6c3d11` retires protocol-version header. Not in 0.18.1/0.18.2 trees.

---

## 2. Nutshell changes since 0.21.0 (70 commits, all main-only / unreleased)

**Wire-verified 2026-10-31 against a local main @ ac1c2e0 FakeWallet mint — `experiments/ns-main-identity-probes/` (7/7 exact-identity PASS). Rows 2.2–2.5 and the new 2.10 carry observed identities.**

### 2.1 Multi-mint V3 token decoding — `e5500d9` (+`ad607fa`)
Confirms our staged finding's dead-code diagnosis, but the fix **bypasses** rather than repairs it: `from_tokenv3` still raises plain `Exception` (base.py:1427) and the `except ValueError` fallback stays dead; instead `deserialize_token_from_string` short-circuits — `len(mints) > 1 → return tokenV3Obj` (helpers.py:109-110) — and `redeem_universal` dispatches per-mint sequential redemption (`Wallet.with_db` per entry). **Multi-mint V3 is now receivable by nutshell-wallet main**; cdk wallet still `Unsupported token`; cashu-ts intentionally rejects. Our staged nutshell issue draft (`private/UPSTREAM-nutshell-multimint-fallback.md`) is **moot as written** — re-scope to "fixed on main, unreleased; 0.21.0-and-older strand senders" or drop. Registry updated.

### 2.2 Keyset redemption balances — `e107c6d` (PR #1176)
New mint-side invariant: checked debit `SET balance = balance - :amount WHERE balance >= :amount` at proof-reservation and at invalidate/commit (one transaction); **HTTP 400 `code 11000` "keyset balance is insufficient for redemption"** when a keyset's outstanding ecash would exceed ever-issued. Defense-in-depth against DB inconsistency / unissued-proof redemption. New error identity for the matrix; neither cdk nor cashu-cf has this (cashu-cf's equivalent guarantee = Phase-0.5 per-input `C == k·H(secret)` crypto verification, which blocks fabricated proofs outright).

### 2.3 Unparsable vs absent witness — `350fc05`/`faf79ca`/`2d9e688`
0.21.0 swallowed witness parse failures → identical to absent (11000 "no signatures in proof."). Main: parse inside the verify path; unparsable JSON or wrong shape → **11000 "witness could not be parsed."**; HTLC valid-JSON-no-preimage → "no HTLC preimage provided"; absent unchanged ("no signatures in proof.", pinned). Escape hatch preserved: expired lock + 0-sig refund spends regardless of garbage witness.

### 2.4 Protocol string limits / request-layer secret validation — `c7d9ace`/`21259e4`/`94c547d`/`e59e022`
Pydantic constraints at request layer: proof **secrets ≤ 1024** (`mint_max_secret_length`, checked *before* `hash_to_curve` — DoS hardening), keyset ids ≤ 66, `B_`/`C_`/`C` ≤ 66, DLEQ `e`/`s` ≤ 64, mint-batch sigs ≤ 130, restore lists capped. Errors are **FastAPI 422** (`string_too_long`, loc-indexed) — framework-layer, **bypassing the spec error registry** (our standing finding; now formally pinned by their own tests). Mitigation: 422 handler strips `input` values (no payload echo). Witness length and memo limits unchanged (ledger-layer 11000).

### 2.5 NUT-04 mint-quote `pubkey` — `e688266` → `751c2c5`
0.21.0 wire: `"pubkey": ""` for unlocked quotes. Main: `""` → `null` → **key omitted entirely** (`response_model_exclude_none=True` on quote create/status/check + WS/event serialization); present with 66-hex for NUT-20 locked quotes.

### 2.6 Auth middleware path matching — `7a5a7ce` (PR #1215) — **security fix**
NUT-13 `Clear/BlindAuthMiddleware` matched `request.url.path`, which Starlette rebuilds from the **Host header** → `Host: testserver?x` (etc.) polluted the path, failed the protected-path match, and **skipped auth entirely** (host-header-controlled auth bypass). Fixed: match raw ASGI `scope["path"]`. cashu-cf relevance: **structurally immune** — see §3.17 and the registry's committed probe note (`9b4361e`, "Host-header auth-bypass probe — Workers immune").

### 2.7 P2BK slot bounds — `f2f2b43`
Slot index outside `0..0xFF` now `ValueError` (was: `bytes([slot & 0xFF])` silent alias — 256≡0). Mint surfaces via generic 400/code-0.

### 2.8 Seed / secret-at-rest wave — `33128c9` `c66faa2` `e062b16` `9bd6078` `9f3704f`
- **0.21.0 auth ledger used hardcoded seed `"auth seed here"`** (startup.py:90) — every auth-enabled nutshell mint shared one public auth keyset. Main: `MINT_AUTH_PRIVATE_KEY` setting, fallback `sha256("auth:"+MINT_PRIVATE_KEY)`. No migration (old blind-auth tokens die on upgrade).
- Encryption-enabled mints previously wrote **plaintext seeds** for new keysets (`c66faa2` fixes; `9bd6078` fixes `encrypt.py migrate` which had *never worked* since 0.16 — positional-vs-named params; `e062b16` blanks `seed` where ciphertext exists). Placeholder-seed refusal at startup (`9f3704f`).

### 2.9 Misc (wire-relevant)
- `aa6bec9`: backend status exception at startup → clean SystemExit instead of raw traceback. `f96b919`: CashuError responses logged info not error.
- `3e2b7d1` (wallet): melt-quote response `method` now Optional (older mints without it parse again — note for our own response shapes: omission tolerated by ns-main wallet).
- `1c682a8` (wallet/core): `supports_nut()` requires literal `true` — truthy strings/ints now False when reading third-party /v1/info.
- LND fee probing (`129a3c1` cluster): `fee_reserve = max(configured, probed routing fee)` for non-MPP — NUT-05 fee_reserve values may differ from 0.21.0 on LND-backed mints.

### 2.10 NEW (discovered on the wire, 2026-31-10 probes) — opaque KeyError on non-denomination swap outputs
Single swap output whose amount is outside the keyset's power-of-2 list (e.g. one 63-sat output after a 1-sat keyset fee on a 64-sat input) → `KeyError(amount)` from `keyset.private_keys[output.amount]` (ledger.py `_sign_blinded_messages`) leaks as **400 `{"detail":"63","code":0}`** — opaque identity, F5-class. Mint stays up, txn rolls back; wallets never trigger it (they split to denominations) — same invisibility class as the registry's F5 `detail:"3"`. cashu-cf unaffected (per-amount keys on demand). Side observation: dict-form `{"kind":"P2PK",...}` secrets are NOT parsed as conditioned secrets — spent as plain (fail-open parse, cdk-parity). Evidence: `experiments/ns-main-identity-probes/FINDINGS.md` S5.

---

## 3. Cross-reference: cashu-cf @ 67285b2 vs upstream delta

Legend: ✅ have / aligned · 🔶 diverges (document or decide) · ❌ gap · ➖ N/A for a bolt11 mint on Workers.

| # | Topic | cdk main | nutshell main | cashu-cf now | Verdict |
|---|---|---|---|---|---|
| 3.1 | **V4/P2BK/NUT-28 (`pe` bstr)** | full, fixed both directions | full (vectors pinned) | **absent** (0 hits) | ❌ gap, **watch-not-build** — V4 still vector-stage upstream; roadmap item |
| 3.2 | **HTLC sig-only refund witnesses** | accepted (20008 gate removed) | accepted (long-standing) | accepted (`spending-conditions.ts:647-658`) | ✅ cashu-cf was already ecosystem-majority; cdk converges to us. #2252 item 6 resolved |
| 3.3 | **Expired keysets — signing/redemption** | refuse 12003 both ways | sign+redeem forever | never refuses (12002/12003 classes defined, **never thrown**); swap-input expiry opt-in (`KEYSET_EXPIRY_ENABLED`, default off, 30d grace); melt never checks | 🔶 known matrix fork (registry row exists); cdk-main unchanged → no action |
| 3.4 | **Restore: expired-keyset sigs; empty outputs** | replay regardless; `[]`→200 empty | (0.21.0) drops nothing / errors on empty | silent-drop unmatched; **`[]`→400 "at least one output is required"** | 🔶 new minor fork when cdk 0.19 lands (200-empty vs 400). Cheap to mirror; low stakes → cashu-cf#102 |
| 3.5 | **max_array_length honesty** | advertises 1000, enforces 100 batch (11017) | 1000-flat (framework 422s beyond) | advertises **50**; actual: batch 50 (11017/11016 ✅), swap inputs cap 100, mint outputs 100, **melt inputs/swap outputs uncapped**, batch-fetch helpers uncapped | 🔶 inverse of cdk's problem (under-advertising swap cap 100). Real issue = **missing caps on melt/swap-outputs + unbounded strings** → cashu-cf#100 |
| 3.6 | **Melt: Paid-before-change ordering** | [main] answers `Pending` until change durably committed | settled atomically w/ change | deliberate: 200 `state:PAID, change:[]` on finalize-failure + alarm recovery retry (`saga.ts:156-177`) | 🔶 **designed divergence** vs cdk-main gating. Our retry path re-signs change (idempotent by preimage); document + consider gating → cashu-cf#102 |
| 3.7 | **Melt ambiguity/compensation** | fail-closed; only terminal states release proofs | atomic invalidate+debit | timeout→PENDING, escalation after 24h; FAILED→compensate | ✅ aligned in spirit (PENDING-never-releases); registry's concurrent double-melt P0 was gonuts, not cf |
| 3.8 | **NUT-19: advertisement** | `{ttl:60s, cached_endpoints:[swap,mint,melt]}` | none (no NUT-19) | `{ttl:300s, cached_endpoints:[mint,swap,melt+aliases]}` when enabled, key omitted when off (ISSUE-094 step 4 live) | ✅ cashu-cf now the most-declaring arm (registry's "`{}` params" note superseded) |
| 3.9 | **NUT-19: cache policy** | **success-only** (typed; errors never stored) | ➖ | **caches 4xx/5xx too** (no status filter; only infinite-TTL skips store) (`nut19-cache.ts:103-106`, `mint-do.ts:509-536`) | 🔶 **action**: mirror success-only. Same threat class as the 2026-10-28 incident (a transient 400/500 replays until TTL for identical body) → **cashu-cf#99 (P1)** |
| 3.10 | **checkstate duplicate Ys** | all copies get true state (0.18.0 fix) | n/a (no checkstate dedup issue known) | **duplicate Ys rejected** (`checkstate.ts:262`) | 🔶 third identity; cf is strictest (reject vs cdk dedupe). Fine; matrix row → cashu-cf#102 |
| 3.11 | **Secret/witness length bounds (DoS)** | custom fields ≤1024; WS strings ≤64-256 | secrets ≤1024 pre-hash_to_curve (422); B_/C ≤66 | **none on swap/melt hot paths** (1000-char cap exists but only on an unrouted coordinator path) | ❌ **P1 adopt** → **cashu-cf#100** — both refs hardened Aug–Oct; cf's `hash_to_curve` runs on arbitrary-length attacker strings |
| 3.12 | **NUT-04 quote `pubkey` when unlocked** | omitted (Option) | omitted (main; was `""` on 0.21.0) | omitted (spread-conditional, `api/mint.ts:434-446`) | ✅ converged on omit; ns-0.21.0 was the outlier |
| 3.13 | **Quote `method` field** | required (0.18.0) | required (ns wallet now *also* tolerates missing) | always present (mint+melt) | ✅ |
| 3.14 | **Keyset redemption balance invariant** | none | 11000 "keyset balance is insufficient" | none; Phase-0.5 crypto verify blocks fabricated C → equivalent primary guarantee | 🔶 document; optional defense-in-depth |
| 3.15 | **Witness identity: absent vs unparsable** | distinct errors (IncorrectWitnessKind etc. → 20008 family) | distinct messages, same 11000 | same **403/30006** both, different details ("No witness in proof" vs "Invalid P2PK/HTLC witness format") | 🔶 matrix gains a fourth identity set once ns releases; cf's 403 (vs refs' 400) is the standing outlier |
| 3.16 | **Duplicate P2PK pubkeys** | rejected at build (wallet-side) | rejected (`pubkeys must be unique`, 0.21.0) | rejected (`assertUniquePubkeys`, x-only) | ✅ |
| 3.17 | **NUT-13/22 auth** | implemented; blind-auth race fixed (31002); auth paths | implemented; **hardcoded-seed security fix**; scope-path fix | **not implemented** (dead error classes 30001-31004 only; `features.ts:86`) — but the ns Host-header class does **not** transfer: cf admin auth is handler-embedded (`anyEnvAdminCheck` per route), path derivation single-source (`new URL(request.url)`, index.ts:241-242); no middleware/path mismatch (static-verified 2026-10-30; cf. registry `9b4361e` probe) | ❌ standing gap (roadmap); when built: mind cdk's race fix + ns's Host-header lesson |
| 3.18 | **NUT-17 WS** | expanding (backfill w/ change sigs, null-id errors, bounded strings) | implemented | disabled (`410 websockets_disabled`, stub DOs) | ❌ known gap, widening; no near-term action |
| 3.19 | **Secrets at rest** | SQLCipher/encrypted backends | encrypted seeds (plaintext-write bug fixed) | nothing persisted to encrypt (HMAC-JIT from env secret; BIP32-CDK optional; metadata-only registry) — but **admin endpoints return raw master key** (`admin-routes.ts:191-208`, `:2491`) | ✅ storage model sound ➖ encryption wave N/A; admin exposure is an owner-seam decision to re-review |
| 3.20 | **Amount overflow / checked math** | AmountOverflow; checked math; DB range checks | pydantic bounds | `MAX_OPERATION_AMOUNT` on melt setup; no general overflow audit found | 🔶 P2 hardening sweep (amounts, `too_many_outputs` lacking code, batch-fetch loops uncapped) → cashu-cf#100/#101 |
| 3.21 | **Error-code hygiene** | spec table enforced | spec table (+documented 422 leak) | **"11003" reused for AMOUNT_TOO_LARGE** (spec: outputs-already-signed; cf uses 10002 for that); saga-internal 10002-10012 non-spec; several 2xxxx collisions | 🔶 P2 cleanup → **cashu-cf#101** — wallets keying on `code` will misread cf |
| 3.22 | **SIG_ALL message leniency** | single canonical message | single (+ legacy pre-0.20.3) | accepts **10 encodings / 3 sort orders** (deliberate compat) | 🔶 known, deliberate; registry row stands; revisit if upstream pins vectors |
| 3.23 | **Mint-retry idempotency (NUT-04 re-send)** | unchanged (replay observed on 0.18.1 wire) | unchanged (11003 reject) | 200 byte-identical replay (registry: cf+cdk majority vs ns) | ✅ no upstream movement; registry row unchanged |
| 3.24 | **HTLC hash-case / delay** | digest-compare (case-insensitive) | digest-compare | honors non-lowercase data via **hardcoded 60s busy-wait "delay mode"** (`spending-conditions.ts:20-22,617-631`) | 🔶 cf-only busy-wait is a self-DoS footgun → cashu-cf#102 (P2: config-gate or bound it) |
| 3.25 | **Bolt12/NUT-25/NUT-18 creqA** | expanding | partial | ➖ (bolt11 + mock backend) | ➖ watch |

---

## 4. Prioritized action items for cashu-cf

**Filed 2026-10-30 as cashu-cf issues #99–#103** (links below). No P0s: no upstream change in the window creates an immediate fund-safety hole in cashu-cf (the two upstream security fixes — ns hardcoded auth seed, ns Host-header auth bypass — live in code paths cashu-cf doesn't have, and cf is structurally immune to the Host-header class).

### P1 — adopt (hardening with upstream precedent)
1. **NUT-19: stop caching non-2xx responses** → **cashu-cf#99** (`src/do/nut19-cache.ts:103-106`, `src/do/mint-do.ts:509-536`). cdk's `post_cache_wrapper!` stores only successful typed responses; cf currently replays transient 4xx/5xx for identical bodies until TTL. Same class as the 2026-10-28 fabricated-melt incident. Minimal change: status filter at store time + regression lock.
2. **Bound request strings + array sizes on hot paths** → **cashu-cf#100**, mirroring the Aug–Oct upstream wave: secret ≤ 1024 *before* `hash_to_curve`, witness JSON ≤ 1024, melt inputs/outputs + swap outputs count caps, cap the uncapped `/v1/mint/quotes` / `/v1/melt/quotes` batch-fetch loops. Prefer spec-coded 11014/11015 over codeless `too_many_outputs`.

### P2 — decide/diverge-or-mirror
3. **Melt Paid-before-change (3.6)** → bundled in **cashu-cf#102**: keep+document or mirror cdk-main's `71aceca7` gate.
4. **Empty-restore semantics (3.4)** → cashu-cf#102: switch `[]`→400 to cdk-main's 200-empty, or keep and matrix it.
5. **Error-code hygiene (3.21)** → **cashu-cf#101**: 11003 reuse, 2xxxx collisions, never-emitted 11014/11015/12002/12003/30007/30008.
6. **HTLC delay-mode busy-wait (3.24)** → cashu-cf#102: 60s synchronous busy-wait hardcoded on — config-gate, bound, or drop.
7. **checkstate duplicate-Y (3.10)** → cashu-cf#102 (document only; strictest-is-fine).
8. **Keyset-balance invariant (3.14)**: optional defense-in-depth mirroring ns-main `e107c6d`; primary guarantee already via Phase-0.5 crypto verify. Decision memo filed 2026-10-30 as **cashu-cf#105** (document-first recommendation; drift-freeze risk called out).

### P3 — gaps to schedule (no upstream pressure)
9. **NUT-13/21/22 auth** (3.17): both references investing. When built: cdk's atomic blind-auth spend (31002), ns's scope-path lesson, per-mint auth seed derivation.
10. **NUT-17 WS** (3.18): gap widening on cdk-main (backfill-with-change-sigs). Revisit scope.
11. **V4/P2BK/NUT-28** (3.1): zero support; wait for spec vectors + ≥1 wallet shipping. Track nuts#402.
12. **Dead code cleanup** → **cashu-cf#103**: `Nut19Metrics` (never wired), swap journal dead write, `LedgerLimit`/`LedgerCache`/`LedgerConditions`, BIP32 stub, `MELT_SAGA_V2` guard; plus NUT-15 advertise-or-reject alignment.

### Watch list (triggers for the next audit cycle)
- **cdk 0.19 cut** (0.18.3 is sqlite/ffi-only — no arms change needed) → add 0.19 arm to conformance-v2; re-run must-gap + spend-matrix against: sig-only HTLC (cf already OK — expect green), Paid-gated melt, restore-empty-200, null-id WS errors, bstr-`pe` V4 (wallet-side; n/a for cf mint).
- **nutshell 0.22 cut** → add arm; new identities to pin: "witness could not be parsed." (11000), keyset-balance 11000, secret>1024 422 shape, quote-pubkey omission, multi-mint V3 per-mint redemption (wallet side — affects our token corpus, `lifecycle/v3_v2_*`).
- **cdk#2252** — item 6 now fixed on main; our posted comment stays accurate; expect maintainer close → watch script flags.
- **cashu-ts v5 line** (rc.12 on the upstream-watch lane) — when stable, the ISSUE-110 canary lane handles it; this audit's findings don't change.
- **nuts repo** — 19.md params wording and 29.md per-endpoint caps remain open structural questions our staged rows track.

---

## 5. Registry implications (re-applied to research/DIVERGENCE-REGISTRY.md after the 2026-10-29/30 repo pull wiped uncommitted edits — see close-out)

1. **pe-serde row (staged 2026-10-22):** fixed upstream on main 2026-10-28 (`17e0553d`+), post-0.18.2/0.18.3, unreleased. Filing dropped; row annotated with the 0.16–0.18.3 affected span.
2. **cdk#2252 row, item 6:** fixed on cdk main (`cd8c84d9`, not in v0.18.3). Row annotated (venue still open for items 5+8).
3. **Multi-mint V3 row (staged 2026-10-23):** nutshell main `e5500d9` makes multi-mint V3 receivable — staged ns issue draft moot as written; row annotated with re-scope options.
4. **Mint-retry fork row's NUT-19 note** ("declaring arms advertise `{}` params"): superseded for cf — ISSUE-094 step 4 deployed; cf advertises `{ttl:300, cached_endpoints:[…]}`; new cf-vs-cdk success-only policy fork noted, pointing at cashu-cf#99.

## 6. Follow-ups queued for existing lanes

- When cdk 0.19 / ns 0.22 release: extend `conformance/` docker arms; add error-identity assertions for the new identities above (witness-parsed 11000, keyset-balance 11000, 422 secret-length, restore-empty 200, quote-pubkey omission on ns). **ns-main identities already pinned as frozen predictions + wire evidence — the released-arm assertions can lift `experiments/ns-main-identity-probes/` verbatim (S1b/S2/S3/S4 rows; add S5 to the matrix as an ns-only opaque identity). cdk-main likewise: `experiments/cdk-main-identity-probes/` C1/C2 verbatim (+C2b 50000 identity + C3 advertisement facts — also watch whether the 0.19 release bumps the workspace version string, currently still 0.18.0 on main).**
- cashu-shadow corpus: no changes required this cycle (all deltas unreleased); re-baseline after either release lands.
- Host-header admin-path probe: **resolved, no lane needed** — static verification (this audit, §3.17) + the committed registry probe (`9b4361e`) both find Workers/cf immune to the ns `7a5a7ce` class.

---

## Close-out (supervisor tick, 2026-10-30 21:25 window)

**Lane status: DONE — parked.**

- Deliverable: this report (re-written 2026-10-30 after loss, see below).
- Registry: 4 annotations re-applied (§5).
- Work filed: cashu-cf **#99** (P1 NUT-19 error caching), **#100** (P1 request bounds), **#101** (P2 error-code hygiene), **#102** (P2 decision bundle: melt ordering / restore-empty / delay-mode / checkstate dup-Y), **#103** (P3 dead-code + NUT-15 alignment).
- **Incident note (handoff):** the first report draft + initial registry annotations (written ~2026-10-28/29 session) were **lost uncommitted** when the repo was pulled forward to `329878e` during the unattended window (working tree reset + clean; no stash; `experiments/keyset-rotation-rung/` appeared from the other lane — untouched). Recovered from session context; the rewrite incorporates the interim upstream events (cdk v0.18.3, `329878e` pe recheck, `9b4361e` Host-header probe). GitHub issues #99–#103 were server-side and unaffected. **Lesson for the next pass: commit or stash audit artifacts before yielding the session.**
- Blocked-on-owner items (recorded, not blocking): decision memo for §4.8 (keyset-balance invariant); re-scope/drop decision for `private/UPSTREAM-nutshell-multimint-fallback.md`; the pe/`#2252` registry rows now say "fixed on main" — no owner action needed unless the owner wants the drafts deleted.

*Evidence: cdk FETCH_HEAD=3523c8a9 (rechecked vs v0.18.3 via repo commit 329878e), ns main=ac1c2e0, cashu-cf=67285b2. Source-verified citations inline; no cashu-cf files were modified.*
