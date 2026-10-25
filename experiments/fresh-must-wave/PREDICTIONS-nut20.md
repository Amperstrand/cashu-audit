# FROZEN PREDICTIONS — NUT-20 quote-lock path (written BEFORE run, 2026-10-25)

Arms: ns-0.21.0, cdk-0.18.2 (docker), testnut (cashu-cf). Method: 20.md
current text (post #370 hardening): quote request gains `pubkey`; mint
request gains BIP340 `signature` over SHA256(b"Cashu_MintQuoteSig_v1"
|| len32(quote)||quote || per-output len32(amount)||amount ||
len32(B_)||B_); errors 20008 (no/invalid sig) / 20009 (pubkey quote,
no pubkey given). Message construction self-tested against 20.md's own
worked example BEFORE any probing (verify-only; no private key needed).

| Leg | testnut (cf) | ns-0.21.0 | cdk-0.18.2 |
|---|---|---|---|
| L1 create locked quote (pubkey in request) | 200, pubkey echoed | 200, echoed | 200, echoed |
| L2 mint PAID locked quote, NO signature | 4xx, code? (cf family — 20008 or cf-local) | 4xx | 4xx **20008** (spec-fresh adopter, cf. 11016 convergence) |
| L3 mint WITH valid BIP340 signature | 200 + sigs | 200 + sigs | 200 + sigs |
| L4 mint with signature from WRONG key | 4xx 20008-class | 4xx | 4xx |
| L5 UNLOCKED quote + spurious signature | accepted-or-ignored (measure) | accepted/ignored | accepted/ignored |
| L6 batch: locked quote + signatures array | (if time) | | |

Secondary: error identities per leg; whether the locked quote still
mints after L2's rejection (retry with sig — spec says Alice CAN repeat;
a burned quote would be a fund-loss finding).

Prediction on L3: if any arm rejects a self-tested-valid signature,
that is a PROBE BUG (message-format mismatch) until proven otherwise —
the #370 "harden (breaking)" rewrite means any arm predating June 2026
may implement the OLD message format; ns 0.21.0 released 2026-09-16 and
cdk 0.18.2 2026-10-14 both postdate the hardening, so current-format
acceptance is expected on all arms.
