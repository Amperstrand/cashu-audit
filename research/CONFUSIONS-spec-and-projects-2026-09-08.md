# Things that genuinely confused us — spec and established projects

Personal-hit evidence for each; candidates for spec clarifications and audit
dimensions. (Agent-authored after the NUT-00 campaign.)

## NUTs (spec-level confusions)

1. **NUT-00 secret encoding** — `x` is "a UTF-8-encoded random string" but
   `hash_to_curve(x: bytes)` takes bytes; the relationship lives implicitly in
   the Proof field description. THE campaign subject; MUST + vectors drafted.
2. **NUT-00 hash_to_curve algorithm versioning** — two algorithms in the wild
   (deprecated re-hash vs domain-separated counter); spec marks neither
   normative, says nothing about migrating tokens across the change. nutshell's
   permanent `verify_deprecated` shim is the scar tissue (our proxnet finding
   is live rot from exactly this).
3. **NUT-05/NUT-08 melt change outputs are BLANK** — wallets attach amounts to
   change outputs; mints ignore them and imprint their own decomposition BY
   INDEX. Spec doesn't state pairing semantics; Amethyst #3847 shipped a
   production bug on exactly this (discarded paid change, matched by amount).
   We independently re-learned it reading cdk's process_melt_change.
4. **Amount JSON serialization** — spec examples use `int`; cashu-ts v4
   serialized string amounts, cdk-mintd 0.17.6 expects integers → our very
   first melt failed with an opaque 50000 "Invalid payment request" (it was a
   string-vs-int serde mismatch). Interop drift the spec text doesn't pin.
5. **NUT-07 checkstate request shape** — cdk expects `{"Ys":[...]}`, cashu-ts
   sends `{"outputs":[...]}`; our first verify script failed with "missing
   field Ys". Documented cross-impl divergence with no spec arbiter.
6. **Error code registry is de facto per-implementation** — cdk 10001
   "Token not verified" vs cashu-cf 14005 "Proof verification failed" vs a
   generic 50000 for parse failures. Our scenario matcher needed a per-family
   pattern library.
7. **NUT-02 keyset id formats** — V1 short (`008e808b89acc141`, cashu-cf) vs
   V2 hex 33-byte (cdk 0.18) both live; v4 tokens CANNOT encode V1 ids
   (cashu-ts throws). Cross-mint token portability is silently bounded.
8. **"active" keyset flag conflates mintable and redeemable** — testnut showed
   two active keysets; one refused minting ("Invalid keyset ID in output").
   Hit directly during the scoping test; spec silent on the distinction.
9. **Interrupted-operation recovery is unspecified** — quotes PENDING/UNKNOWN,
   melts half-paid — every mint builds its own saga/recovery machinery (cdk's
   entire melt_saga + start_up_check subsystem; cashu-cf's ISSUE-103 incident
   class). The biggest underspecified area after encoding.

## Established projects (codebase-level confusions)

1. **cashu-ts `blindMessage(secret: Uint8Array)`** — the footgun; JSDoc says
   "A UTF-8 byte encoded string" and the type says bytes. Campaign subject.
2. **cashu-ts API churn** — five majors; our high-level melt hit
   `AmountError: Unsupported amount input type` on v5-rc; examples in the
   wild target different majors. Version pinning is mandatory reading.
3. **cdk's split config system** — legacy TOML+env loader vs DB-backed
   config-service; **env vars silently don't apply on the DB path** (we
   debugged this for real: CDK_MINTD_LEGACY_ENCODING_KEYSETS did nothing).
   Config precedence is documented as "env wins" but only on one path.
4. **cdk "Invalid payment request" (50000)** for serde failures — parse
   errors and semantic errors share an opaque code.
5. **cashu-cf `secretToBytes` docstring was factually inverted** ("cashu-ts
   compatible" describing the opposite). A lying docstring is worse than none.
6. **Compat-shim ordering divergence** — nutshell verifies new-hash-first
   then deprecated; the archived lnbits fork did the reverse. Same shim,
   different order, no spec guidance.
