#!/usr/bin/env python3
"""Cross-implementation, cross-version differential runner.

Stands up a matrix of mint arms — Docker Hub version tags, locally built
git refs, or already-running URLs — runs ab_probe_p2pk_htlc.py against all
of them in ONE pass, appends the result to the run registry
(conformance/runs/), and reports:

  1. the frozen-prediction check per arm (family-resolved),
  2. an INTRA-RUN version diff: arms of the same family (shared dash-less
     prefix, e.g. cdk-0.17.6 / cdk-0.18.0) compared cell by cell — this is
     "comparing versions across releases, branches, or commits",
  3. an INTER-RUN drift diff against the most recent prior registry entry
     (same arm names) — this is the automation for the silent-flip class
     we twice caught by hand (nutshell d1/d7/d8 between July and Sept;
     cdk d6 between 0.16.0 and 0.18.0).

Bring-up knowledge encoded here (learned the hard way, see
CROSS-IMPLEMENTATION-GUIDE sections 3-4 and AUTOMATED-CROSS-
IMPLEMENTATION-TESTING.md):
  - nutshell images have no ENTRYPOINT: command must be `poetry run mint`;
    env is MINT_BACKEND_BOLT11_SAT / MINT_LISTEN_HOST / MINT_LISTEN_PORT
    (NOT the older MINT_LIGHTNING_BACKEND/MINT_HOST/MINT_PORT names, which
    are silently ignored); MINT_RATE_LIMIT=FALSE unless you love 429s.
  - cashubtc/mintd (cdk) 0.18+ requires `config init --new-mint` from a
    TOML into a work-dir database before the daemon starts; the work dir
    must live under $HOME (colima only mounts the home directory).
  - Startup under x86_64 emulation can take ~3 min for nutshell; the
    readiness loop must be patient.
  - FakeWallet invoices never need payment; the house MintClient still
    tries an SSH bark payment — a failing-fast `ssh` shim is put on PATH
    for the probe subprocess.

Usage:
  python3 version_matrix.py                       # default 2-arm matrix
  python3 version_matrix.py \
    --docker-arm cdk-0.17.6=cdk:cashubtc/mintd:0.17.6 \
    --docker-arm cdk-0.18.0=cdk:cashubtc/mintd:0.18.0 \
    --docker-arm nutshell-0.20.2=nutshell:cashubtc/nutshell:0.20.2 \
    --docker-arm nutshell-0.20.3=nutshell:cashubtc/nutshell:0.20.3
  python3 version_matrix.py \
    --git-arm nutshell@8e19619=nutshell:../nutshell:8e19619   # experimental
  python3 version_matrix.py --url-arm remote=http://...       # no bring-up

Exit code 0 unless infrastructure fails; verdict flips are findings, not
errors.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS_DIR = HERE / "runs"
WORKROOT = Path.home() / "ab-matrix"
PROBE = HERE / "ab_probe_p2pk_htlc.py"
CDK_PORT = 3338  # both families listen on this INSIDE the container

NUTSHELL_TOML = None  # nutshell needs no config file
CDK_TOML = """[info]
url = "http://127.0.0.1:{url_port}/"
listen_host = "0.0.0.0"
listen_port = {cdk_port}
mnemonic = "env:AB_CDK_MNEMONIC"

[database]
engine = "sqlite"

[payment_backend]
backend = "fakewallet"

[onchain]
onchain_backend = "fakewallet"

[fake_wallet]
supported_units = ["sat"]
"""


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def fresh_hex_key() -> str:
    import secrets
    return secrets.token_hex(32)


def fresh_mnemonic() -> str:
    from mnemonic import Mnemonic
    return Mnemonic("english").generate(strength=256)


def wait_ready(url: str, timeout: int = 240) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/v1/info", timeout=3) as r:
                return json.load(r).get("version", "?")
        except Exception:
            time.sleep(5)
    raise TimeoutError(f"mint at {url} not ready after {timeout}s")


class Arm:
    def __init__(self, name: str, family: str):
        self.name = name
        self.family = family
        self.image: str | None = None
        self.git_spec: tuple[str, str] | None = None  # (repo_path, ref)
        self.url_spec: str | None = None
        self.port: int | None = None
        self.url: str | None = None
        self.container: str | None = None
        self.workdir: Path | None = None
        self.mnemonic: str | None = None
        self.identity: str | None = None

    def bring_up(self) -> None:
        if self.url_spec:
            self.url = self.url_spec
            self.identity = wait_ready(self.url)
            return
        if self.git_spec:
            self._build_from_git()
        self.port = free_port()
        if self.family == "nutshell":
            self._bring_up_nutshell()
        elif self.family == "cdk":
            self._bring_up_cdk()
        else:
            raise ValueError(f"unknown family {self.family!r}")
        self.url = f"http://127.0.0.1:{self.port}"
        self.identity = wait_ready(self.url)

    def _bring_up_nutshell(self) -> None:
        self.container = f"abm-{self.name}"
        sh(["docker", "run", "-d", "-p", f"{self.port}:{CDK_PORT}",
            "--name", self.container,
            "-e", "MINT_BACKEND_BOLT11_SAT=FakeWallet",
            "-e", "MINT_LISTEN_HOST=0.0.0.0",
            "-e", f"MINT_LISTEN_PORT={CDK_PORT}",
            "-e", "MINT_RATE_LIMIT=FALSE",
            "-e", f"MINT_PRIVATE_KEY={fresh_hex_key()}",
            self.image, "poetry", "run", "mint"])
        if not self._container_running():
            logs = sh(["docker", "logs", self.container]).stdout[-400:]
            raise RuntimeError(f"nutshell arm {self.name} exited: {logs}")

    def _bring_up_cdk(self) -> None:
        # 0.18+ split config into a database initialized from TOML
        # (`config init`); <=0.17.x reads env vars directly (the legacy
        # recipe from CROSS-IMPLEMENTATION-GUIDE that 0.18 broke — see
        # issues/cdk-config-split.md).
        if self._cdk_has_config_subcommand():
            self._bring_up_cdk_modern()
        else:
            self._bring_up_cdk_legacy()

    def _cdk_has_config_subcommand(self) -> bool:
        help_txt = sh(["docker", "run", "--rm", self.image,
                       "cdk-mintd", "--help"]).stdout
        return "config" in help_txt and "Commands:" in help_txt

    def _bring_up_cdk_modern(self) -> None:
        self.workdir = WORKROOT / self.name
        if self.workdir.exists():
            shutil.rmtree(self.workdir)
        self.workdir.mkdir(parents=True)
        self.mnemonic = fresh_mnemonic()
        (self.workdir / "config.toml").write_text(
            CDK_TOML.format(url_port=self.port, cdk_port=CDK_PORT))
        init = sh(["docker", "run", "--rm", "-v", f"{self.workdir}:/data",
                   "-e", f"AB_CDK_MNEMONIC={self.mnemonic}", self.image,
                   "cdk-mintd", "-w", "/data", "config", "init", "--new-mint",
                   "--file", "/data/config.toml"])
        if "Configuration initialized" not in init.stdout:
            raise RuntimeError(f"cdk config init failed for {self.name}: "
                               f"{init.stdout[-200:]} {init.stderr[-200:]}")
        self.container = f"abm-{self.name}"
        sh(["docker", "run", "-d", "-p", f"{self.port}:{CDK_PORT}",
            "--name", self.container, "-v", f"{self.workdir}:/data",
            "-e", f"AB_CDK_MNEMONIC={self.mnemonic}",
            self.image, "cdk-mintd", "-w", "/data"])

    def _bring_up_cdk_legacy(self) -> None:
        # 0.17.x env surface (enumerated from the binary: strings | grep
        # CDK_MINTD) — note CDK_MINTD_LN_BACKEND, not CDK_MINTD_BACKEND,
        # and LISTEN_HOST/LISTEN_PORT, not HOST/PORT.
        self.container = f"abm-{self.name}"
        sh(["docker", "run", "-d", "-p", f"{self.port}:{CDK_PORT}",
            "--name", self.container,
            "-e", "CDK_MINTD_LN_BACKEND=FakeWallet",
            "-e", "CDK_MINTD_FAKE_WALLET_SUPPORTED_UNITS=sat",
            "-e", "CDK_MINTD_LISTEN_HOST=0.0.0.0",
            "-e", f"CDK_MINTD_LISTEN_PORT={CDK_PORT}",
            "-e", f"CDK_MINTD_URL=http://127.0.0.1:{self.port}/",
            "-e", "CDK_MINTD_MINT_NAME=AB matrix arm",
            "-e", f"CDK_MINTD_MNEMONIC={fresh_mnemonic()}",
            self.image])
        if not self._container_running():
            logs = sh(["docker", "logs", self.container]).stdout[-400:]
            raise RuntimeError(f"cdk legacy arm {self.name} exited: {logs}")

    def _build_from_git(self) -> None:
        repo_path, ref = self.git_spec
        repo_path = str(Path(repo_path).expanduser().resolve())
        if not (Path(repo_path) / ".git").exists():
            raise ValueError(f"{repo_path} is not a git repo")
        sh(["git", "-C", repo_path, "fetch", "--all", "--quiet"])
        sh(["git", "-C", repo_path, "checkout", "--quiet", ref])
        head = sh(["git", "-C", repo_path, "rev-parse", "--short", "HEAD"]).stdout.strip()
        self.image = f"ab-matrix:{self.name}-{head}"
        build = sh(["docker", "build", "-t", self.image, repo_path],
                   timeout=2400)
        if build.returncode != 0:
            raise RuntimeError(f"docker build failed for {self.name}@{ref}: "
                               f"{build.stderr[-300:]}")

    def _container_running(self) -> bool:
        out = sh(["docker", "ps", "--filter", f"name={self.container}",
                  "--format", "{{.Names}}"]).stdout.strip()
        return out == self.container

    def tear_down(self) -> None:
        if self.container:
            sh(["docker", "rm", "-f", self.container])
        if self.workdir and self.workdir.exists():
            shutil.rmtree(self.workdir, ignore_errors=True)


def ssh_shim_dir() -> Path:
    # FakeWallet never needs bark payment; make the client's SSH attempt
    # fail instantly instead of burning ~5-10s per mint quote.
    d = Path("/tmp/opencode/fakebin")
    d.mkdir(parents=True, exist_ok=True)
    shim = d / "ssh"
    shim.write_text("#!/bin/sh\nexit 1\n")
    shim.chmod(0o755)
    return d


def run_probe(arms: list[Arm], out_path: Path, cells: str = "") -> int:
    cmd = [sys.executable, str(PROBE), "--out", str(out_path), "--pace", "3"]
    if cells:
        cmd += ["--cells", cells]
    for a in arms:
        cmd += ["--arm", f"{a.name}={a.url}"]
    env = dict(os.environ)
    env["PATH"] = f"{ssh_shim_dir()}:{env['PATH']}"
    proc = subprocess.run(cmd, cwd=HERE, env=env)
    return proc.returncode


def load_probe_results(out_path: Path) -> dict:
    return json.loads(out_path.read_text())


def cell_verdicts(results: dict, arm: str) -> dict[str, str]:
    return {c: d["verdict"] for c, d in results[arm]["cells"].items()}


def diff_cells(name_a: str, cells_a: dict, name_b: str, cells_b: dict) -> list[str]:
    lines = []
    for cell in sorted(set(cells_a) | set(cells_b)):
        va, vb = cells_a.get(cell, "-"), cells_b.get(cell, "-")
        if va != vb:
            lines.append(f"  FLIP {cell}: {name_a}={va}  {name_b}={vb}")
    return lines


def intra_run_diff(arms: list[Arm], results: dict) -> list[str]:
    families: dict[str, list[Arm]] = {}
    for a in arms:
        families.setdefault(a.family, []).append(a)
    lines = []
    for family, fam_arms in sorted(families.items()):
        if len(fam_arms) < 2 or any(a.name not in results for a in fam_arms):
            continue
        lines.append(f"[intra-run] family {family}:")
        for i in range(len(fam_arms) - 1):
            for j in range(i + 1, len(fam_arms)):
                a, b = fam_arms[i], fam_arms[j]
                flips = diff_cells(a.name, cell_verdicts(results, a.name),
                                   b.name, cell_verdicts(results, b.name))
                if flips:
                    lines.append(f"  {a.name} ({a.identity}) vs "
                                 f"{b.name} ({b.identity}):")
                    lines += flips
                else:
                    lines.append(f"  {a.name} vs {b.name}: no differences")
    return lines


def previous_registry_entry(current: Path) -> Path | None:
    entries = sorted(RUNS_DIR.glob("version-matrix-*.json"))
    entries = [e for e in entries if e != current]
    return entries[-1] if entries else None


def inter_run_diff(current: Path, results: dict) -> list[str]:
    prev_path = previous_registry_entry(current)
    if not prev_path:
        return ["[inter-run] no previous registry entry — baseline set"]
    prev = json.loads(prev_path.read_text())
    prev_results = prev.get("probe_results", {})
    lines = [f"[inter-run] vs {prev_path.name}:"]
    found = False
    for arm in results:
        if arm not in prev_results:
            continue
        flips = diff_cells(f"{arm}@prev", cell_verdicts(prev_results, arm),
                           f"{arm}@now", cell_verdicts(results, arm))
        if flips:
            found = True
            lines.append(f"  {arm} (was {prev_results[arm].get('identity')}"
                         f" -> now {results[arm].get('identity')}):")
            lines += flips
    if not found:
        lines.append("  no drift on shared arms")
    return lines


def markdown_report(arms: list[Arm], results: dict) -> str:
    cells = sorted({c for a in results for c in results[a]["cells"]})
    out = ["# Version matrix run", "",
           f"*{datetime.now(timezone.utc).isoformat(timespec='seconds')}*", "",
           "| cell | " + " | ".join(
               f"{a.name}<br>{a.identity}" for a in arms if a.name in results) + " |",
           "|---|" + "---|" * len(arms)]
    for cell in cells:
        row = [cell]
        for a in arms:
            if a.name in results:
                v = results[a.name]["cells"].get(cell, {}).get("verdict", "-")
                row.append(v)
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out) + "\n"


def parse_arm_spec(spec: str, kind: str) -> Arm:
    name, sep, rest = spec.partition("=")
    if not sep:
        raise ValueError(f"bad arm {spec!r}")
    family, _, tail = rest.partition(":")
    arm = Arm(name, family)
    if kind == "url":
        arm.url_spec = tail
    elif kind == "docker":
        arm.image = tail
    else:  # git
        repo, _, ref = tail.partition(":")
        arm.git_spec = (repo, ref or "main")
    return arm


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--docker-arm", action="append", default=[], metavar="NAME=family:image",
                        help="e.g. cdk-0.17.6=cdk:cashubtc/mintd:0.17.6")
    parser.add_argument("--git-arm", action="append", default=[], metavar="NAME=family:repo:ref",
                        help="experimental: build image from a git checkout, e.g. "
                             "nutshell@dev=nutshell:../nutshell:origin/main")
    parser.add_argument("--url-arm", action="append", default=[], metavar="NAME=url",
                        help="arm that is already running (no bring-up)")
    parser.add_argument("--cells", default="",
                        help="comma-separated probe cell names (passthrough)")
    parser.add_argument("--keep", action="store_true",
                        help="keep containers/workdirs up after the run")
    args = parser.parse_args()

    if not (args.docker_arm or args.git_arm or args.url_arm):
        args.docker_arm = ["cdk-0.18.0=cdk:cashubtc/mintd:0.18.0",
                           "nutshell-0.20.3=nutshell:cashubtc/nutshell:0.20.3"]

    arms: list[Arm] = []
    for spec in args.docker_arm:
        arms.append(parse_arm_spec(spec, "docker"))
    for spec in args.git_arm:
        arms.append(parse_arm_spec(spec, "git"))
    for spec in args.url_arm:
        arms.append(parse_arm_spec(spec, "url"))

    RUNS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    results: dict = {}
    try:
        for arm in arms:
            print(f"== bringing up {arm.name} "
                  f"({arm.image or arm.git_spec or arm.url_spec}) ...", flush=True)
            arm.bring_up()
            print(f"   {arm.name} ready: {arm.identity} @ {arm.url}", flush=True)
        probe_out = RUNS_DIR / f".probe-{ts}.json"
        code = run_probe(arms, probe_out, args.cells)
        if code not in (0, 1):  # 1 = prediction mismatch, still results
            print(f"probe failed hard (exit {code})", file=sys.stderr)
            return code
        results = load_probe_results(probe_out)
        probe_out.unlink()
    finally:
        if not args.keep:
            for arm in arms:
                arm.tear_down()
                print(f"   tore down {arm.name}", flush=True)

    entry = {
        "ts": ts,
        "arms": [{"name": a.name, "family": a.family, "image": a.image,
                  "git": list(a.git_spec) if a.git_spec else None,
                  "url": a.url, "identity": a.identity} for a in arms],
        "probe_results": results,
    }
    reg_path = RUNS_DIR / f"version-matrix-{ts}.json"
    reg_path.write_text(json.dumps(entry, indent=1))
    (RUNS_DIR / f"version-matrix-{ts}.md").write_text(markdown_report(arms, results))

    print(f"\nregistry -> {reg_path}")
    print("\n".join(intra_run_diff(arms, results)))
    print("\n".join(inter_run_diff(reg_path, results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
