# cashu-shadow — Diffy-style cross-implementation audit framework (ISSUE-129)

One command runs the locked scenario corpus against any two Cashu mint
implementations — with cashu-cf either as a compared engine (miniflare)
or as the SHADOW proxy fronting the authoritative backend (proxy-faithful
passthrough asserted).

## Usage

```
# bring up reference mints (once per host):
bash ../../experiments/shadow-proxy-nutshell/setup-nutshell.sh &        # nutshell 0.20.3 :8737
/root/.cargo-target/release/cdk-mintd -w /root/.cdk-mintd &            # cdk 0.18.1     :8739

# cashu-cf bundle must exist:
cd $CASHU_CF && npx wrangler deploy --dry-run --outdir .tmp-wrangler-build --name miniflare-test --env ''

# run:
node run.mjs config.cf-ns.json          # cf engine vs nutshell (direct)
node run.mjs config.cf-ns-proxy.json    # + cashu-cf AS proxy over nutshell (faithfulness pass)
```

Config: `{ cashu_cf_root, backends: {A, B}, proxy }`; backend kinds:
`cf` (cashu-cf in miniflare) or `http` (any mint URL). Reports land in
`out/shadow-<ts>.{json,md}`.

## Corpus (the three-way-locked matrix, 2026-10-22..24 evidence)

Rejection identities (R4/R5/A1/A2/A3/A6b), DLEQ-verified minting (H1),
fee-aware swap + checkstate-SPENT (A7), happy melt + HTLC unlock + SIG_ALL
unlock (the canonical-message recipe: `concat(secret‖C)+quoteId`, schnorr
over sha256), mint-replay semantics. All wire knowledge lives in
`lib/wire.mjs` — witness-as-JSON-string, NUT-02 denomination splitting,
SIG_ALL message builder.

## Status (2026-10-27 initial port)

- 12/12 rows reproduce the study matrix on the framework (cf↔ns, incl.
  the merged keys-400 alignment showing live).
- Proxy-faithfulness pass: 3/3 OK against nutshell.
- Remaining increments (see ISSUE-129): cdk config preset, per-scenario
  dual-send faithfulness (not just the probe pass), drift-vs-last-run
  diffing, normalizer whitelist for metadata endpoints.

## Provenance

Ported from experiments/shadow-proxy-nutshell/proxy-study.mjs (the
2026-10-22..24 three-way study) — that experiment directory remains the
evidence archive; this package is the reusable instrument.

## Increment 2 (2026-10-27): cdk preset + second pair proven

`config.cf-cdk.json` — cf engine vs cdk 0.18.1 direct: full corpus green
through the framework, identities matching the locked three-way table
(cdk 422 strict malformed-Y, 10001/11007/20008 rejections, replay
200-parity with cf, all unlock paths PAID). The any-two-mints claim now
holds for two pairs: cf↔ns and cf↔cdk.
