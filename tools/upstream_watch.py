#!/usr/bin/env python3
"""Daily upstream watch: NUTs spec drift + cdk/nutshell releases.

One run answers: "did the spec move, and did a reference mint ship a
release since yesterday?" New events produce a release digest
(tools/release_digest.py), regenerate the spec timelines
(tools/spec_history.py), append to research/UPSTREAM-WATCH.md, and print
`CHANGE:` lines (house watch convention — a wrapper cron script logs
them and commits the repo).

State: research/upstream-state.json (committed — the baseline travels
with the repo; a fresh clone adopts current upstream as baseline).

Usage: /usr/bin/python3 tools/upstream_watch.py [--rebaseline]
  --rebaseline  adopt current upstream state without digesting (used on
                first install or after an intentional reset)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "research/upstream-state.json"
WATCH = REPO / "research/UPSTREAM-WATCH.md"
DEFAULT_NUTS = Path("/root/src/NUTs")


def ensure_nuts_clone(nuts_dir: Path) -> Path:
    """Any host: create the blobless NUTs clone on first use."""
    if nuts_dir.exists():
        return nuts_dir
    nuts_dir.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["git", "clone", "--quiet", "--filter=blob:none",
                        "https://github.com/cashubtc/NUTs.git", str(nuts_dir)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"NUTs clone failed: {r.stderr[-150:]}")
    return nuts_dir

WATCH_TARGETS = {
    "cdk": {"kind": "release", "repo": "cashubtc/cdk"},
    "nutshell": {"kind": "release", "repo": "cashubtc/nutshell"},
    "cashu-ts": {"kind": "release", "repo": "cashubtc/cashu-ts"},
}


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO), **kw)


def latest_release(repo: str) -> tuple[str, str]:
    # Enumerate the 3 most-recent releases (incl. prereleases) — the
    # /releases/latest endpoint only shows the newest line and misses
    # backport releases (e.g. cdk v0.17.7 published after v0.18.1).
    # State = the full tag SET, so a backport on an older line trips
    # CHANGE even when the newest tag is unchanged.
    r = sh(["gh", "api", f"repos/{repo}/releases?per_page=3",
            "--jq", '.[] | .tag_name + " " + (.published_at // "?")'])
    if r.returncode != 0 or not r.stdout.strip():
        r = sh(["gh", "api", f"repos/{repo}/releases/latest",
                "--jq", ".tag_name + \" \" + .published_at"])
        if r.returncode != 0:
            raise RuntimeError(f"gh api {repo}: {r.stderr.strip()[:120]}")
    lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
    pairs = [tuple(l.split(" ", 1)) for l in lines]
    tags = [p[0] for p in pairs]
    newest = ",".join(tags)          # state: full set, newest first
    tag, published = pairs[0]        # display: newest single release
    return newest, published


def nuts_head(nuts_dir: Path) -> str:
    r = sh(["git", "-C", str(nuts_dir), "fetch", "--quiet", "origin"])
    if r.returncode != 0:
        raise RuntimeError(f"git fetch NUTs: {r.stderr[:120]}")
    return sh(["git", "-C", str(nuts_dir), "rev-parse",
               "origin/HEAD"]).stdout.strip()


def new_spec_commits(nuts_dir: Path, old: str, new: str) -> list[str]:
    r = sh(["git", "-C", str(nuts_dir), "log", "--format=%cs %h %s",
            f"{old}..{new}"])
    return [l for l in r.stdout.splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebaseline", action="store_true")
    ap.add_argument("--nuts-dir", default=str(DEFAULT_NUTS),
                    help="NUTs clone (auto-created if missing)")
    ap.add_argument("--clone-dir", default="/root/src/upstream-cache",
                    help="blobless impl-clone cache for release digests")
    args = ap.parse_args()
    nuts = ensure_nuts_clone(Path(args.nuts_dir))

    state = {"nuts_head": "", "releases": {}}
    if STATE.exists():
        state = json.loads(STATE.read_text())
    events: list[str] = []  # CHANGE: lines
    sections: list[str] = []

    # --- 1. NUTs spec drift ---
    try:
        head = nuts_head(nuts)
        old = state.get("nuts_head")
        if args.rebaseline or not old:
            state["nuts_head"] = head
            if not args.rebaseline:
                events.append(f"CHANGE: nuts baseline set at {head[:10]}")
        elif head != old:
            commits = new_spec_commits(nuts, old, head)
            r = sh(["python3", "tools/spec_history.py", "--refresh",
                    "--nuts-dir", str(nuts)])
            if r.returncode != 0:
                events.append(f"CHANGE: nuts moved {old[:10]}->{head[:10]} "
                              f"but spec_history FAILED: {r.stderr[-150:]}")
            else:
                state["nuts_head"] = head
                events.append(f"CHANGE: NUTs {old[:10]}->{head[:10]} "
                              f"({len(commits)} commits, timelines regenerated)")
                sections.append("### NUTs spec moved\n\n```\n" +
                                "\n".join(commits[:25]) + "\n```\n")
    except Exception as e:  # never die before writing state/log
        events.append(f"CHANGE: nuts check errored: {e}")

    # --- 2. releases ---
    for name, cfg in WATCH_TARGETS.items():
        try:
            tags, published = latest_release(cfg["repo"])
            seen = state.get("releases", {}).get(name)
            if args.rebaseline or not seen:
                state.setdefault("releases", {})[name] = tags
                if not args.rebaseline:
                    events.append(f"CHANGE: {name} baseline set at {tags}")
                continue
            if tags == seen:
                continue
            new_tags = [t for t in tags.split(",") if t not in seen.split(",")]
            proj = name  # WATCH_TARGETS keys are release_digest PROJECTS keys
            digested = []
            last_out = ""
            for tag in new_tags:
                r = sh(["python3", "tools/release_digest.py",
                        "--project", proj, "--version", tag,
                        "--clone-dir", args.clone_dir])
                if r.returncode != 0:
                    events.append(f"CHANGE: {name} release {tag} but digest "
                                  f"FAILED: {r.stderr[-150:]}")
                    continue
                digested.append(tag)
                last_out = r.stdout.strip()
            if not digested:
                continue
            state["releases"][name] = tags
            events.append(f"CHANGE: {name} release(s) {', '.join(digested)} "
                          f"(published {published[:10]}) — {last_out}")
            sections.append(f"### {name} {', '.join(digested)}\n\n```\n{last_out}\n```\n"
                            f"Read the digest, then the tracker cards it names.\n")
        except Exception as e:
            events.append(f"CHANGE: {name} check errored: {e}")

    STATE.write_text(json.dumps(state, indent=1) + "\n")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if not WATCH.exists():
        WATCH.write_text("# UPSTREAM WATCH — daily spec/release drift log\n"
                         f"(generated by tools/upstream_watch.py; first run {stamp})\n")
    if events:
        body = [f"\n## Run {stamp}\n"]
        body += [f"- {e}" for e in events]
        if sections:
            body.append("")
            body.extend(sections)
        with WATCH.open("a") as f:
            f.write("\n".join(body) + "\n")

    for e in events:
        print(e)
    if not events:
        print(f"OK: no upstream movement ({stamp})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
