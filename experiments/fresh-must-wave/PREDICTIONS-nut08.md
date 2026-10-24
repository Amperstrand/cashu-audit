# FROZEN PREDICTIONS — NUT-08 blank-change melt probes (written BEFORE run, 2026-10-24)

Arms: ns-0.21.0, cdk-0.18.2 (docker), testnut (cashu-cf). Melt inputs:
128 sat in powers of 2 (64/32/16/16). Oracle invoice 100 sat. Change
expected: 128 - 100 - fee_reserve (ns/cf fee 10 → 18; cdk 20 → 8).

Leg A (spec #426-compliant): outputs = [blank(0), blank(0)] — two
zero-amount change outputs.

Leg B (#426-violating): outputs = [declared(1), declared(1),
declared(1)] — non-zero declared amounts, deliberately mismatched to any
sane decomposition (tests the nut05-blank-change "mints imprint by
index, ignore declared" claim on current releases).

| Arm | Leg A prediction | Leg B prediction |
|---|---|---|
| ns-0.21.0 | 200; change sigs = ns's own powers-of-2 decomposition of 18 (16+2 → 2 sigs for 2 outputs?); declared-0 accepted | accepted (lenient class); ns imprints by index — sig count = its decomposition length (may be < 3); declared 1-sat ignored |
| cdk-0.18.2 | 200; decomposition of 8 (8 → possibly 1 sig for 2 outputs, or per-output split) | accepted; cdk process_melt_change imprints by index (issue draft's claim) |
| testnut (cf) | 200; cf clamps fee to reserve (F7 finding); decomposition of 18 | accepted (lenient parse class); imprint-by-index expected |

Control: after a successful melt, checkstate of a melted input's Y must
be SPENT on every arm (NUT-07 sanity leg).

Decode method (not a prediction): change C_ unblinded with each output's
r → C; C matched against {a·P_a} over the keyset's listed amounts to
recover the mint-imprinted value per output.
