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
MAX_NEW_ARTICLES = int(os.environ.get("MAX_NEW_ARTICLES", "3"))
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

BANGLA_WRITER_PROMPT = """You are a senior technology journalist at a leading Bangladeshi national daily.

You will receive ONE news item: a headline, a summary, the outlet name and the URL.
You must NOT copy or translate the source text. Read it, understand the facts, and
write a completely original Bangla news report for Bangladeshi readers.

Structure (inverted pyramid):
- title: a clear, accurate Bangla headline, max ~70 characters. No clickbait,
  no sensational punctuation. Use the plain Bangla term with the English word in
  brackets on first use for technical terms, e.g. কৃত্রিম বুদ্ধিমত্তা (এআই).
- lead: 1-2 sentences answering what happened and why it matters.
- body: 3-4 short paragraphs (2-4 sentences each). Attribute the reporting
  naturally — "টেকক্রাঞ্চের প্রতিবেদনে বলা হয়েছে", "গুগলের ব্লগ পোস্ট অনুযায়ী".
  The final paragraph should note why this matters for Bangladeshi readers,
  developers or businesses — but ONLY if you can do so from the given facts.

Hard rules:
- Use ONLY the facts present in the supplied item. Never invent numbers, quotes,
  names, dates or product details. If something is unclear, write around it.
- If the item is thin (a link post with no substance), keep the report short and
  factual rather than padding it.
- Standard modern Bangla (চলিত), warm and professional. No AI clichés.

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

            seen_titles.add(key)
            kept += 1
            items.append(
                {
                    "title": title,
                    "url": url,
                    "summary": clean_text(getattr(entry, "summary", ""))[:400],
                    "source": feed["name"],
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


def pick_candidates(items: list[dict], used: set[str]) -> list[dict]:
    """Highest-signal unpublished items: substantive, from weighted sources."""
    fresh = [
        i
        for i in items
        if i["url"] not in used and len(i["summary"]) >= 120 and len(i["title"]) >= 25
    ]
    fresh.sort(key=lambda i: (i["weight"], i["publishedAt"]), reverse=True)
    return fresh[:MAX_NEW_ARTICLES]


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
            max_tokens=4000,
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
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
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
