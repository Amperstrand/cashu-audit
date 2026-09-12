#!/usr/bin/env python3
"""wallet x mint interop matrix runner.

Reads matrix.yml (declarative: mints / wallets / flows), brings mint arms
up on a docker network, runs each wallet-driver container against each mint
for each flow with the QIR env-var/exit-code contract (0 PASS, 1 FAIL,
127 UNSUPPORTED/SKIP), collects per-cell artifacts (output.txt, wire.ndjson,
result.json) and emits grid.json + grid.md + status.json + DONE. Designed
to run detached (nohup/systemd-run) — collect later, zero babysitting.
"""
from __future__ import annotations
import base64, json, os, secrets, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime


def shlex_quote(x: str) -> str:
    import shlex; return shlex.quote(x)
from pathlib import Path

try:
    import yaml
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "pyyaml", "mnemonic"], check=False)
    import yaml

HERE = Path(__file__).resolve().parent
from debugger import CellDebugger
from cln_autopayer import CLNAutoPayer
ART = HERE / "artifacts"
RUN = None  # set in main


def _gw_dns() -> list[str]:
    # containers on ai-legion cannot reach public DNS directly (EAI_AGAIN);
    # the LAN gateway resolves. No-op where docker already works (macOS).
    import subprocess as _sp
    r = _sp.run(["ip", "route"], capture_output=True, text=True, timeout=10)
    for line in r.stdout.splitlines():
        if line.startswith("default via "):
            return ["--dns", line.split()[2]]
    return []


DNS = _gw_dns()


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def log(msg: str):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    (ART / "runner.log").parent.mkdir(parents=True, exist_ok=True)
    with open(ART / "runner.log", "a") as f:
        f.write(line + "\n")


def free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_ready(url: str, timeout: int = 300) -> str:
    dl = time.time() + timeout
    req_headers = {"User-Agent": "cashu-interop-tester/1.0"}
    while time.time() < dl:
        try:
            req = urllib.request.Request(f"{url}/v1/info", headers=req_headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.load(r).get("version", "?")
        except Exception:
            time.sleep(4)
    raise TimeoutError(f"{url} not ready")


class Mint:
    def __init__(self, spec: dict, net: str):
        self.name = spec["name"]
        self.family = spec["family"]
        self.image = spec.get("image")
        self.url = spec.get("url")
        self.net, self.port, self.container, self.workdir = net, free_port(), f"wxm-{self.name}", None
        if not self.url:
            self.url = f"http://{self.name}:3338"
        self.host_url = self.url if spec.get("url") else f"http://127.0.0.1:{self.port}"
        self.identity = None

    def start(self):
        if self.family == "url":
            # Pre-existing mint, just verify it's reachable
            self.identity = wait_ready(self.url, timeout=30)
            log(f"mint {self.name} ready (url): {self.identity}")
            return
        base = ["docker", "run", "-d", "--network", self.net, "--name", self.container,
                "-p", f"{self.port}:3338"]
        if self.family == "nutshell":
            r = sh(base + ["-e", "MINT_BACKEND_BOLT11_SAT=FakeWallet",
                           "-e", "MINT_LISTEN_HOST=0.0.0.0", "-e", "MINT_LISTEN_PORT=3338",
                           "-e", "MINT_RATE_LIMIT=FALSE",
                           "-e", f"MINT_PRIVATE_KEY={secrets.token_hex(32)}",
                           self.image, "poetry", "run", "mint"])
        else:  # cdk 0.18+: config-init into a workdir, CLN signet backend
            wd = Path.home() / f"wxm-{self.name}"
            if wd.exists():
                sh(["docker", "run", "--rm", "-v", f"{wd}:/data", "alpine",
                    "sh", "-c", "rm -rf /data/. /data/*"])
            wd.mkdir(parents=True, exist_ok=True)
            from mnemonic import Mnemonic
            mnem = Mnemonic("english").generate(strength=256)
            # CLN signet backend — real Lightning, invoices paid by auto-payer
            (wd / "config.toml").write_text(
                '[info]\nurl = "http://%s/"\nlisten_host = "0.0.0.0"\nlisten_port = %d\nmnemonic = "env:WXM_MNEMONIC"\n\n'
                '[database]\nengine = "sqlite"\n\n[payment_backend]\nbackend = "cln"\n\n'
                '[cln]\nrpc_path = "/tmp/cln-rpc"\n' % (self.host_url, self.port))
            if not (wd / "config.toml").exists():
                raise RuntimeError(f"{self.name}: config.toml not written to {wd}")
            log(f"{self.name}: config written, port={self.port}")
            init = sh(["docker", "run", "--rm", "-v", f"{wd}:/data", "-e", f"WXM_MNEMONIC={mnem}",
                       "-v", "/tmp/cln-rpc:/tmp/cln-rpc",
                       self.image, "cdk-mintd", "-w", "/data", "config", "init", "--new-mint",
                       "--file", "/data/config.toml"])
            if "Configuration initialized" not in init.stdout:
                # cdk <=0.17.x: no config subcommand — legacy env vars, keep FakeWallet
                r = sh(base + ["-e", "CDK_MINTD_LN_BACKEND=FakeWallet",
                               "-e", "CDK_MINTD_FAKE_WALLET_SUPPORTED_UNITS=sat",
                               "-e", "CDK_MINTD_LISTEN_HOST=0.0.0.0", "-e", "CDK_MINTD_LISTEN_PORT=3338",
                               "-e", f"CDK_MINTD_URL={self.host_url}/", "-e", "CDK_MINTD_MINT_NAME=wxm",
                               "-e", f"CDK_MINTD_MNEMONIC={mnem}", self.image])
                if r.returncode != 0:
                    raise RuntimeError(f"{self.name} legacy start failed: {r.stderr[-200:]}")
                self.identity = wait_ready(self.host_url)
                log(f"mint {self.name} ready (legacy FakeWallet): {self.identity}")
                return
            r = sh(["docker", "run", "-d", "--network", "host", "--name", self.container,
                    "-v", f"{wd}:/data", "-e", f"WXM_MNEMONIC={mnem}",
                    "-v", "/tmp/cln-rpc:/tmp/cln-rpc",
                    self.image, "cdk-mintd", "-w", "/data"])
        if r.returncode != 0:
            raise RuntimeError(f"{self.name} failed to start: {r.stderr[-200:]}")
        self.identity = wait_ready(self.host_url)
        log(f"mint {self.name} ready: {self.identity}")

    def stop(self):
        if self.family == "url":
            return
        sh(["docker", "rm", "-f", self.container])
        wd = Path.home() / f"wxm-{self.name}"
        if wd.exists():
            sh(["docker", "run", "--rm", "-v", f"{wd}:/data", "alpine",
                "sh", "-c", "rm -rf /data/. /data/*"])


def resolve_install(wallet: dict) -> tuple[bool, str]:
    if wallet.get("install") == "none":
        return True, ""
    """Pre-check package resolvability so unresolvable wallets SKIP fast."""
    pkg = wallet["install"]
    if wallet["driver"] == "node":
        # scoped pkgs carry a leading @: name is everything before the LAST @
        name = pkg.rsplit("@", 1)[0] if "@" in pkg[1:] else pkg
        r = sh(["docker", "run", "--rm", "--network", "host", wallet["image"], "npm", "view", name, "version"])
        ok = r.returncode == 0
    else:
        r = sh(["docker", "run", "--rm", "--network", "host", wallet["image"], "pip", "index", "versions", pkg.split("==")[0].split(">=")[0].split("<")[0]], timeout=120)
        ok = r.returncode == 0 or pkg.split("==")[0].lower() in r.stdout.lower() + r.stderr.lower()
    return ok, (r.stdout + r.stderr).strip()[-200:]



def pay_cln_invoice(invoice: str) -> bool:
    """Pay a bolt11 invoice through the CLN signet node (tunnel on ai-legion)."""
    import subprocess
    r = subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', 'root@inr2.cashu.exchange',
         f'docker exec cln-hub-signet lightning-cli --signet pay {invoice}'],
        capture_output=True, text=True, timeout=60)
    return r.returncode == 0 and 'preimage' in r.stdout


def wait_and_pay_cln(mint_url: str, quote_id: str, timeout: int = 30):
    """Check a mint quote; if unpaid and the mint is CLN-backed, pay the invoice."""
    import urllib.request
    try:
        req = urllib.request.Request(
            f'{mint_url}/v1/mint/quote/bolt11/{quote_id}',
            method='GET')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        if data.get('state') == 'PAID':
            return True
        bolt11 = data.get('request', '')
        if bolt11 and bolt11.startswith('ln'):
            log(f'  paying CLN invoice {bolt11[:30]}...')
            if pay_cln_invoice(bolt11):
                time.sleep(2)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                return data.get('state') == 'PAID'
        return False
    except Exception:
        return False

def run_cell(wallet: dict, mint: Mint, flow: str) -> dict:
    cell_dir = ART / wallet["name"] / mint.name / flow
    cell_dir.mkdir(parents=True, exist_ok=True)
    res = {"wallet": wallet["name"], "mint": mint.name, "mint_identity": mint.identity,
           "flow": flow, "verdict": "DRIVER_ERROR", "reason": "", "wire_shapes": {}}
    if wallet.get("install") == "none":
        pass
    elif wallet.get("_unresolvable"):
        res.update(verdict="SKIP", reason=f"package unresolvable: {wallet.get('_reason','')[:100]}")
        (cell_dir / "result.json").write_text(json.dumps(res, indent=1))
        return res
    env_mint = mint.host_url  # host-network drivers reach the published port
    if wallet["driver"] == "node":
        run_cmd = f"mkdir -p /tmp/w && cd /tmp/w && npm init -y >/dev/null 2>&1 && npm install --no-save --legacy-peer-deps {wallet['install']} 2>&1 && cp /drivers/node_flows.mjs . && node node_flows.mjs 2>&1"
    elif wallet.get("install") == "none":
        run_cmd = "cd /app && PYTHONPATH=/app python3 /drivers/py_flows.py 2>&1"
    else:
        run_cmd = f"pip install -q --no-cache-dir {wallet['install']} && python /drivers/py_flows.py"
    if _dbg: _dbg.cell_begin(wallet["name"], mint.name, flow)
    r = sh(["docker", "run", "--rm"] + ["--network", "host"] + [
            "-e", f"MINT_URL={env_mint}", "-e", f"TESTCASE={flow}",
            "-e", "ARTIFACT_DIR=/art", "-e", f"WALLET_NAME={wallet['name']}",
            "-e", f"WALLET_PACKAGE={wallet['install']}",
            "-v", f"{HERE / 'drivers'}:/drivers:ro",
            "-v", f"{cell_dir}:/art",
            wallet["image"], "bash", "-c", run_cmd], timeout=900)
    try:
        (cell_dir / "output.txt").write_text(r.stdout[-8000:] + r.stderr[-4000:])
    except PermissionError:
        # container-root driver already wrote output.txt; append tail via a root container
        sh(["docker", "run", "--rm", "-v", f"{cell_dir}:/art", "alpine", "sh", "-c",
            f"printf %s {shlex_quote((r.stdout + r.stderr)[-4000:])} >> /art/output.txt.hosttail"])
    code = r.returncode
    try:
        got = json.loads((cell_dir / "result.json").read_text())
        res.update(verdict=got.get("verdict") or ("PASS" if code == 0 else "FAIL" if code == 1 else "SKIP" if code == 127 else "DRIVER_ERROR"),
                   reason=got.get("reason", ""), wire_shapes=got.get("wire_shapes", {}))
    except Exception:
        res.update(verdict={0: "PASS", 1: "FAIL", 127: "SKIP"}.get(code, "DRIVER_ERROR"),
                   reason=f"no result.json; rc={code}; tail={ (r.stdout+r.stderr)[-200:] }")
    if _dbg: _dbg.cell_end(wallet["name"], mint.name, flow, code, r.stdout, r.stderr)
    log(f"cell {wallet['name']} x {mint.name} x {flow} -> {res['verdict']}")
    return res


_dbg = None


def main() -> int:
    global RUN, ART, _dbg
    cfg = yaml.safe_load((HERE / "matrix.yml").read_text())
    RUN = cfg.get("run_name", datetime.now().strftime("run-%Y%m%d-%H%M%S"))
    ART = HERE / "artifacts" / RUN
    ART.mkdir(parents=True, exist_ok=True)
    _dbg = CellDebugger(RUN)
    log(f"run {RUN}: {len(cfg['mints'])} mints x {len(cfg['wallets'])} wallets x {len(cfg['flows'])} flows")
    net = f"wxm-{RUN}"
    sh(["docker", "network", "create", net])
    mints: list[Mint] = []
    cells: list[dict] = []
    cln_payer = None
    try:
        for w in cfg["wallets"]:
            ok, reason = resolve_install(w)
            w["_unresolvable"], w["_reason"] = not ok, reason
            if not ok:
                log(f"wallet {w['name']}: package unresolvable -> cells will SKIP ({reason[:80]})")
        for m in cfg["mints"]:
            mint = Mint(m, net)
            try:
                mint.start()
                mints.append(mint)
            except Exception as e:
                log(f"mint {m['name']} SKIPPED (failed to start): {e}")
        # Start CLN auto-payer for all running mints (v2: sqlite polling —
        # cdk has no quote-list endpoint; we read the mint DBs directly)
        from pathlib import Path as _P
        db_paths = {}
        for m in mints:
            for pat in (_P.home() / f"mint-battery-{m.name}", _P.home() / f"mint-battery/{m.name}",
                        _P.home() / f"wxm-{m.name}"):
                sq = pat / "cdk-mintd.sqlite"
                if sq.exists():
                    db_paths[m.host_url] = str(sq)
                    break
        cln_payer = CLNAutoPayer([m.host_url for m in mints], db_paths=db_paths)
        cln_payer.start()
        log(f"CLN auto-payer started for {len(mints)} mints ({len(db_paths)} with DB polling)")
        jobs = [(w, m, f) for w in cfg["wallets"] for m in mints for f in cfg["flows"]]
        with ThreadPoolExecutor(max_workers=int(cfg.get("max_parallel", 4))) as ex:
            futs = [ex.submit(run_cell, w, m, f) for (w, m, f) in jobs]
            cells = [f.result() for f in futs]
    finally:
        if cln_payer:
            cln_payer.stop()
            log(f"CLN auto-payer: {cln_payer.report()}")
        for m in mints:
            m.stop()
        sh(["docker", "network", "rm", net])

    (ART / "grid.json").write_text(json.dumps({"run": RUN, "ts": datetime.now().isoformat(), "cells": cells}, indent=1))
    wallets_n, mints_n, flows_n = [sorted({c[k] for c in cells}) for k in ("wallet", "mint", "flow")]
    lines = [f"# wallet x mint interop grid — {RUN}", "",
             "| wallet \\ mint | " + " | ".join(f"{m} ({next(c['mint_identity'] for c in cells if c['mint']==m)})" for m in mints_n) + " |",
             "|---|" + "---|" * len(mints_n)]
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "DRIVER_ERROR": "⚠️"}
    for w in wallets_n:
        for f in flows_n:
            row = [f"{w}<br>{f}"]
            for m in mints_n:
                c = next((c for c in cells if c["wallet"] == w and c["mint"] == m and c["flow"] == f), None)
                row.append((icon.get(c["verdict"], "?") + " " + (c["reason"][:40] if c["verdict"] != "PASS" else "")) if c else "-")
            lines.append("| " + " | ".join(row) + " |")
    (ART / "grid.md").write_text("\n".join(lines) + "\n")
    counts = {}
    for c in cells:
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1
    (ART / "status.json").write_text(json.dumps({"run": RUN, "state": "DONE", "counts": counts,
                                                 "finished": datetime.now().isoformat()}, indent=1))
    (ART / "DONE").write_text(datetime.now().isoformat())
    log(f"DONE {counts} -> {ART}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
