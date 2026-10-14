"""Rewrite the block between <!-- ACTIVITY:START --> and <!-- ACTIVITY:END -->
in README.md with a console-style log of recent public GitHub activity."""
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
        return f"push    {repo} ({n} commit{'s' if n != 1 else ''})"
    if t == "PullRequestEvent":
        return f"pr      {repo} {p['action']} #{p['number']}"
    if t == "IssuesEvent":
        return f"issue   {repo} {p['action']} #{p['issue']['number']}"
    if t == "CreateEvent":
        return f"create  {repo} {p.get('ref_type', '')}"
    if t == "ReleaseEvent":
        return f"release {repo} {p['release']['tag_name']}"
    if t == "WatchEvent":
        return f"star    {repo}"
    return None


def build():
    events = api(f"/users/{USER}/events/public?per_page=50")
    rows = []
    for ev in events:
        d = describe(ev)
        # skip the profile repo itself: its CI commits are noise
        if not d or ev["repo"]["name"].lower() == f"{USER}/{USER}".lower():
            continue
        ts = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00")).astimezone(COLOMBO)
        rows.append(f"  {ts:%Y-%m-%d %H:%M}  {d}")
        if len(rows) == LINES:
            break
    if not rows:
        rows = ["  no public activity in the last 90 days"]
    stamp = datetime.now(COLOMBO).strftime("%Y-%m-%d %H:%M")
    body = "\n".join(rows)
    return (
        "```console\n"
        "nivakaran-s@github:~$ tail -n 8 /var/log/git/activity.log\n\n"
        f"{body}\n\n"
        f"-- synced {stamp} Asia/Colombo --\n"
        "```"
    )


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
