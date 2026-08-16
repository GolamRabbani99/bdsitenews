#!/usr/bin/env python3
"""Render a share photocard for an article.

Satori was tried first and mis-shaped every Bangla matra (নিয়ে rendered as
নয়িে), so cards are rendered by headless Chromium instead, which does proper
complex-script shaping. The font is bundled rather than fetched: a network
failure at render time would silently produce a card full of empty boxes.
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_HERE = Path(__file__).resolve().parent
TEMPLATE = _HERE / "photocard_template.html"
QUOTE_TEMPLATE = _HERE / "photocard_quote_template.html"
SCORE_TEMPLATE = _HERE / "photocard_score_template.html"
DUO_TEMPLATE = _HERE / "photocard_duo_template.html"
PUBLIC = ROOT / "public"
CARDS = PUBLIC / "cards"

CARD_W, CARD_H = 1080, 1350

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = [
    "জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন",
    "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর",
]


def bangla_date(iso: str = "") -> str:
    """'১৪ আগস্ট ২০২৬' — readers expect Bangla numerals on a Bangla card."""
    try:
        dt = datetime.fromisoformat(iso) if iso else None
    except ValueError:
        dt = None
    if dt is None:
        dt = datetime.now(timezone(timedelta(hours=6)))
    day = str(dt.day).translate(BN_DIGITS)
    year = str(dt.year).translate(BN_DIGITS)
    return f"{day} {BN_MONTHS[dt.month - 1]} {year}"


def _credit_line(article: dict) -> str:
    """Illustrative label plus the photographer.

    Two separate obligations. The প্রতীকী ছবি label is editorial: an
    unlabelled stock photo beside a news headline reads as documentary
    evidence of something that did not happen. The photographer credit is
    legal — these are CC BY images, and the licence requires attribution
    everywhere the photo appears, which includes a card posted to Facebook.
    """
    image = article.get("image") or {}
    if not image:
        return ""
    label = "প্রতীকী ছবি" if image.get("illustrative", True) else "ফাইল ছবি"
    credit = (image.get("credit") or "").split(" — ")[0].strip()
    return f"{label} · {credit}" if credit else label


def usable_quote(article: dict) -> dict | None:
    """A quote card only works when the quote is genuinely a quote.

    It needs a speaker and a line short enough to read at a glance, and the
    portrait must be of that speaker — a quote over someone else's face
    misattributes it, which is the one mistake this format must never make.
    """
    quote = article.get("quote") or {}
    text = (quote.get("text") or "").strip()
    who = (quote.get("by") or "").strip()
    image = article.get("image") or {}
    if not text or not who:
        return None
    if len(text) < 25 or len(text) > 210:
        return None
    if not image.get("url") or image.get("illustrative", True):
        return None
    # The portrait must be identified as this speaker. "A real photo of
    # somebody" is not enough: a team celebration under one player's name
    # attributes his words to ten other people standing beside him.
    if (image.get("person") or "").strip() != who:
        return None
    return {"text": text, "by": who, "role": (quote.get("role") or "").strip()}


def usable_scoreboard(article: dict) -> dict | None:
    """A scoreline needs at least two sides and a number for each."""
    board = article.get("scoreboard") or {}
    rows = [r for r in (board.get("rows") or [])
            if (r.get("team") or "").strip() and (r.get("score") or "").strip()]
    if len(rows) < 2:
        return None
    return {
        "context": (board.get("context") or "").strip(),
        "rows": rows,
        "status": (board.get("status") or "").strip(),
        "notes": [n for n in (board.get("notes") or []) if n.strip()][:4],
    }


def usable_duo(article: dict) -> dict | None:
    """Two portraits only when we genuinely have two, both of real people.

    A duo card with one stand-in photo implies both faces belong to the story,
    which is how the wrong person ends up beside an accusation.
    """
    second = article.get("image2") or {}
    first = article.get("image") or {}
    if not first.get("url") or not second.get("url"):
        return None
    if first.get("illustrative", True) or second.get("illustrative", True):
        return None
    if not (PUBLIC / second["url"].lstrip("/")).exists():
        return None
    # Both sides must be named, and named differently. Without this the card
    # can show one person twice under two blank plates, which happened the
    # moment a story's first portrait was corrected to the second person.
    who1 = (first.get("person") or "").strip()
    who2 = (second.get("person") or "").strip()
    if not who1 or not who2 or who1 == who2:
        return None
    return second


def _file_uri(url: str) -> str:
    # file:// so Chromium reads the cover straight off disk; cards are
    # rendered before the site deploys, so no HTTP URL exists yet.
    if not url:
        return ""
    path = PUBLIC / url.lstrip("/")
    return path.resolve().as_uri() if path.exists() else ""


def pick_template(article: dict):
    """Order matters: the most specific format that the data can support."""
    if usable_scoreboard(article):
        return SCORE_TEMPLATE, "score"
    if usable_quote(article):
        return QUOTE_TEMPLATE, "quote"
    if usable_duo(article):
        return DUO_TEMPLATE, "duo"
    return TEMPLATE, "standard"


def build_html(article: dict) -> str:
    template, kind = pick_template(article)
    quote = usable_quote(article) if kind == "quote" else None
    board = usable_scoreboard(article) if kind == "score" else None
    second = usable_duo(article) if kind == "duo" else None
    src = template.read_text(encoding="utf-8")
    image = article.get("image") or {}
    url = image.get("url", "")
    photo = _file_uri(url)

    fields = {
        "__CATEGORY__": article.get("category", "সংবাদ"),
        "__DATE__": bangla_date(article.get("publishedAt", "")),
        "__HEADLINE__": article.get("title", ""),
        "__CREDIT__": _credit_line(article) if photo else "",
        "__IMAGE__": photo,
        "__CARDCLASS__": "" if photo else "no-photo",
        "__QUOTE__": quote["text"] if quote else "",
        "__WHO__": quote["by"] if quote else "",
        "__ROLE__": quote["role"] if quote else "",
        "__IMAGE2__": _file_uri(second["url"]) if second else "",
        "__CREDIT2__": (second.get("credit") or "").split(" — ")[0] if second else "",
        "__WHO1__": (image.get("person") or "") if second else "",
        "__WHO2__": (second.get("person") or "") if second else "",
        "__CONTEXT__": board["context"] if board else "",
    }
    for token, value in fields.items():
        src = src.replace(token, html.escape(value, quote=True))

    if board:
        # Injected as JSON rather than markup so a team name containing a
        # quote or angle bracket cannot break out into the page.
        src = src.replace(
            "__SCOREBOARD__",
            json.dumps(board, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e"),
        )
    return src


def card_name(article: dict) -> str:
    # JPEG, not PNG: these are photographs, and a PNG card runs ~1.3 MB
    # against ~130 KB for a JPEG of the same card. At six cards a day the
    # difference is the repository staying usable or not.
    slug = re.sub(r"[^a-z0-9-]", "", article.get("slug", "card"))
    return f"{slug}.jpg"


def render_cards(articles: list[dict], log=print) -> dict[str, Path]:
    """Render one card per article. Returns {slug: png path}.

    Never raises: a missing card costs us a nicer Facebook post, and must not
    take down a publishing run that has already written and paid for articles.
    """
    if not articles:
        return {}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("  ! playwright not installed — skipping photocards")
        return {}

    CARDS.mkdir(parents=True, exist_ok=True)
    made: dict[str, Path] = {}
    tmp = CARDS / "_render.html"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--font-render-hinting=none"])
            page = browser.new_page(viewport={"width": CARD_W, "height": CARD_H},
                                    device_scale_factor=1)
            for article in articles:
                try:
                    tmp.write_text(build_html(article), encoding="utf-8")
                    page.goto(tmp.resolve().as_uri(), wait_until="load")
                    # Without this the screenshot can beat the webfont and the
                    # card renders in a fallback with no Bangla glyphs.
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(250)
                    out = CARDS / card_name(article)
                    page.screenshot(
                        path=str(out), type="jpeg", quality=88,
                        clip={"x": 0, "y": 0, "width": CARD_W, "height": CARD_H},
                    )
                    made[article["slug"]] = out
                    log(f"    🖼 card: {out.name}")
                except Exception as exc:
                    log(f"    ! card failed ({article.get('slug','?')}): "
                        f"{str(exc)[:120]}")
            browser.close()
    except Exception as exc:
        log(f"  ! photocard renderer unavailable: {str(exc)[:140]}")
    finally:
        tmp.unlink(missing_ok=True)

    return made


if __name__ == "__main__":
    # Manual check: python scripts/photocard.py  → renders the newest 2.
    import json
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = json.loads((ROOT / "src/data/articles.json").read_text(encoding="utf-8"))
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    cards = render_cards(data[:n])
    print(f"rendered {len(cards)} card(s) into {CARDS}")
