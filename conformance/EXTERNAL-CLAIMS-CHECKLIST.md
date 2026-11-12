# External-claims checklist — run before citing any measurement outside this repo

Written 2026-11-12 after murdawkmedia's fixture audit on gonuts-tollgate #46 caught
three defects in freshly-committed conformance evidence: a bounds formula that
omitted NUT-02 input fees, a replay scenario whose PASS accepted any second 200
(name said "cached", assertion didn't), and an externally-published table row
that mislabeled a fresh-inputs/same-outputs swap experiment as a melt replay.
All three were green in our own battery. The gap was not the tools — it was that
the same lane wrote, ran, and interpreted its own evidence, then published the
interpretation with no adversarial pass.

Every external claim (issue filings, PR comments, divergence registry rows,
coverage tables) must pass:

1. **Quote the assertion, not the verdict.** Paste the exact lines that gate
   the scenario. If the name promises X and the code checks ~X, fix the code
   first. Any distinction that is *reported* but not *gated on* is a defect.
2. **Run the counterfactual.** Before citing a PASS as evidence, plant the
   opposite behavior (synthetic stub, parameter flip, mutated response) and
   require the scenario to FAIL. A scenario that cannot fail is decoration.
   (This is already the rule for the diff gate; it now applies to any new
   scenario whose verdict will be cited externally.)
3. **Enumerate the money math completely.** For any amount bounds/divergence:
   list every protocol component of both sides — `amount`, `fee_reserve`,
   NUT-02 `input_fee_ppk` (ceiling-rounded per input), unit — and show the
   arithmetic with the *live target's actual metadata* (e.g. pull the keyset
   fee; never assume 0).
4. **A/B against a known-good control.** The claim should hold on the target
   and the control should pass the same scenario. For upstream issue filings:
   a minimal synthetic reproduction (A/B — with and without the trigger)
   before filing. Do not file on observation alone.
5. **State identity provenance.** Remote/self-reported versions are labeled as
   such; docker digests or commit pins are the only "known" identities.
6. **Label experiments by shape, not by error code.** When summarizing, name
   what is sent and what differs — "fresh inputs + same already-signed outputs,
   via swap" — not the code we expect back.

If any step cannot be completed, the claim is downgraded to *unverified* in the
external text, or held. Silence about uncertainty is how test suites end up
arguing for things that aren't true.

---

# Ops addendum — infra-mutation rules (from the 2026-11-12 wrong-workdir incident)

Written after the vps-mint "ghost keyset" resolved to our own `config init`
silently targeting an abandoned mint in `$HOME` while we theorized for hours
about hidden history. Four links in that chain, four rules that break them:

1. **Target echo before mutation.** Before any command that reads-or-writes a
   named resource (mint DB, ledger, unit, volume), print the *resolved* target
   — absolute path, identity read FROM that target (pubkey/keysets/version) —
   and diff it against the pre-flight record. If the command has silent
   defaults (workdir, host, port, profile), the resolved value is the first
   thing to check, not the last. The migration guides' "record everything
   first" ritual IS this mechanism; recording without diffing is decoration.
2. **Attribution before explanation.** When an error names an identifier,
   grep the target for it *before theorizing*. If the target provably lacks
   the identifier → you are talking to the wrong target. (We ran the grep,
   got zero hits, and still spent hours on ghost theories.)
3. **Falsify before irreversible.** Any destructive/irreversible action
   justified by a diagnosis (fresh-ledger, wipe, reset, reseed) requires the
   minimal experiment that would falsify the diagnosis to have been run
   against a COPY first. The 10-minute "init the backup with the correct
   workdir" experiment existed; it just never ran before the decision.
4. **Second key for irreversibles.** Destructive actions get an independent
   premise-check by a second operator/agent (the same two-key rule the repo
   ruleset applies to merges). Single-operator momentum is how a wrong
   premise survives into an irreversible action.

Plus the standing rule the incident re-proved: a theory that survives without
reproduction for more than ~30 minutes gets its *assumptions* re-verified, not
its elaboration extended.
