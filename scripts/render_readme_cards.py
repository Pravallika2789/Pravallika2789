#!/usr/bin/env python3
"""Render the profile README cards (editorial, Starry Night palette) into cards/.

    python scripts/render_readme_cards.py            # cards/*.svg + README.md
    STATIC=1 python scripts/render_readme_cards.py   # final frame only -> preview/ (+ index.html)

Env: STATIC=1, DATA=path (default data/contributions.json), OUT=path (output root).
"""
from __future__ import annotations

import bisect
import datetime as dt
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svgkit as K  # noqa: E402
from portrait import ascii_portrait  # noqa: E402
from stats import parse_days, summarise  # noqa: E402
from svgkit import D, HAIR, MUTED, PALETTE as P, Canvas, n, sec, star, twin, width, wrap  # noqa: E402

ROOT, STATIC = K.ROOT, K.STATIC
DATA_FILE = Path(os.environ.get("DATA") or ROOT / "data" / "contributions.json")
OUT_ROOT = Path(os.environ.get("OUT") or (ROOT / "preview" if STATIC else ROOT))
CARDS = OUT_ROOT / "cards"

# --------------------------------------------------------------------------- content
PROFILE = {
    "login": "Pravallika2789",
    "name": ("Reddy", "Pravallika"),
    "label": "Computer Science & Information Technology student",
    "intro": "I build AI agents and automations, and care as much about how they look as how they run.",
    "website": None,  # e.g. "https://example.com"; shown in the hero and footer once set
    "linkedin": "https://www.linkedin.com/in/reddy-pravallika-812723325",
    "email": "r.pravallika2789@gmail.com",
}

# repo=None means "no verified repository URL yet": the card is rendered without a link.
PROJECTS = [
    dict(slug="neuromorphic", repo="Smart-seizure-detection", category="Neuromorphic AI",
         title="Neuromorphic Seizure Detection",
         desc="EEG-based seizure detection with Spiking Neural Networks, plus plain-language "
              "interpretations of each prediction through the Gemini API.",
         tags=["Spiking Neural Networks", "EEG", "Gemini API", "TypeScript"]),
    dict(slug="pivora", repo="Pivora--Financial-PLanning-and-scenario-Simulation", category="Hackathon project",
         title="PIVORA", subtitle="Financial Simulation Platform",
         desc="Financial planning and scenario simulation. My fork of the PIVORA-Hackathon project.",
         tags=["Fork of PIVORA-Hackathon", "TypeScript"]),
    dict(slug="skyaid", repo=None, category="Disaster relief", title="SKY AID",
         subtitle="Drone-Based Disaster Relief System",
         desc="A drone-based disaster relief system.", tags=[]),
    dict(slug="memprofiler", repo="MemProfiler-OS", category="Systems tooling", title="MemProfiler-OS",
         desc="A system monitoring dashboard that visualises per-process memory use, flags abnormal "
              "behaviour and detects possible memory leaks in real time.",
         tags=["Memory profiling", "Dashboard", "TypeScript"]),
    dict(slug="gesture", repo="Real-time-Hand-Gesture-Recognition", category="Computer vision",
         title="Real-Time Hand Gesture Recognition",
         desc="Classifies gestures live from webcam hand landmarks, using MediaPipe and TensorFlow.",
         tags=["MediaPipe", "TensorFlow", "Computer vision"]),
]

W = 880
TW, TH = 286, 300  # three tiles at 32.5%
T = dict(hero=0.0, graph=2.4, activity=3.6, tiles=4.8, tile_step=0.14, heading=5.7, projects=5.9,
         project_step=0.18, footer=7.3)

INK, IVORY, COBALT, MID, GOLD = P["ink"], P["ivory"], P["cobalt"], P["midnight"], P["gold"]


def fmt_int(v: int) -> str:
    return f"{v:,}"


def fmt_date(d: dt.date) -> str:
    return f"{d.day} {d.strftime('%b')} {d.year}"


def card(name: str, c: Canvas, title: str, desc: str, href: str | None = None, alt: str | None = None) -> dict:
    return dict(name=name, w=c.w, h=c.h, svg=c.svg(title, desc), href=href, alt=alt or f"{title}. {desc}")


# --------------------------------------------------------------------------- hero
def hero(t0: float) -> dict:
    H, x0 = 400, 56
    c = Canvas(W, H)
    c.defs.append(f'<clipPath id="card"><rect width="{W}" height="{H}" rx="16"/></clipPath>')
    c.panel(IVORY, t0)

    # label with a small gold star (twinkles three times, then rests)
    sx, sy = x0 + 7, 64
    star_still = f'<path d="{star(sx, sy, 8)}" fill="{GOLD}"/>'
    star_smil = (f'<path d="{star(sx, sy, 8)}" fill="{GOLD}"><animate attributeName="opacity" values="1;.25;1" '
                 f'dur="1.4s" begin="{sec(t0 + 1.0)}" repeatCount="3"/></path>')
    c.raw(twin(star_smil, star_still))
    c.text(x0 + 24, 68, PROFILE["label"].upper(), 10.5, COBALT, "mono", ls=1.4, cls="rise", d=t0 + 0.15)

    first, second = PROFILE["name"]
    c.text(x0 - 4, 176, first, 104, INK, "serif", cls="rise", d=t0 + 0.3, ls=-1)
    c.text(x0 - 4, 270, second, 104, INK, "serif-i", cls="rise", d=t0 + 0.6, ls=-1)

    c.rect(x0, 292, 56, 2, COBALT, cls="rule", d=t0 + 0.95)
    lines = wrap("sans", PROFILE["intro"], 18, 430, 3)
    for i, ln in enumerate(lines):
        c.text(x0, 328 + i * 25, ln, 18, INK, "sans", cls="rise", d=t0 + 1.0 + i * 0.08)
    if PROFILE["website"]:
        shown = PROFILE["website"].replace("https://", "").replace("http://", "").rstrip("/")
        y = 328 + len(lines) * 25 + 18
        c.text(x0, y, shown, 12.5, COBALT, "mono", cls="rise", d=t0 + 1.3)
        c.rect(x0, y + 5, width("mono", shown, 12.5), 1, COBALT, cls="rise", d=t0 + 1.3)

    # ink portrait, printed row by row
    cols, rows = 56, 38
    fs, lh = 8.0, 9.0
    art, is_photo = ascii_portrait(cols, rows, (cols * width('mono', 'x', fs)) / (rows * lh))
    px, py = W - 52 - width("mono", "x" * cols, fs), 44
    c.open("print-group")
    for r, row in enumerate(art):
        if row.strip():
            c.text(px, py + r * lh, row, fs, INK, "mono", cls="print pre", d=t0 + 0.5 + r * 0.045,
                   extra=' xml:space="preserve"')
    c.close()

    # a very subtle blue highlight sweep across the card, once
    c.defs.append(f'<linearGradient id="sw" x1="0" x2="1"><stop offset="0" stop-color="{COBALT}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{COBALT}" stop-opacity=".07"/>'
                  f'<stop offset="1" stop-color="{COBALT}" stop-opacity="0"/></linearGradient>')
    if not STATIC:
        c.raw(f'<g class="smil" clip-path="url(#card)"><rect y="0" width="200" height="{H}" x="-200" fill="url(#sw)">'
              f'<animate attributeName="x" from="-200" to="{W}" dur="2s" begin="{sec(t0 + 2.2)}" fill="freeze"/></rect></g>')
    desc = f"{PROFILE['label']}. {PROFILE['intro']}"
    return card("hero", c, " ".join(PROFILE["name"]), desc,
                alt=f"{' '.join(PROFILE['name'])}, {PROFILE['label']}. {PROFILE['intro']}")


# --------------------------------------------------------------------------- contribution graph
def empty_state(name: str, h: int, title: str, t0: float) -> dict:
    c = Canvas(W, h)
    c.panel(IVORY, t0)
    c.text(40, 56, title, 30, INK, "serif", cls="rise", d=t0 + 0.2)
    c.text(40, 92, "Contribution data is not available yet. It refreshes daily.", 13, MUTED, "sans", cls="rise", d=t0 + 0.3)
    return card(name, c, title, "Contribution data is not available yet.")


def graph(t0: float, data: dict, days, st) -> dict:
    H = 252
    if not days:
        return empty_state("contributions", H, "Contributions", t0)
    c = Canvas(W, H)
    c.panel(IVORY, t0)
    c.text(40, 58, "Contributions", 30, INK, "serif", cls="rise", d=t0 + 0.2)
    sample = "sample data, " if data.get("sample") else ""
    c.text(W - 40, 54, f"{sample}{fmt_int(st['total'])} in the last year", 11, MUTED, "mono", anchor="end",
           cls="rise", d=t0 + 0.3)

    first = days[0][0]
    off = (first.weekday() + 1) % 7  # weeks start on Sunday
    ncols = (len(days) - 1 + off) // 7 + 1
    gx, gy = 84, 108
    pitch = (W - gx - 40) / ncols
    cell = pitch - 3
    nz = sorted(v for _, v in days if v > 0)
    cuts = [nz[min(len(nz) - 1, int(len(nz) * f))] for f in (.2, .4, .6, .8)] if nz else [1, 2, 3, 4]

    def level(v):
        return 0 if v == 0 else 1 + bisect.bisect_left(cuts, v)

    cols_markup: dict[int, list[str]] = {}
    marks = []
    for i, (day, v) in enumerate(days):
        col, row = divmod(i + off, 7)
        cols_markup.setdefault(col, []).append(
            f'<rect x="{n(gx + col * pitch)}" y="{n(gy + row * pitch)}" width="{n(cell)}" height="{n(cell)}" '
            f'rx="2" fill="{K.HEAT[level(v)]}"/>')
        if day.day == 1:
            marks.append((col, day.strftime("%b")))
    last = -9
    for col, lab in marks:
        if col - last >= 4:
            c.text(gx + col * pitch, gy - 12, lab, 10, MUTED, "mono", cls="rise", d=t0 + 0.4)
            last = col
    for row, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        c.text(40, gy + row * pitch + cell - 1.5, lab, 10, MUTED, "mono", cls="rise", d=t0 + 0.4)
    for col in sorted(cols_markup):
        c.raw(f'<g class="col"{D(t0 + 0.45 + col * 0.014)}>{"".join(cols_markup[col])}</g>')

    ly = H - 22
    c.text(W - 40, ly, "More", 10, MUTED, "mono", anchor="end", cls="rise", d=t0 + 1.3)
    sx = W - 40 - width("mono", "More", 10) - 8 - 6 * 15 + 3
    for k, colr in enumerate(K.HEAT):
        c.rect(sx + k * 15, ly - 10, 11, 11, colr, rx=2, cls="rise", d=t0 + 1.3)
    c.text(sx - 8, ly, "Less", 10, MUTED, "mono", anchor="end", cls="rise", d=t0 + 1.3)
    alt = f"Contribution heatmap for the last year: {fmt_int(st['total'])} contributions."
    return card("contributions", c, "Contributions", alt, alt=alt)


# --------------------------------------------------------------------------- monthly activity
def activity(t0: float, data: dict, days, st) -> dict:
    H = 352
    if not days:
        return empty_state("activity", H, "Monthly activity", t0)
    c = Canvas(W, H)
    c.panel(IVORY, t0)
    c.text(40, 58, "Monthly activity", 30, INK, "serif", cls="rise", d=t0 + 0.2)
    c.text(40, 82, "CONTRIBUTIONS PER MONTH", 10.5, MUTED, "mono", ls=1.2, cls="rise", d=t0 + 0.3)

    months = [(dt.date.fromisoformat(m["month"] + "-01").strftime("%b"), m["count"]) for m in st["monthly"]]
    vmax = max(v for _, v in months) or 1
    peak = max(range(12), key=lambda i: (months[i][1], i))
    left, base, hmax, pitch, bw = 44, 288, 146, 42, 28
    c.rect(left, base, 11 * pitch + bw, 1, INK, cls="fade", d=t0 + 0.3)
    for i, (lab, v) in enumerate(months):
        x, h = left + i * pitch, max(3, hmax * v / vmax)
        d = t0 + 0.4 + i * 0.06
        is_peak = i == peak
        c.rect(x, base - h, bw, h, GOLD if is_peak else INK, rx=3, cls="bar", d=d,
               stroke=INK if is_peak else None)
        c.text(x + bw / 2, base - h - 9, fmt_int(v), 10.5, INK, "mono", anchor="middle", cls="rise", d=d + 0.4)
        c.text(x + bw / 2, base + 20, lab, 10.5, MUTED, "mono", anchor="middle", cls="rise", d=d)

    c.rect(584, 40, 1, H - 80, HAIR, cls="fade", d=t0 + 0.5)
    b = st["busiest"]
    bd = dt.date.fromisoformat(b["date"])
    rows = [
        ("LONGEST STREAK", str(st["longest_streak"]), "days", f"current streak: {st['current_streak']} days"),
        ("ACTIVE DAYS", fmt_int(st["active_days"]), "days", f"of the last {st['span_days']} days"),
        ("BUSIEST DAY", fmt_int(b["count"]), "contributions", f"on {fmt_date(bd)}"),
    ]
    x = 624
    for i, (lab, num, unit, cap) in enumerate(rows):
        y0, d = 42 + i * 100, t0 + 0.7 + i * 0.2
        if i:
            c.rect(x, y0 - 8, 216, 1, HAIR, cls="fade", d=d)
        c.text(x, y0 + 14, lab, 10.5, MUTED, "mono", ls=1.2, cls="rise", d=d)
        if lab == "BUSIEST DAY":
            c.raw(f'<path class="rise" d="{star(x + width("mono", lab, 10.5, 1.2) + 14, y0 + 10.5, 6)}" fill="{GOLD}"{D(d)}/>')
        c.text(x, y0 + 64, num, 56, INK, "serif", cls="rise", d=d + 0.05)
        c.text(x + width("serif", num, 56) + 8, y0 + 64, unit, 14, MUTED, "sans", cls="rise", d=d + 0.05)
        c.text(x, y0 + 86, cap, 13, MUTED, "sans", cls="rise", d=d + 0.1)

    alt = (f"Contributions per month over the last year: " + ", ".join(f"{m} {v}" for m, v in months) +
           f". Longest streak {st['longest_streak']} days, {st['active_days']} active days, busiest day "
           f"{fmt_date(bd)} with {b['count']} contributions.")
    return card("activity", c, "Monthly activity", alt, alt=alt)


# --------------------------------------------------------------------------- feature tiles
def motif_build(c, x, y, d, col, accent):
    c.open("fade", d)
    for r in range(3):
        for k in range(3):
            fill = accent if (r, k) == (1, 2) else "none"
            c.raw(f'<rect x="{x + k * 19}" y="{y + r * 19}" width="13" height="13" rx="2" fill="{fill}" '
                  f'stroke="{col if fill == "none" else accent}" stroke-opacity="{.5 if fill == "none" else 1}"/>')
    c.close()


def motif_create(c, x, y, d, col, accent):
    pts, cx, cy = [], x + 28, y + 28
    for i in range(0, 121):
        a = i / 120 * 2.6 * math.tau
        r = 2 + 26 * i / 120
        pts.append(f"{n(cx + r * math.cos(a))},{n(cy + r * math.sin(a))}")
    c.open("fade", d)
    c.raw(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{accent}" stroke-width="1.6" stroke-linecap="round"/>')
    c.close()


def motif_explore(c, x, y, d, col, accent):
    pts = [(4, 44), (16, 20), (32, 30), (46, 8), (54, 36)]
    c.open("fade", d)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        c.raw(f'<line x1="{x + ax}" y1="{y + ay}" x2="{x + bx}" y2="{y + by}" stroke="{accent}" stroke-width="1" stroke-opacity=".55"/>')
    for k, (ax, ay) in enumerate(pts):
        c.raw(f'<path d="{star(x + ax, y + ay, 6 if k % 2 == 0 else 4)}" fill="{accent}"/>')
    c.close()


def tile(i: int, t0: float, data: dict) -> dict:
    d = t0 + i * T["tile_step"]
    repos = data.get("repo_count")
    specs = [
        dict(name="build", label="Build", bg=MID, fg="#FFFFFF", acc=GOLD, motif=motif_build,
             big=str(repos) if repos else None, big_cap="public repositories",
             head="Software, end to end", desc="Web apps and system tools in TypeScript, JavaScript and Java.",
             href=f"https://github.com/{PROFILE['login']}?tab=repositories"),
        dict(name="create", label="Create", bg=COBALT, fg="#FFFFFF", acc=IVORY, motif=motif_create, big=None,
             head="Brain scans, brainwaves and hand gestures",
             desc="Deep learning and computer-vision experiments, from MRI classifiers to live gesture recognition.",
             href=f"https://github.com/{PROFILE['login']}/Smart-seizure-detection"),
        dict(name="explore", label="Explore", bg=GOLD, fg=INK, acc=MID, motif=motif_explore, big=None,
             head="Always learning, mostly by building",
             desc="Spiking neural networks, AI agents and automation, picked up one small project at a time.",
             href=f"https://github.com/{PROFILE['login']}?tab=stars"),
    ]
    s = specs[i]
    c = Canvas(TW, TH)
    c.rect(0, 0, TW, TH, s["bg"], rx=16, cls="fade", d=d)
    s["motif"](c, TW - 24 - 56, 24, d + 0.4, s["fg"], s["acc"])
    c.text(24, 42, s["label"].upper(), 10.5, s["acc"], "mono", ls=1.6, cls="rise", d=d + 0.15)
    if s.get("big"):
        c.text(22, 156, s["big"], 104, s["fg"], "serif", cls="rise", d=d + 0.25, ls=-1)
        c.text(24, 184, s["big_cap"], 14, s["fg"], "sans-m", cls="rise", d=d + 0.35)
    else:
        for k, ln in enumerate(wrap("serif", s["head"], 34, TW - 48, 4)):
            c.text(24, 112 + k * 38, ln, 34, s["fg"], "serif", cls="rise", d=d + 0.25 + k * 0.07)
    lines = wrap("sans", s["desc"], 13, TW - 48, 4)
    for k, ln in enumerate(lines):
        c.text(24, TH - 26 - (len(lines) - 1 - k) * 18, ln, 13, s["fg"], "sans", cls="rise", d=d + 0.45 + k * 0.05)
    title = f"{s['label']}: {s.get('big') or s['head']}"
    return card(f"tile-{s['name']}", c, title, s["desc"], href=s["href"],
                alt=f"{s['label']}. {(s['big'] + ' ' + s['big_cap']) if s.get('big') else s['head']}. {s['desc']}")


# --------------------------------------------------------------------------- projects
def heading(t0: float) -> dict:
    H = 112
    c = Canvas(W, H)
    c.rect(0, 0, W, H, IVORY, rx=16, cls="fade", d=t0)
    c.text(40, 72, "What I’m building", 54, INK, "serif", cls="rise", d=t0 + 0.2, ls=-.5)
    c.text(W - 40, 70, "SELECTED PROJECTS", 10.5, MUTED, "mono", anchor="end", ls=1.4, cls="rise", d=t0 + 0.35)
    c.rect(40, 92, W - 80, 1, HAIR, cls="rule", d=t0 + 0.4)
    return card("building", c, "What I’m building", "Selected projects.", alt="What I’m building: selected projects.")


def project(i: int, t0: float, p: dict, repos: dict) -> dict:
    H = 184
    d = t0 + i * T["project_step"]
    r = repos.get(p["repo"]) if p["repo"] else None
    href = r["url"] if r else None
    c = Canvas(W, H)
    c.panel("#FFFFFF", d)
    c.raw(f'<path class="fade" d="{star(46, 37, 5.5)}" fill="{GOLD}"{D(d + .1)}/>')
    c.text(60, 41, p["category"].upper(), 10.5, COBALT, "mono", ls=1.4, cls="rise", d=d + 0.1)
    if href:
        lab = "View repository"
        c.text(W - 40, 41, lab, 13, COBALT, "sans-m", anchor="end", cls="rise", d=d + 0.2)
        c.rect(W - 40 - width("sans-m", lab, 13), 46, width("sans-m", lab, 13), 1, COBALT, cls="rise", d=d + 0.2)
    c.text(40, 86, p["title"], 34, INK, "serif", cls="rise", d=d + 0.2, ls=-.3)
    if p.get("subtitle"):
        c.text(40 + width("serif", p["title"], 34, -.3) + 14, 86, p["subtitle"], 34, MUTED, "serif-i", cls="rise", d=d + 0.25)
    for k, ln in enumerate(wrap("sans", p["desc"], 14, 690, 2)):
        c.text(40, 114 + k * 21, ln, 14, INK, "sans", cls="rise", d=d + 0.3 + k * 0.05)
    x = 40
    for tg in p["tags"]:
        w = width("mono", tg, 10.5) + 20
        c.open("rise", d + 0.45)
        c.raw(f'<rect x="{n(x)}" y="142" width="{n(w)}" height="22" rx="11" fill="none" stroke="{K.mix(INK, "#FFFFFF", .72)}"/>')
        c.text(x + 10, 157, tg, 10.5, INK, "mono")
        c.close()
        x += w + 8
    alt = f"{p['title']}{' ' + p['subtitle'] if p.get('subtitle') else ''}: {p['desc']}"
    return card(f"project-{p['slug']}", c, p["title"], p["desc"], href=href, alt=alt)


# --------------------------------------------------------------------------- footer
def footer(t0: float, data: dict) -> dict:
    H = 56
    c = Canvas(W, H)
    c.rect(0, 0, W, H, IVORY, rx=16, cls="fade", d=t0)
    gen = str(data.get("generated_at", ""))
    stamp = ""
    if gen and not data.get("sample"):
        try:
            stamp = "UPDATED " + fmt_date(dt.datetime.fromisoformat(gen).date()).upper()
        except ValueError:
            pass
    c.text(40, 34, stamp or "REDDY PRAVALLIKA", 10.5, MUTED, "mono", ls=1.2, cls="fade", d=t0 + 0.2)
    c.text(W - 40, 34, "Generated with Python, drawn in SVG", 10.5, MUTED, "mono", anchor="end", cls="fade", d=t0 + 0.3)
    return card("footer", c, "Footer", "Last updated and how this page is made.", alt="Footer")


# --------------------------------------------------------------------------- README + preview
def footer_links() -> str:
    L = [("GitHub", f"https://github.com/{PROFILE['login']}"), ("LinkedIn", PROFILE["linkedin"])]
    if PROFILE["website"]:
        L.append(("Portfolio", PROFILE["website"]))
    L.append(("Email", f"mailto:{PROFILE['email']}"))
    return " &nbsp;·&nbsp; ".join(f'<a href="{K.esc(u)}">{t}</a>' for t, u in L)


def stack_html(cards: list[dict]) -> str:
    def img(c, w):
        t = f'<img src="cards/{c["name"]}.svg" width="{w}" alt="{K.esc(c["alt"])}">'
        return f'<a href="{K.esc(c["href"])}">{t}</a>' if c["href"] else t

    by = {c["name"]: c for c in cards}
    single = ["hero", "contributions", "activity"]
    out = [f'<p align="center">{img(by[k], "100%")}</p>' for k in single]
    out.append('<p align="center">\n' + "\n".join(img(by[f"tile-{k}"], "32.5%") for k in ("build", "create", "explore")) + "\n</p>")
    out.append(f'<p align="center">{img(by["building"], "100%")}</p>')
    out += [f'<p align="center">{img(c, "100%")}</p>' for c in cards if c["name"].startswith("project-")]
    out.append(f'<p align="center">{img(by["footer"], "100%")}</p>')
    out.append(f'<p align="center">{footer_links()}</p>')
    return "\n\n".join(out) + "\n"


PREVIEW = """<!doctype html><meta charset="utf-8"><title>Profile preview (static)</title>
<style>body{{margin:0;padding:32px 0;background:#fff;color:#1f2328;font:14px system-ui}}
.col{{max-width:888px;margin:0 auto;padding:0 24px}}p{{margin:16px 0;text-align:center}}img{{vertical-align:top}}
a{{color:#0969da}}@media (prefers-color-scheme:dark){{body{{background:#0d1117}}a{{color:#4493f8}}}}</style>
<div class="col">
{body}</div>
"""


def main() -> None:
    if not DATA_FILE.exists():
        sys.exit(f"{DATA_FILE} not found. Run scripts/fetch_contributions.py first.")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if data.get("sample"):
        print("WARNING: SAMPLE contribution data. Run the update workflow before publishing.", file=sys.stderr)
    days = parse_days(data.get("days", []))
    st = summarise(days)
    repos = {r["name"]: r for r in data.get("repos", [])}
    for p in PROJECTS:
        if p["repo"] and repos and p["repo"] not in repos:
            print(f"WARNING: repo {p['repo']!r} not found in data; {p['slug']} card will not be linked.", file=sys.stderr)

    cards = [hero(T["hero"]), graph(T["graph"], data, days, st), activity(T["activity"], data, days, st)]
    cards += [tile(i, T["tiles"], data) for i in range(3)]
    cards.append(heading(T["heading"]))
    cards += [project(i, T["projects"], p, repos) for i, p in enumerate(PROJECTS)]
    footer_t = T["projects"] + len(PROJECTS) * T["project_step"] + 0.3
    cards.append(footer(max(T["footer"], footer_t), data))

    if CARDS.exists():
        for old in CARDS.glob("*.svg"):
            old.unlink()
    CARDS.mkdir(parents=True, exist_ok=True)
    for c in cards:
        (CARDS / f"{c['name']}.svg").write_text(c["svg"], encoding="utf-8")
        print(f"cards/{c['name']}.svg  {len(c['svg']) / 1024:.1f} KB")
    stack = stack_html(cards)
    if STATIC:
        (OUT_ROOT / "index.html").write_text(PREVIEW.format(body=stack), encoding="utf-8")
        print(f"static preview: {OUT_ROOT / 'index.html'}")
    else:
        (OUT_ROOT / "README.md").write_text(stack, encoding="utf-8")
        print(f"README written: {OUT_ROOT / 'README.md'}")


if __name__ == "__main__":
    main()
