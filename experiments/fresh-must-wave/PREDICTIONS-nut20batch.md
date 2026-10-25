# FROZEN PREDICTIONS — NUT-20 batch locked-mint + version stability (2026-10-25)

Batch locked-mint (29.md): a batch containing one LOCKED (pubkey) quote
must carry signatures[i] per quote (null for unlocked). Legs per arm:
- BL1: batch [locked paid quote + unlocked paid quote], signatures
  [sig, null], valid sig for the locked one -> 200 both signed
- BL2: same batch, signatures omitted -> 4xx (20008 class per 29.md's
  NUT-20 section: "Required if ANY quote is locked")

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| BL1 valid | 200 | 200 | 200 |
| BL2 missing | 4xx 20008-class | 4xx | 4xx |

Version stability (ns-0.20.3, cdk-0.18.1): replay-caching and keyless
behavior expected IDENTICAL to their siblings (0.21.0/0.18.2) — the
features predate both releases. Any drift = version-matrix finding.
