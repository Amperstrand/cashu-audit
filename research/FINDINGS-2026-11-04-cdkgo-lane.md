# cdk-go lane check — tbmg #1190 pin vs upstream, #1149 retire-gate (2026-11-04)

Audit #68 item D. **Flag-only lane check** — drift reported, nothing
changed, nothing filed. "tbmg" = `OpenTollGate/tollgate-module-basic-go`.

## Upstream state (cashubtc/cdk-go, measured 2026-11-04)

Stable line: v0.18.0 → v0.18.1 (2026-09-18) → v0.18.2 (2026-10-14) →
**v0.18.3 (2026-10-29, latest)**. The v0.18.3 release notes advertise
only a CI cleanup (PR #17) — **no runtime fix is mentioned**, yet the
Amperstrand differential (recorded on #1149, two architectures: x86_64
host + aarch64 QEMU) shows upstream **v0.18.2 natives still drop-panic
(240 tokio drop-panics / 120 cycles) while v0.18.3 → 0**. The FFI
RuntimeGuard-class fix therefore rode along silently via rebuilt
natives; no upstream cdk-go PR/issue matches "RuntimeGuard"/"leak"/
"Drop"/"runtime leak" searches. All retirement-relevant evidence lives
on the Amperstrand side.

## tbmg #1190 (cdk_wallet build fix) — pin drift flag

- #1190 (OPEN, created 2026-11-03, stacked on #1137 `cdk-migration`)
  bumps cdk-go **v0.17.3 → v0.18.2** in all four carriers to make the
  `cdk_wallet`-tagged build compile; `cdk_static.go.mod` deliberately
  stays v0.17.3 (bench lane, local replace — reasoned, not drift).
- **Flag**: #1190 was created *after* v0.18.3 shipped, and pins the one
  stable release whose natives **still carry the drop-panic defect**
  per the org's own differential. The `research/upstream-cdkgo-0183-
  slice` branch (@ `9ffccbe8`, #1149 comment) already demonstrates
  upstream v0.18.3 is API-compatible for the used surface (adapter
  builds clean, WalletPort parity 5/5, tagged suite green). Pinning
  v0.18.2 makes the tagged lane compile but lands it on the known-bad
  natives; v0.18.3 is the evidenced better pin. Owner call — reported,
  not changed.

## #1149 (fork-retire tracking) — gate surface

Retire-when: upstream ships a release whose natives include the runtime
fix. Status per the tracking thread:

- **Met (evidence-wise)**: upstream v0.18.3 differential (0 panics,
  both archs); `research/upstream-cdkgo-0183-slice` removes the
  `Amperstrand/cdk-go` replace and passes parity + suite on v0.18.3.
- **Still open**: the #2788 acceptance-suite rerun (EOF-symptom class),
  armv7, physical-aarch64 confirmation — i.e. the real retire PR is
  gated on remaining acceptance work, not on upstream availability.
- **Not riding along**: the `mips-ffi` replace — upstream natives are a
  footprint no-go for 16 MB flash (33.5 MB `.so`); that lane's
  sidecar-vs-static decision is queue item 3, toolchain-blocked.
- Process note from the thread: `Amperstrand/tollgate-module-basic-go`
  is archived (read-only); research branches belong on `origin` under
  the `.pr-branch` marker protocol.

## Honesty

- All facts above are from the two tbmg threads, branch inspection
  (`main` and `cdk-migration` both pin cdk-go v0.17.3 in
  `src/tollwallet/go.mod` as of today), upstream release metadata, and
  upstream PR/issue search. No local build or test was run for this
  item; the v0.18.3-natives-clean claim is Amperstrand's differential,
  not independently reproduced here.
