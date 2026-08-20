#!/usr/bin/env python3
"""Data integrity gate for BD Site News.

The publishing bot writes production data unattended three times a day. This
script is the gate that runs BEFORE anything is committed: if the data is
malformed, the run aborts with a non-zero exit and nothing reaches readers.

Checks are deliberately strict about the failures that have actually bitten
this project: non-ASCII slugs (they 404 in Next routing), duplicate slugs,
missing image files, and unknown categories.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

# This script prints Bangla category names and box characters. A Windows
# console defaults to cp1252 and would crash on them, so the gate must be
# readable where it is run by hand as well as on the Linux CI runner.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "src" / "data" / "articles.json"
STORIES = ROOT / "src" / "data" / "stories.json"
PUBLIC = ROOT / "public"

VALID_CATEGORIES = {
    "বাংলাদেশ", "রাজনীতি", "অপরাধ", "খেলা", "বিনোদন", "অর্থনীতি", "বিশ্ব",
    "প্রযুক্তি", "শিক্ষা", "প্রবাস", "জেলা", "ফ্যাক্ট চেক", "ব্যাখ্যা", "বিতর্ক", "বিদেশে পড়াশোনা",
    # legacy labels still present on older articles
    "খেলাধুলা", "আন্তর্জাতিক",
}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VALID_VERDICTS = {"সত্য", "মিথ্যা", "আংশিক সত্য", "যাচাই করা যায়নি"}

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load(path: Path):
    if not path.exists():
        err(f"{path.name}: file is missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        err(f"{path.name}: invalid JSON — {exc}")
        return None


def check_articles(articles) -> None:
    if not isinstance(articles, list):
        err("articles.json: expected a list")
        return
    if not articles:
        err("articles.json: empty — the site would have no content")
        return

    seen_slugs: dict[str, int] = {}
    for i, a in enumerate(articles):
        where = f"articles[{i}]"
        if not isinstance(a, dict):
            err(f"{where}: not an object")
            continue

        slug = a.get("slug", "")
        title = a.get("title", "")
        label = f"{where} ({title[:34] or slug[:34]})"

        # Slug — the failure that silently 404'd a third of the site before.
        if not slug:
            err(f"{label}: missing slug")
        elif not slug.isascii():
            err(f"{label}: slug is not ASCII — Next.js will 404 this page")
        elif not SLUG_RE.match(slug):
            err(f"{label}: slug has illegal characters: {slug!r}")
        elif slug in seen_slugs:
            err(f"{label}: duplicate slug, collides with articles[{seen_slugs[slug]}]")
        else:
            seen_slugs[slug] = i

        if not title.strip():
            err(f"{label}: empty title")
        if not a.get("lead", "").strip():
            err(f"{label}: empty lead")

        category = a.get("category", "")
        if category not in VALID_CATEGORIES:
            err(f"{label}: unknown category {category!r}")

        # Body OR questions (explainers carry their text as Q&A)
        body = a.get("body") or []
        questions = a.get("questions") or []
        if not body and not questions:
            err(f"{label}: has neither body paragraphs nor explainer questions")
        for q in questions:
            if not q.get("question", "").strip() or not q.get("answer"):
                err(f"{label}: explainer question is incomplete")

        # Sourcing — every article must be traceable to where it came from.
        sources = a.get("sources") or []
        if not sources:
            err(f"{label}: no sources — every article must cite its origin")
        for s in sources:
            if not s.get("url", "").startswith("http"):
                err(f"{label}: source has no valid URL")
            if not s.get("name", "").strip():
                err(f"{label}: source has no name")

        # Timestamp
        try:
            datetime.fromisoformat(a.get("publishedAt", ""))
        except (ValueError, TypeError):
            err(f"{label}: publishedAt is not a valid ISO timestamp")

        # Referenced image must exist, or the page renders a broken image.
        image = a.get("image") or {}
        if image:
            url = image.get("url", "")
            if not url.startswith("/"):
                err(f"{label}: image url must be site-absolute")
            elif not (PUBLIC / url.lstrip("/")).exists():
                err(f"{label}: image file missing on disk: {url}")
            if not image.get("alt", "").strip():
                warn(f"{label}: image has no alt text (accessibility)")

        fc = a.get("factcheck") or {}
        if fc and fc.get("verdict") not in VALID_VERDICTS:
            err(f"{label}: invalid fact-check verdict {fc.get('verdict')!r}")

        # Second portrait: a duo card with a missing file renders half blank.
        image2 = a.get("image2") or {}
        if image2:
            url2 = image2.get("url", "")
            if not url2.startswith("/"):
                err(f"{label}: image2 url must be site-absolute")
            elif not (PUBLIC / url2.lstrip("/")).exists():
                err(f"{label}: second portrait missing on disk: {url2}")
            if not image.get("url"):
                err(f"{label}: has a second portrait but no first one")

        # A quote card puts these words in quotation marks beside a face.
        quote = a.get("quote") or {}
        if quote:
            if not (quote.get("text") or "").strip():
                err(f"{label}: quote has no text")
            if not (quote.get("by") or "").strip():
                err(f"{label}: quote has no speaker — it would be unattributed")

        # Study-abroad panel: students act on these, so a half-filled panel
        # is worse than none. An absent deadline is fine and expected; a
        # deadline with nothing else to act on is not.
        opp = a.get("opportunity") or {}
        if opp:
            if not (opp.get("country") or "").strip() and not (
                opp.get("institution") or ""
            ).strip():
                err(f"{label}: opportunity names neither a country nor an institution")
            url = (opp.get("officialUrl") or "").strip()
            if url and not url.startswith("http"):
                err(f"{label}: opportunity officialUrl is not a real link: {url!r}")
            actionable = any(opp.get(k) for k in ("funding", "eligibility", "howToApply"))
            if not actionable and not (opp.get("deadline") or "").strip() and not url:
                err(f"{label}: opportunity panel has nothing a reader can act on")

        board = a.get("scoreboard") or {}
        if board:
            rows = board.get("rows") or []
            if len(rows) < 2:
                err(f"{label}: scoreboard needs at least two sides")
            for r in rows:
                if not (r.get("team") or "").strip() or not (r.get("score") or "").strip():
                    err(f"{label}: scoreboard row is missing a team or a score")


def check_stories(stories) -> None:
    if not isinstance(stories, list):
        err("stories.json: expected a list")
        return
    if not stories:
        warn("stories.json: empty — the homepage wire will be blank")
        return
    for i, s in enumerate(stories):
        where = f"stories[{i}]"
        if not s.get("title", "").strip():
            err(f"{where}: empty title")
        if not s.get("url", "").startswith("http"):
            err(f"{where}: invalid url")
        if not s.get("source", "").strip():
            err(f"{where}: missing source attribution")


def check_orphan_images() -> None:
    """Cover files nobody references — harmless, but they bloat the repo."""
    covers = PUBLIC / "covers"
    if not covers.exists():
        return
    articles = load(ARTICLES) or []
    referenced = {
        (a.get("image") or {}).get("url", "").split("/")[-1]
        for a in articles
        if isinstance(a, dict)
    }
    orphans = [p.name for p in covers.glob("*.jpg") if p.name not in referenced]
    if len(orphans) > 20:
        warn(f"public/covers: {len(orphans)} unreferenced images are accumulating")


def main() -> int:
    articles = load(ARTICLES)
    stories = load(STORIES)

    if articles is not None:
        check_articles(articles)
    if stories is not None:
        check_stories(stories)
    check_orphan_images()

    print("── data integrity ──────────────────────────────")
    print(f"  articles : {len(articles) if isinstance(articles, list) else 'n/a'}")
    print(f"  wire     : {len(stories) if isinstance(stories, list) else 'n/a'}")

    for w in warnings:
        print(f"  ⚠  {w}")
    for e in errors:
        print(f"  ✗  {e}")

    if errors:
        print(f"\nFAILED — {len(errors)} error(s). Nothing will be published.")
        return 1
    print(f"\nPASSED{f' with {len(warnings)} warning(s)' if warnings else ''}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
