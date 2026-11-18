"""Collect public GitHub profile data into <out_dir>/profile.json and avatar.jpg (stdlib only).

Usage: python fetch_data.py <username> <out_dir> [last_good_profile.json]

The contribution calendar comes from the first source that works:
  1. the profile page's calendar HTML (the only source that includes private contributions shown on the profile),
  2. the official GraphQL API (needs GITHUB_TOKEN; public contributions only),
  3. the calendar saved by the last successful run (last_good_profile.json).
profile.json records which source was used and what each source reported, for troubleshooting.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

user, out_dir = sys.argv[1], Path(sys.argv[2])
last_good = Path(sys.argv[3]) if len(sys.argv) > 3 else None
out_dir.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "profile-readme-generator", "Accept": "application/vnd.github+json"}
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def get(url, headers=None, data=None):
    extra = dict(headers or {})
    if url.startswith("https://api.github.com") and TOKEN:
        extra["Authorization"] = "Bearer " + TOKEN  # higher rate limit inside Actions
    req = urllib.request.Request(url, headers={**UA, **extra}, data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def api(path):
    return json.loads(get("https://api.github.com" + path))


def calendar_html():
    html = get(f"https://github.com/users/{user}/contributions", {"X-Requested-With": "XMLHttpRequest"}).decode("utf-8")
    cells = dict(re.findall(r'data-date="(\d{4}-\d\d-\d\d)" id="(contribution-day-component-\d+-\d+)"', html))
    by_id = {v: k for k, v in cells.items()}
    days = {d: 0 for d in cells}
    for cid, text in re.findall(r'<tool-tip[^>]*for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)', html):
        m = re.match(r"\s*(\d+) contribution", text)
        if cid in by_id and m:
            days[by_id[cid]] = int(m.group(1))
    return days


def calendar_graphql():
    if not TOKEN:
        raise RuntimeError("no GITHUB_TOKEN")
    query = ("query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{"
             "weeks{contributionDays{date contributionCount}}}}}}")
    body = json.dumps({"query": query, "variables": {"login": user}}).encode()
    res = json.loads(get("https://api.github.com/graphql", {"Content-Type": "application/json"}, body))
    weeks = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}


def looks_right(days):
    """A full calendar covers about a year and ends no earlier than yesterday."""
    if len(days) < 300:
        return False
    newest = dt.date.fromisoformat(max(days))
    return newest >= dt.date.today() - dt.timedelta(days=2)


profile = api(f"/users/{user}")
repos = []
for r in api(f"/users/{user}/repos?per_page=100&sort=pushed"):
    if r["fork"]:
        continue
    repos.append({
        "name": r["name"],
        "description": r["description"] or "",
        "stars": r["stargazers_count"],
        "forks": r["forks_count"],
        "language": r["language"],
        "languages": api(f"/repos/{user}/{r['name']}/languages"),
        "url": r["html_url"],
        "pushed_at": r["pushed_at"],
    })

report, days, source = {}, None, None
for name, fn in (("html", calendar_html), ("graphql", calendar_graphql)):
    try:
        found = fn()
        report[name] = {"days": len(found), "total": sum(found.values()), "ok": looks_right(found)}
        if days is None and looks_right(found):
            days, source = found, name
    except Exception as exc:  # keep going: the next source may work
        report[name] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
if days is None and last_good and last_good.exists() and last_good.stat().st_size:
    try:
        days, source = json.loads(last_good.read_text(encoding="utf-8"))["contributions"], "last_good"
    except (ValueError, KeyError) as exc:
        report["last_good"] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
if days is None:
    days, source = {}, "none"

(out_dir / "avatar.jpg").write_bytes(get(profile["avatar_url"] + "&s=240"))
data = {
    "login": profile["login"],
    "name": profile["name"] or profile["login"],
    "bio": profile["bio"] or "",
    "company": profile["company"] or "",
    "location": profile["location"] or "",
    "followers": profile["followers"],
    "public_repos": profile["public_repos"],
    "created_at": profile["created_at"],
    "repos": repos,
    "contributions": dict(sorted(days.items())),
    "contributions_source": source,
    "contributions_report": report,
}
(out_dir / "profile.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
total = sum(days.values())
print(f"{user}: {len(repos)} repos, {len(days)} days, {total} contributions from {source}; sources: {report}")
