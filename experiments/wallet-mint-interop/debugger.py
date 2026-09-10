#!/usr/bin/env python3
"""Wire capture and debugging as first-class citizens.

Runs alongside the experiment runner, capturing:
- Full HTTP wire logs (requests + responses) per cell
- Mint container logs (docker logs) after each cell
- Docker stats snapshots
- Environment state dump

Output: debug/<run_name>/ (gitignored) with per-cell subdirectories.
"""
import json, os, subprocess, time, urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEBUG = HERE / "debug"


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


class CellDebugger:
    """Per-cell debug capture. Call start() before, snapshot() after each cell."""

    def __init__(self, run_name: str):
        self.run_dir = DEBUG / run_name
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.cell_start = None
        self.mint_containers = []

    def start(self, mint_containers: list[str]):
        """Called once after mints are up. Records environment state."""
        self.mint_containers = mint_containers
        env = {
            "ts": datetime.now().isoformat(),
            "mints": {},
            "docker_stats": self._docker_stats(),
        }
        for c in mint_containers:
            info = sh(["docker", "inspect", c, "--format",
                       "{{.Config.Image}} {{.State.Status}}"]).stdout.strip()
            logs = sh(["docker", "logs", "--tail", "5", c]).stdout[-500:]
            env["mints"][c] = {"inspect": info, "recent_logs": logs}
        (self.run_dir / "env.json").write_text(json.dumps(env, indent=1))

    def cell_begin(self, wallet: str, mint: str, flow: str):
        self.cell_start = time.time()
        self.cell_dir = self.run_dir / wallet / mint / flow
        self.cell_dir.mkdir(parents=True, exist_ok=True)

    def cell_end(self, wallet: str, mint: str, flow: str,
                 exit_code: int, stdout: str, stderr: str):
        if not self.cell_dir:
            return
        # Capture full stdout/stderr
        (self.cell_dir / "stdout.txt").write_text(stdout)
        (self.cell_dir / "stderr.txt").write_text(stderr)

        # Capture mint logs at this point
        for c in self.mint_containers:
            logs = sh(["docker", "logs", "--since", "60s", c]).stdout[-3000:]
            if logs:
                (self.cell_dir / f"mint_{c}.log").write_text(logs)

        # Docker stats snapshot
        stats = self._docker_stats()
        (self.cell_dir / "docker_stats.json").write_text(json.dumps(stats, indent=1))

        # Cell summary
        summary = {
            "wallet": wallet, "mint": mint, "flow": flow,
            "exit_code": exit_code,
            "duration_s": round(time.time() - self.cell_start, 2) if self.cell_start else 0,
            "ts": datetime.now().isoformat(),
        }
        (self.cell_dir / "cell_summary.json").write_text(json.dumps(summary, indent=1))

    def _docker_stats(self):
        r = sh(["docker", "stats", "--no-stream"])
        return {"raw": r.stdout}

    def snapshot_all(self):
        """Full environment snapshot at any point."""
        snap = {
            "ts": datetime.now().isoformat(),
            "containers": {},
            "network": sh(["ss", "-tlnp"]).stdout[:2000] if sh(["which", "ss"]).returncode == 0 else "",
        }
        for c in self.mint_containers:
            inspect = sh(["docker", "inspect", c]).stdout
            logs = sh(["docker", "logs", "--tail", "20", c]).stdout[-2000:]
            snap["containers"][c] = {"inspect_raw": inspect[:1000], "logs_tail": logs}
        (self.run_dir / f"snapshot_{int(time.time())}.json").write_text(json.dumps(snap, indent=1))
