#!/usr/bin/env python3
"""Generate self-hosted SVG cards for the GitHub profile README.

Data source: GitHub REST API only.
Generated files:
  assets/github-stats-{light,dark}.svg
  assets/top-languages-{light,dark}.svg
  assets/repos-by-primary-language-{light,dark}.svg
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USERNAME = os.environ.get("GH_USERNAME", "tungchiahui")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
API = "https://api.github.com"
OUT = Path("assets")

if not TOKEN:
    raise SystemExit("GH_TOKEN or GITHUB_TOKEN is required")

LANG_COLORS = {
    "C++": "#f34b7d",
    "C": "#555555",
    "CMake": "#DA3434",
    "HTML": "#e34c26",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "Shell": "#89e051",
    "Dockerfile": "#384d54",
    "Lua": "#000080",
    "Linker Script": "#8f8f8f",
    "Assembly": "#6E4C13",
    "Dart": "#00B4AB",
    "CSS": "#663399",
    "Vue": "#41b883",
    "Makefile": "#427819",
    "Objective-C": "#438eff",
    "Rust": "#dea584",
    "Go": "#00ADD8",
    "Java": "#b07219",
    "Kotlin": "#A97BFF",
}


def api_get(path: str, params: dict[str, object] | None = None) -> object:
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "tungchiahui-profile-cards",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def fetch_public_repos() -> list[dict]:
    repos: list[dict] = []
    page = 1
    while True:
        batch = api_get(
            f"/users/{USERNAME}/repos",
            {"type": "owner", "sort": "updated", "per_page": 100, "page": page},
        )
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected repositories response")
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def search_total(endpoint: str, query: str) -> int:
    data = api_get(endpoint, {"q": query, "per_page": 1})
    if not isinstance(data, dict) or "total_count" not in data:
        raise RuntimeError(f"Unexpected search response for {query}")
    return int(data["total_count"])


def color_for(name: str) -> str:
    if name in LANG_COLORS:
        return LANG_COLORS[name]
    # Stable fallback color derived from the language name.
    palette = ["#58a6ff", "#2dd4bf", "#bc8cff", "#d29922", "#f778ba", "#79c0ff"]
    return palette[sum(name.encode("utf-8")) % len(palette)]


def theme_values(theme: str) -> dict[str, str]:
    if theme == "dark":
        return {
            "bg": "#0d1117",
            "border": "#30363d",
            "title": "#58a6ff",
            "text": "#c9d1d9",
            "muted": "#8b949e",
            "track": "#21262d",
            "accent": "#58a6ff",
        }
    return {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "title": "#0969da",
        "text": "#24292f",
        "muted": "#57606a",
        "track": "#eaeef2",
        "accent": "#0969da",
    }


def svg_shell(width: int, height: int, theme: str, body: str, aria: str) -> str:
    t = theme_values(theme)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(aria)}">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="{t['bg']}" stroke="{t['border']}"/>
  <style>
    text {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
    .title {{ font-size: 22px; font-weight: 600; fill: {t['title']}; }}
    .text {{ font-size: 15px; fill: {t['text']}; }}
    .label {{ font-size: 14px; fill: {t['text']}; }}
    .value {{ font-size: 15px; font-weight: 600; fill: {t['text']}; }}
    .muted {{ font-size: 12px; fill: {t['muted']}; }}
  </style>
{body}
</svg>
"""


def render_stats(theme: str, stats: dict[str, int], updated: str) -> str:
    t = theme_values(theme)
    rows = [
        ("Total Stars", stats["stars"]),
        ("Total Commits", stats["commits"]),
        ("Total PRs", stats["prs"]),
        ("Total Issues", stats["issues"]),
        ("Public Repos", stats["repos"]),
    ]
    y0 = 74
    parts = [
        '  <text x="26" y="38" class="title">Tung Chia-hui\'s GitHub Stats</text>',
    ]
    for i, (label, value) in enumerate(rows):
        y = y0 + i * 24
        parts.append(f'  <circle cx="31" cy="{y - 5}" r="4" fill="{t["accent"]}"/>')
        parts.append(f'  <text x="45" y="{y}" class="text">{escape(label)}</text>')
        parts.append(f'  <text x="455" y="{y}" text-anchor="end" class="value">{value:,}</text>')
    parts.append(f'  <text x="26" y="186" class="muted">Public GitHub data · updated {escape(updated)}</text>')
    return svg_shell(495, 195, theme, "\n".join(parts), "Tung Chia-hui GitHub statistics")


def render_top_languages(theme: str, language_bytes: Counter[str], updated: str) -> str:
    t = theme_values(theme)
    total = sum(language_bytes.values())
    if total <= 0:
        raise RuntimeError("No language byte data found")

    ranked = language_bytes.most_common(6)
    width = 495
    bar_x, bar_y, bar_w, bar_h = 26, 61, 443, 10

    parts = [
        '  <text x="26" y="36" class="title">Top Languages</text>',
        f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="{t["track"]}"/>',
    ]

    cursor = bar_x
    for index, (name, size) in enumerate(ranked):
        seg = bar_w * size / total
        # Let the first/last segment slightly overlap the rounded track so no gaps appear.
        parts.append(
            f'  <rect x="{cursor:.2f}" y="{bar_y}" width="{max(seg, 1):.2f}" height="{bar_h}" fill="{color_for(name)}"/>'
        )
        cursor += seg

    col_x = [28, 262]
    start_y = 100
    for i, (name, size) in enumerate(ranked):
        col = i // 3
        row = i % 3
        x = col_x[col]
        y = start_y + row * 30
        pct = size / total * 100
        parts.append(f'  <circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{color_for(name)}"/>')
        parts.append(f'  <text x="{x + 18}" y="{y}" class="label">{escape(name)} {pct:.2f}%</text>')

    parts.append(f'  <text x="26" y="186" class="muted">Language bytes across public, non-fork repositories · updated {escape(updated)}</text>')
    return svg_shell(width, 195, theme, "\n".join(parts), "Top languages by code size")


def render_primary_languages(theme: str, primary_counts: Counter[str], updated: str) -> str:
    t = theme_values(theme)
    total = sum(primary_counts.values())
    if total <= 0:
        raise RuntimeError("No primary-language data found")

    ranked = primary_counts.most_common(8)
    max_count = ranked[0][1]

    parts = [
        '  <text x="28" y="38" class="title">Repositories by Primary Language</text>',
        '  <text x="28" y="62" class="muted">Each public, non-fork repository contributes one vote for its GitHub primary language</text>',
    ]

    start_y = 96
    label_x = 28
    bar_x = 145
    bar_w = 325
    value_x = 535

    for i, (name, count) in enumerate(ranked):
        y = start_y + i * 31
        fill_w = max(8, bar_w * count / max_count)
        pct = count / total * 100
        parts.append(f'  <text x="{label_x}" y="{y + 9}" class="text">{escape(name)}</text>')
        parts.append(f'  <rect x="{bar_x}" y="{y}" width="{bar_w}" height="12" rx="6" fill="{t["track"]}"/>')
        parts.append(f'  <rect x="{bar_x}" y="{y}" width="{fill_w:.2f}" height="12" rx="6" fill="{color_for(name)}"/>')
        parts.append(f'  <text x="{value_x}" y="{y + 9}" text-anchor="end" class="value">{pct:.2f}%</text>')

    parts.append(f'  <text x="28" y="353" class="muted">Share of repositories by primary language · updated {escape(updated)}</text>')
    return svg_shell(560, 365, theme, "\n".join(parts), "Repositories by primary language")


def main() -> None:
    profile = api_get(f"/users/{USERNAME}")
    if not isinstance(profile, dict):
        raise RuntimeError("Unexpected user profile response")

    repos = fetch_public_repos()
    owned_nonfork = [r for r in repos if not r.get("fork") and not r.get("archived")]

    stars = sum(int(r.get("stargazers_count", 0)) for r in owned_nonfork)
    commits = search_total("/search/commits", f"author:{USERNAME}")
    prs = search_total("/search/issues", f"type:pr author:{USERNAME}")
    issues = search_total("/search/issues", f"type:issue author:{USERNAME}")

    stats = {
        "stars": stars,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "repos": len(owned_nonfork),
    }

    language_bytes: Counter[str] = Counter()
    primary_counts: Counter[str] = Counter()

    for repo in owned_nonfork:
        primary = repo.get("language")
        if primary:
            primary_counts[str(primary)] += 1

        full_name = repo.get("full_name")
        if not full_name:
            continue
        lang_data = api_get(f"/repos/{full_name}/languages")
        if not isinstance(lang_data, dict):
            raise RuntimeError(f"Unexpected language response for {full_name}")
        for name, size in lang_data.items():
            language_bytes[str(name)] += int(size)

    OUT.mkdir(parents=True, exist_ok=True)
    updated = datetime.now(timezone.utc).date().isoformat()

    for theme in ("light", "dark"):
        (OUT / f"github-stats-{theme}.svg").write_text(
            render_stats(theme, stats, updated), encoding="utf-8"
        )
        (OUT / f"top-languages-{theme}.svg").write_text(
            render_top_languages(theme, language_bytes, updated), encoding="utf-8"
        )
        (OUT / f"repos-by-primary-language-{theme}.svg").write_text(
            render_primary_languages(theme, primary_counts, updated), encoding="utf-8"
        )

    print(
        f"Updated profile cards: {stats['repos']} repos, "
        f"{sum(language_bytes.values()):,} language bytes, "
        f"{sum(primary_counts.values())} primary-language votes"
    )


if __name__ == "__main__":
    main()
