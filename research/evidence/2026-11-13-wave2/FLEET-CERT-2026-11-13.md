# Fleet certification + deploy-vintage probe — 2026-11-13 (hermes-cocofix lane)

Owner-directed takeover of the wallet-matrix lane's verification half.

## Certifiers (deployed vintage)
- testnut: 13/13 PASS — CLEAN (experiments/fresh-must-wave/certify_testnut.py)
- signut: 15/15 PASS — CLEAN (experiments/live-mint-matrix/certify_signut.py)

## Deploy vintage (wire probes, evidence in cf#110/#122 comments)
- c64592fe-class fixes DEPLOYED: malformed-bech32 melt quote → 400/14005
  on both mints (was 200).
- Everything AFTER c64592fe NOT deployed: strict NUT-00 UTF-8 (8a496096),
  MPP sat-only boundary (60959ede), #49 (92da59a6), #100 (b473a00d),
  #103 (d860eacc).
- Live #49 evidence: 1500 msat MPP partial of 3000 msat invoice → quote
  amount=2 (Math.ceil overcharge) on signut — the exact class 92da59a6
  kills. Post-deploy the same probe must 400 mpp_sub_satoshi.
- signut /v1/info advertises NO NUT-15 despite an MPP-capable backend —
  the #113 advertisement fix is also undeployed (or the pre-fix builder
  under-advertises); the wave-2 capability probe works around it.

## Wave-2 standing reds (scenarios/postdeploy_boundary_wave2.py)
- signut: mpp_subsat_partial_boundary ❌ (overcharge live), melt_change_outputs_cap ❌
- testnut: mpp SKIP (fakewallet, no MPP backend — loud skip), melt_change_outputs_cap ❌
- nut00_strict_p2pk_hexdecode: NOT YET IMPLEMENTED (needs cf P2PK msg
  derivation pinned first — wave-2 follow-up).
