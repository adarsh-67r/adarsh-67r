import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

TOKEN = os.environ["GITHUB_TOKEN"]
LOGIN = os.environ["GH_LOGIN"]
API_URL = "https://api.github.com/graphql"
RAMP = " .`:-=+*cs#%@"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        languages(first: 6, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def query_github(variables):
    payload = json.dumps({"query": QUERY, "variables": variables}).encode()
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": LOGIN,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]["user"]


def pinned_window():
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=364)
    end = today + timedelta(hours=23, minutes=59, seconds=59)
    iso = lambda value: value.isoformat().replace("+00:00", "Z")
    return iso(start), iso(end)


def shell(width, height, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="monospace"><rect width="100%" height="100%" rx="8" fill="#0d1117"/>{body}</svg>'


def save(path, content):
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def generate_stats(calendar):
    data = calendar["contributionCalendar"]
    days = [day["contributionCount"] for week in data["weeks"] for day in week["contributionDays"]]
    weekly = [sum(days[i:i + 7]) for i in range(0, len(days), 7)][-12:]
    peak = max(weekly, default=1) or 1
    bars = "".join(f'<rect x="{25 + i * 14}" y="{150 - int(value / peak * 70)}" width="10" height="{max(1, int(value / peak * 70))}" fill="#58a6ff" rx="1"/>' for i, value in enumerate(weekly))
    body = (f'<text x="25" y="30" fill="#58a6ff" font-size="15">{LOGIN} — contributions</text>'
            f'<text x="25" y="55" fill="#c9d1d9" font-size="13">total {data["totalContributions"]}   commits {calendar["totalCommitContributions"]}   PRs {calendar["totalPullRequestContributions"]}   issues {calendar["totalIssueContributions"]}</text>{bars}')
    save("stats.svg", shell(495, 170, body))


def generate_streak(calendar):
    days = [(day["date"], day["contributionCount"]) for week in calendar["contributionCalendar"]["weeks"] for day in week["contributionDays"]]
    current = 0
    for _, count in reversed(days):
        if count == 0:
            break
        current += 1
    longest = run = 0
    longest_start = longest_end = None
    for date, count in days:
        if count:
            run += 1
            if run == 1:
                start = date
            if run > longest:
                longest, longest_start, longest_end = run, start, date
        else:
            run = 0
    body = (f'<text x="25" y="30" fill="#58a6ff" font-size="15">{LOGIN} — streak</text>'
            f'<text x="25" y="60" fill="#c9d1d9" font-size="13">current streak: {current} day(s)</text>'
            f'<text x="25" y="82" fill="#c9d1d9" font-size="13">longest streak: {longest} day(s)</text>'
            f'<text x="25" y="104" fill="#8b949e" font-size="11">{longest_start or "-"} to {longest_end or "-"}</text>')
    save("streak.svg", shell(360, 130, body))


def generate_languages(repositories):
    totals = {}
    for repository in repositories["nodes"]:
        for edge in repository["languages"]["edges"]:
            name = edge["node"]["name"]
            size, color = totals.get(name, (0, edge["node"]["color"] or "#999999"))
            totals[name] = (size + edge["size"], color)
    ranked = sorted(totals.items(), key=lambda item: item[1][0], reverse=True)[:6]
    total = sum(value[0] for _, value in ranked) or 1
    rows = ""
    y = 55
    for name, (size, color) in ranked:
        fraction = size / total
        rows += f'<rect x="20" y="{y}" width="{max(4, int(fraction * 220))}" height="9" fill="{color}" rx="2"/><text x="20" y="{y + 21}" fill="#c9d1d9" font-size="11">{name} {fraction * 100:.1f}%</text>'
        y += 32
    save("langs.svg", shell(280, max(100, y + 10), f'<text x="20" y="28" fill="#58a6ff" font-size="15">top languages</text>{rows}'))


def generate_year(calendar):
    days = [day["contributionCount"] for week in calendar["contributionCalendar"]["weeks"] for day in week["contributionDays"]]
    peak = max(days, default=1) or 1
    rows = []
    for offset in range(0, len(days), 53):
        values = days[offset:offset + 53]
        chars = "".join(RAMP[min(int(value / peak * (len(RAMP) - 1)), len(RAMP) - 1)] if value else " " for value in values)
        rows.append(f'<text x="20" y="{20 + offset // 53 * 12}" fill="#8b949e" font-size="10" xml:space="preserve">{chars}</text>')
    save("year.svg", shell(460, max(40, 20 + len(rows) * 12), "".join(rows)))


def main():
    start, end = pinned_window()
    user = query_github({"login": LOGIN, "from": start, "to": end})
    calendar = user["contributionsCollection"]
    generate_stats(calendar)
    generate_streak(calendar)
    generate_languages(user["repositories"])
    generate_year(calendar)


if __name__ == "__main__":
    main()
