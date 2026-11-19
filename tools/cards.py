"""
SVG renderers for every card on the profile.

Animation toolkit (pure CSS inside the SVG, which GitHub renders in <img> tags):
  typed()      typewriter: a clip rect slides right in steps(n), one character per step
  loop_typer() typewriter that types, holds, erases and cycles through phrases
  odometer()   rolling-digit counters (each digit is a column of 0-9 that scrolls)
  .grow .pop .draw .in   bars that grow, cells that pop, lines that draw, fades
Every animated element's *base* style is its final state, so with
prefers-reduced-motion (animation:none) the card is still complete.
"""
from __future__ import annotations

import html
import math
import random
import textwrap

CYAN, VIOLET, PINK, GREEN = "#22d3ee", "#a78bfa", "#f472b6", "#4ade80"
BG, PANEL, TILE, LINE = "#060a14", "#0a1122", "#0d1730", "#1c2740"
TEXT, MUTED, DIM = "#e6edf7", "#94a3b8", "#475569"
PALETTE = [CYAN, VIOLET, PINK, "#fbbf24", "#34d399", "#60a5fa", "#fb7185", "#2dd4bf"]
MONO = "'JetBrains Mono','Fira Code','Cascadia Code',Consolas,'DejaVu Sans Mono',monospace"
SANS = "'Segoe UI','Inter',Ubuntu,'Helvetica Neue',Arial,sans-serif"

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "HTML": "#e34c26",
    "CSS": "#8b5cf6", "C#": "#178600", "Java": "#b07219", "C++": "#f34b7d", "C": "#9ca3af",
    "PLpgSQL": "#336790", "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051", "Go": "#00ADD8",
    "Rust": "#dea584", "Kotlin": "#A97BFF", "Dart": "#00B4AB", "PHP": "#4F5D95", "SCSS": "#c6538c",
    "Vue": "#41b883", "Svelte": "#ff3e00", "NSIS": "#cbd5e1", "Dockerfile": "#384d54",
}

GRAD = (
    '<linearGradient id="g" x1="0" y1="0" x2="1" y2="0">'
    f'<stop offset="0" stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/>'
    f'<stop offset="1" stop-color="{PINK}"/></linearGradient>'
)

BASE_CSS = (
    ".m{font-family:" + MONO + "}.s{font-family:" + SANS + "}"
    "@keyframes in{from{opacity:0;transform:translateY(10px)}}"
    ".in{animation:in .7s cubic-bezier(.2,.8,.2,1) both}"
    "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
    ".blink{animation:blink 1.05s steps(1) infinite}"
    "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}"
    ".pulse{animation:pulse 1.8s ease-in-out infinite}"
    "@keyframes run{to{stroke-dashoffset:-1000}}.run{animation:run 8s linear infinite}"
    # one-shot typewriter (duration/delay/steps set inline per element)
    "@keyframes rev{from{transform:translateX(0)}}.tw{animation-name:rev;animation-fill-mode:both}"
    "@keyframes odo{from{transform:translateY(0)}}.odo{animation:odo 1.8s cubic-bezier(.15,.85,.25,1) both}"
    "@keyframes grow{from{transform:scaleX(0)}}"
    ".grow{transform-box:fill-box;transform-origin:left center;animation:grow 1.4s cubic-bezier(.2,.8,.2,1) both}"
    "@keyframes pop{from{opacity:0;transform:scale(.2)}}"
    ".pop{transform-box:fill-box;transform-origin:center;animation:pop .45s cubic-bezier(.2,.8,.3,1.4) both}"
    "@keyframes draw{from{stroke-dashoffset:1000}}.draw{stroke-dasharray:1000;animation:draw 2.4s ease-out both}"
    "@keyframes fade{from{opacity:0}}.fade{animation:fade 1s ease-out both}"
)


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def n(x: float) -> str:
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s


def ts(x: float) -> str:
    """Animation times keep 2 decimals so chained typing stays in sync."""
    return f"{x:.2f}".rstrip("0").rstrip(".") or "0"


class Canvas:
    def __init__(self, w: int, h: int, title: str):
        self.w, self.h, self.title = w, h, title
        self.defs: list[str] = []
        self.css: list[str] = []
        self.body: list[str] = []
        self.reduced: list[str] = []
        self._n = 0

    def uid(self, p: str = "c") -> str:
        self._n += 1
        return f"{p}{self._n}"

    def add(self, *parts: str) -> None:
        self.body.extend(parts)

    def render(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img">\n<title>{esc(self.title)}</title>\n'
            f'<defs>{GRAD}{"".join(self.defs)}</defs>\n'
            f'<style>{BASE_CSS}{"".join(self.css)}'
            f'@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}{"".join(self.reduced)}}}</style>\n'
            + "\n".join(self.body) + "\n</svg>\n"
        )


# ------------------------------------------------------------------ shared pieces
def panel(cv: Canvas, rx: int = 20, fill: str = PANEL) -> None:
    cv.add(f'<rect x=".75" y=".75" width="{cv.w - 1.5}" height="{cv.h - 1.5}" rx="{rx}" '
           f'fill="{fill}" stroke="{LINE}" stroke-width="1.5"/>')


def runner(cv: Canvas, rx: int, color: str, dur: float = 8, seg: int = 70, offset: float = 0) -> None:
    """A short bright segment that keeps running around the card border."""
    cv.add(f'<rect class="run" x=".75" y=".75" width="{cv.w - 1.5}" height="{cv.h - 1.5}" rx="{rx}" '
           f'pathLength="1000" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" '
           f'stroke-dasharray="{seg} {1000 - seg}" style="animation-duration:{n(dur)}s;animation-delay:-{n(offset)}s"/>')


def title_bar(cv: Canvas, label: str, right: str | None = None, right_fill: str = CYAN, live: bool = False) -> None:
    cv.add("".join(f'<circle cx="{28 + i * 20}" cy="23" r="6" fill="{c}"/>'
                   for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"])))
    cv.add(f'<text x="96" y="28" class="m" font-size="13" fill="{MUTED}">{esc(label)}</text>')
    if right:
        x = cv.w - 28
        cv.add(f'<text x="{x}" y="28" text-anchor="end" class="m" font-size="12" letter-spacing="2.5" fill="{right_fill}">{esc(right)}</text>')
        if live:
            cv.add(f'<circle class="pulse" cx="{n(x - len(right) * 9.7 - 12)}" cy="23" r="4.5" fill="{right_fill}"/>')
    cv.add(f'<rect x="1" y="46" width="{cv.w - 2}" height="1" fill="{LINE}"/>')


def typed(cv: Canvas, x: float, y: float, plain: str, fs: float, delay: float, *, content: str | None = None,
          fill: str = TEXT, weight: int | None = None, spacing: float = 0.0, speed: float = 0.018,
          anchor: str = "start", cls: str = "m") -> tuple[float, float]:
    """Monospace text that types itself in once. Returns (time it finishes, x where it ends)."""
    L = max(len(plain), 1)
    cw = fs * 0.6 + spacing
    w = L * cw
    x0 = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
    dur = max(0.1, L * speed)
    cid = cv.uid("t")
    # The mask travels one spare character (L+1 steps over w+cw). Browsers sometimes finish an
    # animation at progress 0.9999999 instead of 1, which drops the last step: with the spare
    # step that lost step is the empty one, so the final character is always shown.
    travel = w + cw
    cv.defs.append(
        f'<clipPath id="{cid}"><rect class="tw" x="{n(x0 - travel)}" y="{n(y - fs * 1.1)}" width="{n(travel)}" height="{n(fs * 1.6)}" '
        f'style="transform:translateX({n(travel)}px);animation-duration:{ts(dur)}s;animation-delay:{ts(delay)}s;'
        f'animation-timing-function:steps({L + 1},end)"/></clipPath>')
    wt = f' font-weight="{weight}"' if weight else ""
    cv.add(f'<text x="{n(x0)}" y="{n(y)}" class="{cls}" font-size="{n(fs)}"{wt} fill="{fill}" '
           f'textLength="{n(w)}" xml:space="preserve" clip-path="url(#{cid})">'
           f'{content if content is not None else esc(plain)}</text>')
    return delay + dur, x0 + w


def caret(cv: Canvas, x: float, y: float, fs: float, delay: float, color: str = CYAN) -> None:
    cv.add(f'<g class="in" style="animation-delay:{n(delay)}s"><rect class="blink" x="{n(x + 3)}" y="{n(y - fs * .82)}" '
           f'width="{n(max(3, fs * .5))}" height="{n(fs * 1.02)}" fill="{color}" opacity=".9"/></g>')


def loop_typer(cv: Canvas, phrases: list[str], cx: float, y: float, fs: float, fill: str, *, start: float = 1.0,
               slot: float = 3.4, prompt: str = ">", prompt_fill: str = VIOLET, weight: int = 600, key: str = "lt") -> None:
    """Types a phrase, holds it, erases it, then moves on to the next one, forever."""
    CW = fs * 0.6
    T = slot * len(phrases)

    def pc(t: float) -> str:
        return f"{t / T * 100:.3f}%"

    type_end, hold_end, erase_end = min(.75, slot * .2), slot * .8, slot * .9
    cv.css.append(f"@keyframes {key}w{{0%,{pc(slot - .05)}{{opacity:1}}{pc(slot)},100%{{opacity:0}}}}"
                  f".{key}{{opacity:0;animation:{key}w {n(T)}s steps(1) infinite}}")
    pre = len(prompt) + 1 if prompt else 0
    for i, ph in enumerate(phrases):
        L = len(ph)
        Wt = L * CW
        x0 = cx - (L + pre) * CW / 2
        tx = x0 + pre * CW
        d = start + i * slot
        cv.css.append(
            f"@keyframes {key}r{i}{{0%{{transform:translateX(0);animation-timing-function:steps({L},end)}}"
            f"{pc(type_end)}{{transform:translateX({n(Wt)}px);animation-timing-function:linear}}"
            f"{pc(hold_end)}{{transform:translateX({n(Wt)}px);animation-timing-function:steps({L},end)}}"
            f"{pc(erase_end)},100%{{transform:translateX(0)}}}}"
            f".{key}r{i}{{animation:{key}r{i} {n(T)}s {n(d)}s infinite}}.{key}{i}{{animation-delay:{n(d)}s}}")
        cv.defs.append(f'<clipPath id="{key}c{i}"><rect class="{key}r{i}" x="{n(tx - Wt)}" y="{n(y - fs * 1.1)}" '
                       f'width="{n(Wt)}" height="{n(fs * 1.6)}"/></clipPath>')
        p = (f'<text x="{n(x0)}" y="{n(y)}" class="m" font-size="{n(fs)}" font-weight="700" fill="{prompt_fill}">'
             f'{esc(prompt)}</text>') if prompt else ""
        cv.add(f'<g class="{key} {key}{i}">{p}'
               f'<text x="{n(tx)}" y="{n(y)}" class="m" font-size="{n(fs)}" font-weight="{weight}" fill="{fill}" '
               f'textLength="{n(Wt)}" xml:space="preserve" clip-path="url(#{key}c{i})">{esc(ph)}</text>'
               f'<g class="blink"><rect class="{key}r{i}" x="{n(tx + 3)}" y="{n(y - fs * .8)}" width="3" '
               f'height="{n(fs)}" fill="{fill}"/></g></g>')
    cv.reduced.append(f".{key}.{key}0{{opacity:1}}.{key}r0{{transform:translateX({n(len(phrases[0]) * CW)}px)}}")


def odometer(cv: Canvas, x: float, y: float, text: str, fs: float, delay: float, *, fill: str = TEXT,
             weight: int = 800, anchor: str = "start") -> float:
    """Rolling-digit counter. Each digit spins up from 0 and lands on its value. Returns the end x."""
    cw = fs * 0.62
    lh = fs * 1.25
    w = len(text) * cw
    x0 = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
    cid = cv.uid("o")
    cv.defs.append(f'<clipPath id="{cid}"><rect x="{n(x0 - 2)}" y="{n(y - fs * .95)}" width="{n(w + 4)}" height="{n(fs * 1.22)}"/></clipPath>')
    parts = [f'<g clip-path="url(#{cid})" class="m" font-size="{n(fs)}" font-weight="{weight}" fill="{fill}" text-anchor="middle">']
    for i, ch in enumerate(text):
        cx = x0 + (i + .5) * cw
        if ch.isdigit():
            seq = [k % 10 for k in range(10 + int(ch) + 1)]  # one full spin, then land
            col = "".join(f'<text x="{n(cx)}" y="{n(y + k * lh)}">{s}</text>' for k, s in enumerate(seq))
            parts.append(f'<g class="odo" style="transform:translateY(-{n((len(seq) - 1) * lh)}px);'
                         f'animation-delay:{n(delay + i * .07)}s;animation-duration:{n(1.5 + i * .15)}s">{col}</g>')
        else:
            parts.append(f'<text x="{n(cx)}" y="{n(y)}">{esc(ch)}</text>')
    parts.append("</g>")
    cv.add("".join(parts))
    return x0 + w


# ------------------------------------------------------------------ header
def header(cfg: dict) -> str:
    p = cfg["profile"]
    NAME, HANDLE, TAG, ROLES = p["name"], p["handle"], p["tagline"], p["roles"]
    W, H, HZ = 1200, 360, 304
    cx = W / 2
    rnd = random.Random(7)
    cv = Canvas(W, H, f"{NAME}: {' '.join(TAG)}")
    NY, FS, LS = 198, 112, 18
    name_attrs = (f'x="{n(cx + LS / 2)}" y="{NY}" text-anchor="middle" '
                  f'font-size="{FS}" font-weight="900" letter-spacing="{LS}"')

    cv.defs.append(
        f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>'
        f'<radialGradient id="gl1" cx=".16" cy=".95" r=".6"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".38"/>'
        f'<stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="gl2" cx=".86" cy=".05" r=".55"><stop offset="0" stop-color="{CYAN}" stop-opacity=".24"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="gl3" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{PINK}" stop-opacity=".16"/>'
        f'<stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>'
        '<pattern id="crt" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#fff" fill-opacity=".03"/></pattern>'
        '<linearGradient id="ff" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".45" stop-color="#fff" stop-opacity=".65"/><stop offset="1" stop-color="#fff"/></linearGradient>'
        f'<mask id="floor"><rect y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#ff)"/></mask>'
        f'<linearGradient id="hz" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0">'
        f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset=".3" stop-color="{CYAN}"/>'
        f'<stop offset=".7" stop-color="{VIOLET}"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".9" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".75"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<filter id="glow" x="-10%" y="-40%" width="120%" height="180%"><feGaussianBlur stdDeviation="9" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f'<clipPath id="nameclip"><text {name_attrs} class="s">{esc(NAME)}</text></clipPath>'
        f'<clipPath id="band1"><rect x="0" y="{NY - 82}" width="{W}" height="26"/></clipPath>'
        f'<clipPath id="band2"><rect x="0" y="{NY - 42}" width="{W}" height="22"/></clipPath>')

    cv.add('<g clip-path="url(#frame)">', f'<rect width="{W}" height="{H}" fill="{BG}"/>',
           f'<rect width="{W}" height="{H}" fill="url(#gl1)"/>', f'<rect width="{W}" height="{H}" fill="url(#gl2)"/>',
           f'<ellipse cx="{cx}" cy="{NY - 40}" rx="420" ry="120" fill="url(#gl3)"/>',
           f'<rect width="{W}" height="{H}" fill="url(#crt)"/>')

    # retro floor: each horizontal line moves exactly one slot per loop (SMIL), so it is seamless
    fl = [f'<g mask="url(#floor)" stroke="{CYAN}" stroke-width="1" stroke-opacity=".5">']
    for k in range(-15, 16):
        fl.append(f'<line x1="{n(cx + k * 6)}" y1="{HZ}" x2="{n(cx + k * 115)}" y2="{H + 40}"/>')
    F = H + 16 - HZ
    for k in range(12):
        ys = [min(HZ + F / max(1 + k - t / 12, 0.05), H + 40) for t in range(13)]
        anim = f'values="{";".join(n(v) for v in ys)}" dur="1.5s" repeatCount="indefinite"'
        fl.append(f'<line x1="0" x2="{W}" y1="{n(ys[0])}" y2="{n(ys[0])}">'
                  f'<animate attributeName="y1" {anim}/><animate attributeName="y2" {anim}/></line>')
    fl.append("</g>")
    cv.add(*fl)
    cv.add(f'<rect x="0" y="{HZ - 1}" width="{W}" height="2" fill="url(#hz)"/>',
           f'<rect x="0" y="{HZ - 6}" width="{W}" height="12" fill="url(#hz)" opacity=".25" filter="url(#glow)"/>')

    cv.css.append("@keyframes up{0%{transform:translateY(0);opacity:0}20%,80%{opacity:1}100%{transform:translateY(-80px);opacity:0}}"
                  ".pt{animation:up 10s linear infinite}")
    for _ in range(40):
        d = rnd.uniform(7, 15)
        cv.add(f'<circle class="pt" cx="{n(rnd.uniform(20, W - 20))}" cy="{n(rnd.uniform(70, H))}" r="{n(rnd.uniform(.6, 2))}" '
               f'fill="{rnd.choice([CYAN, VIOLET, PINK, "#ffffff"])}" fill-opacity="{n(rnd.uniform(.35, .9))}" '
               f'style="animation-duration:{n(d)}s;animation-delay:-{n(rnd.uniform(0, d))}s"/>')

    title_bar(cv, f"~/{HANDLE}/README.md", "ONLINE", GREEN, live=True)

    # welcome line types itself in
    typed(cv, cx, 98, "••• WELCOME TO MY WORLD •••", 14, .2, spacing=5, anchor="middle", fill=MUTED, speed=.015,
          content=f'<tspan fill="{CYAN}">•••</tspan> WELCOME TO MY WORLD <tspan fill="{CYAN}">•••</tspan>')

    cv.css.append(
        "@keyframes intro{from{opacity:0;transform:translateY(22px)}}.intro{animation:intro 1.4s cubic-bezier(.2,.8,.2,1) .5s both}"
        "@keyframes fl{0%,86%,90%,100%{opacity:1}87%{opacity:.7}89%{opacity:.9}}.nm{animation:fl 5s infinite}"
        "@keyframes gA{0%,86%,100%{opacity:0;transform:translate(0,0)}87%{opacity:.9;transform:translate(-8px,0)}"
        "88%{opacity:.9;transform:translate(6px,0)}89%{opacity:0}}"
        "@keyframes gB{0%,92%,100%{opacity:0;transform:translate(0,0)}93%{opacity:.9;transform:translate(7px,0)}"
        "94%{opacity:.9;transform:translate(-5px,0)}95%{opacity:0}}"
        ".g1{opacity:0;animation:gA 5s steps(1) infinite}.g2{opacity:0;animation:gB 5s steps(1) infinite}"
        "@keyframes sh{0%{transform:translateX(0)}55%,100%{transform:translateX(1750px)}}"
        ".shine{animation:sh 6s cubic-bezier(.45,0,.2,1) 1.8s infinite}"
        "@keyframes scan{to{transform:translateY(460px)}}.scan{animation:scan 7s linear infinite}")
    cv.add('<g class="intro">',
           f'<text {name_attrs} fill="url(#g)" filter="url(#glow)" class="s nm">{esc(NAME)}</text>',
           f'<g clip-path="url(#band1)"><text {name_attrs} fill="{CYAN}" class="s g1">{esc(NAME)}</text></g>',
           f'<g clip-path="url(#band2)"><text {name_attrs} fill="{PINK}" class="s g2">{esc(NAME)}</text></g>',
           f'<g clip-path="url(#nameclip)"><g transform="skewX(-20)"><rect class="shine" x="-300" y="{NY - FS}" '
           f'width="150" height="{FS + 30}" fill="url(#shine)" opacity=".55"/></g></g>', "</g>")

    loop_typer(cv, ROLES, cx, 250, 26, CYAN, start=1.4, slot=3.4, key="rl")

    cv.add(f'<text x="{cx}" y="288" text-anchor="middle" class="s in" font-size="20" fill="{MUTED}" style="animation-delay:1.2s">'
           f'{esc(TAG[0])} <tspan fill="{PINK}" font-style="italic">{esc(TAG[1])}</tspan></text>',
           f'<rect class="scan" y="-100" width="{W}" height="100" fill="url(#scan)"/>', "</g>",
           f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="20" fill="none" stroke="url(#g)" stroke-opacity=".45" stroke-width="1.5"/>')
    runner(cv, 20, CYAN, 9, 60)
    runner(cv, 20, PINK, 9, 60, 4.5)
    return cv.render()


# ------------------------------------------------------------------ ID card
def id_card(cfg: dict, dots: dict | None, github_row: str | None) -> str:
    p = cfg["profile"]
    W, H = 1200, 540
    BX, BY, BS = 40, 82, 410
    cv = Canvas(W, H, "Sanjay: system.info ID card")
    cv.defs.append(
        f'<linearGradient id="pg" gradientUnits="userSpaceOnUse" x1="{BX}" y1="{BY}" x2="{BX + BS}" y2="{BY + BS}">'
        f'<stop offset="0" stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<clipPath id="box"><rect x="{BX}" y="{BY}" width="{BS}" height="{BS}" rx="10"/></clipPath>'
        f'<clipPath id="reveal"><rect class="prev" x="{BX}" y="{BY - BS}" width="{BS}" height="{BS}"/></clipPath>'
        f'<pattern id="bgrid" width="20" height="20" patternUnits="userSpaceOnUse" x="{BX}" y="{BY}">'
        f'<path d="M20 0H0V20" fill="none" stroke="{LINE}" stroke-width="1" stroke-opacity=".55"/></pattern>'
        f'<linearGradient id="scanv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity=".22"/></linearGradient>'
        '<linearGradient id="vline" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{VIOLET}" stop-opacity=".6"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    cv.css.append(
        f".prev{{transform:translateY({BS}px);animation:prev 2.6s cubic-bezier(.2,.8,.2,1) .3s both}}"
        "@keyframes prev{from{transform:translateY(0)}}"
        "@keyframes br{50%{opacity:.8}}.breathe{animation:br 4s ease-in-out 3s infinite}"
        f"@keyframes sc{{to{{transform:translateY({BS + 80}px)}}}}.sc{{animation:sc 3.8s linear infinite}}")

    panel(cv)
    title_bar(cv, "sanjay@github: ~/system.info", "PLAYER_01")

    cv.add(f'<rect x="{BX}" y="{BY}" width="{BS}" height="{BS}" rx="10" fill="#050913"/>',
           f'<rect x="{BX}" y="{BY}" width="{BS}" height="{BS}" rx="10" fill="url(#bgrid)"/>')
    if dots:
        cell = BS / dots["grid"]
        circles = "".join(f'<circle cx="{n(BX + (c + .5) * cell)}" cy="{n(BY + (r + .5) * cell)}" r="{n(s * cell * 1.08)}"/>'
                          for c, r, s in dots["dots"])
        cv.add(f'<g clip-path="url(#reveal)"><g class="breathe" fill="url(#pg)">{circles}</g></g>')
    cv.add(f'<g clip-path="url(#box)"><rect class="sc" x="{BX}" y="{BY - 80}" width="{BS}" height="78" fill="url(#scanv)"/>'
           f'<rect class="sc" x="{BX}" y="{BY - 2}" width="{BS}" height="2" fill="{CYAN}" opacity=".85"/></g>')
    k = 24
    for (x, y, dx, dy) in [(BX, BY, 1, 1), (BX + BS, BY, -1, 1), (BX, BY + BS, 1, -1), (BX + BS, BY + BS, -1, -1)]:
        cv.add(f'<path d="M{x} {y + dy * k}V{y}H{x + dx * k}" fill="none" stroke="{CYAN}" stroke-width="2.5"/>')
    cv.add(f'<text x="{BX + 16}" y="{BY + 26}" class="m" font-size="11" letter-spacing="2" fill="{CYAN}">SUBJECT_01</text>',
           f'<circle class="pulse" cx="{BX + BS - 52}" cy="{BY + 22}" r="4" fill="#ef4444"/>',
           f'<text x="{BX + BS - 16}" y="{BY + 26}" text-anchor="end" class="m" font-size="11" letter-spacing="2" fill="#fca5a5">REC</text>')
    pw = 186
    cv.add(f'<g class="pulse" style="animation-duration:2.6s"><rect x="{BX + (BS - pw) / 2}" y="{BY + BS - 40}" width="{pw}" height="24" rx="12" '
           f'fill="#052e1a" stroke="#22c55e" stroke-opacity=".7"/><text x="{BX + BS / 2}" y="{BY + BS - 24}" text-anchor="middle" '
           f'class="m" font-size="11" letter-spacing="2" fill="{GREEN}">IDENTITY VERIFIED</text></g>',
           f'<rect x="476" y="70" width="1" height="{H - 110}" fill="url(#vline)"/>')

    # terminal side: the command types, then every row types after the previous one
    X, FS = 506, 15
    CW = FS * .6
    prompt = f'<tspan fill="{CYAN}">sanjay@github</tspan><tspan fill="{MUTED}">:~$ </tspan>'
    t, _ = typed(cv, X, 116, "sanjay@github:~$ whoami", 16, .4, speed=.025,
                 content=prompt + f'<tspan fill="{TEXT}">whoami</tspan>')
    rows = [tuple(r) for r in p["info"]]
    if github_row:
        rows.append(("GITHUB", github_row))
    rows.append(("STATUS", p["status"]))
    key_w = 13
    y0 = 166
    step = min(38, (H - 110 - y0) / (len(rows) + 1))
    t += .1
    for i, (key, val) in enumerate(rows):
        y = y0 + i * step
        label = (key + " ").ljust(key_w - 1, ".") + " "
        if key == "STATUS":
            vx = X + key_w * CW
            cv.add(f'<circle class="pulse" cx="{n(vx + 6)}" cy="{n(y - 5)}" r="5" fill="{GREEN}" style="animation-delay:{n(t)}s"/>')
            plain = label + "  " + val
            content = f'<tspan fill="{CYAN}">{esc(label)}</tspan>  <tspan fill="{GREEN}">{esc(val)}</tspan>'
        else:
            plain = label + val
            content = f'<tspan fill="{CYAN}">{esc(label)}</tspan><tspan fill="{TEXT}">{esc(val)}</tspan>'
        t, _ = typed(cv, X, y, plain, FS, t, content=content, speed=.008)
        t += .03
    yl = y0 + len(rows) * step + 14
    end, ex = typed(cv, X, yl, "sanjay@github:~$ ./build --mode=fun", 16, t + .1, speed=.02,
                    content=prompt + f'<tspan fill="{TEXT}">./build --mode=fun</tspan>')
    caret(cv, ex, yl, 16, end)
    runner(cv, 20, VIOLET, 10, 50)
    return cv.render()


# ------------------------------------------------------------------ now.log
def now_card(lines: list[str]) -> str:
    W = 1200
    H = 124 + 34 * (len(lines) + 1)  # +1 row for the blinking caret line
    cv = Canvas(W, H, "now.log: " + "; ".join(l.replace(" // ", " (") + (")" if " // " in l else "") for l in lines))
    panel(cv)
    title_bar(cv, "sanjay@github: ~/now.log", "LIVE", PINK, live=True)
    prompt = f'<tspan fill="{CYAN}">sanjay@github</tspan><tspan fill="{MUTED}">:~$ </tspan>'
    t, _ = typed(cv, 36, 86, "sanjay@github:~$ tail -f now.log", 16, .3, speed=.022,
                 content=prompt + f'<tspan fill="{TEXT}">tail -f now.log</tspan>')
    t += .2
    y = 86
    for i, line in enumerate(lines):
        y = 120 + i * 34
        text, _, note = line.partition(" // ")
        tag = f"[{i + 1:02d}] "
        plain = tag + text + (f"   // {note}" if note else "")
        content = (f'<tspan fill="{VIOLET}">{esc(tag)}</tspan><tspan fill="{TEXT}">{esc(text)}</tspan>'
                   + (f'<tspan fill="{DIM}">   // {esc(note)}</tspan>' if note else ""))
        t, ex = typed(cv, 36, y, plain, 16, t, content=content, speed=.012)
        t += .05
    caret(cv, 36, y + 34, 16, t, PINK)
    runner(cv, 20, PINK, 9, 50)
    return cv.render()


# ------------------------------------------------------------------ section bar
def section(num: str, title: str, note: str) -> str:
    W, H = 1200, 84
    cv = Canvas(W, H, f"{num} {title}")
    cv.defs.append(f'<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}"/>'
                   f'<stop offset="1" stop-color="{PINK}"/></linearGradient>')
    cv.css.append("@keyframes trav{0%{transform:translateX(0);opacity:0}10%,90%{opacity:1}100%{transform:translateX(var(--d));opacity:0}}"
                  ".trav{animation:trav 3.6s cubic-bezier(.6,0,.4,1) 2s infinite;opacity:0}")
    panel(cv, 14)
    cv.add(f'<rect x="22" y="22" width="6" height="40" rx="3" fill="url(#bar)"/>')
    t, _ = typed(cv, 46, 52, num, 18, .1, fill=CYAN, weight=700, speed=.04)
    t, ex = typed(cv, 92, 54, title, 26, t + .05, fill=TEXT, weight=800, spacing=4, speed=.028)
    caret(cv, ex, 54, 26, t)
    lx = ex + 40
    rx = W - 40 - len(note) * 7.8 - 24
    if rx > lx + 40:
        cv.defs.append(f'<linearGradient id="ln" gradientUnits="userSpaceOnUse" x1="{n(lx)}" y1="0" x2="{n(rx)}" y2="0">'
                       f'<stop offset="0" stop-color="{CYAN}" stop-opacity=".8"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>')
        cv.add(f'<rect class="grow" x="{n(lx)}" y="41" width="{n(rx - lx)}" height="2" fill="url(#ln)" style="animation-delay:{n(t)}s"/>',
               f'<circle class="trav" cx="{n(lx)}" cy="42" r="3.5" fill="{CYAN}" style="--d:{n(rx - lx)}px"/>')
    typed(cv, W - 40, 48, note, 13, t + .15, fill=MUTED, anchor="end", speed=.015)
    runner(cv, 14, CYAN, 10, 40)
    return cv.render()


# ------------------------------------------------------------------ project card
def project_card(i: int, p: dict) -> str:
    W, H = 520, 280
    col = p["color"]
    cv = Canvas(W, H, f"Project {i:02d}: {p['title']}")
    cv.defs.append(
        f'<radialGradient id="cg" cx="1" cy="0" r=".9"><stop offset="0" stop-color="{col}" stop-opacity=".26"/>'
        f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>'
        f'<pattern id="dg" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{TEXT}" fill-opacity=".07"/></pattern>'
        f'<clipPath id="cf"><rect width="{W}" height="{H}" rx="18"/></clipPath>')
    cv.css.append("@keyframes glo{50%{opacity:.55}}.glo{animation:glo 5s ease-in-out infinite}")
    panel(cv, 18)
    cv.add(f'<g clip-path="url(#cf)"><rect width="{W}" height="{H}" fill="url(#dg)"/><rect class="glo" width="{W}" height="{H}" fill="url(#cg)"/></g>')
    typed(cv, 28, 42, f"PROJECT_{i:02d}", 12, .2, fill=col, spacing=3, speed=.025)

    x = W - 28
    pills = [(p["lang"], col, False)] + ([("LIVE", GREEN, True)] if p.get("live") else [])
    for k, (label, c, dot) in enumerate(reversed(pills)):
        w = len(label) * 6.8 + (34 if dot else 22)
        x -= w
        g = [f'<g class="pop" style="animation-delay:{n(.4 + k * .1)}s">',
             f'<rect x="{n(x)}" y="25" width="{n(w)}" height="24" rx="12" fill="{c}" fill-opacity=".1" stroke="{c}" stroke-opacity=".55"/>']
        if dot:
            g.append(f'<circle class="pulse" cx="{n(x + 13)}" cy="37" r="4" fill="{c}"/>')
        g.append(f'<text x="{n(x + (24 if dot else 11))}" y="41.5" class="m" font-size="11" letter-spacing="1.5" fill="{c}">{esc(label)}</text></g>')
        cv.add("".join(g))
        x -= 8

    cv.add(f'<text x="28" y="90" class="s in" font-size="28" font-weight="800" fill="{TEXT}" style="animation-delay:.5s">{esc(p["title"])}</text>')
    typed(cv, 28, 116, p["kind"], 12.5, .5, fill=MUTED, speed=.012)
    for j, line in enumerate(textwrap.wrap(p["desc"], 56)[:3]):
        cv.add(f'<text x="28" y="{150 + j * 23}" class="s in" font-size="15.5" fill="#aab6cb" style="animation-delay:{n(1 + j * .12)}s">{esc(line)}</text>')
    x = 28
    for k, t in enumerate(p["tags"]):
        w = len(t) * 7.2 + 24
        if x + w > W - 92:
            break
        cv.add(f'<g class="pop" style="animation-delay:{n(1.4 + k * .1)}s"><rect x="{n(x)}" y="226" width="{n(w)}" height="28" rx="8" '
               f'fill="{col}" fill-opacity=".08" stroke="{col}" stroke-opacity=".35"/><text x="{n(x + w / 2)}" y="245" text-anchor="middle" '
               f'class="m" font-size="12" fill="{TEXT}">{esc(t)}</text></g>')
        x += w + 8
    cv.add(f'<text x="{W - 28}" y="245" text-anchor="end" class="m in" font-size="12" letter-spacing="2" fill="{col}" style="animation-delay:1.8s">VIEW ↗</text>')
    runner(cv, 18, col, 7, 90, i * 1.3)
    return cv.render()


# ------------------------------------------------------------------ stats card
def fmt_bytes(b: int) -> str:
    return f"{b / 1e6:.1f}MB" if b >= 1e6 else f"{max(1, round(b / 1e3))}KB"


def stats_card(s: dict) -> str:
    W, H = 600, 380
    cv = Canvas(W, H, "GitHub stats: " + ", ".join(f"{k} {v}" for k, v in s["tiles"]))
    panel(cv)
    title_bar(cv, "~/stats.json", "LIVE", GREEN, live=True)
    x0, y0, cw, rh = 26, 64, 278, 62
    for i, (label, value) in enumerate(s["tiles"]):
        cx = x0 + (i % 2) * (cw + 8)
        ty = y0 + (i // 2) * rh
        c = PALETTE[i % len(PALETTE)]
        d = .2 + i * .08
        cv.add(f'<g class="in" style="animation-delay:{n(d)}s"><rect x="{cx}" y="{ty}" width="{cw}" height="54" rx="10" fill="{TILE}" stroke="{LINE}"/>'
               f'<rect x="{cx}" y="{ty + 12}" width="3" height="30" rx="1.5" fill="{c}"/></g>')
        typed(cv, cx + 18, ty + 22, label, 11, d + .1, fill=MUTED, spacing=1.2, speed=.012)
        odometer(cv, cx + 18, ty + 46, str(value), 22, d + .3, fill=TEXT)

    # a little game-style XP bar (for fun: built from your real numbers)
    lvl, xp, lo, hi = s["level"]
    by = y0 + 4 * rh + 18
    typed(cv, x0, by + 10, f"LVL {lvl}", 13, 1.2, fill=CYAN, weight=700, speed=.03)
    tx0, tx1 = x0 + 74, W - 150
    frac = max(.04, min(1, (xp - lo) / max(1, hi - lo)))
    cv.add(f'<rect x="{tx0}" y="{by}" width="{tx1 - tx0}" height="12" rx="6" fill="{TILE}" stroke="{LINE}"/>',
           f'<rect class="grow" x="{tx0}" y="{by}" width="{n((tx1 - tx0) * frac)}" height="12" rx="6" fill="url(#g)" style="animation-delay:1.4s;animation-duration:2s"/>')
    typed(cv, W - 26, by + 10, f"{xp} / {hi} XP", 12, 1.6, fill=MUTED, anchor="end", speed=.02)
    runner(cv, 20, GREEN, 9, 50)
    return cv.render()


# ------------------------------------------------------------------ languages card
def languages_card(langs: list[tuple[str, float]]) -> str:
    W, H = 600, 380
    cv = Canvas(W, H, "Most used languages: " + ", ".join(f"{l} {p:.1f}%" for l, p in langs))
    panel(cv)
    title_bar(cv, "~/languages.lock", "BY CODE SIZE", VIOLET)
    bx, bw, by = 30, W - 60, 76
    cv.defs.append(f'<clipPath id="sb"><rect x="{bx}" y="{by}" width="{bw}" height="14" rx="7"/></clipPath>')
    cv.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="14" rx="7" fill="{TILE}"/>', '<g clip-path="url(#sb)">')
    x = bx
    for i, (name, pct) in enumerate(langs):
        w = bw * pct / 100
        cv.add(f'<rect class="grow" x="{n(x)}" y="{by}" width="{n(w + .5)}" height="14" fill="{LANG_COLORS.get(name, PALETTE[i % 8])}" '
               f'style="animation-delay:{n(.3 + i * .12)}s"/>')
        x += w
    cv.add("</g>")
    top = max(p for _, p in langs) if langs else 1
    for i, (name, pct) in enumerate(langs):
        y = 130 + i * 40
        c = LANG_COLORS.get(name, PALETTE[i % 8])
        d = .6 + i * .12
        cv.add(f'<circle class="pop" cx="{bx + 7}" cy="{y - 5}" r="6" fill="{c}" style="animation-delay:{n(d)}s"/>')
        typed(cv, bx + 24, y, name, 14, d, fill=TEXT, speed=.018)
        tx0, tx1 = 230, W - 120
        cv.add(f'<rect x="{tx0}" y="{y - 10}" width="{tx1 - tx0}" height="8" rx="4" fill="{TILE}"/>',
               f'<rect class="grow" x="{tx0}" y="{y - 10}" width="{n(max(4, (tx1 - tx0) * pct / top))}" height="8" rx="4" fill="{c}" '
               f'style="animation-delay:{n(d + .1)}s"/>')
        odometer(cv, W - 30, y, f"{pct:.1f}%", 15, d + .1, fill=MUTED, weight=600, anchor="end")
    runner(cv, 20, VIOLET, 9, 50, 3)
    return cv.render()


# ------------------------------------------------------------------ contributions card
LEVELS = ["#111a2e", "#155e75", "#0891b2", "#8b5cf6", "#f472b6"]


def contributions_card(days: list[list], streaks: tuple[int, int], updated: str) -> str:
    import datetime as dt

    W, H = 1200, 372
    total = sum(c for _, c in days)
    cur, best = streaks
    cv = Canvas(W, H, f"{total} contributions in the last year, current streak {cur} days, longest {best} days")
    panel(cv)
    title_bar(cv, "~/contributions.log", f"UPDATED {updated}", MUTED)

    # top row: odometers + 30-day sparkline
    typed(cv, 36, 84, "CONTRIBUTIONS · LAST 12 MONTHS", 11, .2, fill=MUTED, spacing=1.5, speed=.02)
    odometer(cv, 36, 132, str(total), 44, .4, fill=TEXT, weight=800)
    for k, (label, val, x) in enumerate([("CURRENT STREAK", cur, 380), ("LONGEST STREAK", best, 590)]):
        typed(cv, x, 84, label, 11, .3 + k * .1, fill=MUTED, spacing=1.5, speed=.025)
        ex = odometer(cv, x, 132, str(val), 44, .5 + k * .1, fill=PINK if k == 0 else VIOLET)
        cv.add(f'<text x="{n(ex + 10)}" y="132" class="m in" font-size="14" fill="{MUTED}" style="animation-delay:1.4s">'
               f'{"day" if val == 1 else "days"}</text>')
        if k == 0 and cur > 0:
            cv.add(f'<text x="{n(ex + 58)}" y="130" class="pulse" font-size="22">🔥</text>')

    last = [c for _, c in days[-30:]]
    sx0, sx1, sy0, sy1 = 800, W - 36, 72, 140
    mx = max(last + [1])
    pts = [(sx0 + (sx1 - sx0) * i / max(1, len(last) - 1), sy1 - (sy1 - sy0) * c / mx) for i, c in enumerate(last)]
    line = "M" + " L".join(f"{n(x)} {n(y)}" for x, y in pts)
    cv.defs.append(f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity=".35"/>'
                   f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>')
    typed(cv, sx1, 64, "LAST 30 DAYS", 10, .4, fill=MUTED, spacing=1.5, anchor="end", speed=.03)
    cv.add(f'<path class="fade" d="{line} L{n(sx1)} {sy1} L{sx0} {sy1}Z" fill="url(#area)" style="animation-delay:1.6s"/>',
           f'<path class="draw" d="{line}" pathLength="1000" fill="none" stroke="url(#g)" stroke-width="2.5" stroke-linejoin="round" '
           f'stroke-linecap="round" style="animation-delay:.4s"/>',
           f'<circle class="pop pulse" cx="{n(pts[-1][0])}" cy="{n(pts[-1][1])}" r="4.5" fill="{PINK}" style="animation-delay:2.6s"/>')

    # heatmap: cells pop in along the diagonal, then a light sweeps across
    first = dt.date.fromisoformat(days[0][0])
    off = (first.weekday() + 1) % 7  # Sunday = row 0
    gx, gy, step, size = 88, 186, 20, 15
    mxd = max([c for _, c in days] + [1])
    cells, months = [], []
    for i, (ds, c) in enumerate(days):
        idx = i + off
        col, row = divmod(idx, 7)
        lvl = 0 if c == 0 else min(4, max(1, math.ceil(4 * c / mxd)))
        d = .5 + col * .014 + row * .03
        cells.append(f'<rect class="pop" x="{gx + col * step}" y="{gy + row * step}" width="{size}" height="{size}" rx="3.5" '
                     f'fill="{LEVELS[lvl]}" style="animation-delay:{n(d)}s"><title>{c} on {ds}</title></rect>')
        day = dt.date.fromisoformat(ds)
        if day.day == 1 and col > 0:
            months.append(f'<text x="{gx + col * step}" y="{gy - 10}" class="m fade" font-size="11" fill="{MUTED}" '
                          f'style="animation-delay:{n(d)}s">{day.strftime("%b")}</text>')
    cv.add(*months, *cells)
    for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        cv.add(f'<text x="{gx - 12}" y="{gy + row * step + 12}" text-anchor="end" class="m" font-size="11" fill="{DIM}">{label}</text>')
    ncols = (len(days) + off + 6) // 7
    cv.defs.append(f'<clipPath id="hm"><rect x="{gx}" y="{gy}" width="{ncols * step}" height="{7 * step}"/></clipPath>'
                   '<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                   '<stop offset=".5" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    cv.css.append(f"@keyframes sw{{0%{{transform:translateX(0)}}60%,100%{{transform:translateX({ncols * step + 120}px)}}}}"
                  ".sw{animation:sw 5s cubic-bezier(.5,0,.3,1) 2.5s infinite}")
    cv.add(f'<g clip-path="url(#hm)"><rect class="sw" x="{gx - 120}" y="{gy}" width="100" height="{7 * step}" fill="url(#sweep)"/></g>')
    lx = W - 36 - 5 * 18 - 70
    cv.add(f'<text x="{lx - 8}" y="{H - 22}" text-anchor="end" class="m" font-size="11" fill="{DIM}">less</text>')
    for k, c in enumerate(LEVELS):
        cv.add(f'<rect x="{lx + k * 18}" y="{H - 33}" width="13" height="13" rx="3" fill="{c}"/>')
    cv.add(f'<text x="{lx + 5 * 18 + 4}" y="{H - 22}" class="m" font-size="11" fill="{DIM}">more</text>')
    runner(cv, 20, CYAN, 11, 40)
    return cv.render()


# ------------------------------------------------------------------ footer
def wave_path(width: float, base: float, amp: float, lam: float, phase: float, bottom: float) -> str:
    pts = [f"M0 {bottom}"]
    x = 0.0
    while x <= width:
        pts.append(f"L{n(x)} {n(base + amp * math.sin(2 * math.pi * x / lam + phase))}")
        x += 20
    pts.append(f"L{n(width)} {bottom}Z")
    return "".join(pts)


def footer(quotes: list[str]) -> str:
    W, H = 1200, 250
    cv = Canvas(W, H, "Thanks for dropping by")
    cv.defs.append(f'<clipPath id="fc"><rect width="{W}" height="{H}" rx="20"/></clipPath>')
    cv.css.append("@keyframes wave{to{transform:translateX(-1200px)}}.wv{animation:wave 12s linear infinite}")
    panel(cv)
    cv.add('<g clip-path="url(#fc)">')
    for k, (base, amp, lam, op, dur) in enumerate([(176, 14, 400, .18, 16), (190, 12, 300, .28, 11), (204, 10, 240, .45, 8)]):
        cv.add(f'<path class="wv" d="{wave_path(2400, base, amp, lam, k, H + 2)}" fill="url(#g)" fill-opacity="{op}" style="animation-duration:{dur}s"/>')
    cv.add("</g>",
           f'<text x="{W / 2 + 4}" y="84" text-anchor="middle" class="s in" font-size="34" font-weight="900" letter-spacing="8" fill="url(#g)">THANKS FOR DROPPING BY</text>')
    loop_typer(cv, quotes, W / 2, 130, 17, MUTED, start=.8, slot=4.6, prompt=">", prompt_fill=CYAN, weight=500, key="qt")
    runner(cv, 20, CYAN, 9, 60)
    return cv.render()
