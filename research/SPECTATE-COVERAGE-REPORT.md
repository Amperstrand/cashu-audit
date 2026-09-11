# greatspectations Coverage Report: NUT-10/11/14 Spec Gaps

*2026-09-11. Coverage tool: rustyrussell/greatspectations with `comment_marker = "NUT"`.
Fix for Python: add `comment_marker = "NUT"` to specquotes.toml (default is
uppercase source name = "NUTS" which doesn't match our comment style).
Fix for Rust: pass `--comment-start "// "` (default is `"# "` for Python).*

## Results

| Implementation | Covered | Gaps | Coverage rate |
|---|---|---|---|
| nutshell (spectate/main) | 9 | 6 | 60% |
| cdk (spectate/main) | 5 | 7 | 42% |

## The gap list (spec MUSTs not quoted by any implementation)

Both implementations share most gaps — these are the spec requirements
that NEITHER implementation has annotated (and may not implement):

| # | Spec line | Requirement | Risk if unimplemented |
|---|---|---|---|
| 1 | 11.md:58 | Message to sign MUST use **unescaped** secret string | Signature verification fails on properly-escaped JSON |
| 2 | 11.md:104 | Invalid sigflag values MUST be rejected | Malformed secrets accepted (d1 territory) |
| 3 | 11.md:130 | SIG_ALL inputs MUST have same Secret.data and Secret.tags | Mixed-condition SIG_ALL accepted |
| 4 | 11.md:133 | SIG_ALL: witness MUST be on first input only | Witness placement ambiguity |
| 5 | 11.md:264 | Public keys MUST use compressed format | Uncompressed keys accepted |
| 6 | 11.md:295 | Duplicate keys in pathway MUST be rejected | Duplicate keys accepted (d2 territory) |

**cdk additional gap** (not in nutshell):
| 7 | 11.md:266 | Each key MUST appear at most ONCE per pathway | Key counting semantics |

## What IS covered (quotes that match spec)

### nutshell (9 quotes)
- NUT-10 Caution: anyone-can-spend fallback
- NUT-11 duplicate tags MUST (×2 — the #358 MUSTs)
- NUT-11 n_sigs exceeds pool MUST
- NUT-11 pubkey x-coordinate comparison
- NUT-14 hash encoding (64-char hex)
- NUT-14 hash byte-equality verification
- NUT-14 Sender Pathway (refund signature)
- NUT-11 Schnorr non-deterministic counting

### cdk (5 quotes)
- NUT-11 duplicate tags MUST
- NUT-11 n_sigs exceeds pool MUST (×2 — in tag.rs and mod.rs)
- NUT-14 hash encoding
- NUT-14 Sender Pathway

## What this means

Both implementations cover the **nuts#358 MUSTs** (duplicate tags, n_sigs)
with spec quotes — the code is annotated and verifiable. But 6-7 other
MUSTs have NO quotes, meaning either:
1. The requirement is implemented but not annotated (add quotes)
2. The requirement is NOT implemented (add implementation + quotes)

The gap list directly supports the d2/d3 amendment: these are additional
MUSTs that should have vectors and be included in the "which requirements
are actually enforced" conversation.

## How to reproduce

```bash
# nutshell
cd ~/src/nutshell && git checkout spectate/main
greatspectate check --config specquotes.toml --coverage=/tmp/ns-cov \
  cashu/core/nuts/nut10.py cashu/mint/conditions.py
greatspectate coverage --config specquotes.toml --coverage /tmp/ns-cov --format text

# cdk
cd ~/src/cdk-spectate
greatspectate check --config specquotes.toml --coverage=/tmp/cdk-cov \
  --comment-start "// " \
  crates/cashu/src/nuts/nut10/tag.rs crates/cashu/src/nuts/nut10/mod.rs \
  crates/cashu/src/nuts/nut14/mod.rs
greatspectate coverage --config specquotes.toml --coverage /tmp/cdk-cov --format text
```

## Tool configuration notes

1. **Python marker fix**: default `comment_marker` is the source name
   uppercased (`nuts` → `NUTS`). Our comments use `NUT` (singular).
   Fix: `comment_marker = "NUT"` in specquotes.toml.

2. **Rust comment style**: default `--comment-start` is `"# "` (Python).
   Rust needs `--comment-start "// "`.

3. **Coverage file creation**: the `--coverage` flag on `check` writes a
   line-per-match file that `coverage` then annotates against the spec.
   Without it, the coverage report has no data.

4. **Continuation line trap**: any `#` comment immediately after a spec
   quote is appended to the quote text. Separate developer commentary
   from spec quotes with code, not comments.

## Postscript (2026-09-12): gaps converted to test vectors

The gap list above was converted to live enforcement probes — see
`MUST-GAP-VECTORS-RESULTS.md`. Verdict per gap: invalid-sigflag (V2)
violated by nutshell 0.18.2/0.19.0; SIG_ALL consistency (V3) enforced by
all; SIG_ALL message format (11.md:141) non-conformant in nutshell
0.16.5–0.20.2 and broken-multi-input in 0.20.3; compressed pubkeys (V5)
violated by all nutshell; duplicate keys (V6) regressed in nutshell
0.20.2/0.20.3. Coverage gaps and enforcement gaps overlap but are not
identical: annotated code can still regress (V6), and enforced code can
be non-conformant (SIG_ALL message).
