# TollGate × Cashu: The Complete Mistake Timeline & What To Do Now

*2026-09-11. Internal (Amperstrand). Everything that went wrong, why it went
wrong, and what to do about it.*

## Part 1: Was gonuts a poor choice?

### The upstream (elnosh/gonuts) status

| Metric | Value | What it means |
|---|---|---|
| Last meaningful commit | **2025-08-13** | Over 1 year stale |
| Contributors | 1 (elnosh: 405/413 commits) | **Bus factor = 1** |
| Open issues | 16 (some from 2024) | Maintainer not responsive |
| Stars | 39 | Small community |
| V2 keyset IDs | **Missing** | Cannot interact with modern mints |
| V4 token format | **Missing** | Cannot decode future tokens |
| NUT-20 quote signing | **Missing** | Cannot do locked quotes |
| Offline mode | **Missing** | No offline verification |

**Verdict: upstream gonuts was already effectively unmaintained when we
started relying on it for TollGate.** The last substantive commit was a bug
fix in August 2025. Since then, the Cashu ecosystem has moved on (V2 keysets,
V4 tokens, NUT-20, NUT-28 P2BK) and upstream gonuts has not kept up.

### But the choice wasn't unreasonable at the time

When TollGate started (2025-07):
- gonuts was one of only 3 Cashu wallet libraries (cashu-ts, nutshell wallet, gonuts)
- It was the only Go option (matching TollGate's Go backend)
- It implemented 16 NUTs — more than cashu-ts at the time
- The derivation was correct (Go's type system prevents the NUT-00 trap)
- There was no way to know upstream would go stale

**The mistake wasn't choosing gonuts — it was not monitoring upstream health
and not having a plan for when it went stale.**

## Part 2: The complete mistake timeline

### Era 1: Foundation (2023-05 to 2025-07) — "The dark ages"

```
2023-05  tester created with cashu-ts ^0.8.0-rc
         gonuts forked from elnosh
         Origami74/gonuts-tollgate forked

         MISTAKE #1: No reference-mint testing
         The tester was only tested against cashu-cf (our own mints).
         Nobody checked if it worked against cdk or nutshell.
         Result: 0% compatibility with reference mints for 2+ years,
         and nobody knew.

2023-09  Local cashu-ts build (testing against fork)
         Still 0% reference compatibility.

2025-03  Portal-site created with cashu-ts ^2.2.2
         MISTAKE #2: Over-declared dependency
         The portal only uses getDecodedToken but declares the full
         wallet dependency. This confused dependency audits and made
         the v2 dead-zone look like a wallet problem when it's just
         a decoder problem.

2025-07  TollGate production deployment begins
         Origami74/gonuts-tollgate fork created (stale after 3 commits)
         MISTAKE #3: Forking without a maintenance plan
         The Origami74 fork was created, got 3 commits, then went
         stale for 14 months. No one was assigned to maintain it.
```

### Era 2: Unknowing production (2025-07 to 2026-07) — "The bugs we didn't know about"

```
2025-07  TollGate in production using Origami74/gonuts-tollgate
         The fork had these bugs (all unfixed):

         BUG #1 (fund-loss): Proof deletion before swap completion
           Wallet deletes old proofs, THEN tries to swap.
           If swap fails → old proofs are gone, new ones don't exist.
           → PERMANENT FUND LOSS

         BUG #2 (fund-loss): MultiMintPayment race condition
           Concurrent melts can read the same unspent proofs.
           Both submit; first wins; second's proofs are burned.
           → PROOF BURNING

         BUG #3 (panic): Empty slice panics in keyset/proof/token
           Various crash paths when data structures are empty.
           → CRASH (not fund loss, but availability)

         BUG #4 (wrong verification): DLEQ verification uses active
           keyset instead of proof's keyset
           → False verification failures (proofs rejected as invalid)

         BUG #5 (keyset): V2 keyset IDs not supported
           Cannot interact with mints using V2 keyset format.
           → TOKENS STUCK (not lost, but unusable)

         BUG #6 (keyset): Keyset counter not incremented before swap
           Can cause "already-signed" errors on deterministic secrets.
           → SPEND FAILURES

         All of these were live in production for ~12 months.

2025-09  Tester upgraded to cashu-ts ^2.7.1 (still 0% compat)

2025-11  Tester briefly upgraded to ^3.3.0
         MISTAKE #4: Upgrade without migration path
         v3.3.0 was the first version with any reference compatibility.
         But v3 changed the proof format. The upgrade broke existing
         tokens. The "fix" was to downgrade back to v2.7.4.
         → PROOFS MINTED DURING v3.3.0 WINDOW MAY BE BRICKED

2025-12  Tester downgraded back to ^2.7.4
         (See mistake #4 above)

2026-03  Tester upgraded to ^3.5.0 (stuck this time)
         Better, but still only 11% compatibility with reference mints.
         The tester remains a closed-loop system.
```

### Era 3: Awareness (2026-07) — "The spec-audit sprint"

```
2026-07-17 to 2026-07-28

         The gonuts-tollgate fork got a massive spec-audit sprint:
         - All 6 bugs above fixed
         - V2 keyset support added
         - V4 token format support added
         - NUT-20 quote signing added
         - Offline mode added
         - NUT-04 accounting fields added
         - NUT-11 duplicate tag rejection
         - Race condition serialization
         - Proof deletion ordering fixed
         - Empty slice guards
         - greatspectations spec-quote drift checker

         The fork went from "stale, buggy, unmaintained" to
         "actively maintained, spec-audited, production-hardened."

         But: the bugs had been live in production for a year.
         Any user who hit them during that period experienced
         fund loss with no recovery path.
```

## Part 3: What should TollGate do now?

### Immediate priorities (this month)

**1. Upgrade the tester from cashu-ts v3.5.0 to v4.10.0**

Our matrix shows v4.10.0 is the only version with 75% reference compatibility
(vs 11% for v3.5.0). The upgrade path exists — cashu-ts v4 has migration
documentation. The risk is the same as the November 2025 incident: proofs
minted under v3 format may not be readable by v4. Mitigation: verify all
existing proofs against the mint before upgrading.

**2. Test gonuts-tollgate against reference mints**

We have the infrastructure. We need a Go driver in the experiment matrix.
This tells us:
- Can TollGate verify proofs from cdk/nutshell mints?
- Can TollGate mint from cdk/nutshell mints?
- What happens when a user pays with tokens from a non-cashu-cf mint?

This is the single most important missing data point.

**3. Add the proof-deletion and race-condition bugs to the fund-loss enumeration**

These are vectors #18 and #19:
- #18: Proof deletion before swap completion (fixed 2026-07-25)
- #19: Concurrent melt race condition (fixed 2026-07-25)

They should be documented alongside the 17 vectors from our earlier
enumeration, with a note that they were "self-inflicted" (our own code,
not reference implementation bugs).

### Medium-term (next quarter)

**4. Decide: maintain the gonuts fork or migrate**

Three options:

| Option | Effort | Risk | Ecosystem position |
|---|---|---|---|
| **A: Continue maintaining the fork** | Medium (ongoing) | We own all bugs | Isolated — no community support |
| **B: Migrate backend to cdk** | High (rewrite) | Migration risks | Integrated — reference implementation |
| **C: Migrate frontend to cashu-ts v4.10** | Medium | Lower (JS ecosystem) | Integrated — most compatible wallet |

**Recommendation: Option C** — migrate the tester to cashu-ts v4.10 (it's
already TypeScript, the upgrade path exists) while keeping gonuts-tollgate
as the backend for now. This gets the user-facing component to 75%
compatibility immediately, and defers the harder backend migration.

**5. Contribute our gonuts fixes upstream**

Our fork has 13 commits ahead of upstream, including critical fixes.
Even if upstream is stale, contributing back:
- Helps anyone else using gonuts
- Reduces our divergence (easier to pull future upstream fixes)
- Builds goodwill if upstream becomes active again

**6. Add cashu-cf to the reference-mint test matrix (permanently)**

Not because it's a reference, but because it's OUR mint. Testing gonuts
against cashu-cf in CI catches integration regressions before they hit
production. This is what the production-001 experiment proved works.

### Long-term (next year)

**7. Plan the backend migration**

If the ecosystem converges on cdk (which it seems to be doing), TollGate's
Go backend should eventually use cdk as its Cashu library instead of a
forked gonuts. This is a larger project but would eliminate the
"maintaining our own Cashu implementation" burden.

**8. Contribute to the spec**

Our measurements are the most comprehensive in the ecosystem:
- The historical compatibility matrix (432 cells)
- The d1-d8 divergence documentation
- The fund-loss vector enumeration (now 19 vectors)
- The delay-mode proposal

These should inform the NUT spec evolution. But per the current strategy,
this stays internal until we decide to engage upstream.

## Part 4: The meta-lesson

The TollGate story is a case study in how **deferred maintenance compounds**:

1. Started with a wallet (cashu-ts v0.8) that couldn't talk to reference mints
2. Built on a library (gonuts) that went stale
3. Forked it without a maintenance plan
4. Had 6 fund-loss bugs in production for a year
5. Didn't discover them until a dedicated spec-audit sprint

Each step was individually defensible. Together they created a system that:
- Worked fine in its closed loop (cashu-cf ↔ gonuts ↔ portal)
- Was incompatible with the broader Cashu ecosystem
- Had latent fund-loss bugs that only our own audit found

**The fix is structural, not tactical**: continuous compatibility testing
against reference implementations (which we now have), upstream health
monitoring, and a maintenance budget for critical dependencies.
