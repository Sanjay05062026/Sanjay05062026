#!/usr/bin/env python3
"""
Renders README.md through GitHub's own Markdown API (same HTML GitHub shows),
then writes _preview.html (dark) and _preview-light.html next to it.

    python tools/preview.py
    python -m http.server 8130      # then open http://localhost:8130/_preview.html
"""
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = "https://cdn.jsdelivr.net/npm/github-markdown-css@5.8.1/github-markdown-{}.css"

md = (ROOT / "README.md").read_text(encoding="utf-8")
req = urllib.request.Request(
    "https://api.github.com/markdown",
    data=json.dumps({"text": md, "mode": "gfm"}).encode(),
    headers={"Accept": "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "readme-preview"},
)
try:
    body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
except Exception as e:  # e.g. GitHub's hourly limit for unauthenticated calls
    body = None
    print(f"GitHub markdown API unavailable ({e}); keeping the last rendered preview")

for name, theme, bg, border in ([] if body is None else [("_preview.html", "dark", "#0d1117", "#30363d"), ("_preview-light.html", "light", "#ffffff", "#d0d7de")]):
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>README preview ({theme})</title>
<link rel="stylesheet" href="{CSS.format(theme)}">
<style>body{{background:{bg};margin:0}}.wrap{{box-sizing:border-box;max-width:896px;margin:24px auto;padding:24px;border:1px solid {border};border-radius:6px}}</style>
</head><body><article class="wrap markdown-body">{body}</article></body></html>"""
    (ROOT / name).write_text(page, encoding="utf-8")
    print("wrote", name)

# One self-contained file (local SVGs inlined) that can be opened or shared on its own.
import base64
import re

src = (ROOT / "_preview.html").read_text(encoding="utf-8")


def _inline(m: re.Match) -> str:
    path = ROOT / m.group(1)
    return f'src="data:image/svg+xml;base64,{base64.b64encode(path.read_bytes()).decode()}"' if path.exists() else m.group(0)


(ROOT / "_preview-standalone.html").write_text(re.sub(r'src="(assets/[^"]+\.svg)"', _inline, src), encoding="utf-8")
print("wrote _preview-standalone.html")
