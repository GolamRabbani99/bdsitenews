#!/usr/bin/env python3
"""Share one already-published article to the Facebook Page.

The scheduled run only shares what it wrote in that same run, so a desk piece
added by hand — a special report, a correction, an older story worth
resurfacing — has no way onto the Page. This is that way.

    python scripts/share_one.py <slug>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_publish as ap  # noqa: E402
from photocard import render_cards  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "src" / "data" / "articles.json"


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("usage: python scripts/share_one.py <slug>")
        return 2
    slug = sys.argv[1].strip()

    if not (ap.FB_PAGE_ID and ap.FB_TOKEN):
        print("FACEBOOK_PAGE_ID / FACEBOOK_PAGE_TOKEN are not set — nothing sent.")
        return 1

    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    article = next((a for a in articles if a.get("slug") == slug), None)
    if article is None:
        print(f"no article with slug {slug!r}")
        return 1

    print(f"sharing: {article['title']}")
    if article.get("sharedToFacebook"):
        print("  already marked as shared — posting again anyway (manual run)")

    cards = render_cards([article])
    card = cards.get(slug)
    sent = (ap.post_photocard_to_facebook(article, card) if card
            else ap.post_to_facebook(article))
    if not sent:
        return 1

    article["sharedToFacebook"] = True
    ARTICLES.write_text(
        json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
