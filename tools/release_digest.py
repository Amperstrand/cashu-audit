#!/usr/bin/env python3
"""NUT-impact digest for a mint-implementation release (cdk / nutshell).

Answers: "a new release shipped — what changed, which NUTs does it touch,
which tracker cards must be re-checked?"

Sources per release (all public, no tokens needed beyond gh auth):
    1. GitHub release notes (gh api repos/<repo>/releases/tags/<tag>)
    2. git log <prev>..<tag> from a blobless local clone (auto-created,
       tags fetched) — commit subjects, NUT references, hot paths

Output: research/releases/<project>-<version>.md

Usage:
    python3 tools/release_digest.py --project cdk --version v0.18.2 \
        [--prev v0.18.1] [--clone-dir /root/src/upstream-cache]

Tag conventions: cdk tags are v-prefixed (v0.18.2); nutshell tags are
bare (0.21.0). --version accepts either form.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PROJECTS = {
    "cdk": {
        "git_url": "https://github.com/cashubtc/cdk.git",
        "notes_repo": "cashubtc/cdk",
        "tag_prefix": "v",
        "maps": "cdk 0.18.x",
    },
    "nutshell": {
        "git_url": "https://github.com/cashubtc/nutshell.git",
        "notes_repo": "cashubtc/nutshell",
        "tag_prefix": "",
        "maps": "nutshell 0.20.3/0.21.0 (conformance-v2 arms)",
    },
}

NUT_IN_MSG = re.compile(r"\bNUT-?(\d{2})\b", re.I)
NUT_IN_PATH = re.compile(r"nut[_-]?(\d{2})", re.I)


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def gh_json(path: str) -> dict:
    r = sh(["gh", "api", path])
    if r.returncode != 0:
        raise RuntimeError(f"gh api {path} failed: {r.stderr.strip()[:200]}")
    return json.loads(r.stdout)


def ensure_clone(url: str, clone_dir: Path) -> Path:
    name = url.rstrip("/").split("/")[-1].removesuffix(".git")
    path = clone_dir / name
    if not path.exists():
        clone_dir.mkdir(parents=True, exist_ok=True)
        r = sh(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                url, str(path)])
        if r.returncode != 0:
            raise RuntimeError(f"clone failed: {r.stderr[-300:]}")
    sh(["git", "-C", str(path), "fetch", "--quiet", "--tags", "origin"])
    return path


def resolve_tag(path: Path, version: str, prefix: str) -> str:
    for cand in (version, f"{prefix}{version}"):
        if sh(["git", "-C", str(path), "rev-parse", "--verify",
               "--quiet", f"refs/tags/{cand}"]).returncode == 0:
            return cand
    raise SystemExit(f"tag not found for version {version!r} in {path}")


def tag_date(path: Path, tag: str) -> str:
    out = sh(["git", "-C", str(path), "log", "-1", "--format=%cs",
              f"refs/tags/{tag}"]).stdout.strip()
    return out or "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, choices=PROJECTS)
    ap.add_argument("--version", required=True)
    ap.add_argument("--prev", help="previous tag; default: closest earlier semver tag")
    ap.add_argument("--clone-dir", default="/root/src/upstream-cache")
    args = ap.parse_args()

    cfg = PROJECTS[args.project]
    clone = ensure_clone(cfg["git_url"], Path(args.clone_dir))
    tag = resolve_tag(clone, args.version, cfg["tag_prefix"])

    # previous tag = the tag immediately before this one in tag-date order
    prev = args.prev
    if not prev:
        tags = sh(["git", "-C", str(clone), "for-each-ref",
                   "refs/tags", "--sort=-creatordate",
                   "--format=%(refname:short)%(if)%(objecttype)%(then)%(else),lightweight%(end)"
                   ]).stdout.splitlines()
        names = [t.split(",lightweight")[0] for t in tags]
        # skip rc/beta tags and the target itself
        stable = [t for t in names if not re.search(r"rc|beta|alpha", t, re.I)]
        idx = next((i for i, t in enumerate(stable) if t == tag), None)
        if idx is None or idx + 1 >= len(stable):
            raise SystemExit(f"cannot infer --prev for {tag}; pass it explicitly")
        prev = stable[idx + 1]

    # 1. release notes
    notes = ""
    rel = gh_json(f"repos/{cfg['notes_repo']}/releases/tags/{tag}")
    notes = (rel.get("body") or "").strip()
    notes_url = rel.get("html_url", "")

    # 2. commits between tags
    log = sh(["git", "-C", str(clone), "log", "--name-only",
              "--format=__C__%h%x1f%cs%x1f%s", f"{prev}..{tag}"])
    commits: list[dict] = []
    cur: dict | None = None
    for line in log.stdout.splitlines():
        if line.startswith("__C__"):
            if cur:
                commits.append(cur)
            sha, cdate, subj = line[5:].split("\x1f", 2)
            cur = {"sha": sha, "date": cdate, "subject": subj, "paths": []}
        elif line.strip() and cur is not None:
            cur["paths"].append(line.strip())
    if cur:
        commits.append(cur)

    # 3. NUT impact: from subjects, note bodies, and paths
    nut_hits: dict[str, set[str]] = {}
    for c in commits:
        refs = set(NUT_IN_MSG.findall(c["subject"]))
        for p in c["paths"]:
            refs |= set(NUT_IN_PATH.findall(p))
        for n in refs:
            nut_hits.setdefault(n, set()).add(c["sha"][:8])

    hot = {}
    for c in commits:
        for p in c["paths"]:
            zone = "/".join(p.split("/")[:3])
            hot[zone] = hot.get(zone, 0) + 1
    hot_rows = sorted(hot.items(), key=lambda kv: -kv[1])[:12]

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = REPO / "research" / "releases"
    out_dir.mkdir(exist_ok=True)
    lines = [
        f"# {args.project} {tag.removeprefix(cfg['tag_prefix'])} — NUT-impact digest",
        "",
        f"Released: {tag_date(clone, tag)} · range `{prev}..{tag}` · "
        f"{len(commits)} commits · generated {stamp} by `tools/release_digest.py`",
        f"Maps to arms: {cfg['maps']}",
        "",
        "## NUTs touched → tracker cards to re-check",
        "",
    ]
    if nut_hits:
        lines.append("| NUT | commits touching it |")
        lines.append("|---|---|")
        for n in sorted(nut_hits, key=int):
            shas = ", ".join(sorted(nut_hits[n]))
            lines.append(f"| NUT-{n} | {shas} |")
    else:
        lines.append("_(no NUT-referencing commits or nut-named paths in range)_")
    lines += [
        "",
        "## Hot zones (top-level paths by file-touch count)",
        "",
        "| Zone | touches |",
        "|---|---|",
    ] + [f"| `{z}` | {c} |" for z, c in hot_rows] + [
        "",
        "## Commit subjects (newest first)",
        "",
    ]
    for c in reversed(commits):
        lines.append(f"- `{c['sha']}` {c['date']} {c['subject']}")
    lines += ["", "## Release notes (verbatim)", ""]
    if notes:
        lines.append(f"_source: {notes_url}_")
        lines.append("")
        lines.append(notes[:4000])
    else:
        lines.append(f"_(no release notes body at {notes_url})_")

    out = out_dir / f"{args.project}-{tag.removeprefix(cfg['tag_prefix'])}.md"
    out.write_text("\n".join(lines) + "\n")
    nuts = ", ".join(f"NUT-{n}" for n in sorted(nut_hits, key=int)) or "none"
    print(f"OK {out.relative_to(REPO)}: {len(commits)} commits, NUTs: {nuts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
