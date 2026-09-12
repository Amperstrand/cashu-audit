# testnut (cashu-cf production) — 17-Vector Conformance Report

*2026-09-12. Full vector suite against https://testnut.cashu.exchange
(Nutshell-CF/0.0.1, FakeWallet backend, production deployment with
delay-mode). Raw: `experiments/must-gap-vectors/artifacts/testnut-2026-09-12.json`.*

## Results

| Vector | testnut | vs reference mints |
|---|---|---|
| SANITY / CTRL | ✓ | — |
| V2 invalid sigflag | **REJECT** ✓ | = ns 0.20.x/cdk; better than ns 0.17–0.19.2 (accept) |
| V3 SIG_ALL mixed | **REJECT** ✓ | enforced by all |
| V3B/C multi-input SIG_ALL | REJECT | = all nutshell; only cdk accepts (F5 family) |
| V3D single-input SIG_ALL | **ACCEPT** ✓ | = ns 0.19+/cdk |
| V5 uncompressed pubkey | **REJECT** ✓ | better than EVERY nutshell (all accept); = cdk |
| V6 duplicate keys | **REJECT** ✓ | better than ns 0.20.2/0.20.3 (regressed); = cdk/ns ≤0.20.1 |
| H1 preimage | ✓ | — |
| H2 UPPERCASE hash | **ACCEPT (60s delay)** | **delay-mode live in production** — driver initially timed out at 15s; with 150s timeout the swap completes after the hold. All reference mints digest-compare instantly; testnut string-compares + delay-honors. |
| H3 natural refund witness | **ACCEPT** ✓ | **no F6 bug** — cdk 0.17–HEAD rejects this shape |
| H6 empty-preimage refund | **ACCEPT** ✓ | tolerant of BOTH shapes (unique: works with every wallet) |
| H4/H5/P2 negative controls | REJECT ✓ | correct |
| P1 P2PK refund | **ACCEPT** ✓ | healthy everywhere |

## Conclusions

1. **cashu-cf has no F6 bug**: it accepts the natural wallet refund
   witness (`{"signatures":[...]}`) AND the empty-preimage form — the
   only mint tested that takes both. No fix needed.
2. **Stricter than every nutshell on MUSTs**: V2, V5, V6 all enforced
   (V5 via signature-verification failure — `30006 "Signature threshold
   not met"` — outcome compliant, mechanism differs from a format check).
3. **Delay-mode verified in production a second time** (H2 held ~60s
   then honored — the exact deployed behavior).
4. **Only conformance gap**: multi-input SIG_ALL message family (shared
   with the whole nutshell line; only cdk implements the current spec
   text). Deferred with the F5/F11 amendment work.

## Probe fixes made en route (now in the driver)

- Cloudflare blocks the python default UA → driver sends `curl/8.7.1`
- cashu-cf fee error wording differs ("available for fees (0) ... is
  required (1)") → fee-retry parses `required (N)` first
- Swaps now use 150s timeouts (delay-mode mints legitimately hold 60s)
