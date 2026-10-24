#!/usr/bin/env python3
"""Generate the per-NUT spec-change timeline from the cashubtc/NUTs repo.

Usage:
    python3 tools/spec_history.py [--nuts-dir /root/src/NUTs] [--refresh] [--out research/SPEC-HISTORY]

Output:
    <out>/nut-NN.md   — full commit timeline for one NUT (oldest last)
    <out>/INDEX.md    — summary table: NUT | title | status | created | last changed | commits

Pure data extraction: every row comes from `git log --follow` in the local
NUTs clone (dates = commit dates, subjects verbatim, PR numbers as they
appear in merge subjects). Interpretation lives in research/NUT-TRACKER.md,
not here. Refresh policy: --refresh does fetch + fast-forward; the generated
INDEX records the exact HEAD sha so any timeline row is reproducible.
"""
import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


def git(nuts_dir: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(nuts_dir), *args],
        check=True, capture_output=True, text=True,
    ).stdout


def parse_header(md_text: str) -> dict:
    title, status, depends = "", "", ""
    for line in md_text.splitlines():
        if not title and line.startswith("# NUT-"):
            title = line.lstrip("# ").strip()
            continue
        m = re.fullmatch(r"`(mandatory|optional|draft|deprecated)`.*", line.strip())
        if m and not status:
            status = m.group(1)
        d = re.search(r"`depends on:\s*(.+?)`", line.strip())
        if d and not depends:
            depends = d.group(1)
        if title and status and depends:
            break
    return {"title": title, "status": status or "?", "depends": depends}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nuts-dir", default="/root/src/NUTs")
    ap.add_argument("--refresh", action="store_true", help="git fetch + fast-forward the clone first")
    ap.add_argument("--out", default="research/SPEC-HISTORY")
    args = ap.parse_args()

    nuts = Path(args.nuts_dir).resolve()
    out = Path(args.out)
    if not nuts.exists():
        sys.exit(f"no NUTs clone at {nuts} — git clone https://github.com/cashubtc/NUTs.git first")
    if args.refresh:
        git(nuts, "fetch", "--quiet", "origin")
        git(nuts, "reset", "--hard", "origin/HEAD", "--quiet")

    head = git(nuts, "rev-parse", "--short", "HEAD").strip()
    head_date = git(nuts, "log", "-1", "--format=%cs").strip()

    nut_files = sorted(p for p in nuts.glob("*.md") if re.fullmatch(r"\d{2}\.md", p.name))
    if not nut_files:
        sys.exit(f"no NN.md files found in {nuts} — wrong repo?")

    out.mkdir(parents=True, exist_ok=True)
    summary = []

    for f in nut_files:
        num = f.stem
        meta = parse_header(f.read_text())

        # Full history with rename tracking (nut-11.md -> 11.md renames).
        log = git(nuts, "log", "--follow", "--name-status",
                  "--format=__COMMIT__%H%x1f%cs%x1f%an%x1f%s", "--", f.name)
        rows, current = [], None
        for line in log.splitlines():
            if line.startswith("__COMMIT__"):
                if current:
                    rows.append(current)
                sha, cdate, author, subject = line[len("__COMMIT__"):].split("\x1f", 3)
                current = {"sha": sha[:10], "date": cdate, "author": author,
                           "subject": subject, "rename": ""}
            elif current and line.strip():
                parts = line.split("\t")
                if parts[0].startswith("R") and len(parts) >= 3:
                    current["rename"] = f"{parts[1]} → {parts[2]}"
        if current:
            rows.append(current)

        first = rows[-1]["date"] if rows else "?"
        last = rows[0]["date"] if rows else "?"
        summary.append((num, meta, len(rows), first, last))

        lines = [
            f"# {meta['title'] or f'NUT-{num}'} — spec change history",
            "",
            f"Status: `{meta['status']}`"
            + (f" · depends on: {meta['depends']}" if meta["depends"] else ""),
            f"History: {len(rows)} commits · first {first} · last {last}",
            f"Generated from cashubtc/NUTs @ {head} ({head_date}) — `tools/spec_history.py`",
            "",
            "Newest first. Rename rows mark spec-file renames tracked by `--follow`.",
            "",
            "| Date | Commit | Subject | Rename |",
            "|---|---|---|---|",
        ]
        for r in rows:
            subj = r["subject"].replace("|", "\\|")
            lines.append(f"| {r['date']} | `{r['sha']}` | {subj} | {r['rename']} |")
        (out / f"nut-{num}.md").write_text("\n".join(lines) + "\n")

    index = [
        "# SPEC-HISTORY INDEX — cashubtc/NUTs change timeline summary",
        "",
        f"Generated from cashubtc/NUTs @ `{head}` ({head_date}) by `tools/spec_history.py --refresh`.",
        "Per-NUT timelines in `nut-NN.md`. Dates are commit dates, not PR-open dates.",
        "",
        "| NUT | Title | Status | First commit | Last changed | Commits |",
        "|---|---|---|---|---|---|",
    ]
    for num, meta, n, first, last in summary:
        t = meta["title"].replace("|", "\\|")
        index.append(f"| NUT-{num} | {t} | `{meta['status']}` | {first} | {last} | {n} |")
    index += ["", f"Total: {len(summary)} NUTs, {sum(s[2] for s in summary)} tracked commits."]
    (out / "INDEX.md").write_text("\n".join(index) + "\n")

    churn = sorted(summary, key=lambda s: s[4], reverse=True)[:8]
    print(f"OK: {len(summary)} NUTs @ {head}. Most-recently-changed:")
    for num, meta, n, first, last in churn:
        print(f"  NUT-{num} {meta['status']:<10} last {last} ({n} commits) — {meta['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
