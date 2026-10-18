#!/usr/bin/env python3
"""Nightly divergence gate for the token-conformance corpus.

Compares tonight's consumer-conformance report against the committed
baseline (reports/nightly-baseline.json) and lists every NEW or CHANGED
divergence. With --file and a GitHub token in GH_TOKEN, files one issue
per new divergence key, deduplicated by the `REGKEY:` line in open
issues (never re-files an existing key). A missing baseline means
bootstrap: record it, file nothing, exit 0.

Exit code: 0 when nothing new diverged (or bootstrap), 1 when new or
changed divergences exist (after filing, so the run shows red).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

REPO = "Amperstrand/cashu-audit"


def row_key(row: dict) -> str:
    return f"{row['lane']}/{row['vector']}"


def divergence_state(row: dict) -> str | None:
    if row.get("result") == "FAIL":
        return "FAIL"
    if row.get("result") == "FILL":
        return "FILL"
    return None


def load_baseline(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def gh(*args: str) -> str:
    env = dict(os.environ)
    env["GH_TOKEN"] = env.get("GH_TOKEN") or env.get("GITHUB_TOKEN", "")
    out = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    if out.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def issue_exists(regkey: str) -> bool:
    query = urllib.parse.quote(f"repo:{REPO} is:issue is:open REGKEY:{regkey} in:body")
    out = gh("search", "issues", query, "--json", "number", "--limit", "1")
    return bool(json.loads(out))


def file_issue(regkey: str, kind: str, rows: list[dict]) -> str:
    title = f"[nightly-corpus] {kind}: {regkey}"
    body_lines = [
        f"REGKEY: {regkey}",
        "",
        f"Auto-filed by the nightly corpus workflow ({kind} divergence vs reports/nightly-baseline.json).",
        "",
        "| lane | vector | expected | actual | detail |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        body_lines.append(
            f"| {r['lane']} | {r['vector']} | {r['expected']} | {r['actual']} | {r.get('detail','')} |"
        )
    body_lines += [
        "",
        "Triage: a surprising FAIL is a probe bug until proven otherwise (AGENTS.md method rule 1) —",
        "read the report artifact for this run date before treating it as consumer drift.",
    ]
    return gh("issue", "create", "--repo", REPO, "--title", title, "--body", "\n".join(body_lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--baseline", default="reports/nightly-baseline.json")
    ap.add_argument("--file", action="store_true", help="file GitHub issues for new keys (needs GH_TOKEN)")
    args = ap.parse_args()

    report = json.loads(Path(args.report).read_text())
    baseline = load_baseline(Path(args.baseline))
    rows = report.get("rows", [])

    if baseline is None:
        Path(args.baseline).parent.mkdir(parents=True, exist_ok=True)
        slim = {"keys": {row_key(r): r.get("result") for r in rows if divergence_state(r)}}
        Path(args.baseline).write_text(json.dumps(slim, indent=2, sort_keys=True) + "\n")
        print(f"bootstrap: recorded {len(slim['keys'])} divergence keys as the baseline; nothing filed")
        return 0

    old_keys: dict[str, str] = baseline.get("keys", {})
    new_divergences: dict[str, list[dict]] = {}
    changed: dict[str, list[dict]] = {}
    for r in rows:
        state = divergence_state(r)
        key = row_key(r)
        old_state = old_keys.get(key)
        if state and old_state is None:
            new_divergences.setdefault(key, []).append(r)
        elif state and old_state != state:
            changed.setdefault(key, []).append(r)

    print(f"rows={len(rows)} baseline_keys={len(old_keys)} new={len(new_divergences)} changed={len(changed)}")
    for key, rs in list(new_divergences.items()) + list(changed.items()):
        for r in rs:
            print(f"  {'NEW' if key in new_divergences else 'CHANGED'} {key}: {r.get('result')} (was {old_keys.get(key, '—')}) expected={r.get('expected')} actual={r.get('actual')}")

    if args.file and (new_divergences or changed):
        for key, rs in new_divergences.items():
            if issue_exists(key):
                print(f"  dedupe: {key} already has an open issue — skipped")
                continue
            url = file_issue(key, "new divergence", rs)
            print(f"  filed: {url}")
        for key, rs in changed.items():
            if issue_exists(key):
                print(f"  dedupe: {key} already has an open issue — skipped")
                continue
            url = file_issue(key, "changed verdict", rs)
            print(f"  filed: {url}")

    slim = {"keys": {row_key(r): r.get("result") for r in rows if divergence_state(r)}}
    Path(args.baseline).write_text(json.dumps(slim, indent=2, sort_keys=True) + "\n")
    return 1 if (new_divergences or changed) else 0


if __name__ == "__main__":
    sys.exit(main())
