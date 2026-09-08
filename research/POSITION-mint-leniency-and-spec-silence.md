# Position discussion: mint leniency, spec silence, and who owns the bug

**Venue rule:** this file is where Amperstrand argues in full (verbose, no
character limits). Upstream artifacts (issues, PRs) link here and stay short.

## The claim under debate

> "Those wallets weren't buggy. They just didn't do the thing because the spec
> says SHOULD, not MUST — arguably the mint being overly strict IS the bug.
> Mints should allow this spend path until the spec changes to a MUST."

## Steelman (we find this substantially correct)

1. **The spec is silent, not permissive-by-accident.** Stock NUT-00 attaches
   no RFC-2119 force to the verification derivation. Its only normative
   language is about token serialization. A wallet author in 2022–2025 reading
   `hash_to_curve(x: bytes)` next to "random string" and choosing to hash 32
   random bytes was making a *permitted reading of an ambiguous document* —
   not violating anything. Calling those wallets "buggy" conflates
   *interoperability outcome* with *conformance*. We retire the word.
2. **The mint signed it.** Every entropy-bound token was minted through a paid
   quote; `C_ = k·B_` is a real issuance the mint performed. A strict mint
   refusing its own signature over a representational detail the spec never
   pinned is, from the holder's chair, the deviating party. The debt-honoring
   argument for leniency is strong and we accept it as the operating default
   for real mints with issued balances (this is what cashu-cf now runs).
3. **Ambiguity is a spec defect first.** Multiple independent implementers
   diverged — by the "when implementations disagree, the spec failed" rule,
   the primary bug lives in the document, and every party downstream
   (divergent wallets, strict mints, lenient mints) is choosing a coping
   strategy, not causing the harm.

## Counterweight (where the claim overreaches)

1. **"The mint is the bug" inverts cause and effect for the *outcome*.** The
   entropy reading produces money whose validity is mint-dependent — an
   outcome no wallet author would choose knowingly. Whichever mint the token
   reaches that disagrees, loses. Leniency doesn't remove that defect; it
   relocates it to the next strict mint, later, after commitment. Fairness to
   the wallet author is not the same as safety for the holder.
2. **Postel's law's documented cost.** "Liberal in what you accept" famously
   freezes ambiguity: nothing breaks loudly, so the spec never gets fixed, and
   every new implementation (increasingly: every LLM-generated client)
   re-rolls the dice forever. "Allow it until the spec says MUST" removes the
   ecosystem's only incentive to ever write the MUST. Strict mints are the
   pressure that canonicalization requires.
3. **A mint is not a message receiver.** It is a counterparty defining what
   money *is* on its ledger. Uniform validity across mints is the product.
   Leniency mints a currency that looks identical but isn't — an externality
   billed to whoever is strict next.

## Our position (what we shipped, and why it satisfies both halves)

- **Transition rule:** lenient by default, with telemetry
  (`hexDecodeMatch`), honoring everything the mint signed. The user's
  principle holds operationally — until the spec speaks, spend paths stay
  open. ✔ the claim.
- **Terminal state:** keyset-scoped. At the next keyset rotation, legacy
  derivations are honored only under old keysets; new keysets verify
  strictly; leniency self-retires as keysets drain. When our nuts PR lands
  (wallet-side MUST + vectors + negatives), the clock this implies starts
  formally. ✘ "strict mints are the bug" as a terminal claim.
- **Note on our nuts PR:** the MUST we propose binds WALLETS (what to hash),
  deliberately not mints (what to accept). Mint-side leniency remains
  spec-legal even after it merges — the user's principle is not violated by
  the change we're proposing; it's given a clean boundary.

## Prediction: what upstream will actually do

- **cdk / nutshell verification stays strict.** They are the reference
  enforcement and their unit tests already pin the utf8 convention. They will
  take vectors, possibly the log-only sensor; per-keyset leniency as an
  *operator config* has a real chance (fits cdk-mintd's config surface and
  they already ship keyset rotation) — that is the concession to extract.
- **nuts wallet-side MUST + aligned vectors: likely accepted.** It changes no
  reference implementation's behavior — the vectors are their own unit tests.
- **A mint-side "MUST NOT accept alternates": unlikely to be adopted**, and we
  won't propose it. Operator freedom is the community default.
- **Likely terminal state:** wallets MUST (new code correct), mints MAY honor
  legacy derivations (documented practice), vectors + negatives everywhere.
  Our keyset-scoped design becomes the best-practice template for honoring
  legacy debt without permanent masking.

## Engagement plan

Host the argument here. When filing upstream: lead with shared facts
(repro + matrix + vectors), state the leniency position in two sentences,
link this file for the full reasoning. Never argue spec philosophy in a
GitHub issue body — link it.

## Refinement (2026-09-08, after review): duty follows issuance, not the spec

Two sharpenings make the argument durable against the obvious rebuttal
("the spec literally says Bob checks k·H(utf8(x))"):

1. **The spec describes, it does not oblige.** NUT-00's verification line is
   part of a descriptive protocol walkthrough — no RFC-2119 keyword attaches
   to it, for wallets OR mints. "The spec targets wallets not mints" is
   therefore slightly overclaimed; the accurate form is: the spec defines a
   canonical form and assigns obligation to nobody. Obligations that do not
   exist cannot be enforced retroactively against issued value.
2. **The honoring duty comes from issuance, not from the spec.** The mint
   signed these exact B_ against paid quotes. Both derivations yield
   deterministic, unforgeable signatures the mint can verify at negligible
   cost. Refusing one is a choice with a holder cost, made after the value
   changed hands. Whatever the spec says, the mint's own signature is the
   claim it must honor.

**Corollary (governance principle):** spec tightening MUST be prospective
over keysets. A wallet-side MUST changes what new outputs must look like; it
cannot void claims under keysets already issued while a divergent-but-
unforbidden interpretation was live. Keyset rotation is therefore the
enforcement mechanism: old keysets honor the lenient interpretation, new
keysets verify strictly, and the boundary is objective (the keyset id),
auditable (fallback-use telemetry), and self-retiring.

**Engineering consequence:** the reference mints need an optional, per-keyset
lenient mode — default off for new keysets, allowlisted for legacy ones, with
a log-only sensor so operators can find affected keysets. Implementation
tracked on our forks: cdk `nut00-per-keyset-leniency` (this work), cashu-cf
shipped (`nut00-strict-v2` → main), nutshell to follow if adopted in
discussion.
