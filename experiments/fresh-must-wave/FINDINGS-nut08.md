# FINDINGS — NUT-08 melt-change probes (2026-10-24, ~07:35 UTC)

Frozen predictions: `PREDICTIONS-nut08.md`. Driver: `melt_change.py`
(reuses must-gap-vectors crypto; melts an invoice-oracle invoice so
targets settle). Artifacts: `out/nut08.json`. Arms: ns-0.21.0, cdk-0.18.2
(docker), testnut (cashu-cf). Inputs 128 sat (64/32/16/16), invoice 60
sat, fee_reserve 2 (testnut 1). All melts returned 200/PAID with a real
preimage; control checkstate on a melted input = SPENT on all arms.

## Prediction scorecard

- Leg A accepted with mint-decomposed change: HIT on all three arms.
- Leg B accepted (nobody enforces #426's amount-0): HIT.
- Imprint-by-index: HIT — but stronger than predicted (see below).

## Measured (byte-level convergence)

| Arm | Leg A outputs=[0,0] | Leg B outputs=[1,1,1] |
|---|---|---|
| testnut (cf) | change=[32,16] | change=[32,16,2] |
| ns-0.21.0 | change=[32,16] | change=[32,16,2] |
| cdk-0.18.2 | change=[32,16] | change=[32,16,2] |

1. **Perfect three-family convergence**: identical change decompositions
   per leg on every arm. The nut05-blank-change-outputs issue's
   "mints imprint by index, ignore declared amounts" is now measured
   CONVERGENT behavior on current releases — not a divergence.
2. **Declared amounts are ignored, not rejected** — outputs=[1,1,1]
   melt PAID everywhere; #426 (2026-08-23) makes amount-0 a wallet-side
   MUST and no mint rejects non-zero. Same enforcement-gap class the
   registry tracks for other NUT-11/12 MUSTs (mint-side leniency).
3. **Decomposition adapts to the offered slot count** — 2 slots →
   [32,16]; 3 slots → [32,16,2]. The mint re-decomposes its change over
   however many outputs the wallet offers. A wallet that offers N blank
   outputs receives N signatures — the Amethyst #3847 class (wallet
   discards change it didn't expect) is directly explained by this.
4. Response field is `change` (with amount + id + C_ per entry) on all
   three families — spec-conformant (NUT-05 melt response).
5. **Open arithmetic (honest gap)**: change totals (48 leg A / 50 leg B)
   do not equal inputs − amount − fee_reserve (66) on any arm — actual
   fees exceed the quoted reserve on these keysets, consistent with the
   registry's F7 finding (ns actual fee > quoted fee_reserve; cf clamps
   to reserve). Leg B's total being 2 higher than leg A's with identical
   inputs/invoice-size is unexplained — input-fee arithmetic per family
   is the follow-up (same inputs both legs; only slot count differs).

## Leg C (2026-10-24 ~07:40): slot-count truncation CONFIRMED — inputs were 112, not 128 (probe bug, see Leg D)

`out/nut08_legc.json` + correction from `out/nut08_legd.json`:

| Arm | 2 slots | 3 slots | 4 slots |
|---|---|---|---|
| ns-0.21.0 | [32,16] = **48** | [32,16,2] = **50** | [32,16,2] = 50 |
| testnut (cf) | — | [32,16,2] = **50** | — |

CORRECTION (leg D): legs A/B/C minted **112 sat, not 128** — the probe's
dict literal `{64:..,32:..,16:..,16:..}` collapsed the duplicate `16`
key, so one 16-sat output was never minted (this also explains ns's
"Provided: 112" in the first failed run). With inputs=112: 112 − 60 −
reserve(2) = 50 exactly — the "unaccounted ~16 sat" of the first
findings draft was this probe bug, nothing more. All structural results
survive (they were measured against the same 112-sat inputs on every
arm):

- True change 50 = 32+16+2 needs three power-of-2 denominations; in 2
  slots the mint returns [32,16]=48 and **silently keeps the 2-sat
  remainder**. Offering too few change outputs shortchanges the wallet
  by construction (wallet-compat class; Amethyst-#3847 adjacent).
- Decomposition is stable once slots suffice (3 slots == 4 slots).

## Leg D (2026-10-24 ~07:45): fee ledger is EXACT — no hidden fees

Frozen predictions: `PREDICTIONS-nut08d.md` (all three hypotheses
refuted/refined by measurement). Inputs {64,64} / {64,32,16,16} /
{16×8} = 128 sat each (dict-collision fixed), invoice 60, **4 blank
slots**, `out/nut08_legd.json`:

| Arm | every input count (2/4/8) | gap vs 128−60−reserve |
|---|---|---|
| ns-0.21.0 | change=[64,2]=66 | **0** (exact) |
| testnut (cf) | change=[64,2]=66 | 1 (charged 2 vs reserve 1 — F7 class: actual vs quoted reserve, cf rounds) |

- No per-input hidden fee, no fixed payment-side fee. NUT-08/NUT-02
  fee arithmetic is exact and input-count-independent on both families
  at these sizes (ppk 10/100 is sub-sat and rounds away).
- testnut charged 2 while quoting fee_reserve 1 — consistent with the
  registry's F7 (ns actual fee exceeds quoted reserve) / cf-clamps
  catalogue row; ns was exact here.
- Notable: with true change 66 = 64+2, TWO slots suffice — the leg-C
  truncation only bites when the decomposition needs more denominations
  than slots offered.

## Probe bugs found (and fixed) per the mismatch discipline

- First run melted a 1000-sat oracle invoice (mints derive the amount
  from the invoice, ignoring my `amount` field — itself a note: the
  melt-quote `amount` request field is advisory at best on all arms).
- melt_body truncated at 400 chars cut the `change` array on the first
  successful run; raised to 2500.
- Legs A–C minted 112 not 128 sat: dict literal with a duplicate `16:`
  key collapsed one output (caught by leg D's clean arithmetic; fixed
  in `mint_128`).
