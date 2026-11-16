"""ASCII 'ink' portrait. Uses assets/portrait.(jpg|png|webp) if present, else a typographic starry sky."""
from __future__ import annotations

import math
import random

from svgkit import ROOT

RAMP = " .:-=+*#%@"  # light -> dark ink


def _from_photo(cols: int, rows: int, aspect: float) -> list[str] | None:
    """`aspect` = drawn width / drawn height of the whole art block, so faces are not stretched."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = ROOT / "assets" / f"portrait.{ext}"
        if not p.exists():
            continue
        from PIL import Image, ImageOps

        im = ImageOps.autocontrast(ImageOps.exif_transpose(Image.open(p)).convert("L"), cutoff=2)
        if im.width / im.height > aspect:  # too wide: crop the sides, centred
            tw, th = int(im.height * aspect), im.height
            box = ((im.width - tw) // 2, 0, (im.width - tw) // 2 + tw, th)
        else:  # too tall: crop top-biased, which keeps a head-and-shoulders portrait's face
            tw, th = im.width, int(im.width / aspect)
            top = int((im.height - th) * 0.25)
            box = (0, top, tw, top + th)
        px = im.crop(box).resize((cols, rows), Image.LANCZOS).load()
        return ["".join(RAMP[min(len(RAMP) - 1, int((255 - px[x, y]) / 256 * len(RAMP)))] for x in range(cols)).rstrip()
                for y in range(rows)]
    return None


def _sky(cols: int, rows: int) -> list[str]:
    """A night sky in type: crescent moon, wind contours, cross-shaped stars, a cypress, rolling hills."""
    rnd = random.Random(1889)
    g = [[" "] * cols for _ in range(rows)]
    A = 0.5 * cols / rows  # horizontal cells per vertical cell, so circles stay round

    def put(c, r, ch):
        if 0 <= r < rows and 0 <= c < cols:
            g[r][c] = ch

    for r in range(rows):
        v = r / rows
        for c in range(cols):
            u = c / cols
            ch = " "
            # wind: flowing contour lines, strongest mid-sky
            if .27 < v < .70:
                phase = u * 15 + 5 * math.sin(v * 8 + u * 5) + v * 9
                w = abs(math.sin(phase))
                fade = 1 - abs(v - .48) / .22
                if w < .30 and fade > .10:
                    ch = "=" if (w < .12 and fade > .5) else ("~" if fade > .3 else "-")
            # hills: contour bands that thicken toward the bottom
            hill = .78 + .04 * math.sin(u * 6.5) + .025 * math.sin(u * 17 + 1)
            if v > hill:
                k = abs(math.sin((v - hill) * 42 + u * 7))
                ch = "=" if k < .42 else (":" if k < .75 else ".")
                if v > hill + .12:
                    ch = "#" if k < .5 else "="
            # cypress
            if ((u - .20) / .05) ** 2 + ((v - .66) / .30) ** 2 < 1:
                ch = "%" if (r + c) % 5 else "#"
            if ch == " " and v < .76 and ((c * 7919 + r * 104729) % 17) < 1:
                ch = "."
            g[r][c] = ch
    # moon: crescent with two glow rings
    mc, mr, rad = cols * .74, rows * .21, rows * .20
    for r in range(rows):
        for c in range(cols):
            dx, dy = (c - mc) / A / 2, r - mr
            m1 = math.hypot(dx, dy) / rad
            m2 = math.hypot((c - mc - cols * .085) / A / 2, r - mr + rows * .03) / (rad * .86)
            if m1 < 1 and m2 >= 1:
                g[r][c] = "@"
            elif m1 < 1:
                g[r][c] = " "
            elif 1.28 < m1 < 1.40 and g[r][c] in " .":
                g[r][c] = ":"
            elif 1.62 < m1 < 1.72 and g[r][c] in " .":
                g[r][c] = "."
    # stars: a centre with four arms
    for _ in range(11):
        c, r = int(rnd.uniform(.05, .95) * cols), int(rnd.uniform(.04, .52) * rows)
        if math.hypot((c - cols * .74) / A / 2, r - rows * .21) < rows * .36:
            continue
        put(c, r, "@"); put(c - 1, r, "-"); put(c + 1, r, "-"); put(c, r - 1, ":"); put(c, r + 1, ":")
    return ["".join(row).rstrip() for row in g]


def ascii_portrait(cols: int = 56, rows: int = 38, aspect: float = 0.79) -> tuple[list[str], bool]:
    """Returns (rows, is_photo). `aspect` is the drawn width/height of the block."""
    photo = _from_photo(cols, rows, aspect)
    return (photo, True) if photo else (_sky(cols, rows), False)
