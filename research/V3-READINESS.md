# V3 READINESS — the Nutroot epoch (#443) audit plan (pre-staged 2026-10-25)

Status: nuts#443 is OPEN, mergeable **clean**, 29 files, +1482/−143.
The daily watch regenerates SPEC-HISTORY and fires a CHANGE line the
day it merges; this doc is the pre-staged plan for that day. cdk is
already building against it (cdk#2607 Nutroot PR); cashu-ts carries
v3 derivation-table extensions (0x02/0x03 map) — the ecosystem will
have implementations quickly. Nutshell shows no v3 prep.

## What v3 is (from the #443 diffs, read 2026-10-25)

- **V3 keysets** (NUT-02, version byte `02`): BLS12-381 pairing-based
  BDHKE; `Y = hash_to_curve_G1(secret)` → 48-byte / 96-hex points
  (checkstate, keys).
- **Transaction model moves into NUT-00** (+168): "the transaction
  transcript" + input digests; inputs SIGN (a paid quote is a
  transaction input); key-path witness + spend info + receive-time
  checks.
- **Nutroot locking** (NUT-10, +154): tweak + internal key + condition
  leaves + tree + script path; core leaves `threshold`, `after`,
  `hashlock`, `commit`; leaf-type registry; `0xff` never allocated
  (unknown-type vector stays valid); mints list understood leaves in
  NUT-06 `"10"` settings (`leaves`).
- **V3 mint quotes are ALWAYS LOCKED** (NUT-04, +10): quote MUST carry
  `pubkey`; mints MUST reject unlocked v3 quotes; the mint request
  `signature` carries BIP-340 (key path) OR serialized script-path
  witness JSON; quote lock MAY be a nutroot point with leaves;
  amount_issued committed in the witness → 20008 on mismatch.
- **Checkstate** (NUT-07, +5): returns `witness` (also while PENDING
  for v3) + `input_digest` (what the v3 witness signs).
- **NUT-13 v3 derivation** (+197): 0x00 key / 0x01 blinding (rejection
  sampled vs BLS_FR_ORDER) / 0x02 NUMS / 0x03 leaf keys / 0x04
  quote-lock; length-framed scope; counters full u64.
- **NUT-18/26/28** (+66): P2BK on the keys inside payment requests;
  **NUT-22** (+37): v3 blind auth; **NUT-29** (+6): batch on v3.
- **Test vectors**: new files for 10/18/22/26/28/29; +315 lines of
  00-tests; 13-tests rewritten for v2+v3 (+94/−13).

## Merge-day sequence (the day the watch fires)

1. `python3 tools/spec_history.py --refresh`; rewrite the tracker's
   "In flight" section as a landed epoch; bump NUT-02/04/07/10/13/18/
   22/26/28/29 cards with their v3 sections.
2. Read the new tests/* vectors — they are the frozen predictions for
   every v3 probe (implement our helpers AGAINST them before probing).
3. Arms: cdk nutroot branch as a git-arm
   (`--git-arm cdk-nutroot=cdk:/root/src/cdk:<branch>`), cashu-ts
   latest, plus all four pinned arms for the pre-v3 regression sweep
   (nothing pre-v3 should move).
4. Probe battery, in order (each with frozen predictions first):
   a. v3 keyset listing + ID verification vs 02-tests vectors
   b. unlocked v3 mint quote MUST reject (20008) — the always-locked
      rule; locked v3 quote with BIP-340 key-path witness (reuses
      today's NUT-20 machinery — msg = the INPUT DIGEST now, not the
      NUT-20 message)
   c. checkstate v3 shapes: 96-hex Ys, witness + input_digest on
      SPENT and PENDING
   d. nutroot leaves mint-side: each core leaf accept + reject paths;
      unlisted leaf type; the 0xff vector
   e. v3 derivation vectors cross-impl (cdk nutroot vs 13-tests vs
      cashu-ts)
   f. batch mint on v3 (locked quotes + signatures array)
   g. PRE-V3 REGRESSION: full must-gap + fresh-must-wave batteries on
      the pinned arms — v3 must not leak into pre-v3 behavior
5. Update MINT-NUT-SUPPORT with a v3 arm column; new tracker cards
   NUT-02/10 v3 rows.

## Tooling state (pre-staged 2026-10-25)

- **py_ecc installed** on the hub (/usr/bin/python3): BLS12-381 G1/G2
  + pairing verified working. `hash_to_curve_G1` must be implemented
  against 00-tests vectors (py_ecc has the primitives; the IETF
  hash-to-curve is in py_ecc.bls12_381.hash_to_curve? — verify against
  vectors, do not trust memory).
- must_gap_vectors.py is secp-only; the v3 harness extends it with a
  BLS module (blind-sign ops differ: pairing-based — the PROBE side
  only needs keyset-listing/locking/checkstate shapes + derivation;
  full BLS blinding round-trips only needed for end-to-end v3 mints —
  estimate: G1 hash + point add + pairing check ≈ small addition).
- The NUT-20 lock machinery (bip340_sign + mint_quote_sig_msg) is
  reusable for v3 key-path witnesses — only the signed MESSAGE changes
  (input digest).

## Open questions to answer on merge day (not before)

- Does cdk#2607 ship mint-side v3 or wallet-side first? (Mint-side =
  probeable; wallet-only = the v3 arms are decode-only.)
- Do v3 quotes keep the NUT-20 error family (20008) for all v3 lock
  failures (the 04.md diff says yes for amount mismatch)?
- Is pre-v3 NUT-20 locking unchanged on v3 mints (the diff says the
  signature field REPLACES the NUT-20 message for v3 — verify no
  double-requirement).

## Currency check (2026-10-30)
#443 open, mergeable-clean, 101 commits, quiet since Oct 26. Direction
UNCHANGED from this doc's basis (Oct-14 summary reconfirms: transcript
quote inputs 0x12, blinded outputs 0x21, tagged-hash quote ids, NUT-13
type 0x05 preimage, NUT-22 path-relative targets, tighter malformed-
input rules — the last item is the same wave as cashu-cf#100's request
bounds). Sequence below stands as written; the watch fires on merge.
