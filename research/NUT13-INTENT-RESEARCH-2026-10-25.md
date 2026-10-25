# NUT-13 intent research — bug or deliberate design difference? (2026-10-25)

Owner question, answered from primary sources: cdk/nutshell/cashu-ts git
history, nuts PR #182/#331/#384 threads, dev-call minutes (Chatham House
— information used, speakers unattributed), cdk v0.18.2 source.

## Verdict

**Neither a shipped divergence nor a deliberate difference. cdk's
shipped deterministic keys are spec-conformant; the 0x01-slot
`SecretKey::derive` is dead, unreferenced legacy code from a pre-spec
prototype.** The original "cross-family P2PK restore broken by
construction" claim (source-read 2026-10-24, registry row 2026-10-24)
is RETRACTED — it generalized from dead code.

## The actual shipped behaviors (v0.18.2 / 0.21.0 / current main)

| Impl | secrets (0x00) | blinding r (0x01) | P2PK keys | quote-lock keys |
|---|---|---|---|---|
| cdk 0.18.2 | HMAC ‖0x00 ✓ | elsewhere (dhke random/BIP32 path, not the 0x01 slot) | **`m/129373'/10'/0'/0'/{n}`** (`wallet/p2pk.rs`, P2PK_PURPOSE=129373, P2PK_ACCOUNT=10) — spec-exact, in active wallet code | `m/129373'/20'/0'/0'/{n}` (`nut20.rs`) |
| cashu-ts | HMAC ‖0x00 ✓ | HMAC ‖0x01 ✓ | m/129373'/10' ✓ | m/129373'/20' (QuoteLock: 20) |
| nutshell 0.21.0 | HMAC ‖0x00 ✓ | HMAC ‖0x01 ✓ | **absent** (no deterministic P2PK) | absent |

cdk and cashu-ts agree on BOTH BIP32 key paths. The only shipped gap is
nutshell's missing deterministic P2PK/quote-lock derivation.

## Timeline (all dates primary-source)

- **2024-10-30** — nuts#182 (davidcaseria, Keyset ID V2) opens; the
  draft 13.md carries the type table `0x00 secrets / 0x01 blinded
  messages` AND the muddled step 3 ("secret = hmac_digest and
  blinding_factor = hmac_digest % N") from early review state (table
  verbatim in the fork's branch; quoted in #182 review 2025-08-18).
- **2025-07-31** — cdk (lollerfirst) invents "new secret derivation"
  with a `Cashu_KDF_HMAC_SHA512` domain string that never existed in
  any spec text; `SecretKey::derive` (P2PK) exists from this commit.
- **2025-08-06** — cdk "update to spec": appends type bytes — `0x00`
  to `Secret::derive`, **`0x01` to `SecretKey::derive`** — while the
  available #182 draft table already labeled 0x01 "blinded messages".
  No commit, comment, or PR states a rationale: the reading is a
  mechanical two-functions/two-bytes mapping against an ambiguous
  step-3. The SHA512 string itself stays (patched to SHA256 only
  2025-08-29, cdk#1013 — leaving the dead test-comment fossil).
- **2025-10-30** — dev call logs "NUT-XX (nuts#292) Deterministic
  NUT-13 Derivation Paths".
- **2026-01-11** — #182 merges; the table becomes spec text.
- **2026-01-19** — nuts#331 (lescuer97, BIP32 P2PK path m/129373'/10')
  opens; first reply asks whether it should be a KDF type byte instead
  ("Keysets v2 is moving away from BIP32… align with this approach?").
- **2026-03-20** — nutshell #798 implements the V2 KDF per spec text.
- **2026-03-27** — 129373 lands in 13.md ("use correct purpose and
  tests").
- **2026-05-29** — robwoodgate proposes the KDF alternative (#384)
  that "would close this PR".
- **2026-06-25** — dev call: "#331 deterministic P2PK generation and
  #373 NUT-20 quote locking — active around BIP32 vs KDF tradeoffs."
- **2026-07-15** — #331 described as "fully in production (CDK/Coco
  led, CTS recently)"; **2026-07-30** it merges. cdk had already
  shipped the BIP32 path; the 0x01 SecretKey::derive was by then (and
  remains in v0.18.2) **unreferenced by any caller in the workspace**.

## So: bug or deliberate?

- The byte label inside cdk's dead API: an **unforced mislabel**
  against the then-available draft table, never reconciled — closest
  to "bug," but harmless (zero callers).
- The P2PK-key-source question itself (BIP32 vs KDF): **explicitly and
  deliberately debated upstream** (#331 vs #384, dev-call "BIP32 vs KDF
  tradeoffs"); BIP32 won on production-readiness grounds. cdk ships the
  winner; cashu-ts ships the winner; nutshell ships nothing here.
- The only live spec nit: **V2 step 3's one-digest-two-outputs
  wording** — demonstrated consequence: one reference implementation
  mislabeled a byte in code that never shipped. That is a wording-
  polish datapoint, not an interop finding.

## Disposition

- Upstream: **nothing meets the bar** (AGENTS rule 2). Hold the #443
  comment permanently unless a v2-vectors PR opens, in which case the
  step-3 wording + this timeline is the contribution.
- Registry row: downgraded + retraction recorded (the 2026-10-24
  "unspendable by construction" claim was wrong — it generalized from
  dead code).
- Tracker card: corrected to the shipped-behavior table above.
- cashu-ts's 0x02/0x03 extension matches #443's v3 table (0x02 NUMS,
  0x03 leaf keys) — cashu-ts is building against the v3 PR, confirmed.
