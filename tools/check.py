#!/usr/bin/env python3
"""
Sanity checks for the generated profile. The workflow runs this after
build.py and only commits when every check passes, so a broken build can
never reach your profile.

    python tools/check.py           # offline checks
    python tools/check.py --links   # also request every link and image URL
"""
from __future__ import annotations

import re
import sys
import tomllib
import urllib.request
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []


def check(ok: bool, msg: str) -> None:
    if not ok:
        errors.append(msg)


# ---------------------------------------------------------------- config
cfg = tomllib.loads((ROOT / "profile.toml").read_text(encoding="utf-8"))
p = cfg.get("profile", {})
for key in ("name", "handle", "tagline", "roles", "status", "info", "now", "quotes"):
    check(bool(p.get(key)), f"profile.toml: [profile] {key} is missing or empty")
check(len(p.get("tagline", [])) == 2, "profile.toml: tagline must have exactly 2 parts")
for e in cfg.get("project", []):
    check("repo" in e, f"profile.toml: a [[project]] block has no repo: {e}")

# ---------------------------------------------------------------- SVGs
svgs = sorted((ROOT / "assets").rglob("*.svg"))
check(len(svgs) >= 18, f"expected at least 18 SVGs, found {len(svgs)}")
for f in svgs:
    rel = f.relative_to(ROOT)
    try:
        text = f.read_text(encoding="utf-8")
        xml.dom.minidom.parseString(text)
    except Exception as e:
        check(False, f"{rel}: invalid SVG ({e})")
        continue
    check(f.stat().st_size < 5_000_000, f"{rel}: too large ({f.stat().st_size // 1024} KB)")
    check("font-family:Outfit" in text, f"{rel}: embedded Outfit font missing")
    # every typewriter mask must use the spare step (L+1), see cards.typed()
    for m in re.finditer(r'class="tw"[^>]*translateX\(([\d.]+)px\)[^>]*steps\((\d+),end\)', text):
        check(int(m.group(2)) >= 2, f"{rel}: typewriter mask without spare step")
    for ref in re.findall(r'url\(#([\w-]+)\)', text):
        check(f'id="{ref}"' in text, f"{rel}: references missing id #{ref}")

# ---------------------------------------------------------------- README
readme = (ROOT / "README.md").read_text(encoding="utf-8")
check("{{" not in readme, "README.md: unreplaced {{PLACEHOLDER}}")
check("YOUR-" not in readme, "README.md: placeholder link left in")
for src in re.findall(r'src="(assets/[^"]+)"', readme):
    check((ROOT / src).exists(), f"README.md: image {src} does not exist")
links = re.findall(r'href="([^"]+)"', readme) + re.findall(r"\]\((https?://[^)\s]+)\)", readme)
for href in links:
    check(href.startswith(("https://", "mailto:")), f"README.md: suspicious link {href}")
imgs = re.findall(r'(?:src|srcset)="(https://[^"]+)"', readme)

# ---------------------------------------------------------------- logic
check(build.streaks([["d", 1], ["d", 1], ["d", 0], ["d", 2], ["d", 3]]) == (2, 2), "streaks(): wrong result")
check(build.streaks([["d", 1], ["d", 1], ["d", 0]]) == (2, 2), "streaks(): today=0 should keep yesterday's streak")
check(build.streaks([["d", 0], ["d", 0]]) == (0, 0), "streaks(): empty calendar")
check(build.pretty("MINI_PROJECTS") == "Mini Projects", "pretty(): MINI_PROJECTS")
check(build.pretty("EpicFunds") == "EpicFunds", "pretty(): keeps CamelCase")
check("Local%20LLMs" in build.shield("Ollama", "Local LLMs"), "shield(): spaces not encoded")
check("FINE--TUNING" in build.shield("LLM FINE-TUNING"), "shield(): dashes not escaped")
lvl, xp, lo, hi = build.level(161)
check(lo <= xp < hi, "level(): xp outside its level range")

# ---------------------------------------------------------------- live URLs (optional)
if "--links" in sys.argv:
    seen = set()
    for url in links + imgs:
        if url in seen or url.startswith("mailto:") or "/output/github-snake" in url and "--snake" not in sys.argv:
            continue
        seen.add(url)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-check"})
            code = urllib.request.urlopen(req, timeout=30).status
        except Exception as e:
            code = getattr(e, "code", str(e))
        check(code == 200, f"URL {url} -> {code}")
    print(f"checked {len(seen)} URLs")

if errors:
    print("FAILED:\n  " + "\n  ".join(errors))
    sys.exit(1)
print(f"all checks passed ({len(svgs)} SVGs, {len(links)} links, {len(imgs)} external images)")
