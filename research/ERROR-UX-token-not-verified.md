# Error-UX analysis — "Error receiving tokens: MintOperationError: Token not verified"

**Date:** 2026-09-08 · **Repo:** cashu.me (+ cashu-ts) · **Status:** proposal, contribution-ready

## The exact chain (verified against source)

1. **Mint** (cdk-mintd, e.g. mint.minibits.cash): proof fails
   `C == a·hash_to_curve(utf8(secret))` → HTTP 400
   `{"code":10001,"detail":"Token not verified"}`
   (cdk `error.rs`: `TokenNotVerified → Unknown(10001)`).
2. **cashu-ts** `src/transport/request.ts` detects the mint error body and throws
   `MintOperationError` (`src/model/Errors.ts:177`) — a class that **does** carry
   `.code` and `.detail`, but renders as `MintOperationError: Token not verified`
   via default `toString()`.
3. **cashu.me** `src/stores/wallet.ts:843`:
   ```ts
   } catch (error: any) {
     console.error(error);
     throw new Error("Error receiving tokens: " + error);   // string concatenation
   }
   ```
4. The UI shows the concatenated string verbatim.

So the user sees a library class name + a five-word spec phrase, with no code,
no mint, no next step. Everything needed for a good message already exists on
the error object at step 3 — it is discarded by `"" + error`.

## Proposal: map NUT codes to human messages, keep detail expandable

cashu.me (or any wallet using cashu-ts — the mapping belongs in a shared layer):

```ts
import { isMintOperationError } from '@cashu/cashu-ts';

function humanizeReceiveError(e: unknown, mintUrl?: string): { title: string; body: string; detail: string } {
  const detail = e instanceof Error ? `${e.name}: ${e.message}` : String(e);
  if (isMintOperationError(e)) {
    switch (e.code) {
      case 10001:
        return {
          title: "Couldn't receive this payment",
          body:
            "The mint that issued this money could not verify it, so it can't be added " +
            "to your wallet. Nothing was deducted from your balance. The token itself may " +
            "still be valid — ask the sender to send it again. If it keeps failing, the " +
            "sending wallet may have a compatibility problem, and the sender should " +
            "contact their wallet or mint.",
          detail: `Mint ${mintUrl ?? ''} rejected the token (error 10001: token not verified).`,
        };
      // 20002 inputs already spent, 20008 witness missing, ... — each gets its own copy
    }
  }
  return {
    title: "Couldn't receive this payment",
    body: "Something went wrong while contacting the mint. Nothing was deducted. Please try again in a moment.",
    detail,
  };
}
```

Design rules used:

- **Say what happened** in one plain sentence ("the mint could not verify it").
- **Say what it means for the user's money** ("nothing was deducted from your
  balance") — the #1 question a user has.
- **Say what to do next** (ask sender to re-send; escalate to wallet/mint if repeat).
- **Never claim the token is fine** when it may be permanently invalid (encoding-trap
  tokens exist — this error is exactly how they surface); route the sender-side
  investigation instead of promising recovery.
- Keep `name`/`code`/`detail`/mint URL/time in a collapsed "technical details" for
  support conversations — the raw string belongs there, not in the headline.

## Library-level improvements (drafts ready)

- **cashu-ts**: `MintOperationError.toString()` could default to
  `MintOperationError (code 10001): Token not verified` — and a
  `codeToHint(code)` map would give wallets canonical copy to localize.
- **Mints (cdk issue draft)**: before returning 10001, run a log-only dual-derivation
  probe (utf8 vs hex-decoded Y) and emit an observability field like
  `encoding_mismatch: true` when the C matches the WRONG derivation. Zero
  protocol change, no leniency — turns every strict mint into a sensor for the
  trap so we can finally measure how much money it eats.
