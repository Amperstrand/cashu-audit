# nutshell #1100 bisect — pinning the 0.20.2→0.20.3 fix commit

Date: 2026-09-28 · Task: pin the commit that fixed cashubtc/nutshell #1100
(SIG_ALL + expired locktime drops primary spending pathway) within
`0.20.2..0.20.3`. Frozen predictions in `/tmp/opencode/issue1100/PREDICTIONS.txt`
(written before any probe run).

## TL;DR

The only commit in the window that changes any SIG_ALL-relevant code — and the
exact empirical behavioral boundary — is:

```
14762bd354772b25a75ca32d213e8526a5eda61c
extend and refactor nut11 sig_all message aggregation (#811)
callebtc, 2026-07-08 13:33:30 +0300
```

The "fix" **is** the SIG_ALL message-format flip (legacy `secrets ∥ B_` →
spec `secret∥C ∥ amount∥B_`); there is **no separate pathway-logic change
anywhere in the window**. Additionally, the claimed ≤0.20.2 mint-level
primary-pathway drop **does not reproduce on the 0.20.2 release tag** with a
format-matched probe (details in §5) — the primary/refund asymmetry recorded
on 2026-09-27 is most consistent with a probe format-mode artifact.

## 1. Window survey (git)

- `~/src/nutshell` was a **shallow** clone: `git log --oneline 0.20.2..0.20.3`
  initially showed **1 commit** (grafting artifact). After
  `git fetch origin --unshallow --tags`: **118 commits** in the window
  (0.20.2 = `19e86e6` 2026-07-03, 0.20.3 = `1853902` 2026-07-22).
- Commits touching the SIG_ALL / NUT-11 / conditions machinery in
  `0.20.2..0.20.3`:
  - `cashu/mint/conditions.py`: **only `14762bd`**
  - `cashu/core/nuts/nut11.py`: **only `14762bd`** (file created there)
  - `cashu/mint/verification.py`, `cashu/core/p2pk.py`,
    `cashu/core/secret.py`, `cashu/core/crypto/secp.py`: **untouched**
- `14762bd` touches: `cashu/core/nuts/nut11.py` (+17, new
  `sigall_message_to_sign()`), `cashu/mint/conditions.py` (SIG_ALL default
  message → `nut11.sigall_message_to_sign`), `cashu/mint/ledger.py` (melt
  SIG_ALL message → same helper), `cashu/wallet/p2pk.py` (same flip,
  wallet-side), plus official NUT-11 test vectors (+427) and conditions tests.
- `git diff 0.20.2 0.20.3 -- cashu/mint/conditions.py` equals exactly the
  `14762bd` hunk: import shuffle + message construction. **No key-set,
  locktime, or main/refund path-selection logic changed in the window.**
- Parent `14762bd^` = `b2f39fac2d1363cb4c10f273e530bbaffe74ced5`
  (2026-07-07). Seven commits sit between the 0.20.2 tag and `b2f39fa`;
  among the spend-flow files only `ledger.py` changed (`84d396e` MeltQuote
  `paid` field, `6e9c22c` quote `method` field — melt-quote plumbing, not
  swap/P2PK verification), and `base.py` changed only in MeltQuote/Keysets
  models (Proof/P2PKWitness untouched, checked by targeted diff).
  `conditions.py`, `verification.py`, `core/p2pk.py`, `core/crypto/secp.py`
  are byte-identical to 0.20.2 — and L1b tests the 0.20.2 tag directly
  anyway, so the bridge does not rest on code equivalence.

## 2. Empirical evidence

Mints: exact-commit local builds (see §6 for why not zoo deploys), FakeWallet
backend, `127.0.0.1:4411/4412`. Probe: the #1100 discriminators with the
message mode **forced** per run (auto-detect disabled — see §5). SIG_ALL
secret: `locktime = now-10`, `refund_keys=[rk]`, `n_sigs_refund=1`,
`sigflag=SIG_ALL`; PRIMARY = sig by main key, REFUND = sig by refund key.
Every cell is a real `/v1/swap` round trip (mint quote → mint → swap to P2PK
→ attempted spend).

| # | Code under test        | Commit    | Probe mode | PRIMARY | REFUND | Verdict |
|---|------------------------|-----------|------------|---------|--------|---------|
| L1a | `14762bd^` (pre-flip) | `b2f39fa` | legacy     | **200** | 200    | both pathways work |
| L1a-rerun | `14762bd^`       | `b2f39fa` | legacy     | **200** | 200    | stable, no flake |
| L1b | 0.20.2 **release tag**| `19e86e6` | legacy     | **200** | 200    | no pathway drop at mint level |
| L2  | `14762bd^`            | `b2f39fa` | standard   | 400 `0 < 1` | 400 `0 < 1` | format mismatch — **symmetric** |
| F1  | flip commit           | `14762bd` | standard   | **200** | 200    | both pathways work |
| F2  | flip commit           | `14762bd` | legacy     | 400 `0 < 1` | 400 `0 < 1` | format flipped **at this commit** — symmetric |
| X1  | 0.20.3 tag (standing zoo mint `ns-1853902`, :4187) | `1853902` | standard | **200** | 200 | fixed-side anchor confirmed |
| S1a | `14762bd^`            | `b2f39fa` | SIG_INPUTS (sig over each secret) | **200** | 200 | SIG_INPUTS primary pathway intact |
| S1b | flip commit           | `14762bd` | SIG_INPUTS | **200** | 200    | intact |

Mint stderr on every 400 (e.g. `logs/fix.log`):
`ERROR | CashuError: signature threshold not met. 0 < 1.` (code 11000) —
raised from `_verify_p2pk_signatures` after both main and refund legs fail.

Acceptance boundary within the window is exactly `14762bd`: everything at or
after it speaks the spec message (accepts standard, rejects legacy);
everything before it speaks legacy (accepts legacy, rejects standard). Both
sides accept **both** primary and refund legs when the probe speaks their
format.

## 3. Answers

**Fixing commit:** `14762bd354772b25a75ca32d213e8526a5eda61c` — "extend and
refactor nut11 sig_all message aggregation (#811)". Unique candidate by
file-level survey (§1); unique behavioral boundary empirically (§2).

**Did the fix ride with the format flip?** Yes — they are the same thing.
The entire mint-side delta in the window is the SIG_ALL message construction
(legacy → spec). No commit in `0.20.2..0.20.3` alters main/refund key-set
selection or locktime gating. Anyone who was signing the spec message (or a
wallet built against the new format) starts passing at exactly `14762bd`;
anyone signing legacy stops passing at exactly `14762bd`.

**Does legacy-era code drop primary for SIG_INPUTS too?** No. SIG_INPUTS
primary spend after locktime expiry is accepted (200) on `b2f39fa`
(pre-flip). SIG_INPUTS signs each input's own secret, which never changed
format — no drop, before or after the flip.

## 4. Frozen predictions vs outcomes

| Prediction | Outcome |
|---|---|
| L1 bug present (primary 400 / refund 200) | **WRONG** — primary 200 (both `b2f39fa` and the 0.20.2 tag) |
| L2 standard-on-legacy: both 400 | correct |
| F1 fixed (primary 200 standard) | correct |
| F2 both 400 legacy | correct |
| S1 SIG_INPUTS primary 200 | correct |
| X1 0.20.3 primary 200 | correct |

The one wrong prediction is the load-bearing surprise of this run and is
 interrogated in §5, not explained away.

## 5. Discrepancy vs the 2026-09-27 context

The handoff context states: "on nutshell <=0.20.2 … PRIMARY after locktime
expiry returned 400 'signature threshold not met. 0 < 1' while the REFUND key
worked (200)". My matrix cannot reproduce that **as mint behavior**:

- On the 0.20.2 release tag with a legacy-format probe: primary **200**,
  refund 200 (L1b).
- Format mismatches are **symmetric**: standard message against a legacy mint
  fails both legs with `0 < 1` (L2); legacy message against a spec mint fails
  both legs (F2). The mint code (read at both revisions) is symmetric between
  main and refund legs — same `message_to_sign`, same
  `_verify_p2pk_signatures`, main leg tried first, refund leg after locktime.
- Both halves of the 09-27 observation reproduce exactly under **cross-mode**
  conditions: a primary leg signing the *standard* message against the
  legacy mint → 400 `0 < 1`; a refund leg signing the *legacy* message → 200.
  That is a harness format-mode artifact (one leg forced/auto-set standard,
  the other legacy), not mint code. The v2 discriminator's own docstring
  documents precisely this class of probe bug ("ProofBuilder.__init__ auto-
  sets 'legacy' for any nutshell version string… we re-set mode AFTER builder
  construction"); the mirror-image mistake against ≤0.20.2 mints (forcing
  standard, or a stale per-URL mode-cache entry between legs) yields the
  recorded asymmetry.

Caveat, stated plainly: I could not inspect the 09-27 harness state, so
"cross-mode artifact" is the best-supported explanation, not a proven one.
What is proven: (a) no ≤0.20.2 mint-level primary drop with format-matched
probes; (b) the only code delta in the window is the format flip; (c) the
fixed-by-0.20.3 observation in standard mode holds (X1). If #1100's
reporter saw the asymmetry through a *wallet* flow on ≤0.20.2 against a
0.20.3-format counterparty (or vice versa), both legs would fail
symmetrically — so the issue's premise at mint level deserves re-verification
before any upstream contribution. Per registry rules: nothing posted, nothing
drafted for posting from this file.

## 6. Method deviation: local mints instead of zoo deploys (and why)

`./zoo-ctl deploy ns <sha>` was **blocked by the disk sentry**
(`/tmp/opencode/disk-sentry.status` = ALERT; root fs 95 % ≥ 85 % gate;
zoo-ctl exits 76, "deploy later"). Cause is chronic, not task-induced:
`~/.local/share/opencode/` holds a 58 GB session DB + 16 GB WAL — not
touchable. The sentry's own suggested fixes (docker builder prune, journal
vacuum, volume prune) free ≲1 GB of the ~20 GB needed to clear 85 %; I ran
nothing destructive and did **not** bypass the gate.

Substitute: exact-commit ephemeral mints built locally —
`git worktree` at each SHA → venv → `pip install <worktree>` →
`python -m cashu.mint` with `MINT_BACKEND_BOLT11_SAT=FakeWallet`,
`MINT_LISTEN_{HOST,PORT}=127.0.0.1:{4411,4412}`, per-mint throwaway
`MINT_PRIVATE_KEY`. Two pins were needed because pip resolved newer
deps than poetry.lock (marshmallow 3.25.1, limits 4.0.1 — the lock's
versions). This honors every hard constraint: read-only GitHub, ≤2
concurrent ephemeral mints (peak: 2), no tracked files modified in
cashu-audit or cashu-mint-zoo, and identical evidence quality (exact
commit source; direct port; full stderr). FakeWallet needs no Lightning
(the probe mints via instantly-paid dummy quotes; only /v1/swap is
exercised).

## 7. Reaping ledger (all ephemeral mints)

| Ephemeral | Commit | Port | Started | Reaped |
|---|---|---|---|---|
| local venv mint "pre" | `b2f39fa` | 4411 | 2026-09-28 08:57 | stopped (pid 3017562), venv+data+key deleted |
| local venv mint "fix" | `14762bd` | 4412 | 2026-09-28 08:57 | stopped (pid 3017565), venv+data+key deleted |
| local venv mint "tag" | `19e86e6` (0.20.2) | 4412 | 2026-09-28 09:06 | stopped (pid 3033539), venv+data+key deleted |

Post-reap verification: ports 4411/4412 closed; no `cashu.mint` processes of
mine remain; `git worktree list` shows only the main nutshell checkout;
zoo standing mints (cdk-4312959/a056e0f/d3dec24, ns-1853902, ns-a974914)
untouched and healthy; no zoo deploy was ever attempted past the gate
(it fails before any side effect). Foreign host mints (pids 617049/617232,
not started by this session) left alone.

## 8. Raw artifacts

Kept under `/tmp/opencode/issue1100/`: `PREDICTIONS.txt` (frozen),
`disc_legacy.py`, `disc_standard.py`, `disc_siginputs.py`,
`disc_legacy_tag.py` (mode-forced probe copies), `logs/{pre,fix,tag}.log`
(full mint-side request logs incl. the `0 < 1` error lines),
`start-mint.sh`/`stop-mint.sh`. The probe edits were made to copies; the
originals in `/tmp/opencode/issue1100_discriminator{,_v2}.py` were not
modified.
