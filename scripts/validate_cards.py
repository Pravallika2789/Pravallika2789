#!/usr/bin/env python3
"""Validate every card in cards/: well-formed, safe for <img>, accessible, animation rules honoured."""
from __future__ import annotations

import base64
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CARDS = Path(__file__).resolve().parent.parent / "cards"
SVG = "{http://www.w3.org/2000/svg}"
MAX_BYTES = 400_000


def check(path: Path) -> list[str]:
    errs, raw = [], path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        return [f"not well-formed XML: {e}"]
    if root.tag != SVG + "svg" or not root.get("viewBox"):
        errs.append("root must be <svg> with a viewBox")
    if len(raw.encode()) > MAX_BYTES:
        errs.append(f"larger than {MAX_BYTES} bytes")
    if root.find(SVG + "title") is None or root.find(SVG + "desc") is None:
        errs.append("missing <title>/<desc>")
    for bad in ("<script", "foreignObject", "onload=", "onclick="):
        if bad in raw:
            errs.append(f"forbidden content: {bad}")
    for m in re.finditer(r'(?:href|src)="(?!data:|#)([^"]+)"', raw):
        errs.append(f"external reference: {m.group(1)[:60]}")
    if re.search(r"url\((?!data:|#)(?!['\"]?data:)", raw.replace("url(#", "")):
        errs.append("external url() reference")
    animated = "@keyframes" in raw or "<animate" in raw
    if animated and "prefers-reduced-motion:reduce" not in raw:
        errs.append("animated but no prefers-reduced-motion block")
    if "<animate" in raw and ".smil{display:none}" not in raw:
        errs.append("SMIL present but not hidden under reduced motion")
    for b64 in re.findall(r"data:font/woff;base64,([A-Za-z0-9+/=]+)", raw):
        if base64.b64decode(b64)[:4] != b"wOFF":
            errs.append("embedded font is not WOFF")
    if "@font-face" not in raw:
        errs.append("no embedded font")
    return errs


def main() -> None:
    files = sorted(CARDS.glob("*.svg"))
    if not files:
        sys.exit("no cards found")
    bad = 0
    for f in files:
        errs = check(f)
        print(("FAIL " if errs else "ok   ") + f.name + "".join(f"\n       - {e}" for e in errs))
        bad += bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
