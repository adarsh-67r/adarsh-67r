#!/usr/bin/env python3
"""Draw local profile stat graphics from GitHub GraphQL, stdlib only."""
import base64
import functools
import html
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com/graphql"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions weeks { contributionDays { contributionCount date weekday } } }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes { languages(first: 12, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
  }
}
"""
LIGHT = dict(data="#6e7681", emph="#424a53", dim="#8c959f", rule="#d8dee4", surface="#ffffff")
DARK = dict(data="#c9d1d9", emph="#f0f6fc", dim="#8b949e", rule="#30363d", surface="#0d1117")
MONO = "JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
WIDTH, LEFT, REVEAL = 620, 34, 1.30
RAMP = [" ", ":", "+", "#", "@"]


@functools.lru_cache(maxsize=None)
def face(filename, weight):
    path = os.path.join(FONT_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as file:
        import base64
        encoded = base64.b64encode(file.read()).decode("ascii")
    return f"@font-face{{font-family:JBMono;font-style:normal;font-weight:{weight};font-display:block;src:url(data:font/woff2;base64,{encoded}) format('woff2')}}"


def font_text():
    return face("jbmono-400.woff2", 400) + face("jbmono-600.woff2", 600)


def style(font=None):
    def block(theme):
        return f".d-f{{fill:{theme['data']}}}.d-s{{stroke:{theme['data']}}}.e-f{{fill:{theme['emph']}}}.m-f{{fill:{theme['dim']}}}.u-s{{stroke:{theme['rule']}}}.r{{stroke:{theme['surface']}}}"
    return f"<style>{font or font_text()}{block(LIGHT)}.w{{fill:{LIGHT['data']};opacity:.13}}@media(prefers-color-scheme:dark){{{block(DARK)}.w{{fill:{DARK['data']};opacity:.16}}}}</style>"


def head(w, h, font=None):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" font-family="{MONO}">{style(font)}'


def fade(delay, dur=.45):
    return f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/>'


def wipe(cid, x, y, w, h, delay, dur=REVEAL):
    clip = f'<clipPath id="{cid}"><rect x="{x}" y="{y}" height="{h}" width="0"><animate attributeName="width" from="0" to="{w}" begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/></rect></clipPath>'
    cursor = f'<rect y="{y}" width="2" height="{h}" class="d-f" opacity="0"><animate attributeName="x" from="{x}" to="{x+w}" begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/><set attributeName="opacity" to="0.55" begin="{delay:.2f}s"/><set attributeName="opacity" to="0" begin="{delay+dur:.2f}s"/></rect>'
    return clip, cursor


def label(x, y, text, size=11, cls="m-f", anchor="start", extra=""):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}"{a}{extra}>{html.escape(str(text))}</text>'


def contribution_days(calendar):
    return [day for week in calendar["weeks"] for day in week["contributionDays"]]


def window():
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    return f"{start.isoformat()}T00:00:00Z", f"{today.isoformat()}T23:59:59Z"


def fetch(login, token):
    since, until = window()
    payload = json.dumps({"query": QUERY, "variables": {"login": login, "from": since, "to": until}}).encode()
    request = urllib.request.Request(API, data=payload, headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": f"{login}-profile-stats"})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise SystemExit(f"GraphQL errors: {result['errors']}")
    user = (result.get("data") or {}).get("user")
    if not user:
        raise SystemExit(f"no such user: {login}")
    return user


def streaks(days):
    best = dict(length=0, start=None, end=None)
    run = 0
    for day in days:
        if day["contributionCount"] > 0:
            run += 1
            start = day["date"] if run == 1 else start
            if run > best["length"]:
                best = dict(length=run, start=start, end=day["date"])
        else:
            run = 0
    current = dict(length=0, start=None, end=None)
    tail = days[:-1] if days and days[-1]["contributionCount"] == 0 else days
    for day in reversed(tail):
        if not day["contributionCount"]:
            break
        current["length"] += 1
        current["start"] = day["date"]
        current["end"] = current["end"] or day["date"]
    return current, best


def languages(repositories):
    by_size, by_repo = {}, {}
    for node in repositories:
        edges = (node.get("languages") or {}).get("edges") or []
        for edge in edges:
            name = edge["node"]["name"]
            by_size[name] = by_size.get(name, 0) + edge["size"]
        if edges:
            top = edges[0]["node"]["name"]
            by_repo[top] = by_repo.get(top, 0) + 1
    rank = lambda values: sorted(values.items(), key=lambda item: (-item[1], item[0]))[:5]
    return rank(by_size), rank(by_repo)


def summarise(user):
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = [week["contributionDays"] for week in calendar["weeks"]]
    days = [day for week in weeks for day in week]
    current, longest = streaks(days)
    by_size, by_repo = languages(user["repositories"]["nodes"])
    weekly = [sum(day["contributionCount"] for day in week) for week in weeks]
    return dict(total=calendar["totalContributions"], active=sum(day["contributionCount"] > 0 for day in days), best_week=max(weekly, default=0), weekly=weekly, weeks=weeks, current=current, longest=longest, by_size=by_size, by_repo=by_repo)


def draw_stats(summary):
    height = 148
    weekly = summary["weekly"] or [0]
    peak = max(weekly) or 1
    points = [(i * WIDTH / max(len(weekly) - 1, 1), height - 10 - value / peak * 48) for i, value in enumerate(weekly)]
    clip, cursor = wipe("rs", 0, height - 68, WIDTH, 60, .5)
    area = f'<path d="M{points[0][0]:.1f} {height-10:.1f}' + "".join(f'L{x:.1f} {y:.1f}' for x, y in points) + f'L{points[-1][0]:.1f} {height-10:.1f}Z" class="w"/>'
    line = f'<path d="M{points[0][0]:.1f} {points[0][1]:.1f}' + "".join(f'L{x:.1f} {y:.1f}' for x, y in points[1:]) + '" class="d-s" stroke-width="2" stroke-linejoin="round" fill="none"/>'
    body = f'<g opacity="0">{fade(.1)}{label(0,50,summary["total"],52,"e-f",extra=" font-weight=\"600\"")}{label(0,72,"contributions in the last year",12)}</g>'
    body += f'<g opacity="0">{fade(.3)}{label(WIDTH,30,summary["active"],19,"e-f","end", " font-weight=\"600\"")}{label(WIDTH,47,"active days",11,"m-f","end")}</g>'
    body += clip + f'<g clip-path="url(#rs)">{area}{line}</g>{cursor}</svg>'
    return head(WIDTH, height) + body


def draw_streak(summary):
    mid = WIDTH / 2
    cells = []
    for key, text in (("current", "current streak"), ("longest", "longest streak")):
        value = summary[key]
        cells.append((value["length"], text, f'{value["start"] or "-"} – {value["end"] or "-"}'))
    body = f'<line x1="{mid:.0f}" y1="16" x2="{mid:.0f}" y2="80" class="u-s"/>'
    for i, (value, text, dates) in enumerate(cells):
        x = LEFT if i == 0 else mid + LEFT
        body += label(x,44,value,34,"e-f",extra=" font-weight=\"600\"") + label(x,64,text,11) + label(x,80,dates,10)
    return head(WIDTH,96) + body + "</svg>"


def draw_langs(summary):
    rows = max(len(summary["by_size"]), len(summary["by_repo"]), 1)
    colw = (WIDTH - LEFT - 30) / 2
    body = ""
    for gx, title, data, percentage in ((LEFT,"by bytes",summary["by_size"],True),(LEFT+colw+30,"by repos",summary["by_repo"],False)):
        body += label(gx,12,title.upper(),9,"m-f",extra=' letter-spacing="1.3"')
        top = max((value for _, value in data), default=1)
        total = sum(value for _, value in data) or 1
        for index, (name, value) in enumerate(data):
            y = 26 + index * 22
            shown = f"{value / total * 100:.0f}%" if percentage else str(value)
            body += label(gx,y+8,name.lower()[:11],11,"e-f") + label(gx+colw-6,y+8,shown,11,"m-f","end")
            body += f'<rect x="{gx+82:.1f}" y="{y}" width="{max(1, (colw-126)*value/top):.1f}" height="7" class="d-f" rx="3"/>'
    return head(WIDTH,26+rows*22+6) + body + "</svg>"


def draw_year(summary):
    weeks = summary["weeks"]
    fs, lh = 9.2, 11
    body = label(LEFT,16,"THE YEAR",9,"m-f",extra=' letter-spacing="1.3"') + label(LEFT,32,f'{summary["active"]} active days',11)
    for row in range(7):
        chars = ""
        for week in weeks:
            day = next((item for item in week if item.get("weekday") == row), None)
            count = day["contributionCount"] if day else 0
            chars += RAMP[min(4, 0 if count == 0 else 1 if count <= 2 else 2 if count <= 5 else 3 if count <= 9 else 4)] * 2
        body += f'<text x="{LEFT}" y="{44 + row * lh}" class="d-f" font-size="{fs}" xml:space="preserve">{chars}</text>'
    return head(WIDTH,130) + body + "</svg>"


def heading(word):
    text_end = len(word) * 16 * .6 + 18
    return head(WIDTH,26,font_text()) + label(0,18,word,16,"e-f",extra=' font-weight="600"') + f'<line x1="{text_end:.0f}" y1="12.5" x2="{WIDTH}" y2="12.5" class="u-s"/>' + "</svg>"


def write(path, content):
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if old != content:
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return True
    return False


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set")
    login = os.environ.get("GH_LOGIN", "adarsh-67r")
    out_dir = os.environ.get("OUT_DIR", ".")
    summary = summarise(fetch(login, token))
    files = {"stats.svg": draw_stats(summary), "streak.svg": draw_streak(summary), "langs.svg": draw_langs(summary), "year.svg": draw_year(summary)}
    for word in ("about", "stack", "projects", "stats", "about this page"):
        files[f"hd-{word.replace(' ', '-')}.svg"] = heading(word)
    changed = [name for name, content in files.items() if write(os.path.join(out_dir, name), content)]
    print(f'{summary["total"]} contributions, {summary["active"]} active days, best week {summary["best_week"]}, current streak {summary["current"]["length"]}, longest {summary["longest"]["length"]}')
    print("updated: " + (", ".join(sorted(changed)) if changed else "nothing"))


if __name__ == "__main__":
    main()
