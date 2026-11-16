#!/usr/bin/env python3
"""Refresh data/contributions.json from GitHub's GraphQL API.

Auth: GH_TOKEN (falls back to GITHUB_TOKEN), read from the environment only; it is never written to
disk or printed. The workflow's built-in token sees PUBLIC contributions. For private ones, add a
repo secret PROFILE_TOKEN and enable "Include private contributions" in your profile settings.

On any failure this exits non-zero WITHOUT touching the existing JSON, so cards never go blank or fake.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import parse_days, summarise  # noqa: E402

LOGIN = os.environ.get("PROFILE_LOGIN", "Pravallika2789")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(privacy: PUBLIC, ownerAffiliations: OWNER, first: 100, orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes { name url description isFork stargazerCount primaryLanguage { name } }
    }
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def call() -> dict:
    if not TOKEN:
        sys.exit("Set GH_TOKEN (or GITHUB_TOKEN) to call the GitHub GraphQL API.")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "profile-cards"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.load(r)
            user = (payload.get("data") or {}).get("user")
            if payload.get("errors") or not user:
                sys.exit(f"GraphQL error: {[e.get('message') for e in payload.get('errors', [])] or 'user not found'}")
            return user
        except urllib.error.HTTPError as e:  # never echo headers: they can carry the token
            if e.code in (401, 403):
                sys.exit(f"GitHub rejected the token (HTTP {e.code}).")
            if attempt == 2:
                sys.exit(f"GitHub API error: HTTP {e.code}")
        except urllib.error.URLError as e:
            if attempt == 2:
                sys.exit(f"GitHub API unreachable: {e.reason}")
        time.sleep(2 * (attempt + 1))
    raise AssertionError


def main() -> None:
    u = call()
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [{"date": d["date"], "count": d["contributionCount"]}
            for w in cal["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    if not days:
        sys.exit("GitHub returned an empty contribution calendar; keeping the existing file.")
    st = summarise(parse_days(days))
    data = {
        "login": LOGIN,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "GitHub GraphQL contributionsCollection",
        "repo_count": u["repositories"]["totalCount"],
        "total": cal["totalContributions"],
        "days": days,
        "summary": {k: v for k, v in st.items() if k != "monthly"},
        "monthly": st["monthly"],
        "repos": [{"name": r["name"], "url": r["url"], "description": r["description"], "isFork": r["isFork"],
                   "stars": r["stargazerCount"], "language": (r["primaryLanguage"] or {}).get("name")}
                  for r in u["repositories"]["nodes"]],
    }
    OUT.parent.mkdir(exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(OUT)
    print(f"wrote {OUT.name}: {len(days)} days, {cal['totalContributions']} contributions, {len(data['repos'])} repos")


if __name__ == "__main__":
    main()
