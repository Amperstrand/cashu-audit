# One-command reproduction (clean VM)

Any machine with docker (no other prerequisites — the vector runs inside
the nutshell image which ships coincurve):

```bash
./verify.sh                 # spawns stock cdk-mintd 0.17.6 (fakewallet) + runs the repro
./verify.sh <mint_url>      # or point at any running cdk/nutshell mint
```

Expected output on stock cdk (0.17.0/0.17.6/0.18.0/main):

```
witness sent: {"signatures": ["65a1..."]}
refund swap:  400 {"code":50000,"detail":"Secret is not a HTLC secret"}
VERDICT: REJECTED (stock cdk behavior)
```

On tolerant mints (nutshell >= 0.19, testnut) and on the fix branch
(Amperstrand/cdk htlc-refund-witness, built from source):

```
refund swap:  200 {"signatures":[{...
VERDICT: ACCEPTED (fix present / tolerant mint)
```

Files: `verify_htlc_refund.py` (self-contained single vector: quote →
blind-mint an HTLC-locked proof with past locktime + refund key → refund
swap with the wallet-natural signature-only witness). Verified against
all three targets on 2026-09-13.

For the fix branch: `git clone -b htlc-refund-witness
https://github.com/Amperstrand/cdk && cargo build --release -p cdk-mintd`,
then configure a fakewallet mint (see cdk-fix-data config in this
directory's git history or the cdk README) and run
`./verify.sh http://127.0.0.1:<port>`.
