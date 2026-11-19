"""
SVG renderers for every card on the profile, in a calm monochrome style
(warm off-white paper, near-black ink, Outfit type embedded in each SVG).

Animation toolkit (pure CSS inside the SVG, which GitHub renders in <img> tags):
  typed()      typewriter for monospace lines: a clip rect slides right in steps(n)
  wipe()       smooth left-to-right reveal for display type
  loop_typer() types, holds, erases and cycles through phrases
  odometer()   rolling-digit counters
  .grow .pop .draw .in   bars that grow, cells that appear, lines that draw, fades
Every animated element's *base* style is its final state, so with
prefers-reduced-motion (animation:none) the card is still complete.
"""
from __future__ import annotations

import base64
import html
import math
import textwrap
from pathlib import Path

PAPER, CARD, TILE, LINE = "#f1f0ed", "#f7f6f3", "#ebe9e5", "#dedcd7"
INK, INK2, MUTED, DIM = "#151515", "#3d3c3a", "#6f6d68", "#a8a6a0"
GRAYS = ["#151515", "#45443f", "#75736d", "#a19f99", "#c6c4be", "#dcdad5"]
HEAT = ["#e6e4df", "#c4c2bc", "#8f8d88", "#55534f", "#151515"]
MONO = "ui-monospace,'JetBrains Mono','SF Mono','Cascadia Code',Consolas,'DejaVu Sans Mono',monospace"
SANS = "Outfit,'Segoe UI',system-ui,sans-serif"

_FONT = Path(__file__).resolve().parent / "fonts" / "outfit.woff2"
FONT_FACE = (
    "@font-face{font-family:Outfit;font-weight:100 900;src:url(data:font/woff2;base64,"
    + base64.b64encode(_FONT.read_bytes()).decode() + ") format('woff2')}"
) if _FONT.exists() else ""

INKGRAD = (f'<linearGradient id="ink" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INK}"/>'
           f'<stop offset="1" stop-color="#77756f"/></linearGradient>')

BASE_CSS = (
    FONT_FACE +
    ".m{font-family:" + MONO + "}.s{font-family:" + SANS + "}"
    "@keyframes in{from{opacity:0;transform:translateY(8px)}}"
    ".in{animation:in .8s cubic-bezier(.2,.8,.2,1) both}"
    "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
    ".blink{animation:blink 1.05s steps(1) infinite}"
    "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}"
    ".pulse{animation:pulse 2.4s ease-in-out infinite}"
    "@keyframes rev{from{transform:translateX(0)}}.tw{animation-name:rev;animation-fill-mode:both}"
    ".wp{animation-name:rev;animation-fill-mode:both;animation-timing-function:cubic-bezier(.65,0,.25,1)}"
    "@keyframes odo{from{transform:translateY(0)}}.odo{animation:odo 1.6s cubic-bezier(.15,.85,.25,1) both}"
    "@keyframes grow{from{transform:scaleX(0)}}"
    ".grow{transform-box:fill-box;transform-origin:left center;animation:grow 1.3s cubic-bezier(.2,.8,.2,1) both}"
    "@keyframes pop{from{opacity:0;transform:scale(.6)}}"
    ".pop{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.2,.8,.2,1) both}"
    "@keyframes draw{from{stroke-dashoffset:1000}}.draw{stroke-dasharray:1000;animation:draw 2.2s ease-out both}"
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
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{self.w}" '
            f'height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img">\n<title>{esc(self.title)}</title>\n'
            f'<defs>{INKGRAD}{"".join(self.defs)}</defs>\n'
            f'<style>{BASE_CSS}{"".join(self.css)}'
            f'@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}{"".join(self.reduced)}}}</style>\n'
            + "\n".join(self.body) + "\n</svg>\n"
        )


# ------------------------------------------------------------------ shared pieces
def panel(cv: Canvas, rx: int = 18, fill: str = CARD) -> None:
    cv.add(f'<rect x=".75" y=".75" width="{cv.w - 1.5}" height="{cv.h - 1.5}" rx="{rx}" '
           f'fill="{fill}" stroke="{LINE}" stroke-width="1.5"/>')


def title_bar(cv: Canvas, label: str, right: str | None = None, live: bool = False) -> None:
    cv.add("".join(f'<circle cx="{28 + i * 18}" cy="23" r="5" fill="{c}"/>' for i, c in enumerate(["#d3d1cb", "#d3d1cb", "#d3d1cb"])))
    cv.add(f'<text x="90" y="27.5" class="m" font-size="12.5" fill="{MUTED}">{esc(label)}</text>')
    if right:
        x = cv.w - 28
        cv.add(f'<text x="{x}" y="27.5" text-anchor="end" class="s" font-size="12" font-weight="600" letter-spacing="2.5" fill="{MUTED}">{esc(right)}</text>')
        if live:
            cv.add(f'<circle class="pulse" cx="{n(x - len(right) * 10 - 10)}" cy="23" r="4" fill="{INK}"/>')
    cv.add(f'<rect x="1" y="45" width="{cv.w - 2}" height="1" fill="{LINE}"/>')


def typed(cv: Canvas, x: float, y: float, plain: str, fs: float, delay: float, *, content: str | None = None,
          fill: str = INK, weight: int | None = None, spacing: float = 0.0, speed: float = 0.018,
          anchor: str = "start") -> tuple[float, float]:
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
    cv.add(f'<text x="{n(x0)}" y="{n(y)}" class="m" font-size="{n(fs)}"{wt} fill="{fill}" '
           f'textLength="{n(w)}" xml:space="preserve" clip-path="url(#{cid})">'
           f'{content if content is not None else esc(plain)}</text>')
    return delay + dur, x0 + w


def wipe(cv: Canvas, svg: str, x: float, y_top: float, w: float, h: float, delay: float, dur: float = .9) -> None:
    """Smoothly reveals any element(s) left to right (used for display type)."""
    cid = cv.uid("w")
    cv.defs.append(f'<clipPath id="{cid}"><rect class="wp" x="{n(x - w)}" y="{n(y_top)}" width="{n(w)}" height="{n(h)}" '
                   f'style="transform:translateX({n(w)}px);animation-duration:{ts(dur)}s;animation-delay:{ts(delay)}s"/></clipPath>')
    cv.add(f'<g clip-path="url(#{cid})">{svg}</g>')


def caret(cv: Canvas, x: float, y: float, fs: float, delay: float) -> None:
    cv.add(f'<g class="in" style="animation-delay:{ts(delay)}s"><rect class="blink" x="{n(x + 3)}" y="{n(y - fs * .82)}" '
           f'width="{n(max(3, fs * .5))}" height="{n(fs * 1.02)}" fill="{INK}" opacity=".85"/></g>')


def loop_typer(cv: Canvas, phrases: list[str], x: float, y: float, fs: float, fill: str, *, start: float = 1.0,
               slot: float = 3.4, prompt: str = ">", prompt_fill: str = MUTED, weight: int = 500, key: str = "lt",
               center: bool = True) -> None:
    """Types a phrase, holds it, erases it, then moves on to the next one, forever."""
    CW = fs * 0.6
    T = slot * len(phrases)

    def pc(t: float) -> str:
        return f"{t / T * 100:.3f}%"

    type_end, hold_end, erase_end = min(.75, slot * .2), slot * .8, slot * .9
    cv.css.append(f"@keyframes {key}w{{0%,{pc(slot - .05)}{{opacity:1}}{pc(slot)},100%{{opacity:0}}}}"
                  f".{key}{{opacity:0;animation:{key}w {ts(T)}s steps(1) infinite}}")
    pre = len(prompt) + 1 if prompt else 0
    for i, ph in enumerate(phrases):
        L = len(ph)
        Wt = L * CW
        x0 = x - (L + pre) * CW / 2 if center else x
        tx = x0 + pre * CW
        d = start + i * slot
        cv.css.append(
            f"@keyframes {key}r{i}{{0%{{transform:translateX(0);animation-timing-function:steps({L},end)}}"
            f"{pc(type_end)}{{transform:translateX({n(Wt)}px);animation-timing-function:linear}}"
            f"{pc(hold_end)}{{transform:translateX({n(Wt)}px);animation-timing-function:steps({L},end)}}"
            f"{pc(erase_end)},100%{{transform:translateX(0)}}}}"
            f".{key}r{i}{{animation:{key}r{i} {ts(T)}s {ts(d)}s infinite}}.{key}{i}{{animation-delay:{ts(d)}s}}")
        cv.defs.append(f'<clipPath id="{key}c{i}"><rect class="{key}r{i}" x="{n(tx - Wt)}" y="{n(y - fs * 1.1)}" '
                       f'width="{n(Wt)}" height="{n(fs * 1.6)}"/></clipPath>')
        p = (f'<text x="{n(x0)}" y="{n(y)}" class="m" font-size="{n(fs)}" fill="{prompt_fill}">{esc(prompt)}</text>') if prompt else ""
        cv.add(f'<g class="{key} {key}{i}">{p}'
               f'<text x="{n(tx)}" y="{n(y)}" class="m" font-size="{n(fs)}" font-weight="{weight}" fill="{fill}" '
               f'textLength="{n(Wt)}" xml:space="preserve" clip-path="url(#{key}c{i})">{esc(ph)}</text>'
               f'<g class="blink"><rect class="{key}r{i}" x="{n(tx + 2)}" y="{n(y - fs * .8)}" width="2" '
               f'height="{n(fs)}" fill="{fill}"/></g></g>')
    cv.reduced.append(f".{key}.{key}0{{opacity:1}}.{key}r0{{transform:translateX({n(len(phrases[0]) * CW)}px)}}")


def odometer(cv: Canvas, x: float, y: float, text: str, fs: float, delay: float, *, fill: str = INK,
             weight: int = 700, anchor: str = "start") -> float:
    """Rolling-digit counter. Each digit spins up from 0 and lands on its value. Returns the end x."""
    cw = fs * 0.62
    lh = fs * 1.25
    w = len(text) * cw
    x0 = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
    cid = cv.uid("o")
    cv.defs.append(f'<clipPath id="{cid}"><rect x="{n(x0 - 4)}" y="{n(y - fs * .95)}" width="{n(w + 8)}" height="{n(fs * 1.22)}"/></clipPath>')
    parts = [f'<g clip-path="url(#{cid})" class="s" font-size="{n(fs)}" font-weight="{weight}" fill="{fill}" text-anchor="middle">']
    for i, ch in enumerate(text):
        cx = x0 + (i + .5) * cw
        if ch.isdigit():
            seq = [k % 10 for k in range(10 + int(ch) + 1)]
            col = "".join(f'<text x="{n(cx)}" y="{n(y + k * lh)}">{s}</text>' for k, s in enumerate(seq))
            parts.append(f'<g class="odo" style="transform:translateY(-{n((len(seq) - 1) * lh)}px);'
                         f'animation-delay:{ts(delay + i * .06)}s;animation-duration:{ts(1.4 + i * .12)}s">{col}</g>')
        else:
            parts.append(f'<text x="{n(cx)}" y="{n(y)}">{esc(ch)}</text>')
    parts.append("</g>")
    cv.add("".join(parts))
    return x0 + w


# ------------------------------------------------------------------ header
def header(cfg: dict, avatar: bytes | None = None) -> str:
    p = cfg["profile"]
    NAME, HANDLE, TAG, ROLES = p["name"], p["handle"], p["tagline"], p["roles"]
    W, H = 1200, 440
    cv = Canvas(W, H, f"{NAME}: {' '.join(TAG)}")
    cv.defs.append(f'<radialGradient id="halo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffffff" stop-opacity=".9"/>'
                   f'<stop offset=".7" stop-color="#ffffff" stop-opacity=".35"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>'
                   f'<radialGradient id="shadow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#000" stop-opacity=".18"/>'
                   f'<stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>'
                   f'<clipPath id="hf"><rect width="{W}" height="{H}" rx="18"/></clipPath>')
    panel(cv, fill=PAPER)
    cv.add('<g clip-path="url(#hf)">', f'<circle cx="960" cy="230" r="300" fill="url(#halo)"/>',
           f'<circle cx="960" cy="230" r="230" fill="none" stroke="{LINE}" stroke-width="1"/>', "</g>")

    typed(cv, 72, 92, "WELCOME TO MY WORLD", 12.5, .2, fill=MUTED, spacing=4, speed=.02)
    name_svg = (f'<text x="66" y="244" class="s" font-size="160" font-weight="800" letter-spacing="-4" '
                f'fill="url(#ink)">{esc(NAME)}</text>')
    wipe(cv, name_svg, 60, 100, 720, 175, .35, 1.1)
    cv.add(f'<rect class="grow" x="72" y="276" width="56" height="3" fill="{INK}" style="animation-delay:1.3s"/>')
    loop_typer(cv, ROLES, 72, 322, 24, INK, start=1.5, slot=3.2, key="rl", center=False)
    cv.add(f'<text x="72" y="364" class="s in" font-size="20" fill="{MUTED}" style="animation-delay:1.2s">'
           f'{esc(TAG[0])} <tspan fill="{INK}" font-weight="600">{esc(TAG[1])}</tspan></text>')
    cv.add(f'<text x="72" y="404" class="m in" font-size="12" fill="{DIM}" style="animation-delay:1.6s">github.com/{esc(HANDLE)}</text>')

    if avatar:
        # 120-frame turntable (animated WebP) standing in the halo, with a soft floor shadow
        b64 = base64.b64encode(avatar).decode()
        cv.add(f'<ellipse cx="960" cy="414" rx="90" ry="12" fill="url(#shadow)"/>',
               f'<g class="in" style="animation-delay:.6s"><image x="{960 - 105}" y="26" width="210" height="388" '
               f'href="data:image/webp;base64,{b64}" preserveAspectRatio="xMidYMax meet"/></g>')
    return cv.render()


# ------------------------------------------------------------------ ID card
def id_card(cfg: dict, photo: bytes | None, github_row: str | None) -> str:
    p = cfg["profile"]
    W, H = 1200, 540
    BX, BY, BS = 40, 80, 412
    cv = Canvas(W, H, "Sanjay: ID card")
    cv.defs.append(
        f'<linearGradient id="pg" gradientUnits="userSpaceOnUse" x1="0" y1="{BY}" x2="0" y2="{BY + BS}">'
        f'<stop offset="0" stop-color="{INK}"/><stop offset="1" stop-color="#7a7872"/></linearGradient>'
        f'<clipPath id="box"><rect x="{BX}" y="{BY}" width="{BS}" height="{BS}" rx="12"/></clipPath>'
        f'<clipPath id="reveal"><rect class="prev" x="{BX}" y="{BY - BS}" width="{BS}" height="{BS}"/></clipPath>'
        f'<linearGradient id="scanv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity=".55"/></linearGradient>')
    cv.css.append(
        f".prev{{transform:translateY({BS}px);animation:prev 2.4s cubic-bezier(.2,.8,.2,1) .3s both}}"
        "@keyframes prev{from{transform:translateY(0)}}"
        f"@keyframes sc{{0%{{transform:translateY(0)}}70%,100%{{transform:translateY({BS + 80}px)}}}}"
        ".sc{animation:sc 6s cubic-bezier(.5,0,.5,1) 2.8s infinite}")
    panel(cv)
    title_bar(cv, "sanjay@github: ~/id", "ID · " + p["handle"][-4:])

    cv.add(f'<rect x="{BX}" y="{BY}" width="{BS}" height="{BS}" rx="12" fill="{TILE}"/>')
    if photo:
        # black-and-white cutout, bottom-aligned in the frame, revealed top to bottom
        b64 = base64.b64encode(photo).decode()
        cv.add(f'<g clip-path="url(#box)"><g clip-path="url(#reveal)"><image x="{BX}" y="{BY + 14}" width="{BS}" height="{BS}" '
               f'preserveAspectRatio="xMidYMax meet" href="data:image/webp;base64,{b64}"/></g></g>')
    cv.add(f'<g clip-path="url(#box)"><rect class="sc" x="{BX}" y="{BY - 80}" width="{BS}" height="80" fill="url(#scanv)"/></g>')
    cv.add(f'<rect x="{BX}" y="{BY}" width="{BS}" height="{BS}" rx="12" fill="none" stroke="{LINE}" stroke-width="1.5"/>')
    cv.add(f'<rect x="484" y="80" width="1" height="{H - 120}" fill="{LINE}"/>')

    X, FS = 516, 15
    CW = FS * .6
    prompt = f'<tspan fill="{MUTED}">sanjay@github:~$ </tspan>'
    t, _ = typed(cv, X, 116, "sanjay@github:~$ whoami", 16, .4, speed=.025,
                 content=prompt + f'<tspan fill="{INK}">whoami</tspan>')
    rows = [tuple(r) for r in p["info"]]
    if github_row:
        rows.append(("GITHUB", github_row))
    rows.append(("STATUS", p["status"]))
    key_w = 13
    y0 = 166
    step = min(38, (H - 110 - y0) / (len(rows) + 1))
    t += .1
    for key, val in rows:
        y = y0 + rows.index((key, val)) * step
        label = (key + " ").ljust(key_w - 1, ".") + " "
        if key == "STATUS":
            vx = X + key_w * CW
            cv.add(f'<circle class="pulse" cx="{n(vx + 5)}" cy="{n(y - 5)}" r="4.5" fill="{INK}"/>')
            plain = label + "  " + val
            content = f'<tspan fill="{DIM}">{esc(label)}</tspan>  <tspan fill="{INK}" font-weight="600">{esc(val)}</tspan>'
        else:
            plain = label + val
            content = f'<tspan fill="{DIM}">{esc(label)}</tspan><tspan fill="{INK}">{esc(val)}</tspan>'
        t, _ = typed(cv, X, y, plain, FS, t, content=content, speed=.008)
        t += .03
    yl = y0 + len(rows) * step + 14
    end, ex = typed(cv, X, yl, "sanjay@github:~$ ./build --mode=fun", 16, t + .1, speed=.02,
                    content=prompt + f'<tspan fill="{INK}">./build --mode=fun</tspan>')
    caret(cv, ex, yl, 16, end)
    return cv.render()


# ------------------------------------------------------------------ now.log
def now_card(lines: list[str]) -> str:
    W = 1200
    H = 124 + 34 * (len(lines) + 1)  # +1 row for the blinking caret line
    cv = Canvas(W, H, "now.log: " + "; ".join(l.replace(" // ", " (") + (")" if " // " in l else "") for l in lines))
    panel(cv)
    title_bar(cv, "sanjay@github: ~/now.log", "NOW", live=True)
    prompt = f'<tspan fill="{MUTED}">sanjay@github:~$ </tspan>'
    t, _ = typed(cv, 36, 86, "sanjay@github:~$ tail -f now.log", 16, .3, speed=.022,
                 content=prompt + f'<tspan fill="{INK}">tail -f now.log</tspan>')
    t += .15
    y = 86
    for i, line in enumerate(lines):
        y = 120 + i * 34
        text, _, note = line.partition(" // ")
        tag = f"{i + 1:02d}  "
        plain = tag + text + (f"   // {note}" if note else "")
        content = (f'<tspan fill="{DIM}">{esc(tag)}</tspan><tspan fill="{INK}">{esc(text)}</tspan>'
                   + (f'<tspan fill="{DIM}">   // {esc(note)}</tspan>' if note else ""))
        t, _ = typed(cv, 36, y, plain, 16, t, content=content, speed=.012)
        t += .05
    caret(cv, 36, y + 34, 16, t)
    return cv.render()


# ------------------------------------------------------------------ section bar
def section(num: str, title: str, note: str) -> str:
    W, H = 1200, 96
    cv = Canvas(W, H, f"{num} {title}")
    panel(cv, 16, PAPER)
    cv.add(f'<text x="40" y="58" class="s in" font-size="15" font-weight="600" fill="{DIM}" style="animation-delay:.1s">{num}</text>')
    tw = len(title) * 24
    wipe(cv, f'<text x="84" y="62" class="s" font-size="34" font-weight="800" letter-spacing="-.5" fill="{INK}">{esc(title)}</text>',
         82, 20, tw + 30, 60, .15, .8)
    lx = 84 + tw + 34
    rx = W - 40 - len(note) * 7.8 - 26
    if rx > lx + 40:
        cv.add(f'<rect class="grow" x="{n(lx)}" y="50" width="{n(rx - lx)}" height="1" fill="{LINE}" style="animation-delay:.6s;animation-duration:1.6s"/>')
    typed(cv, W - 40, 55, note, 13, .8, fill=MUTED, anchor="end", speed=.015)
    return cv.render()


# ------------------------------------------------------------------ project card
def project_card(i: int, p: dict) -> str:
    W, H = 520, 280
    cv = Canvas(W, H, f"Project {i:02d}: {p['title']}")
    panel(cv)
    cv.add(f'<text x="28" y="44" class="s in" font-size="12" font-weight="600" letter-spacing="2.5" fill="{DIM}" style="animation-delay:.1s">PROJECT {i:02d}</text>')

    x = W - 28
    pills = [(p["lang"], False)] + ([("LIVE", True)] if p.get("live") else [])
    for k, (label, dot) in enumerate(reversed(pills)):
        w = len(label) * 7 + (32 if dot else 22)
        x -= w
        g = [f'<g class="in" style="animation-delay:{ts(.3 + k * .1)}s">',
             f'<rect x="{n(x)}" y="26" width="{n(w)}" height="24" rx="12" fill="{INK if dot else "none"}" stroke="{INK if dot else LINE}" stroke-width="1.2"/>']
        if dot:
            g.append(f'<circle class="pulse" cx="{n(x + 13)}" cy="38" r="3.5" fill="{PAPER}"/>')
        g.append(f'<text x="{n(x + (23 if dot else 11))}" y="42.5" class="s" font-size="11.5" font-weight="600" letter-spacing="1.2" '
                 f'fill="{PAPER if dot else INK2}">{esc(label)}</text></g>')
        cv.add("".join(g))
        x -= 8

    wipe(cv, f'<text x="28" y="94" class="s" font-size="30" font-weight="700" letter-spacing="-.5" fill="{INK}">{esc(p["title"])}</text>',
         26, 58, 470, 50, .35, .8)
    typed(cv, 28, 120, p["kind"], 12.5, .7, fill=MUTED, speed=.012)
    for j, line in enumerate(textwrap.wrap(p["desc"], 58)[:3]):
        cv.add(f'<text x="28" y="{154 + j * 23}" class="s in" font-size="15.5" fill="{INK2}" style="animation-delay:{ts(.9 + j * .1)}s">{esc(line)}</text>')
    x = 28
    for k, t in enumerate(p["tags"]):
        w = len(t) * 7.4 + 24
        if x + w > W - 92:
            break
        cv.add(f'<g class="in" style="animation-delay:{ts(1.2 + k * .08)}s"><rect x="{n(x)}" y="226" width="{n(w)}" height="28" rx="14" '
               f'fill="{TILE}"/><text x="{n(x + w / 2)}" y="244.5" text-anchor="middle" class="s" font-size="12.5" fill="{INK2}">{esc(t)}</text></g>')
        x += w + 8
    cv.add(f'<text x="{W - 28}" y="245" text-anchor="end" class="s in" font-size="13" font-weight="600" letter-spacing="1.5" fill="{INK}" style="animation-delay:1.5s">VIEW →</text>')
    return cv.render()


# ------------------------------------------------------------------ stats card
def fmt_bytes(b: int) -> str:
    return f"{b / 1e6:.1f}MB" if b >= 1e6 else f"{max(1, round(b / 1e3))}KB"


def stats_card(s: dict) -> str:
    W, H = 600, 380
    cv = Canvas(W, H, "GitHub stats: " + ", ".join(f"{k} {v}" for k, v in s["tiles"]))
    panel(cv)
    title_bar(cv, "~/stats", "LIVE", live=True)
    x0, y0, cw, rh = 26, 64, 270, 62
    for i, (label, value) in enumerate(s["tiles"]):
        cx = x0 + (i % 2) * (cw + 8)
        ty = y0 + (i // 2) * rh
        d = .15 + i * .07
        cv.add(f'<rect class="in" x="{cx}" y="{ty}" width="{cw}" height="54" rx="12" fill="{TILE}" style="animation-delay:{ts(d)}s"/>')
        cv.add(f'<text x="{cx + 18}" y="{ty + 21}" class="s in" font-size="11" font-weight="600" letter-spacing="1.6" fill="{MUTED}" '
               f'style="animation-delay:{ts(d + .1)}s">{esc(label)}</text>')
        odometer(cv, cx + 18, ty + 45, str(value), 22, d + .2)

    lvl, xp, lo, hi = s["level"]
    by = y0 + 4 * rh + 18
    cv.add(f'<text x="{x0}" y="{by + 10}" class="s in" font-size="13" font-weight="700" fill="{INK}" style="animation-delay:1.1s">LVL {lvl}</text>')
    tx0, tx1 = x0 + 64, W - 150
    frac = max(.04, min(1, (xp - lo) / max(1, hi - lo)))
    cv.add(f'<rect x="{tx0}" y="{by}" width="{tx1 - tx0}" height="10" rx="5" fill="{TILE}"/>',
           f'<rect class="grow" x="{tx0}" y="{by}" width="{n((tx1 - tx0) * frac)}" height="10" rx="5" fill="{INK}" style="animation-delay:1.3s;animation-duration:1.8s"/>')
    cv.add(f'<text x="{W - 26}" y="{by + 10}" text-anchor="end" class="s in" font-size="12.5" fill="{MUTED}" style="animation-delay:1.5s">{xp} / {hi} XP</text>')
    return cv.render()


# ------------------------------------------------------------------ languages card
def languages_card(langs: list[tuple[str, float]]) -> str:
    W, H = 600, 380
    cv = Canvas(W, H, "Most used languages: " + ", ".join(f"{l} {p:.1f}%" for l, p in langs))
    panel(cv)
    title_bar(cv, "~/languages", "BY CODE SIZE")
    bx, bw, by = 30, W - 60, 76
    cv.defs.append(f'<clipPath id="sb"><rect x="{bx}" y="{by}" width="{bw}" height="12" rx="6"/></clipPath>')
    cv.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="12" rx="6" fill="{TILE}"/>', '<g clip-path="url(#sb)">')
    x = bx
    for i, (name, pct) in enumerate(langs):
        w = bw * pct / 100
        cv.add(f'<rect class="grow" x="{n(x)}" y="{by}" width="{n(w + .5)}" height="12" fill="{GRAYS[i % len(GRAYS)]}" '
               f'style="animation-delay:{ts(.3 + i * .1)}s"/>')
        x += w + 2
    cv.add("</g>")
    top = max(p for _, p in langs) if langs else 1
    for i, (name, pct) in enumerate(langs):
        y = 132 + i * 40
        c = GRAYS[i % len(GRAYS)]
        d = .5 + i * .1
        cv.add(f'<circle class="pop" cx="{bx + 6}" cy="{y - 5}" r="5.5" fill="{c}" stroke="{LINE}" style="animation-delay:{ts(d)}s"/>',
               f'<text x="{bx + 22}" y="{y}" class="s in" font-size="15.5" font-weight="500" fill="{INK}" style="animation-delay:{ts(d)}s">{esc(name)}</text>')
        tx0, tx1 = 220, W - 120
        cv.add(f'<rect x="{tx0}" y="{y - 9}" width="{tx1 - tx0}" height="6" rx="3" fill="{TILE}"/>',
               f'<rect class="grow" x="{tx0}" y="{y - 9}" width="{n(max(4, (tx1 - tx0) * pct / top))}" height="6" rx="3" fill="{INK}" '
               f'style="animation-delay:{ts(d + .1)}s"/>')
        odometer(cv, W - 30, y, f"{pct:.1f}%", 15, d + .1, fill=MUTED, weight=500, anchor="end")
    return cv.render()


# ------------------------------------------------------------------ contributions card
def contributions_card(days: list[list], streaks: tuple[int, int], updated: str) -> str:
    import datetime as dt

    W, H = 1200, 372
    total = sum(c for _, c in days)
    cur, best = streaks
    cv = Canvas(W, H, f"{total} contributions in the last year, current streak {cur} days, longest {best} days")
    panel(cv)
    title_bar(cv, "~/contributions", f"UPDATED {updated}")

    for k, (label, val, x) in enumerate([("CONTRIBUTIONS · LAST 12 MONTHS", total, 36), ("CURRENT STREAK", cur, 400), ("LONGEST STREAK", best, 600)]):
        cv.add(f'<text x="{x}" y="84" class="s in" font-size="11" font-weight="600" letter-spacing="1.6" fill="{MUTED}" style="animation-delay:{ts(.15 + k * .08)}s">{label}</text>')
        ex = odometer(cv, x, 132, str(val), 44, .3 + k * .1, weight=700)
        if k:
            cv.add(f'<text x="{n(ex + 8)}" y="132" class="s in" font-size="15" fill="{MUTED}" style="animation-delay:1.3s">{"day" if val == 1 else "days"}</text>')

    last = [c for _, c in days[-30:]]
    sx0, sx1, sy0, sy1 = 800, W - 36, 74, 140
    mx = max(last + [1])
    pts = [(sx0 + (sx1 - sx0) * i / max(1, len(last) - 1), sy1 - (sy1 - sy0) * c / mx) for i, c in enumerate(last)]
    line = "M" + " L".join(f"{n(x)} {n(y)}" for x, y in pts)
    cv.defs.append(f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INK}" stop-opacity=".12"/>'
                   f'<stop offset="1" stop-color="{INK}" stop-opacity="0"/></linearGradient>')
    cv.add(f'<text x="{sx1}" y="64" text-anchor="end" class="s in" font-size="10.5" font-weight="600" letter-spacing="1.5" fill="{DIM}" style="animation-delay:.3s">LAST 30 DAYS</text>',
           f'<path class="fade" d="{line} L{n(sx1)} {sy1} L{sx0} {sy1}Z" fill="url(#area)" style="animation-delay:1.5s"/>',
           f'<path class="draw" d="{line}" pathLength="1000" fill="none" stroke="{INK}" stroke-width="2" stroke-linejoin="round" '
           f'stroke-linecap="round" style="animation-delay:.4s"/>',
           f'<circle class="pop" cx="{n(pts[-1][0])}" cy="{n(pts[-1][1])}" r="4" fill="{INK}" style="animation-delay:2.4s"/>')

    first = dt.date.fromisoformat(days[0][0])
    off = (first.weekday() + 1) % 7  # Sunday = row 0
    gx, gy, step, size = 88, 186, 20, 15
    mxd = max([c for _, c in days] + [1])
    cells, months = [], []
    for i, (ds, c) in enumerate(days):
        col, row = divmod(i + off, 7)
        lvl = 0 if c == 0 else min(4, max(1, math.ceil(4 * c / mxd)))
        d = .4 + col * .012 + row * .02
        cells.append(f'<rect class="pop" x="{gx + col * step}" y="{gy + row * step}" width="{size}" height="{size}" rx="3.5" '
                     f'fill="{HEAT[lvl]}" style="animation-delay:{ts(d)}s"><title>{c} on {ds}</title></rect>')
        day = dt.date.fromisoformat(ds)
        if day.day == 1 and col > 0:
            months.append(f'<text x="{gx + col * step}" y="{gy - 10}" class="s fade" font-size="11.5" fill="{MUTED}" '
                          f'style="animation-delay:{ts(d)}s">{day.strftime("%b")}</text>')
    cv.add(*months, *cells)
    for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        cv.add(f'<text x="{gx - 12}" y="{gy + row * step + 12}" text-anchor="end" class="s" font-size="11.5" fill="{DIM}">{label}</text>')
    lx = W - 36 - 5 * 18 - 70
    cv.add(f'<text x="{lx - 8}" y="{H - 22}" text-anchor="end" class="s" font-size="11.5" fill="{DIM}">less</text>')
    for k, c in enumerate(HEAT):
        cv.add(f'<rect x="{lx + k * 18}" y="{H - 33}" width="13" height="13" rx="3" fill="{c}"/>')
    cv.add(f'<text x="{lx + 5 * 18 + 4}" y="{H - 22}" class="s" font-size="11.5" fill="{DIM}">more</text>')
    return cv.render()


# ------------------------------------------------------------------ footer
def footer(quotes: list[str]) -> str:
    W, H = 1200, 220
    cv = Canvas(W, H, "Thanks for dropping by")
    panel(cv, fill=PAPER)
    wipe(cv, f'<text x="{W / 2}" y="104" text-anchor="middle" class="s" font-size="44" font-weight="800" letter-spacing="-1" '
             f'fill="url(#ink)">Thanks for dropping by.</text>', 300, 50, 600, 70, .2, 1)
    loop_typer(cv, quotes, W / 2, 152, 16, MUTED, start=1, slot=4.6, weight=400, key="qt")
    return cv.render()
