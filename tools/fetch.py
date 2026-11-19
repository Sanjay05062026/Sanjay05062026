"""
Pulls live public data for one GitHub user: profile, repos, languages, README
summaries, commit / PR / issue counts and the contribution calendar.

With GITHUB_TOKEN set (always true inside GitHub Actions) the calendar comes from
the GraphQL API. Without a token it is read from the public contributions page,
so the script also works on your own machine.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
import urllib.request

API = "https://api.github.com"
UA = "profile-readme-builder"


def _get(url: str, token: str | None, accept: str = "application/vnd.github+json", data: bytes | None = None) -> str:
    headers = {"Accept": accept, "User-Agent": UA}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _json(path: str, token: str | None):
    return json.loads(_get(API + path, token))


# ------------------------------------------------------------------ README summary
def summarize_readme(md: str, limit: int = 170) -> str:
    """First real paragraph of a README, as plain text."""
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    for block in re.split(r"\n\s*\n", md):
        lines = [l.strip() for l in block.strip().splitlines()]
        if not lines or lines[0].startswith(("#", "|", "!", "<", "-", "*", ">", "[!", "```")):
            continue
        text = " ".join(lines)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # images
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)       # links -> text
        text = re.sub(r"<[^>]+>", "", text)                        # html
        text = re.sub(r"[*_`]{1,3}", "", text).strip()
        if len(text) < 30:
            continue
        if len(text) > limit:
            text = text[: limit].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
        return text
    return ""


# ------------------------------------------------------------------ contributions
GQL = """query($login:String!){user(login:$login){contributionsCollection{
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def calendar_graphql(login: str, token: str) -> list[list]:
    body = json.dumps({"query": GQL, "variables": {"login": login}}).encode()
    res = json.loads(_get(API + "/graphql", token, data=body))
    weeks = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[d["date"], d["contributionCount"]] for w in weeks for d in w["contributionDays"]]


def calendar_scrape(login: str) -> list[list]:
    html = _get(f"https://github.com/users/{login}/contributions", None, accept="text/html")
    tips = {}
    for for_id, text in re.findall(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        m = re.match(r"\s*([\d,]+)\s+contribution", text)
        tips[for_id] = int(m.group(1).replace(",", "")) if m else 0
    days = []
    for tag in re.findall(r"<td\b[^>]*ContributionCalendar-day[^>]*>", html):
        date = re.search(r'data-date="([^"]+)"', tag)
        cid = re.search(r'\bid="([^"]+)"', tag)
        if date and cid:
            days.append([date.group(1), tips.get(cid.group(1), 0)])
    if not days:
        raise RuntimeError("contribution calendar markup not found")
    return sorted(days)


# ------------------------------------------------------------------ main fetch
def fetch(login: str, token: str | None = None) -> dict:
    user = _json(f"/users/{login}", token)

    repos, page = [], 1
    while True:
        batch = _json(f"/users/{login}/repos?per_page=100&page={page}&type=owner&sort=pushed", token)
        repos += batch
        if len(batch) < 100:
            break
        page += 1

    own = []
    for r in repos:
        if r["fork"] or r.get("archived") or r.get("private") or r["name"].lower() == login.lower():
            continue
        item = {k: r.get(k) for k in (
            "name", "html_url", "description", "homepage", "language", "stargazers_count",
            "forks_count", "pushed_at", "created_at", "topics")}
        item["languages"] = _json(f"/repos/{login}/{r['name']}/languages", token)
        try:
            md = _get(f"{API}/repos/{login}/{r['name']}/readme", token, accept="application/vnd.github.raw")
            item["readme_summary"] = summarize_readme(md)
        except Exception:
            item["readme_summary"] = ""
        own.append(item)

    def search_count(kind: str, q: str) -> int | None:
        try:
            return _json(f"/search/{kind}?q={urllib.parse.quote(q, safe=':+')}&per_page=1", token)["total_count"]
        except Exception:
            return None

    counts = {
        "commits": search_count("commits", f"author:{login}"),
        "prs": search_count("issues", f"author:{login}+type:pr"),
        "issues": search_count("issues", f"author:{login}+type:issue"),
    }

    calendar, source = None, None
    if token:
        try:
            calendar, source = calendar_graphql(login, token), "graphql"
        except Exception as e:  # fall through to the public page
            print(f"  graphql calendar failed ({e}), trying the public page")
    if calendar is None:
        calendar, source = calendar_scrape(login), "page"

    return {
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "login": login,
        "followers": user.get("followers", 0),
        "public_repos": user.get("public_repos", 0),
        "created_at": user.get("created_at"),
        "repos": own,
        "counts": counts,
        "calendar": calendar,
        "calendar_source": source,
    }
