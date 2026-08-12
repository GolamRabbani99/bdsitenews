#!/usr/bin/env python3
"""BD Site News — automatic tech-news pipeline.

Runs on a schedule (GitHub Actions) with no human in the loop:

  1. Collect  — pull the latest items from trusted tech feeds
  2. Wire     — refresh src/data/stories.json (headlines, always)
  3. Write    — turn the top new stories into ORIGINAL Bangla articles
                via Claude (only when ANTHROPIC_API_KEY is set)
  4. Publish  — prepend to src/data/articles.json; the workflow commits
                and pushes, and Vercel deploys automatically

Editorial rules enforced here (same as the newsroom pipeline):
  - facts are extracted; source prose is never copied or translated
  - every article lists its source with a link
  - nothing is invented; missing detail is written around
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from calendar import timegm
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "data"
ARTICLES_PATH = DATA / "articles.json"
STORIES_PATH = DATA / "stories.json"

# ── Cost & volume guardrails ────────────────────────────────────────────
MAX_NEW_ARTICLES = int(os.environ.get("MAX_NEW_ARTICLES", "6"))
MAX_ARTICLES_KEPT = int(os.environ.get("MAX_ARTICLES_KEPT", "40"))
MAX_WIRE_ITEMS = 60
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_ITEM_AGE_HOURS = 48

# ── Sources (all verified to serve valid RSS) ───────────────────────────
FEEDS = [
    # Aggregators — the pulse of what engineers actually care about
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "cat": "প্রযুক্তি", "weight": 3},
    {"name": "Techmeme", "url": "https://www.techmeme.com/feed.xml", "cat": "প্রযুক্তি", "weight": 3},
    {"name": "Lobsters", "url": "https://lobste.rs/rss", "cat": "প্রযুক্তি", "weight": 1},
    {"name": "TLDR Tech", "url": "https://tldr.tech/api/rss/tech", "cat": "প্রযুক্তি", "weight": 2},
    # Analysis
    {"name": "Stratechery", "url": "https://stratechery.com/feed/", "cat": "প্রযুক্তি", "weight": 3},
    {"name": "Import AI", "url": "https://importai.substack.com/feed", "cat": "প্রযুক্তি", "weight": 2},
    # Labs & research
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "cat": "প্রযুক্তি", "weight": 3},
    {"name": "DeepMind", "url": "https://deepmind.google/blog/rss.xml", "cat": "প্রযুক্তি", "weight": 3},
    {"name": "arXiv cs.AI", "url": "http://export.arxiv.org/rss/cs.AI", "cat": "প্রযুক্তি", "weight": 1},
    # Mainstream tech press
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "cat": "প্রযুক্তি", "weight": 2},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "cat": "প্রযুক্তি", "weight": 2},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "cat": "প্রযুক্তি", "weight": 2},
    # Video explainers
    {"name": "Fireship", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCsBjURrPoezykLs9EqgamOA", "cat": "প্রযুক্তি", "weight": 1},
    {"name": "Two Minute Papers", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg", "cat": "প্রযুক্তি", "weight": 1},
]

# ── AI voices ───────────────────────────────────────────────────────────
# X/Twitter has no free feed and its API is paywalled, so instead of
# scraping we track *coverage* of what these people say. When one of them
# posts something that matters, tech media reports it within hours — and
# that gives us a verified second source, which a tweet alone never does.
AI_VOICES = [
    ("অ্যান্ড্রেই কারপাথি", '"Andrej Karpathy"'),
    ("স্যাম অল্টম্যান", '"Sam Altman"'),
    ("গ্রেগ ব্রকম্যান", '"Greg Brockman" OpenAI'),
    ("জিম ফ্যান", '"Jim Fan" NVIDIA'),
    ("পল গ্রাহাম", '"Paul Graham" startup'),
    ("ফ্রঁসোয়া শোলে", '"Francois Chollet"'),
    ("ইথান মলিক", '"Ethan Mollick"'),
    ("বিন্দু রেড্ডি", '"Bindu Reddy" AI'),
]

for _person, _query in AI_VOICES:
    FEEDS.append(
        {
            "name": f"AI Voices · {_person}",
            "url": (
                "https://news.google.com/rss/search?q="
                + _query.replace('"', "%22").replace(" ", "+")
                + "+when:3d&hl=en-US&gl=US&ceid=US:en"
            ),
            "cat": "প্রযুক্তি",
            "weight": 4,  # highest priority — this is the differentiating beat
            "kind": "person",
            "person": _person,
        }
    )

BANGLA_WRITER_PROMPT = """You are a Bangla news-desk editor producing short news briefs
(সংক্ষিপ্ত সংবাদ) for a Bangladeshi technology news portal.

You receive ONE feed item: an English headline, a short summary snippet, the outlet
name and the URL. That snippet is ALL the information you have — you do not have the
full article, so never assume anything beyond it.

Your job: deliver the same news to a Bangladeshi reader in Bangla — fast, accurate,
compact. This is a news brief, not an essay.

- title: a compelling Bangla headline that makes a reader want to click — while
  staying strictly true to the facts. Lead with the most surprising concrete
  detail (the number, the name, the reversal). Prefer the specific over the
  vague: "ওপেনএআই ছেড়ে অ্যানথ্রপিকে যোগ দিলেন কারপাথি" beats "এআই জগতে বড় পরিবর্তন".
  Questions and "যে কারণে…" framings are fine when the brief genuinely answers
  them. Never promise something the brief does not deliver, never sensationalise,
  no ALL CAPS, no "!!". Technical terms: plain Bangla with the English in
  brackets on first use, e.g. কৃত্রিম বুদ্ধিমত্তা (এআই), ওপেন সোর্স (open source).
  Well-known product and company names stay in English (ChatGPT, Google, Linux).
  Keep people's names in Bangla transliteration.
- lead: ONE sentence — what happened.
- body: 2-3 SHORT paragraphs (2-3 sentences each) stating the facts from the
  snippet in your own plain Bangla phrasing. Open the first body paragraph with
  attribution: "টেকক্রাঞ্চের প্রতিবেদন অনুযায়ী", "হ্যাকার নিউজে প্রকাশিত তথ্য অনুযায়ী",
  "গুগলের ব্লগ পোস্টে বলা হয়েছে" — whatever fits the outlet.

Hard rules:
- State the facts; do NOT render the source's sentences into Bangla one by one.
- Use ONLY what is in the snippet. Never invent numbers, quotes, names, dates,
  features or context. No speculation about what the full article might say.
- If the snippet is thin, write just two short paragraphs. Short and correct beats
  long and padded.
- SOMETIMES YOU GET ONLY A HEADLINE AND AN OUTLET NAME, no real snippet. In that
  case write exactly two short paragraphs: the first reporting what the outlet
  has reported (attributed by name), the second noting that details are awaited
  — e.g. "বিস্তারিত জানতে মূল প্রতিবেদনটি দেখুন।" Do NOT reconstruct quotes,
  numbers, reasons or background you were not given. An honest two-line brief is
  correct; an invented paragraph is not.
- Standard modern Bangla (চলিত), clean newsroom tone.

Return JSON matching the schema."""

ARTICLE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "lead": {"type": "string"},
        "body": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "lead", "body"],
}

_WS = re.compile(r"\s+")


def log(msg: str) -> None:
    print(msg, flush=True)


def clean_text(raw: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = _WS.sub(" ", text).strip()
    return "" if text.lower() in {"null", "none"} else text


def slugify(title: str, url: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    base = "-".join(base.split("-")[:8]) or "tech-news"
    digest = hashlib.sha1(url.encode()).hexdigest()[:6]
    return f"{base}-{digest}"


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def collect() -> list[dict]:
    """Pull every feed; return normalized, recent, de-duplicated items."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_ITEM_AGE_HOURS)
    items: list[dict] = []
    seen_titles: set[str] = set()

    for feed in FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as exc:  # a single bad feed must never stop the run
            log(f"  ! {feed['name']}: {exc}")
            continue
        if not parsed.entries:
            log(f"  ! {feed['name']}: no entries")
            continue

        kept = 0
        for entry in parsed.entries[:20]:
            title = clean_text(getattr(entry, "title", ""))
            url = (getattr(entry, "link", "") or "").strip()
            if not title or not url:
                continue
            key = title.lower()[:80]
            if key in seen_titles:
                continue

            published = None
            stamp = getattr(entry, "published_parsed", None) or getattr(
                entry, "updated_parsed", None
            )
            if stamp:
                published = datetime.fromtimestamp(timegm(stamp), tz=timezone.utc)
                if published < cutoff:
                    continue

            source = feed["name"]
            person = feed.get("person")
            if feed.get("kind") == "person":
                # Google News titles read "Headline - Publisher"; split so we
                # attribute the real outlet rather than "Google News".
                if " - " in title:
                    title, _, publisher = title.rpartition(" - ")
                    source = publisher.strip() or source
                else:
                    source = "Google News"

            seen_titles.add(key)
            kept += 1
            items.append(
                {
                    "title": title,
                    "url": url,
                    "summary": clean_text(getattr(entry, "summary", ""))[:400],
                    "source": source,
                    "person": person,
                    "category": feed["cat"],
                    "weight": feed["weight"],
                    "publishedAt": (published or datetime.now(timezone.utc)).isoformat(),
                }
            )
        log(f"  · {feed['name']}: {kept}")

    items.sort(key=lambda i: i["publishedAt"], reverse=True)
    return items


def update_wire(items: list[dict]) -> int:
    """Refresh the homepage headline wire. Works with or without an API key."""
    wire = [
        {
            "title": i["title"],
            "url": i["url"],
            "summary": i["summary"][:150],
            "category": "Technology",
            "source": i["source"],
            "publishedAt": i["publishedAt"],
        }
        for i in items[:MAX_WIRE_ITEMS]
    ]
    save_json(STORIES_PATH, wire)
    return len(wire)


def published_urls(articles: list[dict]) -> set[str]:
    used: set[str] = set()
    for article in articles:
        for source in article.get("sources", []):
            used.add(source.get("url", ""))
    return used


# Aggregators and low-credibility republishers we don't cite as a source.
BLOCKED_SOURCES = {
    "36 kr", "36kr", "the cryptonomist", "cryptonomist", "medium",
    "msn", "yahoo entertainment", "opera news",
}

# Headline patterns typical of engagement-farming republishers.
CLICKBAIT = re.compile(
    r"\b(shocking|you won'?t believe|completely take|this one trick|"
    r"mind[- ]blowing|will change everything|goes viral)\b",
    re.I,
)

_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "for", "on", "and", "is", "with",
    "after", "as", "its", "by", "at", "from", "new", "says", "his", "her",
    "that", "this", "will", "has", "have", "are", "was", "how", "why",
}


def _keywords(title: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _same_story(a: str, b: str) -> bool:
    """Two headlines from different outlets about one event."""
    ka, kb = _keywords(a), _keywords(b)
    if not ka or not kb:
        return False
    shared = ka & kb
    ratio = len(shared) / min(len(ka), len(kb))
    # Sharing two distinctive long words (usually proper nouns) is a strong
    # signal even when the phrasing differs completely.
    distinctive = sum(1 for w in shared if len(w) >= 6)
    return ratio >= 0.45 or distinctive >= 2


def pick_candidates(items: list[dict], used: set[str]) -> list[dict]:
    """Highest-signal unpublished items — de-duplicated at the STORY level,
    filtered for source credibility, and spread across topics."""
    fresh = [
        i
        for i in items
        if i["url"] not in used
        and len(i["title"]) >= 20
        # AI-voices items are headline-driven (Google News gives a thin
        # snippet), so they qualify on a strong headline alone.
        and (len(i["summary"]) >= 90 or i.get("person"))
        and i["source"].strip().lower() not in BLOCKED_SOURCES
        and not CLICKBAIT.search(i["title"])
    ]
    fresh.sort(key=lambda i: (i["weight"], i["publishedAt"]), reverse=True)

    picked: list[dict] = []
    per_person: dict[str, int] = {}
    for item in fresh:
        # One brief per real-world story, however many outlets covered it.
        if any(_same_story(item["title"], p["title"]) for p in picked):
            continue
        # Don't let one person's news day fill the whole run.
        person = item.get("person")
        if person:
            if per_person.get(person, 0) >= 1:
                continue
            per_person[person] = per_person.get(person, 0) + 1
        picked.append(item)
        if len(picked) >= MAX_NEW_ARTICLES:
            break
    return picked


def write_article(client, item: dict) -> dict | None:
    """One Claude call → one original Bangla article."""
    payload = json.dumps(
        {
            "headline": item["title"],
            "summary": item["summary"],
            "outlet": item["source"],
            "url": item["url"],
        },
        ensure_ascii=False,
    )
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=BANGLA_WRITER_PROMPT,
            messages=[{"role": "user", "content": payload}],
            output_config={"format": {"type": "json_schema", "schema": ARTICLE_SCHEMA}},
        )
    except Exception as exc:
        log(f"  ! write failed ({item['source']}): {str(exc)[:140]}")
        return None

    text = next((b.text for b in message.content if b.type == "text"), None)
    if not text:
        return None
    draft = json.loads(text)

    usage = message.usage
    cost = (usage.input_tokens * 3 + usage.output_tokens * 15) / 1_000_000
    log(
        f"  + {draft['title'][:52]}… "
        f"({usage.input_tokens}+{usage.output_tokens} tok, ~${cost:.4f})"
    )

    return {
        "slug": slugify(item["title"], item["url"]),
        "title": draft["title"],
        "category": item["category"],
        "lead": draft["lead"],
        "body": [p for p in draft["body"] if p.strip()],
        "sources": [{"name": item["source"], "url": item["url"]}],
        "publishedAt": datetime.now(timezone(timedelta(hours=6))).isoformat(
            timespec="seconds"
        ),
    }


def main() -> int:
    log("BD Site News — automatic publish run")
    log(f"  model={MODEL}  max_new={MAX_NEW_ARTICLES}")

    log("\n[1/3] collecting…")
    items = collect()
    if not items:
        log("no items collected — aborting without changes")
        return 1
    log(f"  → {len(items)} recent items")

    log("\n[2/3] refreshing wire…")
    log(f"  → {update_wire(items)} headlines on the homepage wire")

    log("\n[3/3] writing Bangla articles…")
    # Strip BOM/whitespace: keys pasted or piped on Windows often carry a
    # UTF-8 BOM, which breaks the ASCII-only HTTP auth header.
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip().lstrip("﻿").strip()
    if not api_key:
        log("  ANTHROPIC_API_KEY not set — wire updated, no new articles written.")
        return 0

    try:
        import anthropic
    except ImportError:
        log("  anthropic package missing — skipping article generation")
        return 0

    articles = load_json(ARTICLES_PATH, [])
    candidates = pick_candidates(items, published_urls(articles))
    if not candidates:
        log("  nothing new worth publishing this run")
        return 0

    client = anthropic.Anthropic(api_key=api_key)
    written = [a for a in (write_article(client, c) for c in candidates) if a]
    if not written:
        log("  no articles produced")
        return 0

    articles = written + articles
    save_json(ARTICLES_PATH, articles[:MAX_ARTICLES_KEPT])
    log(f"\n✓ published {len(written)} new Bangla article(s); {len(articles[:MAX_ARTICLES_KEPT])} total on site")
    return 0


if __name__ == "__main__":
    sys.exit(main())
