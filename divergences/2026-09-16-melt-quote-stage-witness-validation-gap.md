# Pre-existing: melt-quote-stage witness validation gap (NUT-11/14)

Found 2026-09-16 post-PR1/PR2 conformance run; **NOT PR-induced** — identical
on nofeestestnut (pre-PR code, baseline run same day).

## Symptom
Melt quotes created with P2PK/HTLC-conditioned proofs that lack the required
witness (or carry the wrong key before locktime) return **200** at
quote-creation; the matrix expects rejection.

- melt_p2pk_unsigned_fails → 200
- melt_p2pk_sigall_unsigned_fails → 200
- melt_htlc_preimage_only_fails → 200
- melt_htlc_signature_only_fails → 200
- melt_p2pk_before_locktime_wrong_key_fails → 200

Also (testnut only): secret_encoding_entropy_trap_rejected — mint accepts an
entropy-blinded proof at the NUT-00 boundary (lenient verification).

## Attribution
Witness validation exists on the swap/spend path (ISSUE-030/031 fixed it
there); the **melt-quote creation stage** does not re-validate input proof
witnesses. Both CDK and Nutshell validate witnesses at melt input
(`MeltRequest` proof checks / `verify_witnesses` on spend inputs).

## Matrix environmental notes (signut)
`mint_tokens_after_quote`, the two `sigall_*_succeeds`, and
`concurrent_double_melt_rejected` fail on signut only because the matrix's
payment destinations are not payable on signet (real CLN → payment_failed →
quote PENDING). Not code defects; test-harness limitation.
