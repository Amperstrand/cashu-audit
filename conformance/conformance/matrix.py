"""Comparison matrix generator — renders results as a markdown table."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from .scenarios import Result, ScenarioResult


def generate_matrix(
    results: dict[str, list[ScenarioResult]],
    mint_urls: list[str],
    identities: dict[str, str] | None = None,
) -> str:
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append(f"# Cashu Conformance Matrix — {now}")
    lines.append("")

    # #40: provenance block — mint identity captured at run start, adjacent
    # to every URL so the report is attributable without external state.
    if identities:
        lines.append("**Targets** (identity captured at run start):")
        for u in mint_urls:
            lines.append(f"- `{u}` — {identities.get(u, 'identity-unavailable')}")
        lines.append("")

    total_pass = sum(1 for rs in results.values() for r in rs if r.result == Result.PASS)
    total_fail = sum(1 for rs in results.values() for r in rs if r.result == Result.FAIL)
    total_skip = sum(1 for rs in results.values() for r in rs if r.result in (Result.SKIP, Result.XFAIL))
    total = total_pass + total_fail + total_skip
    lines.append(f"**Summary**: {total_pass} passed, {total_fail} failed, {total_skip} skipped ({total} total)")
    lines.append("")

    categories = defaultdict(list)
    all_names: list[str] = []
    seen = set()
    for mint_url in mint_urls:
        for r in results.get(mint_url, []):
            if r.name not in seen:
                categories[r.category].append(r.name)
                all_names.append(r.name)
                seen.add(r.name)

    # #40: column headers use the captured identity (short form), not the
    # raw URL — the URL stays in the provenance block above.
    def _label(u: str) -> str:
        ident = (identities or {}).get(u)
        if not ident or ident.startswith("identity-unavailable"):
            return f"`{u}`" if len(u) <= 40 else f"`{u[:37]}...`"
        short = ident.split(" / ")[0]
        ver = ident.split(" / ")[1] if " / " in ident else "?"
        return f"`{short}@{ver}`"

    mint_labels = [_label(u) for u in mint_urls]

    for category, names in categories.items():
        lines.append(f"## {category}")
        lines.append("")
        header = "| Scenario | " + " | ".join(mint_labels) + " |"
        sep = "|---|" + "|".join(["---"] * len(mint_labels)) + "|"
        lines.append(header)
        lines.append(sep)

        for name in names:
            cells = []
            for mint_url in mint_urls:
                match = next((r for r in results.get(mint_url, []) if r.name == name), None)
                if match is None:
                    cells.append("—")
                elif match.result == Result.PASS:
                    cells.append("✅")
                elif match.result == Result.FAIL:
                    cells.append(f"❌")
                elif match.result == Result.XFAIL:
                    cells.append("⚠️")
                else:
                    cells.append("⏭️")
            lines.append(f"| `{name}` | " + " | ".join(cells) + " |")

        lines.append("")

        for name in names:
            for mint_url in mint_urls:
                match = next((r for r in results.get(mint_url, []) if r.name == name), None)
                if match and match.result == Result.FAIL:
                    lines.append(f"> ❌ `{name}` @ `{mint_url}`: {match.note}")
                    lines.append("")

    return "\n".join(lines)
