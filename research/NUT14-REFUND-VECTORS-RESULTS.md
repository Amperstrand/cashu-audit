# NUT-14 HTLC + Refund-Path Vector Results: The d6 Root Cause

*2026-09-12. Same driver/method as MUST-GAP-VECTORS-RESULTS.md (raw
protocol, controlled secrets, frozen predictions, SANITY/CTRL gates).
Raw runs: `artifacts/mgv-run{6,7}.txt`.*

## Vectors

| ID | Construction | Spec expectation |
|---|---|---|
| H1 | HTLC, valid preimage witness | ACCEPT (control) |
| H2 | HTLC, UPPERCASE hash in `data` + valid preimage | map: string-compare vs digest-compare |
| H3 | HTLC, locktime expired, refund key tag, witness `{"signatures":[sig]}` | ACCEPT (14.md:69 refund path) |
| H4 | same, locktime NOT expired | REJECT |
| H5 | HTLC, no witness | REJECT |
| H6 | same as H3 but witness `{"preimage":"","signatures":[sig]}` | ACCEPT (workaround shape) |
| P1 | P2PK, locktime expired + refund tag + refund sig | ACCEPT (11.md refund path) |
| P2 | same, locktime future | REJECT |

## Matrix

| Mint | H1 | H2 | H3 | H4 | H5 | H6 | P1 | P2 |
|---|---|---|---|---|---|---|---|---|
| cdk 0.17.0/0.17.6/0.18.0 | ✓ | **ACCEPT** | **REJECT (!)** | REJ | REJ | **ACCEPT** | ✓ | REJ |
| nutshell 0.20.0–0.20.3 | ✓ | ACCEPT | ACCEPT | REJ | REJ | ACCEPT | ✓ | REJ |
| nutshell 0.19.0 | ✓ | ACCEPT | ACCEPT | REJ | REJ | ACCEPT | ✓ | REJ |
| nutshell 0.18.2 | ✓ | ACCEPT | **REJECT (!)** | REJ | REJ | **REJECT (!)** | ✓ | REJ |
| nutshell 0.16.5 | ✓ | ACCEPT | ACCEPT | REJ | REJ | ACCEPT | ✓ | REJ |

## Findings

### F6 — d6 solved: HTLC refund is unspendable on cdk with the natural witness shape

cdk's wire struct (crates/cashu/src/nuts/nut14/mod.rs):

```rust
pub struct HTLCWitness {
    pub preimage: String,                    // REQUIRED, not Option
    pub signatures: Option<Vec<String>>,     // optional
}
```

The witness enum is untagged. A refund-path witness `{"signatures":[sig]}`
lacks `preimage` → cannot parse as HTLCWitness → falls through to
P2PKWitness → `verify_htlc` rejects with the misleading
`{"code":50000,"detail":"Secret is not a HTLC secret"}`.

**Every cdk version tested (0.17.0–0.18.0) rejects the refund path in
the shape wallets naturally produce.** Adding an empty preimage field
(H6: `{"preimage":"","signatures":[sig]}`) is accepted everywhere —
cdk then fails the preimage check and falls to the refund path, which
verifies. nutshell treats `preimage:""` as falsy and also accepts.

This is the mint-side half of the historical d6 (htlc_refund 0/108)
mystery: wallet-driven refund spends die on cdk mints regardless of
wallet correctness.

### F7 — nutshell 0.18.2 has no HTLC refund branch at all

`{"detail":"no HTLC preimage provided"}` — 0.18.2's
`verify_htlc_spending_conditions` lacks the "refund path unlocks once
the timelock has expired" branch (present in 0.19.0+ and 0.16.5).
HTLC tokens with expired locktime are permanently unspendable on
0.18.2 mints. H6 fails too — the workaround can't help a missing path.

### F8 — hash-case (H2): all 9 mints do digest-compare; cashu-cf was the outlier

Uppercase hash in `data` + valid preimage accepted by every cdk and
nutshell tested (both parse hex case-insensitively and compare digests).
The string-comparison trap that motivated delay-mode on testnut
(cashu-cf) does not exist in the reference implementations — the
delay-mode fix addressed a genuine one-implementation bug.

### F9 — P2PK refund path (P1/P2): healthy everywhere

Locktime+refund tags on P2PK secrets spend correctly after expiry and
are rejected before expiry on all 9 mints. The refund-path machinery
itself works; only the HTLC witness typing (F6) is broken.

## Spec gap (amendment material)

14.md does not specify the witness shape for the refund path. Two
conformant-looking shapes exist:
- `{"signatures":[...]}` — produced by nutshell-style spenders; cdk rejects
- `{"preimage":"","signatures":[...]}` — accepted by all; semantically odd

The amendment should either normatively define the refund witness, or
require mints to accept a P2PK-shaped witness for HTLC refunds.

## Reproduce

```bash
ssh ai-legion 'docker run --rm --network host -v /tmp/mgv-drv:/drv:ro \
  cashubtc/nutshell:0.20.3 python3 /drv/mgv.py http://127.0.0.1:3500{0..8}'
```

## Postscript (same day): version boundaries completed

Ephemeral runs against nutshell 0.16.0/0.17.0/0.18.0 (images on
ai-legion; `MINT_PRIVATE_KEY` must be 64-hex for old versions, and
0.14.x/0.15.x speak the pre-v1 REST API — `/keys`, not `/v1/keys` — so
the v1 driver does not cover them; boundary story is complete from
0.16.0 onward):

Full nutshell release line covered (0.16.0, 0.16.5, 0.17.0, 0.18.0,
0.18.1, 0.18.2, 0.19.0, 0.19.1, 0.19.2, 0.20.0, 0.20.1, 0.20.2,
0.20.3) plus cdk 0.17.0/0.17.6/0.18.0 — 16 mint versions × 17 vectors.

| Feature (nutshell) | 0.16.0 | 0.16.5 | 0.17.0–0.18.1 | 0.18.2 | 0.19.0–0.19.2 | 0.20.0 | 0.20.1 | 0.20.2 | 0.20.3 |
|---|---|---|---|---|---|---|---|---|---|
| sigflag validation (V2) | enforce | enforce | **LOST** | **LOST** | **LOST** | restored | enforce | enforce | enforce |
| HTLC refund branch (H3/H6) | **missing** | present | **missing** | **missing** | present | present | present | present | present |
| SIG_ALL msg format (V3B) | old | old | old | old | old | old | old | old | **new** |
| duplicate keys (V6) | enforce | enforce | enforce | enforce | enforce | enforce | enforce | **REGRESSED** | **REGRESSED** |
| uncompressed pubkey (V5) | accept | accept | accept | accept | accept | accept | accept | accept | accept |

Precise boundaries: V6 regression enters at **0.20.2**; sigflag-loss
window is **0.17.0–0.19.2**; HTLC-refund absence window is
**0.17.0–0.18.2** (with an anomalous presence in 0.16.5 only of the
pre-0.17 line); SIG_ALL format flips old→new at **0.20.3**. cdk
`mintd:latest` (2026-09-02 rebuild) is still 0.18.0, and the required
`preimage: String` HTLCWitness struct is still present in upstream
main (per the 2026-09-09 spectate sync) — the refund-witness bug is
unfixed upstream.

The sawtooth shapes (enforced → lost → restored) show these MUSTs are
not regression-tested upstream: each is a window where conformance
silently drifted. V5 is never enforced across the entire 0.16–0.20
range. Raw runs: `artifacts/mgv-run8.txt`.

## Wallet-level confirmation (same day, wire captured)

`experiments/must-gap-vectors/wallet_htlc_refund.py` runs the full
wallet flow (mint → lock → expire → sign → spend) with an httpx wire
tap, against fee-free ephemeral mints:

- **nutshell wallet 0.20.3 × nutshell mint 0.20.3: PASS** (refund
  spent, keep 4 sats). Confirms the raw H3 result end-to-end.
- **nutshell wallet 0.20.2 × cdk mint 0.17.6: FAIL** — wire witness is
  `{"preimage":null,"signatures":["<sig>"]}` → cdk responds
  `{"code":50000,"detail":"Secret is not a HTLC secret"}`.

The `preimage: null` detail matters: it is not a missing field — the
wallet explicitly serializes null. cdk's `HTLCWitness.preimage:
String` cannot accept null OR missing, so both the natural wallet
shape (null) and the signature-only shape (missing) fail; only the
empty-string workaround (H6) parses. **HTLC refund tokens are
unspendable with any nutshell wallet on any cdk mint tested
(0.17.0–0.18.0).** The historical d6 (htlc_refund 0/108) is now fully
explained: this mint-side rejection for wallet-driven cells, missing
refund branch on nutshell 0.17.0–0.18.2 mints for the rest, and the
driver never attempting a spend at all.

Also observed on the wire: the wallet's swap outputs carry
`"C_": null` (tolerated by both implementations).

## cdk upstream HEAD check (2026-09-12, built from cashubtc/cdk main today)

Full vector suite + NUT-20 probes against a locally built
`cdk-mintd` HEAD (reports version 0.18.0-dev):

- **H3 (natural refund witness): still REJECT** — the
  `HTLCWitness.preimage: String` required-field bug is **unfixed in
  upstream main** as of this build.
- H6 (empty-preimage workaround): still ACCEPT.
- All other vectors identical to the 0.18.0 release (multi-input
  SIG_ALL swap OK, V2/V5/V6 enforced, NUT-20 accepts both schemes).

The F6 finding is upstream-reportable against HEAD with a reproducible
vector and a working interop workaround (H6).
