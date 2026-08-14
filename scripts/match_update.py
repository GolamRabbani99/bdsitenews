#!/usr/bin/env python3
"""Live Test-match updates: scoreboard card to the Page, live page on the site.

Runs on a short cron through play. It posts only at the punctuation points of
a day's cricket — lunch, tea, stumps, an innings break, a result — because a
Page that posts every half hour is a Page people mute.

Deliberately makes no model calls. The status line is translated by rule, and
anything the rules do not recognise is skipped rather than guessed: posting a
wrong score is worse than posting nothing, and an English status line on a
Bangla page is worse than silence.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "src" / "data" / "articles.json"
STATE = ROOT / "src" / "data" / "match_state.json"

MATCH_ID = os.environ.get("CRICBUZZ_MATCH_ID", "148316").strip()
MATCH_SLUG = os.environ.get(
    "CRICBUZZ_MATCH_SLUG", "aus-vs-ban-1st-test-bangladesh-tour-of-australia-2026"
).strip()
LIVE_SLUG = os.environ.get("LIVE_ARTICLE_SLUG", "live-aus-ban-1st-test").strip()

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")

TEAMS_BN = {
    "AUS": "অস্ট্রেলিয়া", "BAN": "বাংলাদেশ", "IND": "ভারত", "PAK": "পাকিস্তান",
    "ENG": "ইংল্যান্ড", "SA": "দক্ষিণ আফ্রিকা", "NZ": "নিউজিল্যান্ড",
    "SL": "শ্রীলঙ্কা", "WI": "ওয়েস্ট ইন্ডিজ", "AFG": "আফগানিস্তান",
    "ZIM": "জিম্বাবুয়ে", "IRE": "আয়ারল্যান্ড",
}
FULL_BN = {
    "Australia": "অস্ট্রেলিয়া", "Bangladesh": "বাংলাদেশ", "India": "ভারত",
    "Pakistan": "পাকিস্তান", "England": "ইংল্যান্ড", "South Africa": "দক্ষিণ আফ্রিকা",
    "New Zealand": "নিউজিল্যান্ড", "Sri Lanka": "শ্রীলঙ্কা",
    "West Indies": "ওয়েস্ট ইন্ডিজ", "Afghanistan": "আফগানিস্তান",
    "Zimbabwe": "জিম্বাবুয়ে", "Ireland": "আয়ারল্যান্ড",
}
BREAK_BN = {
    "Stumps": "দিনের খেলা শেষ", "Lunch": "লাঞ্চ বিরতি", "Tea": "চা বিরতি",
    "Innings Break": "ইনিংস বিরতি",
}
# Only these moments are worth a post.
MILESTONE = re.compile(r"Stumps|Lunch|Tea|Innings Break|won by|Match drawn|"
                       r"Match tied", re.I)


def log(msg: str) -> None:
    print(msg, flush=True)


def bn(n) -> str:
    return str(n).translate(BN_DIGITS)


def fetch() -> str | None:
    url = f"https://www.cricbuzz.com/live-cricket-scores/{MATCH_ID}/{MATCH_SLUG}"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "ignore")
    except Exception as exc:
        log(f"  ! could not fetch the score: {str(exc)[:120]}")
        return None


def parse(html: str) -> dict | None:
    """Pull the innings and the status line out of the page.

    Returns None on anything unexpected. The caller must treat that as
    'no update', never as 'nothing happened'.
    """
    text = " ".join(re.sub(r"<[^>]+>", " ", html).split())

    # The page repeats team codes all over — partnerships, run rates, other
    # fixtures. Only the summary block immediately before the day/status line
    # holds the innings totals, so parse that window and nothing else.
    anchor = re.search(r"Day \d\s*:", text)
    if not anchor:
        return None
    window = text[max(0, anchor.start() - 220):anchor.start()]

    # Wickets are written both "351/6" and "351 - 6" depending on which
    # layout the page serves; accepting only the slash silently dropped the
    # wicket count and published a total that looked like an all-out score.
    innings = re.findall(
        r"\b([A-Z]{2,4})\s+(\d{1,3})(?:\s*[/-]\s*(\d{1,2}))?"
        r"\s*(?:\(\s*([\d.]+)\s*\))?",
        window,
    )
    seen: dict[str, dict] = {}
    order: list[str] = []
    for code, runs, wkts, overs in innings:
        if code not in TEAMS_BN or code in seen:
            continue  # keep the first sighting; later ones are not the total
        order.append(code)
        seen[code] = {"code": code, "runs": runs, "wkts": wkts, "overs": overs}
    if len(order) < 2:
        return None

    # "Day 2: Stumps - Bangladesh lead by 153 runs"
    m = re.search(r"(Day \d)\s*:\s*([^-]+?)\s*-\s*([A-Za-z ]+?(?:lead|trail)"
                  r"[a-z]* by \d+ runs?)", text)
    if m:
        day, moment, status = m.group(1), m.group(2).strip(), m.group(3).strip()
    else:
        m2 = re.search(r"(Day \d)\s*:\s*(Stumps|Lunch|Tea|Innings Break)", text)
        if not m2:
            return None
        day, moment, status = m2.group(1), m2.group(2), ""

    return {
        "day": day,
        "moment": moment,
        "status": status,
        "rows": [seen[c] for c in order[:2]],
    }


def status_bn(status: str) -> str:
    """Translate the status by rule, or return '' and let the caller skip."""
    m = re.match(r"([A-Za-z ]+?)\s+(lead|trail)[a-z]*\s+by\s+(\d+)\s+runs?",
                 status.strip())
    if m:
        team = FULL_BN.get(m.group(1).strip())
        if not team:
            return ""
        verb = "এগিয়ে" if m.group(2).lower() == "lead" else "পিছিয়ে"
        return f"{team} {verb} {bn(m.group(3))} রানে"

    m = re.match(r"([A-Za-z ]+?)\s+won by\s+(.+)", status.strip(), re.I)
    if m:
        team = FULL_BN.get(m.group(1).strip())
        if team:
            margin = m.group(2)
            runs = re.match(r"(\d+)\s+runs?", margin)
            wkts = re.match(r"(\d+)\s+wickets?", margin)
            if runs:
                return f"{team} জিতেছে {bn(runs.group(1))} রানে"
            if wkts:
                return f"{team} জিতেছে {bn(wkts.group(1))} উইকেটে"
    return ""


def build_scoreboard(state: dict) -> dict | None:
    rows = []
    for r in state["rows"]:
        score = bn(r["runs"])
        if r["wkts"]:
            score = f"{bn(r['runs'])}/{bn(r['wkts'])}"
        rows.append({"team": TEAMS_BN[r["code"]], "score": score, "lead": False})

    status = status_bn(state["status"]) if state["status"] else ""
    if state["status"] and not status:
        log(f"  ! status not understood, skipping: {state['status'][:70]}")
        return None

    # Mark the side the status says is in front.
    for row in rows:
        if status.startswith(row["team"]) and "এগিয়ে" in status:
            row["lead"] = True

    day_bn = f"{bn(state['day'].split()[1])} দিন"
    moment = BREAK_BN.get(state["moment"], state["moment"])
    context = f"১ম টেস্ট · ডারউইন · {day_bn} · {moment}"

    return {"context": context, "status": status or moment,
            "rows": rows, "notes": []}


def main() -> int:
    html = fetch()
    if not html:
        return 0  # transient; try again next tick

    parsed = parse(html)
    if not parsed:
        log("  score not parseable right now — no update")
        return 0

    fingerprint = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    previous = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    if previous.get("fingerprint") == fingerprint:
        log(f"  unchanged since last check ({parsed['moment']}) — nothing to do")
        return 0

    board = build_scoreboard(parsed)
    if not board:
        return 0

    log(f"  {board['context']} — {board['status']}")
    for r in board["rows"]:
        log(f"    {r['team']}: {r['score']}")

    # Always keep the live page current; only post at the day's punctuation.
    update_live_article(board, parsed)
    posted = previous.get("posted_moment")
    at_milestone = bool(MILESTONE.search(parsed["moment"] + " " + parsed["status"]))
    should_post = at_milestone and posted != parsed["moment"] + parsed["day"]

    if should_post and post(board):
        previous["posted_moment"] = parsed["moment"] + parsed["day"]
    elif not at_milestone:
        log("  mid-session — site updated, not posting to the Page")

    previous["fingerprint"] = fingerprint
    previous["updatedAt"] = datetime.now(timezone(timedelta(hours=6))).isoformat(
        timespec="seconds")
    STATE.write_text(json.dumps(previous, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    return 0


def update_live_article(board: dict, parsed: dict) -> None:
    """One article that keeps changing, rather than a new one every session."""
    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    now = datetime.now(timezone(timedelta(hours=6))).isoformat(timespec="seconds")
    teams = " বনাম ".join(r["team"] for r in board["rows"])

    article = next((a for a in articles if a.get("slug") == LIVE_SLUG), None)
    fresh = article is None
    if fresh:
        article = {"slug": LIVE_SLUG, "category": "খেলা", "body": [],
                   "sources": [{
                       "name": "Cricbuzz — লাইভ স্কোর",
                       "url": f"https://www.cricbuzz.com/live-cricket-scores/"
                              f"{MATCH_ID}/{MATCH_SLUG}"}]}
        articles.insert(0, article)

    article["title"] = f"লাইভ: {teams}, ১ম টেস্ট — {board['status']}"
    article["lead"] = f"{board['context']}। সর্বশেষ অবস্থা: {board['status']}।"
    article["scoreboard"] = board
    article["publishedAt"] = now
    article["body"] = [
        f"ডারউইনের মারারা ওভালে চলমান প্রথম টেস্টের সর্বশেষ স্কোর। "
        f"{board['context']}।",
        " ".join(f"{r['team']} {r['score']}।" for r in board["rows"]),
        f"সর্বশেষ অবস্থা: {board['status']}।",
    ]
    ARTICLES.write_text(json.dumps(articles, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    log(f"  live page {'created' if fresh else 'updated'}: /news/{LIVE_SLUG}")


def post(board: dict) -> bool:
    import auto_publish as ap
    from photocard import render_cards

    if not (ap.FB_PAGE_ID and ap.FB_TOKEN):
        log("  facebook not configured — card not posted")
        return False

    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    article = next(a for a in articles if a.get("slug") == LIVE_SLUG)
    cards = render_cards([article], log=log)
    card = cards.get(LIVE_SLUG)
    if not card:
        log("  ! card render failed — not posting a scoreless post")
        return False
    return ap.post_photocard_to_facebook(article, card)


if __name__ == "__main__":
    sys.exit(main())
