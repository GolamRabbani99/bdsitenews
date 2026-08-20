#!/usr/bin/env python3
"""Turn a published article into a video kit: script, voiceover text, slides.

    python scripts/make_video_kit.py <slug>
    python scripts/make_video_kit.py            # newest article

Produces `video-kits/<slug>/` containing

    script.md       the full plan — narration, visual direction, on-screen text
    voiceover.txt   narration only, ready to paste into a TTS tool
    youtube.txt     title, description and tags
    slide-01.png …  1920×1080 frames rendered from the article

Deliberately stops short of assembling the video. YouTube's inauthentic
content policy targets exactly the end-to-end pipeline — templated scripts,
slideshows with little narration — and removes channels for it. The editing
is where a person adds the judgement that keeps a channel monetisable, so
this hands over a kit rather than an upload.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "src" / "data" / "articles.json"
KITS = ROOT / "video-kits"
TEMPLATE = Path(__file__).resolve().parent / "video_slide_template.html"
PUBLIC = ROOT / "public"

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
SITE_URL = "https://www.bdsitenews.com"

SCRIPT_PROMPT = """You are a Bangla news video producer writing a script for a
60–90 second news video for a Bangladeshi audience.

You are given one published article. Turn it into a spoken script.

THE SHAPE:
- 5–7 scenes. Each scene is one idea and one on-screen frame.
- Scene 1 is the hook: the single most arresting fact, in one sentence. If a
  viewer does not stay past this line, nothing else matters.
- Middle scenes carry the reporting — the numbers, the names, what was said.
- The last scene closes with what happens next, and invites the viewer to
  read the full report on bdsitenews.com.

FOR EACH SCENE:
- narration: what the voice says, in natural spoken Bangla. Written to be
  HEARD, not read: short sentences, no clause stacking, no bracketed asides.
  Spell numbers the way a newsreader says them. 12–28 words.
- onscreen: 3–9 words of Bangla for the slide. NOT the narration repeated —
  the phrase a viewer should remember. Often just the number or the name.
- visual: one line of English direction for the editor — what footage or
  graphic goes here. Say plainly when a stock shot is needed, e.g.
  "stock: Dhaka street traffic" or "graphic: scoreboard from the article".

RULES THAT MATTER:
- Every fact must come from the article. Add nothing, sharpen nothing.
- Never write a visual direction that requires broadcast or agency footage.
  YouTube's Content ID finds it and the channel takes a copyright strike.
  Stock, own graphics, or stills the site already owns — nothing else.
- Total narration across all scenes: 130–200 Bangla words. That is 60–90
  seconds spoken. Longer gets cut by the viewer, not by the editor.

ALSO RETURN:
- title: a YouTube title in Bangla, under 70 characters. Name the subject.
- description: 2–3 sentences in Bangla, then the article URL on its own line.
- tags: 8–12 Bangla and English search terms, no hashes."""

SCRIPT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "narration": {"type": "string"},
                    "onscreen": {"type": "string"},
                    "visual": {"type": "string"},
                },
                "required": ["narration", "onscreen", "visual"],
            },
        },
    },
    "required": ["title", "description", "tags", "scenes"],
}


def log(msg: str) -> None:
    print(msg, flush=True)


def load_article(slug: str | None) -> dict | None:
    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    if not slug:
        return articles[0] if articles else None
    return next((a for a in articles if a.get("slug") == slug), None)


def write_script(article: dict) -> dict | None:
    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY", "").strip().lstrip("﻿").strip()
    if not key:
        log("ANTHROPIC_API_KEY is not set — cannot write the script.")
        return None

    payload = {
        "title": article["title"],
        "lead": article["lead"],
        "body": article.get("body") or [],
        "impact": article.get("impact") or [],
        "context": article.get("context") or [],
        "questions": article.get("questions") or [],
        "scoreboard": article.get("scoreboard") or {},
        "opportunity": article.get("opportunity") or {},
        "category": article["category"],
        "url": f"{SITE_URL}/news/{article['slug']}",
    }
    client = anthropic.Anthropic(api_key=key)
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SCRIPT_PROMPT,
            messages=[{"role": "user",
                       "content": json.dumps(payload, ensure_ascii=False)}],
            output_config={"format": {"type": "json_schema",
                                      "schema": SCRIPT_SCHEMA}},
        )
    except Exception as exc:
        log(f"! script failed: {str(exc)[:160]}")
        return None

    if getattr(message, "stop_reason", None) == "max_tokens":
        log("! script was cut off at the token limit — not usable")
        return None
    text = next((b.text for b in message.content if b.type == "text"), None)
    if not text:
        return None
    try:
        draft = json.loads(text)
    except json.JSONDecodeError as exc:
        log(f"! script came back malformed: {exc}")
        return None

    usage = message.usage
    cost = (usage.input_tokens * 3 + usage.output_tokens * 15) / 1_000_000
    log(f"  script: {len(draft.get('scenes') or [])} scenes (~${cost:.4f})")
    return draft


def render_slides(article: dict, scenes: list[dict], out: Path) -> int:
    """One 1920×1080 frame per scene, rendered by the same Chromium that
    makes the photocards — so Bangla is shaped correctly here too."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("  ! playwright not installed — slides skipped")
        return 0

    from photocard import bangla_date

    image = article.get("image") or {}
    photo = ""
    if image.get("url"):
        p = PUBLIC / image["url"].lstrip("/")
        if p.exists():
            photo = p.resolve().as_uri()

    src_template = TEMPLATE.read_text(encoding="utf-8")
    tmp = out / "_render.html"
    made = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--font-render-hinting=none"])
            page = browser.new_page(viewport={"width": 1920, "height": 1080},
                                    device_scale_factor=1)
            for i, scene in enumerate(scenes, 1):
                import html as html_mod
                fields = {
                    "__CATEGORY__": article["category"],
                    "__DATE__": bangla_date(article.get("publishedAt", "")),
                    "__HEADLINE__": scene.get("onscreen", ""),
                    "__KICKER__": "",
                    # Only the opening frame carries the photo; later frames
                    # stay clean so the on-screen phrase reads at a glance.
                    "__IMAGE__": photo if i == 1 else "",
                    "__SLIDECLASS__": "",
                }
                page_html = src_template
                for token, value in fields.items():
                    page_html = page_html.replace(
                        token, html_mod.escape(value, quote=True))
                tmp.write_text(page_html, encoding="utf-8")
                page.goto(tmp.resolve().as_uri(), wait_until="load")
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(220)
                page.screenshot(path=str(out / f"slide-{i:02d}.png"),
                                clip={"x": 0, "y": 0, "width": 1920, "height": 1080})
                made += 1
            browser.close()
    except Exception as exc:
        log(f"  ! slide rendering failed: {str(exc)[:140]}")
    finally:
        tmp.unlink(missing_ok=True)
    return made


def main() -> int:
    slug = sys.argv[1].strip() if len(sys.argv) > 1 else None
    article = load_article(slug)
    if not article:
        log(f"no article found for {slug!r}")
        return 1

    log(f"article: {article['title'][:66]}")
    draft = write_script(article)
    if not draft:
        return 1

    scenes = [s for s in (draft.get("scenes") or []) if s.get("narration")]
    if not scenes:
        log("! no usable scenes")
        return 1

    out = KITS / article["slug"]
    out.mkdir(parents=True, exist_ok=True)

    narration = "\n\n".join(s["narration"].strip() for s in scenes)
    words = len(narration.split())
    (out / "voiceover.txt").write_text(narration + "\n", encoding="utf-8")

    url = f"{SITE_URL}/news/{article['slug']}"
    lines = [
        f"# {draft['title']}", "",
        f"**Article:** {url}",
        f"**Narration:** {words} words — roughly {round(words / 2.4)} seconds spoken",
        "",
        "| # | On screen | Narration | Visual |",
        "|---|---|---|---|",
    ]
    for i, s in enumerate(scenes, 1):
        n = s["narration"].replace("|", "/").strip()
        o = s.get("onscreen", "").replace("|", "/").strip()
        v = s.get("visual", "").replace("|", "/").strip()
        lines.append(f"| {i} | {o} | {n} | {v} |")
    lines += [
        "", "## How to finish it", "",
        "1. Paste `voiceover.txt` into ElevenLabs or Azure TTS (Bangla) and export the audio.",
        "2. Drop the audio into CapCut, then lay `slide-01.png` … over it in order.",
        "3. Replace any slide with stock footage where the Visual column asks for it —",
        "   Pexels, Pixabay, Mixkit. Never broadcast or agency clips.",
        "4. Burn in Bangla subtitles. Most viewers watch on mute.",
        "5. Upload natively to YouTube AND to Facebook. Do not post a YouTube link",
        "   to Facebook — it is throttled.",
    ]
    (out / "script.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (out / "youtube.txt").write_text(
        f"TITLE\n{draft['title']}\n\nDESCRIPTION\n{draft['description']}\n\n{url}\n\n"
        f"TAGS\n{', '.join(draft.get('tags') or [])}\n",
        encoding="utf-8",
    )

    made = render_slides(article, scenes, out)
    log(f"  slides: {made}")
    log(f"\n✓ kit ready: video-kits/{article['slug']}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
