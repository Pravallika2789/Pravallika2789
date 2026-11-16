"""Contribution statistics, shared by the fetcher (writes them) and the renderer (reads daily data)."""
from __future__ import annotations

import datetime as dt


def parse_days(raw: list[dict]) -> list[tuple[dt.date, int]]:
    return sorted((dt.date.fromisoformat(d["date"]), int(d["count"])) for d in raw)


def summarise(days: list[tuple[dt.date, int]]) -> dict:
    """Everything the cards display, computed from the daily counts and nothing else."""
    if not days:
        return {}
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if counts[i] == 0:  # today may simply not have happened yet
        i -= 1
    current = 0
    while i >= 0 and counts[i] > 0:
        current, i = current + 1, i - 1
    busiest = max(days, key=lambda dc: (dc[1], dc[0]))
    return {
        "total": sum(counts),
        "span_days": len(counts),
        "active_days": sum(1 for c in counts if c > 0),
        "longest_streak": longest,
        "current_streak": current,
        "busiest": {"date": busiest[0].isoformat(), "count": busiest[1]},
        "monthly": monthly(days),
    }


def monthly(days: list[tuple[dt.date, int]]) -> list[dict]:
    """The last 12 calendar months ending with the month of the latest day."""
    last = days[-1][0]
    keys = []
    for k in range(11, -1, -1):
        m, y = last.month - k, last.year
        while m <= 0:
            m, y = m + 12, y - 1
        keys.append((y, m))
    totals = {key: 0 for key in keys}
    for d, c in days:
        if (d.year, d.month) in totals:
            totals[(d.year, d.month)] += c
    return [{"month": f"{y}-{m:02d}", "count": totals[(y, m)]} for y, m in keys]
