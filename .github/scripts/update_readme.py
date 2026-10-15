"""Rewrite the block between <!-- ACTIVITY:START --> and <!-- ACTIVITY:END -->
in README.md with a short list of recent public GitHub activity."""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

USER = os.environ.get("GH_USER", "Nivakaran-S")
TOKEN = os.environ.get("GITHUB_TOKEN")
README = "README.md"
LINES = 8
COLOMBO = timezone(timedelta(hours=5, minutes=30))


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "readme-activity",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def describe(ev):
    repo = ev["repo"]["name"].split("/")[-1]
    p = ev["payload"]
    t = ev["type"]
    if t == "PushEvent":
        n = p.get("size") or len(p.get("commits", [])) or 1
        return f"pushed {n} commit{'s' if n != 1 else ''} to **{repo}**"
    if t == "PullRequestEvent":
        return f"{p['action']} pull request #{p['number']} in **{repo}**"
    if t == "IssuesEvent":
        return f"{p['action']} issue #{p['issue']['number']} in **{repo}**"
    if t == "CreateEvent":
        return f"created a {p.get('ref_type', 'repository')} in **{repo}**"
    if t == "ReleaseEvent":
        return f"released {p['release']['tag_name']} of **{repo}**"
    if t == "WatchEvent":
        return f"starred **{repo}**"
    return None


def build():
    events = api(f"/users/{USER}/events/public?per_page=100")
    pushes = {}  # (day, repo) -> commit count, so a busy day is one line
    order = []
    for ev in events:
        # skip the profile repo itself: its CI commits are noise
        if ev["repo"]["name"].lower() == f"{USER}/{USER}".lower():
            continue
        ts = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00")).astimezone(COLOMBO)
        day = f"{ts:%d %b %Y}"
        repo = ev["repo"]["name"].split("/")[-1]
        if ev["type"] == "PushEvent":
            key = (day, repo)
            if key not in pushes:
                pushes[key] = 0
                order.append(("push", day, repo))
            pushes[key] += ev["payload"].get("size") or len(ev["payload"].get("commits", [])) or 1
        else:
            d = describe(ev)
            if d:
                order.append(("other", day, d))
    rows = []
    for kind, day, x in order[:LINES]:
        if kind == "push":
            n = pushes[(day, x)]
            rows.append(f"- {day}, pushed {n} commit{'s' if n != 1 else ''} to **{x}**")
        else:
            rows.append(f"- {day}, {x}")
    if not rows:
        rows = ["- No public activity in the last 90 days."]
    stamp = datetime.now(COLOMBO).strftime("%d %b %Y, %H:%M")
    return "\n".join(rows) + f"\n\n<sub>Updated {stamp} (Asia/Colombo).</sub>"


def main():
    text = open(README, encoding="utf-8").read()
    pat = re.compile(r"(<!-- ACTIVITY:START -->\n).*?(\n<!-- ACTIVITY:END -->)", re.S)
    if not pat.search(text):
        sys.exit("ACTIVITY markers not found in README.md")
    new = pat.sub(lambda m: m.group(1) + build() + m.group(2), text)
    if new != text:
        open(README, "w", encoding="utf-8", newline="\n").write(new)


if __name__ == "__main__":
    main()
