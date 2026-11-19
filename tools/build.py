#!/usr/bin/env python3
"""
Builds the whole profile: fetches live GitHub data, renders every animated SVG
into /assets and writes README.md from README.template.md + profile.toml.

    python tools/build.py      # normal run (also what the workflow runs)

To change the ID-card photo, replace tools/portrait.webp (transparent-background cutout).

Set GITHUB_TOKEN for higher API limits and GraphQL contributions (Actions does this).
If GitHub can't be reached, the last fetched data in tools/cache/github.json is used.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
import tomllib
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cards  # noqa: E402
import fetch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
CACHE = ROOT / "tools" / "cache" / "github.json"

SKILL_NAMES = {
    "js": "JavaScript", "ts": "TypeScript", "cs": "C#", "cpp": "C++", "py": "Python", "postgres": "PostgreSQL",
    "mysql": "MySQL", "supabase": "Supabase", "vscode": "VS Code", "opencv": "OpenCV", "pytorch": "PyTorch",
    "github": "GitHub", "html": "HTML", "css": "CSS", "nextjs": "Next.js", "nodejs": "Node.js",
}
SHORT_LANG = {"JavaScript": "JS", "TypeScript": "TS", "Jupyter Notebook": "JUPYTER"}


# ------------------------------------------------------------------ data
def load_data(login: str) -> dict | None:
    try:
        data = fetch.fetch(login, os.environ.get("GITHUB_TOKEN"))
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"fetched live data ({len(data['repos'])} repos, calendar via {data['calendar_source']})")
        return data
    except Exception as e:
        print(f"could not fetch GitHub data: {e}")
        if CACHE.exists():
            print("using cached data from", CACHE.relative_to(ROOT))
            return json.loads(CACHE.read_text(encoding="utf-8"))
        return None


def languages(data: dict, top: int = 5) -> list[tuple[str, float]]:
    totals: dict[str, int] = {}
    for r in data["repos"]:
        for lang, b in r["languages"].items():
            totals[lang] = totals.get(lang, 0) + b
    s = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    out = [(k, v * 100 / s) for k, v in ranked[:top]]
    rest = sum(v for _, v in ranked[top:])
    if rest:
        out.append(("Other", rest * 100 / s))
    return out


def streaks(days: list[list]) -> tuple[int, int]:
    best = run = 0
    for _, c in days:
        run = run + 1 if c else 0
        best = max(best, run)
    cur = 0
    seq = [c for _, c in days]
    if seq and seq[-1] == 0:  # today not counted yet: streak may still be alive from yesterday
        seq = seq[:-1]
    for c in reversed(seq):
        if not c:
            break
        cur += 1
    return cur, best


def level(xp: int) -> tuple[int, int, int, int]:
    """(level, total xp, xp where this level started, xp needed for the next level)"""
    lvl = int(math.sqrt(xp / 10)) + 1
    return lvl, xp, 10 * (lvl - 1) ** 2, 10 * lvl ** 2


def stats(data: dict) -> dict:
    c = data["counts"]
    total_contrib = sum(x for _, x in data["calendar"])
    stars = sum(r["stargazers_count"] for r in data["repos"])
    code = sum(sum(r["languages"].values()) for r in data["repos"])
    langs = len({l for r in data["repos"] for l in r["languages"]})
    commits, prs, issues = c.get("commits") or 0, c.get("prs") or 0, c.get("issues") or 0
    xp = total_contrib + commits + 5 * stars + 3 * prs + 10 * data["public_repos"]
    return {
        "tiles": [
            ("COMMITS", commits), ("CONTRIBUTIONS / YR", total_contrib),
            ("PULL REQUESTS", prs), ("ISSUES", issues),
            ("PUBLIC REPOS", data["public_repos"]), ("STARS EARNED", stars),
            ("LANGUAGES", langs), ("CODE WRITTEN", cards.fmt_bytes(code)),
        ],
        "level": level(xp),
    }


# ------------------------------------------------------------------ projects
def pretty(name: str) -> str:
    words = name.replace("-", " ").replace("_", " ").split()
    return " ".join(w.capitalize() if (w.isupper() or w.islower()) else w for w in words)


def project_entry(r: dict | None, e: dict, idx: int) -> dict:
    r = r or {}
    langs = sorted((r.get("languages") or {}).items(), key=lambda kv: -kv[1])
    primary = e.get("lang") or (SHORT_LANG.get(r.get("language"), r.get("language")) or "CODE").upper()
    live = e.get("live", r.get("homepage") or "")
    topics = r.get("topics") or []
    return {
        "repo": r.get("name", e.get("repo")),
        "title": e.get("title") or pretty(r.get("name", e.get("repo", "Project"))),
        "kind": e.get("kind") or (" · ".join(topics[:2]) if topics else (r.get("language") or "project").lower()),
        "desc": e.get("desc") or r.get("description") or r.get("readme_summary") or "Fresh repo, description coming soon.",
        "tags": e.get("tags") or ([k for k, _ in langs[:3]] + [t for t in topics[:1]]) or [primary.title()],
        "lang": primary,
        "live": live,
        "url": live or r.get("html_url") or f"https://github.com/{e.get('repo', '')}",
    }


def featured(cfg: dict, data: dict | None) -> list[dict]:
    repos = {r["name"].lower(): r for r in (data or {}).get("repos", [])}
    entries = cfg.get("project") or []
    if not entries and data:  # nothing ranked yet: best by stars, then most recently active
        ranked = sorted(data["repos"], key=lambda r: (-r["stargazers_count"], r["pushed_at"] or ""), reverse=False)
        entries = [{"repo": r["name"]} for r in ranked[:6]]
    out = []
    for e in entries:
        r = repos.get(e["repo"].lower())
        if data and r is None:
            print(f"  skipping project '{e['repo']}': no public repo with that name")
            continue
        out.append(project_entry(r, e, len(out)))
    return out


# ------------------------------------------------------------------ README pieces
def shield(label: str, message: str = "", color: str = "0a1122", **extra: str) -> str:
    q = lambda s: urllib.parse.quote(s.replace("-", "--").replace("_", "__"))
    path = f"{q(label)}-{q(message)}-{color}" if message else f"{q(label)}-{color}"
    params = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in {"style": "for-the-badge", **extra}.items())
    return f"https://img.shields.io/badge/{path}?{params}"


def stack_html(cfg: dict) -> str:
    rows = []
    for s in cfg.get("stack", []):
        icons = s.get("icons", [])
        cell = []
        if icons:
            alt = ", ".join(SKILL_NAMES.get(i, i.capitalize()) for i in icons)
            cell.append(f'<img src="https://skillicons.dev/icons?i={",".join(icons)}&theme=dark" height="44" alt="{alt}" />')
        for b in s.get("badges", []):
            cell.append(f'<img src="{shield(b["text"], b.get("sub", ""), b.get("color", "3d3c3a"), labelColor="151515")}" height="28" alt="{b["text"]}" />')
        label = s["label"].replace(" ", "&nbsp;")
        rows.append(f"  <tr>\n    <td><b>{label}</b></td>\n    <td>{' '.join(cell)}</td>\n  </tr>")
    return '<table align="center">\n' + "\n".join(rows) + "\n</table>"


def chips_html(cfg: dict) -> str:
    chips = cfg.get("exploring", {}).get("chips", [])
    imgs = [f'  <img src="{shield(t, color=c)}" alt="{t.title()}" />' for t, c in chips]
    return '<p align="center">\n' + "\n".join(imgs) + "\n</p>" if imgs else ""


def projects_html(items: list[dict]) -> str:
    rows = []
    for i in range(0, len(items), 2):
        pair = items[i:i + 2]
        cells = "\n".join(f'  <a href="{p["url"]}"><img src="assets/projects/{i + j + 1:02d}.svg" width="48%" '
                          f'alt="{p["title"]}: {p["desc"][:90]}" /></a>' for j, p in enumerate(pair))
        rows.append(f'<p align="center">\n{cells}\n</p>')
    return "\n".join(rows)


def all_works_md(data: dict | None, items: list[dict]) -> str:
    if not data or not data["repos"]:
        return ""
    by_name = {p["repo"].lower(): p for p in items}
    repos = sorted(data["repos"], key=lambda r: r["pushed_at"] or "", reverse=True)
    lines = [f"<details>\n<summary><b>📂 All works ({len(repos)} public repos, newest first)</b></summary>\n",
             "| Repo | What it is | Language | Updated |", "|---|---|---|---|"]
    for r in repos:
        p = by_name.get(r["name"].lower())
        desc = (p["desc"] if p else (r["description"] or r["readme_summary"] or "")).replace("|", "/")
        if len(desc) > 110:
            desc = desc[:110].rsplit(" ", 1)[0] + "…"
        star = " ⭐" + str(r["stargazers_count"]) if r["stargazers_count"] else ""
        live = f" · [live]({r['homepage']})" if r.get("homepage") else ""
        lines.append(f"| [{r['name']}]({r['html_url']}){star} | {desc}{live} | {r['language'] or '-'} | {(r['pushed_at'] or '')[:10]} |")
    lines.append("\n</details>")
    return "\n".join(lines)


def links_html(cfg: dict, handle: str) -> str:
    L = cfg.get("links", {})
    items = [("GitHub", f"https://github.com/{handle}", "151515", "github")]
    if L.get("linkedin"):
        items.append(("LinkedIn", L["linkedin"], "151515", ""))
    if L.get("instagram"):
        items.append(("Instagram", L["instagram"], "151515", "instagram"))
    if L.get("email"):
        items.append(("Email", f"mailto:{L['email']}", "151515", "gmail"))
    if L.get("website"):
        items.append(("Website", L["website"], "151515", "googlechrome"))
    imgs = []
    for name, url, color, logo in items:
        extra = {"logo": logo, "logoColor": "white"} if logo else {}
        imgs.append(f'  <a href="{url}"><img src="{shield(name, color=color, **extra)}" alt="{name}" /></a>')
    return '<p align="center">\n' + "\n".join(imgs) + "\n</p>"


# ------------------------------------------------------------------ main
def write(rel: str, content: str) -> None:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {rel:<28} {len(content.encode()) / 1024:6.1f} KB")


def main() -> None:
    cfg = tomllib.loads((ROOT / "profile.toml").read_text(encoding="utf-8"))
    handle = cfg["profile"]["handle"]

    data = load_data(handle)
    items = featured(cfg, data)
    sections = {"about": ("01", "WHO AM I", "// whoami"), "stack": ("02", "TECH STACK", "// tools of the trade"),
                "work": ("03", "FEATURED BUILDS", "// level select"), "stats": ("04", "GITHUB STATS", "// grinding xp"),
                "contact": ("05", "CONNECT", "// say hi")}

    print("rendering:")
    avatar = OUT / "avatar.webp"  # 3D turntable, built once by tools/turntable.py
    write("header.svg", cards.header(cfg, avatar.read_bytes() if avatar.exists() else None))
    gh_row = None
    if data:
        total = sum(c for _, c in data["calendar"])
        gh_row = f"{data['public_repos']} public repos · {total} contributions this year"
    photo = ROOT / "tools" / "portrait.webp"  # black-and-white cutout shown on the ID card
    write("id-card.svg", cards.id_card(cfg, photo.read_bytes() if photo.exists() else None, gh_row))
    prof = cfg["profile"]
    write("now.svg", cards.now_card(prof.get("now", [])))
    for key, (num, title, note) in sections.items():
        write(f"sections/{key}.svg", cards.section(num, title, note))
    for old in (OUT / "projects").glob("*.svg"):
        old.unlink()
    for i, p in enumerate(items, 1):
        write(f"projects/{i:02d}.svg", cards.project_card(i, p))
    if data:
        updated = dt.datetime.fromisoformat(data["fetched_at"]).strftime("%d %b %Y").upper()
        write("stats.svg", cards.stats_card(stats(data)))
        write("languages.svg", cards.languages_card(languages(data)))
        write("contributions.svg", cards.contributions_card(data["calendar"], streaks(data["calendar"]), updated))
    write("footer.svg", cards.footer(prof.get("quotes") or ["Keep building."]))

    now_alt = "; ".join(l.split(" // ")[0] for l in prof.get("now", []))
    readme = (ROOT / "README.template.md").read_text(encoding="utf-8")
    for key, val in {
        "HANDLE": handle, "NOW_ALT": now_alt, "STACK": stack_html(cfg), "EXPLORING": chips_html(cfg),
        "PROJECTS": projects_html(items), "ALL_WORKS": all_works_md(data, items), "LINKS": links_html(cfg, handle),
    }.items():
        readme = readme.replace("{{" + key + "}}", val)
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print("wrote README.md")


if __name__ == "__main__":
    main()
