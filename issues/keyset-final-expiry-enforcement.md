# Divergence note: cdk enforces keyset final_expiry at swap; nutshell never expires


## Why a developer or LLM gets confused

NUT-02's `active` flag conflates the mint window with the redeem window, so implementers assume rotated-out keysets remain redeemable forever. They don't have to: `final_expiry` ends the mint's obligation entirely, and implementations genuinely differ on whether they ever invoke it.

## The lesson

- **Spec (NUT-02 §Keyset Final Expiry):** after `final_expiry` the mint "is no longer obliged to fulfill promises signed with the keys from that keyset" and may irrevocably delete the keyset's nullifiers. The refusal is standardized: error code **12003 "Keyset has expired"** (nuts PR #367).
- **cdk 0.17.6:** enforces — swaps on expired keysets fail outright with `could not swap proofs: Keyset has expired` (observed live; `CDK_MINTD_FAKE_WALLET_KEYSET_ROTATIONS` with `expired:true` sets a past final expiry).
- **nutshell:** keysets never expire (nutshell #7) — proofs on rotated keysets stay redeemable indefinitely.
- **Inactive ≠ expired:** NUT-02 is explicit that inactive (`active=false`) keysets MUST still accept swap inputs; expiry is the separate, terminal state.

## Improvement

Wallets that hold balances across rotations (payment routers, resellers) must treat `active=false` as "swap off now" and `final_expiry` as a deadline, and classify 12003 distinctly from transport errors. Downstream tracking: OpenTollGate/tollgate-module-basic-go#417.

*Source: live lab reproduction (tollgate cloud-lab keyset-rotation lane, 2026-09-19) cross-checked against NUT-02 and the cdk 0.17.6 source; corroborates issues/keyset-active-flag-semantics.md and the "#7 old keysets never expire" row in divergences/CDK-VS-NUTSHELL-ALIGNMENT-2026-07-29.md.*
