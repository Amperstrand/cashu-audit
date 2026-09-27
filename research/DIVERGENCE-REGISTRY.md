# DIVERGENCE REGISTRY — our findings ↔ upstream venues

*The map that prevents noisy contributions: what upstream already
knows vs. what we hold that is new. Read before drafting any upstream
contribution; update after any venue research. Method: research prior
PRs/issues FIRST (AGENTS.md rule 1).*

## Open venues

| Venue | What it tracks | What it already says | What we hold that is NEW |
|---|---|---|---|
| **cashubtc/cdk#2252** (open, callebtc; **our comment posted 2026-09-13**: https://github.com/cashubtc/cdk/issues/2252#issuecomment-5645490705 — items 5+6+8) | NUT-10/11/14 divergences cdk↔nutshell, for per-item equalization | Item 6 = HTLC refund signatures-only witness: cdk rejects (`verify_htlc` → `IncorrectWitnessKind`), nutshell accepts (optional preimage), SIG_ALL mode accepts on cdk. Item 5 = HTLC hash case: "cdk accepts mixed/upper; nutshell requires lowercase." **Both items UNDECIDED.** | (a) both wallet families' live emissions are wire-captured (nutshell: `null`; cashu-ts: omitted) — deployed wallets cannot spend HTLC refunds on any cdk release; (b) regression window 0.16.0→0.17.0 (silent); (c) why suites can't see it (in-tree `add_preimage("")` workaround; checker built on cdk); (d) design trap: optional `preimage` breaks P2PK (untagged enum ordering); (e) delay-to-signal proposal. Item 5 NEW: (a) spec self-split — prose (14.md:86,88) lowercase vs normative formula (14.md:93) digest-compare via case-insensitive hex_to_bytes; (b) measured: nutshell mints 0.16.5–0.20.3 ACCEPT uppercase data + valid preimage (digest compare, same as cdk) — mint-layer divergence may be nil. **Draft v3.1 staged (items 5+6+8).** Item 8 NEW: released nutshell flipped — 0.16.5 accepts+ignores witness-on-plain; 0.18.2–0.20.3 reject (11000 "witness data not allowed"); #1008-branch accept restores 0.16.5-era behavior. |
| cashubtc/nutshell#1009 + PR #1008 | NUT-10 problems mostly SIG_ALL (nutshell side); refactor wave following CDK architecture | 20/58 checker failures enumerated; #1008 open error-handling question ("reject and log? what error?") | Our answer to their open question = the soft-failure pattern (staged nostr post, unlinked). F5 crash data on 0.20.3 if ever relevant. |

## Other open issues (assessed 2026-09-13, not venues for us)

| Venue | Why not |
|---|---|
| cashubtc/nutshell#1100 | Ours (Amperstrand, 2026-07-28): SIG_ALL + locktime drops primary pathway. **CLOSED 2026-09-18 by ye0man** (comment 5730580588: "appears to be fixed already in #1008, issue was never linked… please let me know if I'm mistaken"). **Measured 2026-09-27** (zoo ns-1853902 + ns-a974914, discriminator primary/refund × standard message): NOT reproducible on released 0.20.3 **or** 0.21.0 — primary-after-expiry accepted on both, refund too. Original repro was the ≤0.20.2 legacy-message path (refund 200 / primary `0 < 1`); already gone in 0.20.3, which **predates #1008's merge (2026-08-11)** → fix window is 0.20.2→0.20.3 (SIG_ALL format-flip release), not #1008. cashu-cf side fixed by 2026-07-30 (testnut all-green). Close is correct; only the attribution is off. **Replied 2026-09-27: https://github.com/cashubtc/nutshell/issues/1100#issuecomment-5856212690** ("not mistaken — confirmed fixed" + the 0.20.2→0.20.3 window fact; owner-approved, posted as Amperstrand). Follow-ups tabled: audit#37 (probe fix), audit#38 (0.20.3/0.21.0 re-run + must-gap on 0.21.0), audit#39 (fix-window bisect). **Probe caveat discovered:** conformance `ProofBuilder.__init__` force-sets legacy SIG_ALL mode for any "nutshell" version string → all suite SIG_ALL scenarios sign the legacy message against ≥0.20.3 mints and fail with `0 < 1` regardless of mint behavior. Any historical suite SIG_ALL FAIL on nutshell ≥0.20.3 is probe-poisoned; must-gap raw-protocol drivers unaffected. |
| cashubtc/nutshell#1126 | robwoodgate: are #1008's changed P2PK error codes intentional? nutshell-scoped; our cdk error-misdirection point adjacent, not additive. |
| cashubtc/nuts#431 | locktime == now boundary undefined — we hold no boundary-exact data (vectors used ±1000s). |
| cashubtc/nuts#319 | SIG_ALL multi-party — relevant only if a message-format item opens. |

## Resolved / historical precedent

| Venue | Outcome | Relevance |
|---|---|---|
| cashubtc/nutshell#848 + PR #803 | Fixed: "NUT-14 HTLC refund path incorrectly requires preimage (spec violation)" | The nutshell-side mirror of cdk item 6, already adjudicated as a bug. Precedent for the equalization direction. (Maps to our F7 restoration in 0.19.0.) |
| cashubtc/nuts#315 (merged 2026-01-08) | "New P2PK/HTLC rules" — Sender Pathway = signatures per NUT-11 Refund MultiSig; no preimage | The pathway text cdk's required-`preimage` type contradicts. Do not file anything new here; cite it. |
| cashubtc/nuts#302 (SIG_ALL legacy context) | Referenced by #1009 | Context for the SIG_ALL message family (our F5/F11). |

## Known blind spots (do not re-litigate)

- **SatsAndSports nut-10-checker**: built on CDK → wallet side always
  emits preimage-ful witnesses → cannot test wallet-natural shapes.
  Its "CDK 58/58" is consistent with our findings. Self-described
  obsolete (pre-SIG_ALL-update). Not a venue; a documented limitation.
- Dev calls: cashubtc/dev-calls repo, minutes under Chatham House
  rule; published minutes lag (last: 2025-12-18). Announcement posts
  on nostr (Cashu npub). Research venue only.

## Rules of engagement

See AGENTS.md "Upstream contribution protocol". Short version: add a
new fact or stay silent; no self-narration; no offers; draft → owner
approval → post.

## Watches standing (ai-legion crontab)

- `43 8 * * * ~/bin/watch-upstream-threads.sh` — daily comment-count on
  cdk#2252 (known: 1, ours) and nutshell#1100 (known: 0); a `CHANGE`
  line in `~/watch-upstream.log` means someone replied — read the
  thread before any further upstream action.
- `17 3 * * * ~/bin/must-gap-nightly.sh` — 17-vector drift detection.
