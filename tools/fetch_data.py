"""Collect public GitHub profile data into data/profile.json (stdlib only).

Usage: python fetch_data.py <username> <out_dir>
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

user, out_dir = sys.argv[1], Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "profile-readme-generator", "Accept": "application/vnd.github+json"}


def get(url, headers=None):
    extra = dict(headers or {})
    if url.startswith("https://api.github.com") and os.environ.get("GITHUB_TOKEN"):
        extra["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]  # higher rate limit inside Actions
    req = urllib.request.Request(url, headers={**UA, **extra})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def api(path):
    return json.loads(get("https://api.github.com" + path))


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

# Contribution calendar: public HTML fragment, one cell per day plus a tooltip with the count.
html = get(f"https://github.com/users/{user}/contributions", {"X-Requested-With": "XMLHttpRequest"}).decode("utf-8")
cells = dict(re.findall(r'data-date="(\d{4}-\d\d-\d\d)" id="(contribution-day-component-\d+-\d+)"', html))
by_id = {v: k for k, v in cells.items()}
days = {d: 0 for d in cells}
for cid, text in re.findall(r'<tool-tip[^>]*for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)', html):
    m = re.match(r"\s*(\d+) contribution", text)
    if cid in by_id and m:
        days[by_id[cid]] = int(m.group(1))

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
}
(out_dir / "profile.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
total = sum(days.values())
print(f"{user}: {len(repos)} repos, {len(days)} days, {total} contributions, "
      f"{sum(1 for v in days.values() if v)} active days, max {max(days.values())}")
