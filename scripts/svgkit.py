"""Shared SVG toolkit: palette, fonts (checked, measured, subset, embedded), animation CSS, Canvas.

Animation model: an element's base styling is its FINAL frame. Keyframes only declare the `from`
state. Removing the animation block (STATIC=1) or switching it off (prefers-reduced-motion) therefore
leaves a finished card. SMIL cannot be disabled from CSS, so SMIL-only decoration sits in
<g class="smil"> (hidden under reduced motion) and anything essential has a `.still` twin.
"""
from __future__ import annotations

import base64
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
STATIC = os.environ.get("STATIC", "").lower() not in ("", "0", "false", "no")

PALETTE = {
    "midnight": "#102D50", "cobalt": "#285BA8", "cerulean": "#4598B8", "gold": "#E8C95C",
    "ivory": "#F5F3EC", "ink": "#252B32", "navy": "#172A46", "pale": "#DCE8F3",
    "soft_gold": "#F3E5B1", "white": "#FFFFFF",
}
# Contribution ramp requested in the brief: none, low, medium, high, very high, maximum.
HEAT = ["#E8E8E5", "#DCE8F3", "#8CB8DF", "#4598B8", "#285BA8", "#102D50"]


def mix(a: str, b: str, t: float) -> str:
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def luminance(h: str) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(int(h[i:i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# Secondary text and hairlines are ink mixed into ivory, so everything stays in the palette.
MUTED = mix(PALETTE["ink"], PALETTE["ivory"], 0.34)
HAIR = mix(PALETTE["ink"], PALETTE["ivory"], 0.84)
assert contrast(MUTED, PALETTE["ivory"]) >= 4.5, "muted text fails contrast on ivory"

# --------------------------------------------------------------------------- fonts
# key -> (file, expected family, expected style, expected weight, expected italic, css family, fallback)
FACES = {
    "serif":   ("instrument-serif-regular.woff", "Instrument Serif", "Regular", 400, False, "InstrumentSerif",
                "'Instrument Serif',Georgia,'Times New Roman',serif"),
    "serif-i": ("instrument-serif-italic.woff", "Instrument Serif", "Italic", 400, True, "InstrumentSerif",
                "'Instrument Serif',Georgia,'Times New Roman',serif"),
    "sans":    ("geist-regular.woff", "Geist", "Regular", 400, False, "Geist",
                "Geist,'Helvetica Neue',Arial,sans-serif"),
    "sans-m":  ("geist-medium.woff", "Geist", "Medium", 500, False, "Geist",
                "Geist,'Helvetica Neue',Arial,sans-serif"),
    "mono":    ("geist-mono-regular.woff", "Geist Mono", "Regular", 400, False, "GeistMono",
                "'Geist Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"),
}
_fonts: dict[str, TTFont] = {}


def font(key: str) -> TTFont:
    """Load a face and verify its REAL metadata matches what the cards assume."""
    if key not in _fonts:
        file, fam, style, weight, italic, *_ = FACES[key]
        t = TTFont(ROOT / "fonts" / file)
        n, os2 = t["name"], t["OS/2"]
        got = (n.getBestFamilyName(), n.getBestSubFamilyName(), os2.usWeightClass, bool(os2.fsSelection & 1))
        if got != (fam, style, weight, italic):
            sys.exit(f"font metadata mismatch for {file}: file says {got}, expected {(fam, style, weight, italic)}")
        _fonts[key] = t
    return _fonts[key]


def width(key: str, s: str, size: float, ls: float = 0.0) -> float:
    """Advance width of `s` in px, from the font's own hmtx table (kerning ignored)."""
    t = font(key)
    cmap, hmtx, upm = t.getBestCmap(), t["hmtx"], t["head"].unitsPerEm
    w = sum(hmtx[cmap[ord(c)]][0] if ord(c) in cmap else upm * 0.5 for c in s)
    return w / upm * size + ls * len(s)


def wrap(key: str, text: str, size: float, max_w: float, max_lines: int, ls: float = 0.0) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if width(key, trial, size, ls) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while width(key, lines[-1] + "…", size, ls) > max_w and " " in lines[-1]:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += "…"
    return lines


_subset_cache: dict[tuple, str] = {}


def subset_b64(key: str, chars: str) -> str:
    ck = (key, chars)
    if ck in _subset_cache:
        return _subset_cache[ck]
    src = ROOT / "fonts" / FACES[key][0]
    exe = shutil.which("pyftsubset")
    cmd = [exe] if exe else [sys.executable, "-m", "fontTools.subset"]
    with tempfile.TemporaryDirectory() as tmp:
        txt, out = Path(tmp) / "c.txt", Path(tmp) / "f.woff"
        txt.write_text(chars, encoding="utf-8")
        subprocess.run(cmd + [str(src), f"--text-file={txt}", f"--output-file={out}", "--flavor=woff",
                              "--layout-features=kern", "--no-hinting", "--drop-tables+=FFTM"], check=True)
        b64 = base64.b64encode(out.read_bytes()).decode()
    _subset_cache[ck] = b64
    return b64


# --------------------------------------------------------------------------- helpers
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def sec(v: float) -> str:
    return f"{v:.2f}s"


def D(delay: float) -> str:
    return f' style="--d:{sec(delay)}"'


def star(cx: float, cy: float, r: float) -> str:
    """Four-point star path (the Starry Night nod used across the cards)."""
    k = r * 0.22
    return (f"M{n(cx)} {n(cy - r)}Q{n(cx + k)} {n(cy - k)} {n(cx + r)} {n(cy)}Q{n(cx + k)} {n(cy + k)} "
            f"{n(cx)} {n(cy + r)}Q{n(cx - k)} {n(cy + k)} {n(cx - r)} {n(cy)}Q{n(cx - k)} {n(cy - k)} {n(cx)} {n(cy - r)}Z")


BASE_CSS = (
    ".f-serif,.f-serif-i{font-family:'InstrumentSerif','Instrument Serif',Georgia,'Times New Roman',serif;font-weight:400}"
    ".f-serif-i{font-style:italic}"
    ".f-sans,.f-sans-m{font-family:Geist,'Helvetica Neue',Arial,sans-serif;font-weight:400}.f-sans-m{font-weight:500}"
    ".f-mono{font-family:'GeistMono','Geist Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-weight:400}"
    "text{font-variant-ligatures:none}.pre{white-space:pre}"
)

ANIM_CSS = """
@keyframes fade{from{opacity:0}}
@keyframes rise{from{opacity:0;transform:translateY(12px)}}
@keyframes col{from{opacity:0;transform:translateY(4px)}}
@keyframes print{from{opacity:0;transform:translateY(-3px)}}
@keyframes growy{from{transform:scaleY(0)}}
@keyframes growx{from{transform:scaleX(0)}}
.fade{animation:fade .6s ease-out var(--d,0s) backwards}
.rise{animation:rise .7s cubic-bezier(.2,.7,.2,1) var(--d,0s) backwards}
.col{animation:col .5s ease-out var(--d,0s) backwards}
.print{animation:print .3s ease-out var(--d,0s) backwards}
.bar{transform-box:fill-box;transform-origin:50% 100%;animation:growy .8s cubic-bezier(.2,.7,.2,1) var(--d,0s) backwards}
.rule{transform-box:fill-box;transform-origin:0 50%;animation:growx .8s cubic-bezier(.2,.7,.2,1) var(--d,0s) backwards}
.still{display:none}
@media (prefers-reduced-motion:reduce){
*{animation:none!important;transition:none!important}
.smil{display:none}
.still{display:inline}
}
"""


def twin(smil: str, still: str) -> str:
    return still if STATIC else f'<g class="smil">{smil}</g><g class="still">{still}</g>'


class Canvas:
    """Collects markup and the characters each face needs, then emits one self-contained SVG."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.parts: list[str] = []
        self.defs: list[str] = []
        self.chars: dict[str, set[str]] = {}

    def raw(self, markup: str) -> None:
        self.parts.append(markup)

    def open(self, cls: str = "", d: float | None = None, extra: str = "") -> None:
        c = f' class="{cls}"' if cls else ""
        self.parts.append(f"<g{c}{D(d) if d is not None else ''}{extra}>")

    def close(self) -> None:
        self.parts.append("</g>")

    def text(self, x, y, s, size, fill, face="sans", *, anchor="start", ls=0.0, cls="", d=None,
             extra="") -> None:
        self.chars.setdefault(face, set()).update(s)
        a = "" if anchor == "start" else f' text-anchor="{anchor}"'
        l = f' letter-spacing="{n(ls)}"' if ls else ""
        k = f"f-{face}" + (f" {cls}" if cls else "")
        self.parts.append(f'<text x="{n(x)}" y="{n(y)}" font-size="{n(size)}" fill="{fill}" class="{k}"{a}{l}'
                          f'{D(d) if d is not None else ""}{extra}>{esc(s)}</text>')

    def rect(self, x, y, w, h, fill, *, rx=0, stroke=None, cls="", d=None, extra="") -> None:
        s = f' stroke="{stroke}"' if stroke else ""
        k = f' class="{cls}"' if cls else ""
        self.parts.append(f'<rect{k} x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{n(rx)}" '
                          f'fill="{fill}"{s}{D(d) if d is not None else ""}{extra}/>')

    def panel(self, fill: str, d: float, rx: int = 16, stroke: str = HAIR) -> None:
        self.rect(.5, .5, self.w - 1, self.h - 1, fill, rx=rx, stroke=stroke, cls="fade", d=d)

    def svg(self, title: str, desc: str) -> str:
        faces = []
        for key, chars in sorted(self.chars.items()):
            fam, weight, italic = FACES[key][5], FACES[key][3], FACES[key][4]
            b64 = subset_b64(key, "".join(sorted(chars | {" "})))
            faces.append(f"@font-face{{font-family:'{fam}';font-style:{'italic' if italic else 'normal'};"
                         f"font-weight:{weight};src:url(data:font/woff;base64,{b64}) format('woff')}}")
        css = "".join(faces) + BASE_CSS + ("" if STATIC else ANIM_CSS)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}" role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title>'
                f'<desc id="d">{esc(desc)}</desc><style>{css}</style><defs>{"".join(self.defs)}</defs>'
                f'{"".join(self.parts)}</svg>\n')
