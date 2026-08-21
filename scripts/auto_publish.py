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
import html
import json
import os
import re
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
import sys
from calendar import timegm
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

from photocard import render_cards

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "data"
ARTICLES_PATH = DATA / "articles.json"
STORIES_PATH = DATA / "stories.json"

# ── Cost & volume guardrails ────────────────────────────────────────────
# Fewer, deeper. Six 45-word briefs a day is thin content that cannot be
# monetised and risks Google's scaled-content-abuse policy; two proper
# reports are worth more than thirty stubs.
MAX_NEW_ARTICLES = int(os.environ.get("MAX_NEW_ARTICLES", "3"))
# Nothing older than this gets written up. Ranking alone sorted by weight
# first, so a three-day-old high-weight story beat this morning's news — the
# site read as a digest of the week rather than a news portal.
MAX_ITEM_AGE_HOURS = int(os.environ.get("MAX_ITEM_AGE_HOURS", "36"))
# Scholarships are the exception: a call published five days ago is still
# open, and its value is the deadline rather than the announcement.
SLOW_DESKS = {"বিদেশে পড়াশোনা": 24 * 7}
# Desks that get a guaranteed slot each run. Ranked purely on freshness
# neither would ever win one, yet these are the two people come back for:
# study-abroad keeps its value for months, football is simply the most read.
RESERVED_DESKS = [
    d.strip()
    for d in os.environ.get("RESERVED_DESKS", "বিদেশে পড়াশোনা,ফুটবল").split(",")
    if d.strip()
]
MAX_PER_CATEGORY = int(os.environ.get("MAX_PER_CATEGORY", "2"))
# Articles must NOT rotate out: at ~24/day a 40-item cap meant every article
# 404'd about 36 hours after Google indexed it, which destroys the search
# traffic the whole plan depends on. Keep the archive; paginate instead.
MAX_ARTICLES_KEPT = int(os.environ.get("MAX_ARTICLES_KEPT", "2000"))
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
            "kind": "gnews",
            "person": _person,
        }
    )

# ── Bangladesh desks ────────────────────────────────────────────────────
# Bangla-language Google News queries, one per section of the paper. These
# fill বাংলাদেশ / রাজনীতি / অপরাধ / খেলা / বিনোদন / অর্থনীতি / শিক্ষা /
# প্রবাস / জেলা — the categories a Bangladeshi reader actually opens.
BD_DESKS = [
    ("বাংলাদেশ", "বাংলাদেশ সরকার জাতীয়", 5),
    ("রাজনীতি", "বাংলাদেশ রাজনীতি নির্বাচন", 5),
    ("অপরাধ", "বাংলাদেশ আদালত মামলা তদন্ত", 3),
    ("খেলা", "বাংলাদেশ ক্রিকেট ফুটবল খেলা", 5),
    ("বিনোদন", "বাংলাদেশ বিনোদন সিনেমা নাটক", 3),
    ("অর্থনীতি", "বাংলাদেশ অর্থনীতি ব্যবসা বাণিজ্য", 5),
    ("শিক্ষা", "বাংলাদেশ শিক্ষা পরীক্ষা ভর্তি", 4),
    ("প্রবাস", "প্রবাসী বাংলাদেশি রেমিট্যান্স ভিসা", 4),
    ("জেলা", "চট্টগ্রাম সিলেট রাজশাহী খুলনা জেলা", 2),
]

for _cat, _query, _weight in BD_DESKS:
    FEEDS.append(
        {
            "name": f"বাংলাদেশ ডেস্ক · {_cat}",
            "url": (
                "https://news.google.com/rss/search?q="
                + _query.replace(" ", "+")
                + "+when:2d&hl=bn&gl=BD&ceid=BD:bn"
            ),
            "cat": _cat,
            "weight": _weight,
            "kind": "gnews",
        }
    )

# বিদেশে পড়াশোনা — scholarships, PhD calls, intakes and admission deadlines.
# Queried in English because that is the language these are announced in; the
# reports are written in Bangla for students here.
STUDY_DESKS = [
    ("fully funded scholarship international students application", 5),
    ("PhD position fully funded apply deadline", 5),
    ("Chevening Commonwealth scholarship application", 4),
    ("Erasmus Mundus joint masters scholarship", 4),
    ("DAAD scholarship Germany international students", 4),
    ("Canada study permit international students intake", 3),
    ("UK university admission international students deadline", 3),
    ("USA university funding assistantship international students", 3),
]

for _query, _weight in STUDY_DESKS:
    FEEDS.append(
        {
            "name": f"বিদেশে পড়াশোনা · {_query.split()[0].title()}",
            "url": (
                "https://news.google.com/rss/search?q="
                + urllib.parse.quote_plus(_query)
                + "+when:7d&hl=en-US&gl=US&ceid=US:en"
            ),
            "cat": "বিদেশে পড়াশোনা",
            "weight": _weight,
            "kind": "gnews",
        }
    )

# ফুটবল — the most-read sport online in Bangladesh. Messi and Ronaldo carry
# the desk; the domestic query keeps it from being only European football.
FOOTBALL_DESKS = [
    ("Lionel Messi", 5, "en"),
    ("Messi Inter Miami goal", 5, "en"),
    ("Cristiano Ronaldo", 4, "en"),
    ("Champions League", 4, "en"),
    ("Premier League", 3, "en"),
    ("Real Madrid Barcelona La Liga", 3, "en"),
    ("বাংলাদেশ ফুটবল হামজা চৌধুরী জামাল ভূঁইয়া", 4, "bn"),
]

for _query, _weight, _lang in FOOTBALL_DESKS:
    _loc = ("hl=bn&gl=BD&ceid=BD:bn" if _lang == "bn"
            else "hl=en-US&gl=US&ceid=US:en")
    FEEDS.append(
        {
            "name": f"ফুটবল · {_query.split()[0]}",
            "url": (
                "https://news.google.com/rss/search?q="
                + urllib.parse.quote_plus(_query)
                + "+when:2d&" + _loc
            ),
            "cat": "ফুটবল",
            "weight": _weight,
            "kind": "gnews",
        }
    )

# Direct football feeds. Google News hands back news.google.com redirect
# links whose real article URL cannot be recovered, so those items can only
# ever be a 150-character snippet. These give the publisher's own URL, which
# means the writer can read the match report and write a real one.
FEEDS += [
    {"name": "BBC Sport Football", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml",
     "cat": "ফুটবল", "weight": 5},
    {"name": "Sky Sports Football", "url": "https://www.skysports.com/rss/12040",
     "cat": "ফুটবল", "weight": 4},
    {"name": "ESPN Soccer", "url": "https://www.espn.com/espn/rss/soccer/news",
     "cat": "ফুটবল", "weight": 4},
    {"name": "The Guardian Football", "url": "https://www.theguardian.com/football/rss",
     "cat": "ফুটবল", "weight": 4},
]

# Direct feeds from established Bangladeshi outlets
FEEDS += [
    {"name": "প্রথম আলো", "url": "https://www.prothomalo.com/feed", "cat": "বাংলাদেশ", "weight": 5},
    {"name": "ঢাকা পোস্ট", "url": "https://www.dhakapost.com/rss/rss.xml", "cat": "বাংলাদেশ", "weight": 4},
    {"name": "রাইজিংবিডি", "url": "https://www.risingbd.com/rss/rss.xml", "cat": "বাংলাদেশ", "weight": 4},
    # Fact-checking desk — Bangladesh's established rumour-verification outfit.
    # Verification is only credible when it comes from real fact-checkers.
    {"name": "রিউমর স্ক্যানার", "url": "https://rumorscanner.com/feed", "cat": "ফ্যাক্ট চেক", "weight": 5},
    {
        "name": "ফ্যাক্ট চেক ডেস্ক",
        "url": (
            "https://news.google.com/rss/search?q="
            + "ফ্যাক্ট+চেক+ভুয়া+গুজব+বাংলাদেশ+when:5d&hl=bn&gl=BD&ceid=BD:bn"
        ),
        "cat": "ফ্যাক্ট চেক",
        "weight": 5,
        "kind": "gnews",
    },
]

BANGLA_WRITER_PROMPT = """You are a Bangla news-desk reporter writing original
reports for a Bangladeshi news portal.

You receive ONE item: a headline (in English OR Bangla), a summary snippet, the
outlet name, the URL, and usually "source_text" — the text of the source
article. The "material" field tells you which you have.

HOW MUCH TO WRITE IS DECIDED BY WHAT YOU WERE GIVEN, never by a target length:

- material = "full": you have the source article. Write a PROPER REPORT of
  5-8 body paragraphs. Use the specifics that make journalism worth reading —
  names, numbers, dates, places, what was said and by whom. This is the
  difference between a page worth publishing and a stub.
- material = "snippet-only": you have two sentences and nothing more. Write
  2-3 short paragraphs and STOP. Do not pad, do not speculate, do not restate
  the same fact in different words to reach a length. A short honest brief is
  correct here; an inflated one is a lie about how much we know.

USING source_text — this matters legally and professionally:
  - Take the FACTS. Write every sentence yourself, in your own Bangla.
  - Never translate the source sentence-by-sentence, and never reproduce its
    phrasing or structure. Translation of an article is the copyright owner's
    exclusive right; stating the facts it reports is not.
  - Quote at most ONE short direct quotation, in quotation marks, attributed
    to the person who said it.
  - Attribute throughout: "রয়টার্সের প্রতিবেদন অনুযায়ী", "প্রথম আলোর খবরে বলা হয়েছে".
  - If source_text contradicts the headline, trust source_text.

If the source item is ALREADY in Bangla, you must still write your own sentences.
Do not lift, lightly edit, or re-order the source's phrasing — read it, take the
facts, and compose the brief fresh in your own words.

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
  FOR FOOTBALL AND SPORT, the headline is the whole product. A Bangladeshi
  reader scrolling a feed decides in one second, and these rules decide it:
    • NAME THE STAR. "মেসি" in the headline outperforms "ইন্টার মায়ামি" every
      time. Readers scan for the name, not the club.
    • LEAD WITH THE NUMBER OR THE MOMENT — the hat-trick, the 92nd minute,
      the comeback from two down. Specifics sell; adjectives do not.
    • Put the stake in it: what it decides, who it beats, what it ends.
    • The facts almost always supply the drama. If they do not, the story is
      not worth a dramatic headline — write the plain one. Never manufacture
      tension, never promise a revelation the report does not contain, never
      write a question the piece cannot answer. A reader who feels tricked
      does not come back, and that costs more than the click was worth.

  LEAD THE HEADLINE WITH THE CONCRETE FACT, not the framing. The number, the
  age, the score, the name — first, where a scrolling reader sees it.
  "৫৯ বছর বয়সে গোল, নতুন রেকর্ড কাজুইউশি মিউরার" works because the number is
  the first thing on screen. "রেকর্ড গড়লেন এক জাপানি ফুটবলার" wastes the only
  second you get. Never bury the fact behind a description of the fact.

- lead: ONE sentence — what happened.
- body: paragraphs of 2-4 sentences each, in your own plain Bangla. How many
  is set by "material": 5-8 when you have the full source text, 2-3 when you
  only have the snippet. Open the first paragraph with attribution:
  "টেকক্রাঞ্চের প্রতিবেদন অনুযায়ী", "গুগলের ব্লগ পোস্টে বলা হয়েছে" — whatever fits
  the outlet. With full material, structure it the way a reporter would:
  what happened → the detail and the numbers → who said what → why it matters
  to a Bangladeshi reader → what happens next.

STRUCTURE THAT SETS THIS PAPER APART. Readers do not just want the event; they
want to know what it means for them. Fill these when — and ONLY when — the facts
you were given genuinely support it:

- impact (এতে কী বদলাবে): 1-2 short paragraphs on the concrete, direct
  consequence for ordinary Bangladeshi readers — a price they pay, a rule they
  must follow, a deadline, a service that changes. Derive it strictly from the
  stated facts. If the item is a routine statement, a foreign story with no
  local bearing, or too thin to reason from, return an EMPTY array. An empty
  impact is always better than a guessed one.
- context (প্রেক্ষাপট): 1 short paragraph of background — but ONLY if the
  snippet itself supplies it. Do NOT supply history from your own knowledge,
  because you cannot verify it here. Otherwise return an EMPTY array.
- verdict / claim: leave BOTH as "" unless this item is itself a fact-check
  from a fact-checking organisation. When it is, put the viral claim being
  checked in `claim` and choose the verdict the fact-checkers reached.

Never stretch a thin story into a structured one. Empty fields are expected and
correct on most routine items.

- image_query: 2-4 ENGLISH keywords for a representative photograph to run with
  the story, searched against Wikimedia Commons. Think about what a picture desk
  would pull:
    • PREFER THE NAMED PERSON the story is actually about. A reader scrolling
      a feed stops for a face and ignores a generic building, so this is the
      single biggest thing you can do for a story's reach. If the headline
      names a player, minister, actor or executive, request that person by
      name. Add a disambiguating word for common names ("Nathan Lyon
      cricketer", "Steve Smith cricketer").
    • a named public figure, company, product, team or landmark → name it
      ("Sam Altman", "Dhaka University campus", "Bangladesh cricket team")
    • an institution or setting → the place ("Bangladesh Bank building",
      "Bangladesh Supreme Court", "school classroom Bangladesh")
    • a subject with an obvious visual ("cricket stadium", "solar eclipse")
  For FACT CHECKS and stories about a viral claim, picture the SUBJECT MATTER of
  the claim, never the person it concerns: a claim about power cuts →
  "electricity transmission tower Bangladesh"; about exam results →
  "school examination hall"; about floods → "flood Bangladesh". These stories
  should almost always have an image — just not of anyone accused.

- image_is_of_subject: true ONLY when the query names the actual person, team,
  place or object the story is about. The photo is genuinely them, just not
  taken at this event, so it is labelled ফাইল ছবি. Set false for a generic
  stand-in that merely illustrates the topic, which is labelled প্রতীকী ছবি.
  Getting this wrong claims we pictured something we did not. Always false for
  crime, court and allegation stories.

- quote_text / quote_by / quote_role: if the source reports someone SAYING
  something quotable, give the line in Bangla (under 200 characters), the
  speaker's name in Bangla, and their position. This becomes a quote card for
  social media, so it must be safe to put in quotation marks beside that
  person's face:
    • Only a statement the source actually attributes to them. Never a
      paraphrase presented as a quote, never words they did not say.
    • Leave all three empty when nobody is quoted, when you are unsure who
      said it, or when the quote is an accusation against someone else.
    • quote_by must be the person the photo will show — set image_query to
      that same person, or leave the quote fields empty.

- person_name / second_person_query / second_person_name: when a story is
  genuinely ABOUT TWO named people facing each other — two captains, two
  candidates, an accuser and the accused — give both. person_name is the
  Bangla name of whoever image_query returns; second_person_query is the
  other one in English for Commons; second_person_name is their Bangla name.
  This produces a two-portrait card. Leave all three empty unless the story
  really is about both of them; a second face implies involvement, so never
  add one to pad the card out, and never for crime or allegation stories.

- scoreboard: for a match RESULT or an in-progress score, and only when the
  source states the figures. Give context ("১ম টেস্ট · ডারউইন · ২য় দিন শেষে"),
  a row per side with the team name and score in Bangla numerals, lead=true
  on the side in front, a status line ("বাংলাদেশ এগিয়ে ১৫৩ রানে"), and up to
  four notes for top performers ("তানজিদ হাসান ১০১"). This becomes a
  scoreboard card, so every number must come from the source — never
  estimate, never round, and leave rows empty if the score is unclear.

- opportunity: fill this ONLY for a genuine study-abroad opportunity — a
  scholarship, fellowship, PhD call, or an admission intake with a deadline.
  This becomes a details panel students act on, so accuracy is not
  negotiable:
    - deadline: ONLY if the source states one. Copy the date it gives, in
      Bangla. If no deadline is stated, return an EMPTY string. NEVER infer,
      estimate, or carry over a date from a previous year — a wrong deadline
      makes a student miss the opportunity entirely.
    - official_url: the official scholarship or university page if the source
      names it. Otherwise empty. Never guess a URL.
    - funding: what is actually covered as stated (tuition, stipend, airfare,
      health cover). Do not write "fully funded" unless the source does.
    - eligibility: the stated requirements. Do not claim Bangladeshi students
      are eligible unless the source says so or the call is open to all
      international students.
    - how_to_apply: the concrete steps the source describes, in order.
    - country, institution, level (স্নাতক / মাস্টার্স / পিএইচডি / পোস্টডক): as stated.
  Leave every field empty for a story that is merely ABOUT education policy,
  visa trends or rankings — that is a news report, not an opportunity.

- source_line: the Bangla attribution line that closes the report, in the
  form "সূত্র: রয়টার্স" — the outlet whose reporting this is, written in Bangla
  (রয়টার্স, এএফপি, বিবিসি, এপি, প্রথম আলো, দ্য ডেইলি স্টার). This credits the
  reporting, which is separate from any photograph. One line, nothing else.

- image_caption: one line of Bangla describing WHAT THE PHOTO SHOWS, for the
  reader who cannot see it well — "ডারউইন টেস্টে ব্যাট করছেন নাজমুল হোসেন শান্ত",
  not "শান্তর ছবি". Describe only what your image_query would return. Leave
  empty when image_query is empty. Never describe the event itself unless the
  photo is of that event, which it never is here. Do NOT write "প্রতীকী ছবি"
  or "ফাইল ছবি" inside the caption — the page prints that label itself, and
  repeating it reads as a mistake.

  Rules that matter more than having an image:
    • For crime, court, accident or allegation stories, NEVER request a person.
      Ask only for a neutral setting ("courthouse building", "police vehicle").
      A photo of the wrong face beside a crime story is defamatory.
    • Never request photos of victims, children, or private individuals.
    • Return "" ONLY when no honest picture exists for the subject — for
      example a story that is purely about one named individual's conduct.
      Prefer a truthful subject-matter photo over an empty query: it is
      labelled প্রতীকী ছবি on the page, so readers know it is illustrative.
- category: the desk this story belongs on, judged from the story itself — not
  from where it was collected. A Chattogram arrest is অপরাধ, not বাংলাদেশ or
  জেলা. A cricket result is খেলা. A university expulsion is শিক্ষা. A remittance
  figure is অর্থনীতি. Use জেলা only when the story's substance is local district
  affairs rather than a crime or a national matter, and বাংলাদেশ only for
  national news that fits no sharper desk.

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

LEGAL SAFETY — crime, courts and allegations (অপরাধ / আদালত):
- Never state or imply that a named person committed a crime. Write "অভিযোগ",
  "অভিযুক্ত", "পুলিশের ভাষ্য অনুযায়ী", "আদালতে দায়ের করা মামলায় বলা হয়েছে".
- Only name individuals if the source names them AND the matter is already
  before police or a court. Never name suspects who have only been accused
  informally, and never name victims of sexual crimes or children.
- Attribute every allegation to whoever made it. If the source is vague about
  who alleges what, keep the brief general and do not name anyone.

Return JSON matching the schema."""

ARTICLE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "lead": {"type": "string"},
        # কী ঘটেছে
        "body": {"type": "array", "items": {"type": "string"}},
        # এতে সাধারণ মানুষের কী বদলাবে — empty when the facts don't support it
        "impact": {"type": "array", "items": {"type": "string"}},
        # প্রেক্ষাপট — empty unless the source itself supplies background
        "context": {"type": "array", "items": {"type": "string"}},
        # Only for fact-check items; "" otherwise
        "verdict": {
            "type": "string",
            "enum": ["", "সত্য", "মিথ্যা", "আংশিক সত্য", "যাচাই করা যায়নি"],
        },
        "claim": {"type": "string"},
        # English keywords for a representative photo, or "" if none is safe
        "image_query": {"type": "string"},
        "image_is_of_subject": {"type": "boolean"},
        "source_line": {"type": "string"},
        "image_caption": {"type": "string"},
        "quote_text": {"type": "string"},
        "quote_by": {"type": "string"},
        "quote_role": {"type": "string"},
        "person_name": {"type": "string"},
        "second_person_query": {"type": "string"},
        "second_person_name": {"type": "string"},
        "opportunity": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "country": {"type": "string"},
                "institution": {"type": "string"},
                "level": {"type": "string"},
                "deadline": {"type": "string"},
                "funding": {"type": "array", "items": {"type": "string"}},
                "eligibility": {"type": "array", "items": {"type": "string"}},
                "how_to_apply": {"type": "array", "items": {"type": "string"}},
                "official_url": {"type": "string"},
            },
            "required": ["country", "institution", "level", "deadline",
                         "funding", "eligibility", "how_to_apply",
                         "official_url"],
        },
        "scoreboard": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "context": {"type": "string"},
                "status": {"type": "string"},
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "team": {"type": "string"},
                            "score": {"type": "string"},
                            "lead": {"type": "boolean"},
                        },
                        "required": ["team", "score", "lead"],
                    },
                },
                "notes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["context", "status", "rows", "notes"],
        },
        # The desk this story belongs on, judged from its content
        "category": {
            "type": "string",
            "enum": [
                "বাংলাদেশ", "রাজনীতি", "অপরাধ", "খেলা", "বিনোদন", "অর্থনীতি",
                "বিশ্ব", "প্রযুক্তি", "শিক্ষা", "বিদেশে পড়াশোনা", "ফুটবল",
                "প্রবাস", "জেলা",
                "ফ্যাক্ট চেক",
            ],
        },
    },
    "required": [
        "title", "lead", "body", "impact", "context", "verdict", "claim",
        "category", "image_query", "image_is_of_subject",
        "source_line", "image_caption",
        "quote_text", "quote_by", "quote_role",
        "person_name", "second_person_query", "second_person_name",
        "opportunity",
        "scoreboard",
    ],
}

VALID_CATEGORIES = set(ARTICLE_SCHEMA["properties"]["category"]["enum"])

_WS = re.compile(r"\s+")

EXPLAINER_PROMPT = """You are the explainer desk of a Bangladeshi news site. Your
readers already saw the headline elsewhere. What they don't have is: what does
this actually MEAN for me?

You will receive SEVERAL reports from DIFFERENT outlets about ONE story —
headlines and short snippets. Together they are all the information you have.

Write a Bangla explainer in question-and-answer form. Ask the questions a normal
reader genuinely has, in plain language, and answer each one directly.

- title: a Bangla headline framed as the explainer it is — e.g.
  "যা জানা দরকার: <বিষয়>" or "<বিষয়> নিয়ে যা ঘটছে, ব্যাখ্যা". Concrete, no hype.
- lead: two sentences setting up why this story matters right now.
- questions: 4 to 6 items. Each has a `question` a reader would actually ask and
  an `answer` of 1-3 short paragraphs. Use this arc, adapted to the story:
    1. ঘটনাটি আসলে কী? / কী সিদ্ধান্ত নেওয়া হয়েছে?
    2. কেন এখন এটি গুরুত্বপূর্ণ?
    3. সাধারণ মানুষের কী বদলাবে?  ← the most important question; be concrete
    4. এর পেছনে কী ঘটেছিল?        ← only if the reports supply background
    5. এরপর কী হতে পারে?          ← only what the reports themselves indicate
- category: the desk this belongs on.

Hard rules — an explainer that invents is worse than no explainer:
- Use ONLY facts present in the supplied reports. Never add history, numbers,
  quotes or predictions from your own knowledge.
- Where the reports disagree, say so plainly: "একাধিক সংবাদমাধ্যমে ভিন্ন তথ্য
  এসেছে". Where something is unknown, say "এখনো জানা যায়নি" — do not fill it in.
- For "এরপর কী", only describe next steps the reports actually mention (a
  scheduled hearing, an announced deadline). Never speculate about outcomes.
- Attribute contested or single-source claims to the outlet that reported them.
- Crime and court matters: অভিযোগ / অভিযুক্ত framing, never assert guilt.
- Standard modern Bangla (চলিত), warm and clear. Short sentences.

Return JSON matching the schema."""

EXPLAINER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "lead": {"type": "string"},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["question", "answer"],
            },
        },
        "category": {
            "type": "string",
            "enum": [
                "বাংলাদেশ", "রাজনীতি", "অপরাধ", "খেলা", "বিনোদন", "অর্থনীতি",
                "বিশ্ব", "প্রযুক্তি", "শিক্ষা", "প্রবাস", "জেলা",
            ],
        },
    },
    "required": ["title", "lead", "questions", "category"],
}


DEBATE_PROMPT = """You are the বিতর্ক (debate) desk of a Bangladeshi news site.

You are given several outlets' reports on the same story. Your job is to
determine whether credible sources GENUINELY DISAGREE about something, and if
so, to lay out both sides fairly in Bangla.

This desk exists to cover real disagreement, not to manufacture it. Set
"has_real_disagreement" to false whenever:
  - the outlets simply report the same facts with different wording
  - the only 'disagreement' is one side not having commented yet
  - the dispute is trivial, or about a matter of taste
  - you would have to invent, sharpen or guess a position to make it a debate

When it IS a real dispute, write:
  - title: a neutral question in Bangla. Never imply which side is correct.
  - lead: one paragraph in Bangla stating what is actually contested.
  - side_a / side_b: the two positions. Each needs a short Bangla label, and
    2-3 Bangla sentences stating that side's argument AS ITS HOLDERS PUT IT.
  - settled: what is NOT in dispute — the facts both sides accept.
  - open_question: what would have to be established to resolve it.

Rules that are not negotiable:
  - Attribute every contested claim to who said it. Never state a contested
    claim in the site's own voice.
  - Do not accuse any named person of a crime or wrongdoing. Report only that
    an allegation was made, and by whom.
  - Give both sides comparable weight and length. Do not write one side as
    obviously correct.
  - If one side is a fringe position contradicted by strong evidence, say so
    plainly in "settled" rather than presenting a false balance."""

DEBATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "has_real_disagreement": {"type": "boolean"},
        "title": {"type": "string"},
        "lead": {"type": "string"},
        "side_a_label": {"type": "string"},
        "side_a": {"type": "array", "items": {"type": "string"}},
        "side_b_label": {"type": "string"},
        "side_b": {"type": "array", "items": {"type": "string"}},
        "settled": {"type": "array", "items": {"type": "string"}},
        "open_question": {"type": "string"},
    },
    "required": [
        "has_real_disagreement", "title", "lead", "side_a_label", "side_a",
        "side_b_label", "side_b", "settled", "open_question",
    ],
}


def log(msg: str) -> None:
    print(msg, flush=True)


def clean_text(raw: str | None) -> str:
    # Decode entities first (&nbsp;, &amp;, &#x27;) so they don't survive into
    # the page, then drop markup, then collapse whitespace.
    text = html.unescape(raw or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = _WS.sub(" ", text).strip()
    return "" if text.lower() in {"null", "none"} else text


# ── Desk classification ─────────────────────────────────────────────────
# A general national feed can't tell us whether an item is crime, politics or
# education, so we read the text. Order matters: the first desk that matches
# wins, and the distinctive desks are checked before the broad ones.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("ফুটবল", ("মেসি", "রোনালদো", "ফুটবল", "গোল করে", "চ্যাম্পিয়নস লিগ",
               "প্রিমিয়ার লিগ", "লা লিগা", "বার্সেলোনা", "রিয়াল মাদ্রিদ",
               "ইন্টার মায়ামি", "আর্জেন্টিনা", "ব্রাজিল", "ফিফা", "হ্যাটট্রিক")),
    ("বিদেশে পড়াশোনা", ("স্কলারশিপ", "বৃত্তি", "ফুল ফান্ডেড", "ফেলোশিপ",
                        "পিএইচডি", "মাস্টার্স", "আবেদনের শেষ", "ইনটেক",
                        "চিভনিং", "কমনওয়েলথ", "ইরাসমাস", "ড্যাড",
                        "স্টুডেন্ট ভিসা", "বিদেশে উচ্চশিক্ষা", "টিউশন ফি")),
    ("খেলা", ("ক্রিকেট", "ফুটবল", "উইকেট", "টি-টোয়েন্টি", "টেস্ট ম্যাচ", "ওয়ানডে",
              "বিশ্বকাপ", "খেলোয়াড়", "টাইগার", "গোল করে", "ম্যাচে", "সিরিজ",
              "টুর্নামেন্ট", "লিগ", "ব্যাটিং", "বোলিং")),
    ("বিনোদন", ("সিনেমা", "চলচ্চিত্র", "নাটক", "অভিনেতা", "অভিনেত্রী", "নায়িকা",
                "নায়ক", "গানের", "শিল্পী", "সংগীত", "বলিউড", "ঢালিউড", "শোবিজ")),
    ("অপরাধ", ("গ্রেপ্তার", "গ্রেফতার", "রিমান্ড", "হত্যা", "খুন", "ধর্ষণ",
               "ছিনতাই", "সন্ত্রাসী", "মামলা", "আদালত", "তদন্ত", "অভিযোগে",
               "অভিযুক্ত", "কারাদণ্ড", "জামিন", "লুট", "মাদক", "সংঘর্ষ")),
    ("শিক্ষা", ("শিক্ষার্থী", "বিশ্ববিদ্যালয়", "পরীক্ষা", "ভর্তি", "এসএসসি",
                "এইচএসসি", "রেজাল্ট", "ফলাফল প্রকাশ", "শিক্ষক", "মাদ্রাসা",
                "কলেজের", "শিক্ষাপ্রতিষ্ঠান", "এমপিও")),
    ("অর্থনীতি", ("ব্যাংক", "রেমিট্যান্স", "রপ্তানি", "আমদানি", "বিনিয়োগ",
                  "শেয়ারবাজার", "ডলার", "মূল্যস্ফীতি", "অর্থনীতি", "রাজস্ব",
                  "বাজেট", "জিডিপি", "ব্যবসা", "বাণিজ্য")),
    ("প্রবাস", ("প্রবাসী", "ভিসা", "অভিবাসন", "মালয়েশিয়া", "সৌদি", "দুবাই",
                "কর্মী পাঠানো", "বিদেশগামী")),
    ("প্রযুক্তি", ("প্রযুক্তি", "কৃত্রিম বুদ্ধিমত্তা", "এআই", "সফটওয়্যার",
                   "স্মার্টফোন", "অ্যাপ", "ইন্টারনেট", "সাইবার", "গুগল",
                   "ওপেনএআই", "চ্যাটজিপিটি")),
    ("রাজনীতি", ("নির্বাচন", "ভোট", "বিএনপি", "আওয়ামী", "জামায়াত", "রাজনৈতিক",
                 "সংসদ", "রাষ্ট্রপতি", "প্রধান উপদেষ্টা", "মন্ত্রী", "দলীয়")),
    ("জেলা", ("চট্টগ্রাম", "সিলেট", "রাজশাহী", "খুলনা", "বরিশাল", "রংপুর",
              "ময়মনসিংহ", "কুমিল্লা", "নোয়াখালী", "উপজেলা")),
]


def classify(title: str, summary: str, fallback: str) -> str:
    """Pick the desk from the text. Falls back to the feed's own category."""
    text = f"{title} {summary}"
    for category, keywords in CATEGORY_RULES:
        if any(k in text for k in keywords):
            return category
    return fallback


def useful_summary(summary: str, title: str) -> str:
    """Feed summaries are often just the headline repeated, sometimes with the
    publisher's domain tacked on. Those add nothing on the page."""
    if not summary:
        return ""
    stripped = summary.strip()
    # Drop a trailing bare domain ("… citizensvoicebd.com")
    stripped = re.sub(r"\s*[\w.-]+\.(com|net|org|bd|tv|news)\s*$", "", stripped)
    normal = re.sub(r"\W+", "", stripped.lower())
    title_normal = re.sub(r"\W+", "", title.lower())
    if not normal or normal == title_normal or normal.startswith(title_normal):
        return ""
    return stripped


# Bangla → Latin, for URLs only. Raw Bangla slugs were tried and reverted:
# Next.js could not serve the non-ASCII dynamic routes (308 → 404), which
# silently made every Bangla-titled article unreachable.
_BN_TRANSLIT = {
    "অ": "o", "আ": "a", "ই": "i", "ঈ": "i", "উ": "u", "ঊ": "u", "ঋ": "ri",
    "এ": "e", "ঐ": "oi", "ও": "o", "ঔ": "ou",
    "ক": "k", "খ": "kh", "গ": "g", "ঘ": "gh", "ঙ": "ng",
    "চ": "ch", "ছ": "chh", "জ": "j", "ঝ": "jh", "ঞ": "n",
    "ট": "t", "ঠ": "th", "ড": "d", "ঢ": "dh", "ণ": "n",
    "ত": "t", "থ": "th", "দ": "d", "ধ": "dh", "ন": "n",
    "প": "p", "ফ": "ph", "ব": "b", "ভ": "bh", "ম": "m",
    "য": "j", "র": "r", "ল": "l", "শ": "sh", "ষ": "sh", "স": "s", "হ": "h",
    "ড়": "r", "ঢ়": "rh", "য়": "y", "ৎ": "t", "ং": "ng", "ঃ": "h", "ঁ": "n",
    "া": "a", "ি": "i", "ী": "i", "ু": "u", "ূ": "u", "ৃ": "ri",
    "ে": "e", "ৈ": "oi", "ো": "o", "ৌ": "ou", "্": "",
    "০": "0", "১": "1", "২": "2", "৩": "3", "৪": "4",
    "৫": "5", "৬": "6", "৭": "7", "৮": "8", "৯": "9",
}


def transliterate_bn(text: str) -> str:
    return "".join(_BN_TRANSLIT.get(ch, ch) for ch in text)


def slugify(title: str, url: str, category: str = "") -> str:
    """ASCII slug carrying the headline's words, transliterated from Bangla."""
    base = transliterate_bn(title.lower())
    base = re.sub(r"[^a-z0-9]+", " ", base)
    base = "-".join(base.split()[:8]).strip("-")
    if not base:
        cat = re.sub(r"[^a-z0-9]+", "-", transliterate_bn(category.lower())).strip("-")
        base = cat or "news"
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
            if feed.get("kind") == "gnews":
                # Google News titles read "Headline - Publisher"; split so we
                # attribute the real outlet rather than "Google News".
                if " - " in title:
                    title, _, publisher = title.rpartition(" - ")
                    source = publisher.strip() or source
                else:
                    source = "Google News"

            summary = clean_text(getattr(entry, "summary", ""))[:400]
            # Fact-check feeds are already a desk; everything else is read.
            category = (
                feed["cat"]
                if feed["cat"] == "ফ্যাক্ট চেক"
                else classify(title, summary, feed["cat"])
            )

            seen_titles.add(key)
            kept += 1
            items.append(
                {
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "source": source,
                    "person": person,
                    "category": category,
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
            # Use the desk the item actually came from — labelling a crime
            # story "Technology" is worse than showing no label at all.
            "category": i["category"],
            "summary": useful_summary(i["summary"], i["title"])[:150],
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
    now = datetime.now(timezone.utc)

    def too_old(i: dict) -> bool:
        limit = SLOW_DESKS.get(i["category"], MAX_ITEM_AGE_HOURS)
        try:
            age = (now - datetime.fromisoformat(i["publishedAt"])).total_seconds() / 3600
        except (ValueError, TypeError):
            return False  # unparseable date: judge it on merit, not on a guess
        return age > limit

    fresh = [
        i
        for i in items
        if not too_old(i)
        if i["url"] not in used
        and len(i["title"]) >= 20
        # AI-voices items are headline-driven (Google News gives a thin
        # snippet), so they qualify on a strong headline alone.
        and (len(i["summary"]) >= 90 or i.get("person"))
        and i["source"].strip().lower() not in BLOCKED_SOURCES
        and not CLICKBAIT.search(i["title"])
    ]
    fresh.sort(key=lambda i: (i["weight"], i["publishedAt"]), reverse=True)

    # Each reserved desk takes one slot before ranking decides the rest.
    reserved: list[dict] = []
    for desk in RESERVED_DESKS:
        for item in fresh:
            if item["category"] == desk and item not in reserved:
                reserved.append(item)
                break

    picked: list[dict] = list(reserved)
    per_person: dict[str, int] = {}
    per_category: dict[str, int] = {c["category"]: 1 for c in reserved}
    reserved_urls = {r["url"] for r in reserved}
    for item in fresh:
        if item["url"] in reserved_urls:
            continue
        # One brief per real-world story, however many outlets covered it.
        if any(_same_story(item["title"], p["title"]) for p in picked):
            continue
        # Don't let one person's news day fill the whole run.
        person = item.get("person")
        if person:
            if per_person.get(person, 0) >= 1:
                continue
            per_person[person] = per_person.get(person, 0) + 1
        # Spread the run across desks so the front page isn't all one section.
        cat = item["category"]
        if per_category.get(cat, 0) >= MAX_PER_CATEGORY:
            continue
        per_category[cat] = per_category.get(cat, 0) + 1
        picked.append(item)
        if len(picked) >= MAX_NEW_ARTICLES:
            break
    return picked


READABLE_TAGS = re.compile(r"<(script|style|nav|header|footer|aside|form)\b[^>]*>.*?</\1>",
                           re.I | re.S)


def fetch_source_text(url: str, limit: int = 7000) -> str:
    """Read the source article so there are facts enough to report from.

    A feed gives roughly 150 characters, which is why briefs come out at 45
    words: the writer has nothing else. Reading the page is ordinary
    reporting — the facts are used to write our own account, and the source's
    own sentences are never reproduced. Returns "" on any failure, and the
    writer falls back to the snippet.
    """
    if not url.startswith("http"):
        return ""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; BDSiteNewsBot/1.0; "
                          "+https://www.bdsitenews.com)",
            "Accept": "text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req, timeout=25) as resp:
            if "html" not in resp.headers.get("Content-Type", ""):
                return ""
            raw = resp.read(1_500_000).decode("utf-8", "ignore")
    except Exception as exc:
        log(f"    source not readable: {str(exc)[:60]}")
        return ""

    raw = READABLE_TAGS.sub(" ", raw)
    # Paragraph text is where the reporting lives; headers and menus are not.
    paras = re.findall(r"<p\b[^>]*>(.*?)</p>", raw, re.I | re.S)
    junk = re.compile(
        r"copyright|all rights reserved|unauthorized use|subscribe|newsletter|"
        r"cookie|privacy policy|terms of|follow us|share this|read more|"
        r"advertisement|sign up|log in", re.I)
    kept = []
    for p in paras:
        line = clean_text(re.sub(r"<[^>]+>", " ", p)).strip()
        # Boilerplate is short and formulaic; real paragraphs are neither.
        if len(line) < 40 or junk.search(line):
            continue
        kept.append(line)
    text = " ".join(" ".join(kept).split())
    if len(text) < 400:  # a paywall, a consent wall, or a stub
        return ""
    return text[:limit]


def write_article(client, item: dict) -> dict | None:
    """One Claude call → one original Bangla article."""
    source_text = fetch_source_text(item["url"])
    if source_text:
        log(f"    ↓ read source ({len(source_text)} chars)")
    payload = json.dumps(
        {
            "headline": item["title"],
            "summary": item["summary"],
            "outlet": item["source"],
            "url": item["url"],
            "source_text": source_text,
            "material": "full" if source_text else "snippet-only",
        },
        ensure_ascii=False,
    )
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=5000,
            system=BANGLA_WRITER_PROMPT,
            messages=[{"role": "user", "content": payload}],
            output_config={"format": {"type": "json_schema", "schema": ARTICLE_SCHEMA}},
        )
    except Exception as exc:
        log(f"  ! write failed ({item['source']}): {str(exc)[:140]}")
        return None

    draft = parse_draft(message, f"write ({item['source']})")
    if not draft:
        return None

    usage = message.usage
    cost = (usage.input_tokens * 3 + usage.output_tokens * 15) / 1_000_000
    log(
        f"  + {draft['title'][:52]}… "
        f"({usage.input_tokens}+{usage.output_tokens} tok, ~${cost:.4f})"
    )

    # Trust the writer's read of the story over the feed it arrived on.
    category = draft.get("category", "")
    if category not in VALID_CATEGORIES:
        category = item["category"]

    article = {
        "slug": slugify(draft["title"], item["url"], category),
        "title": draft["title"],
        "category": category,
        "lead": draft["lead"],
        "body": [p for p in draft["body"] if p.strip()],
        "sources": [{"name": item["source"], "url": item["url"]}],
        "publishedAt": datetime.now(timezone(timedelta(hours=6))).isoformat(
            timespec="seconds"
        ),
    }
    # Only attach the structured blocks the model actually filled.
    impact = [p for p in draft.get("impact", []) if p.strip()]
    context = [p for p in draft.get("context", []) if p.strip()]
    if impact:
        article["impact"] = impact
    if context:
        article["context"] = context

    source_line = (draft.get("source_line") or "").strip()
    if source_line:
        article["sourceLine"] = source_line

    quote_text = (draft.get("quote_text") or "").strip()
    quote_by = (draft.get("quote_by") or "").strip()
    if quote_text and quote_by:
        article["quote"] = {
            "text": quote_text,
            "by": quote_by,
            "role": (draft.get("quote_role") or "").strip(),
        }
        # Name the face, so the quote card can check the portrait really is
        # the speaker before putting words beside it.
        image = article.get("image") or {}
        if image and not image.get("illustrative", True) and not image.get("person"):
            person = (draft.get("person_name") or "").strip()
            if person == quote_by:
                image["person"] = person

    opp = draft.get("opportunity") or {}
    if any((opp.get(k) or "") for k in ("country", "institution", "deadline")):
        article["opportunity"] = {
            "country": (opp.get("country") or "").strip(),
            "institution": (opp.get("institution") or "").strip(),
            "level": (opp.get("level") or "").strip(),
            "deadline": (opp.get("deadline") or "").strip(),
            "funding": [x.strip() for x in (opp.get("funding") or []) if x.strip()],
            "eligibility": [x.strip() for x in (opp.get("eligibility") or []) if x.strip()],
            "howToApply": [x.strip() for x in (opp.get("how_to_apply") or []) if x.strip()],
            "officialUrl": (opp.get("official_url") or "").strip(),
        }

    board = draft.get("scoreboard") or {}
    rows = [r for r in (board.get("rows") or [])
            if (r.get("team") or "").strip() and (r.get("score") or "").strip()]
    if len(rows) >= 2:
        article["scoreboard"] = {
            "context": (board.get("context") or "").strip(),
            "status": (board.get("status") or "").strip(),
            "rows": rows,
            "notes": [n.strip() for n in (board.get("notes") or []) if n.strip()][:4],
        }
    if draft.get("verdict") and draft.get("claim"):
        article["factcheck"] = {
            "claim": draft["claim"].strip(),
            "verdict": draft["verdict"],
        }
    # A picture where one genuinely helps; the designed headline card otherwise.
    attach_image(article, draft.get("image_query", ""),
                 of_subject=bool(draft.get("image_is_of_subject")))
    caption = (draft.get("image_caption") or "").strip()
    if caption and article.get("image"):
        article["image"]["caption"] = caption

    # A second portrait, only when the first one is genuinely of a person —
    # otherwise the duo card would pair a real face with a stock stand-in and
    # imply both belong to the story.
    second_query = (draft.get("second_person_query") or "").strip()
    if second_query and not (article.get("image") or {}).get("illustrative", True):
        article["image"]["person"] = (draft.get("person_name") or "").strip()
        attach_second_portrait(
            article, second_query, (draft.get("second_person_name") or "").strip()
        )
    time.sleep(1.5)  # be polite to the Commons API between lookups
    return article


# ── Pictures ────────────────────────────────────────────────────────────
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_UA = {"User-Agent": "BDSiteNews/1.0 (editorial illustration; bdsitenews.com)"}
COVERS_DIR = ROOT / "public" / "covers"

# Licences that permit reuse with attribution.
ALLOWED_LICENCE = re.compile(r"(public domain|cc[ -]?(by|0)|cc[ -]?by[ -]?sa)", re.I)


def find_commons_image(query: str) -> dict | None:
    """Search Wikimedia Commons for a reusable photo matching the query."""
    if not query.strip():
        return None
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": "6",
        "gsrlimit": "8", "prop": "imageinfo|categories", "cllimit": "50",
        "iiprop": "url|size|extmetadata|mime", "iiurlwidth": "1200",
    }
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    data = None
    # Commons rate-limits bursts with 429. Backing off costs a few seconds;
    # not backing off costs the article its photo, silently.
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=COMMONS_UA)
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            log(f"    image search failed: HTTP {exc.code}")
            return None
        except Exception as exc:
            log(f"    image search failed: {str(exc)[:70]}")
            return None
    if data is None:
        return None

    # Every distinctive word of the query must be answered by the file's own
    # name. Commons search matches loosely, and a loose match is how a story
    # about a Test match ends up illustrated with an empty sky.
    stop = {"the", "of", "in", "at", "a", "and", "bangladesh",
            "building", "photo"}

    # The role word is the whole point of a query like "Hasan Mahmud
    # cricketer": Bangladesh has a Test bowler and a former minister of that
    # name. Treating it as a stopword once put the politician's face on a
    # cricket report. It is checked against the file's Commons categories
    # instead, which is where Wikimedia actually records who someone is.
    role_topic = {
        "cricketer": "cricket", "cricket": "cricket", "footballer": "football",
        "politician": "politic", "minister": "politic", "mp": "politic",
        "actor": "actor", "actress": "actress", "singer": "sing",
        "musician": "music", "director": "director", "economist": "econom",
    }
    words = re.findall(r"[a-z]+", query.lower())
    roles = [w for w in words if w in role_topic]
    topic = role_topic[roles[0]] if roles else ""
    wanted = [w for w in words
              if len(w) > 2 and w not in stop and w not in role_topic]

    pages = data.get("query", {}).get("pages", {})
    for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") != "image/jpeg" or info.get("width", 0) < 800:
            continue
        meta = info.get("extmetadata", {})
        licence = re.sub(r"<[^>]+>", "", meta.get("LicenseShortName", {}).get("value", ""))
        if not ALLOWED_LICENCE.search(licence):
            continue

        title = page.get("title", "").lower()
        if wanted and not all(w in title for w in wanted):
            continue

        # When the query named a role, the file must actually be filed under
        # it. Two public figures sharing a name is common in Bangladesh, and
        # the wrong face on a story is not a cosmetic error.
        if topic:
            cats = " ".join(c.get("title", "")
                            for c in (page.get("categories") or [])).lower()
            if topic not in title and topic not in cats:
                continue

        # Landscapes and skylines make poor cards: the subject is too small
        # to read at feed size. Portrait or near-square crops far better.
        w, h = info.get("width", 0), info.get("height", 1)
        if w / max(h, 1) > 2.2:
            continue
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
        return {
            "thumb": info.get("thumburl"),
            "credit": f"{artist[:60]}, {licence} — Wikimedia Commons"
            if artist
            else f"{licence} — Wikimedia Commons",
        }
    return None


OPENVERSE_API = "https://api.openverse.org/v1/images/"


def find_openverse_image(query: str) -> dict | None:
    """Second source: Openverse, which aggregates Flickr CC and others.

    Commons is thin on Bangladesh news photography. Openverse is queried only
    for licences that allow commercial use and modification, so everything it
    returns is genuinely reusable with attribution — which is the difference
    between crediting a photographer and republishing an agency's copyright.
    """
    if not query.strip():
        return None
    params = {
        "q": query, "license_type": "commercial,modification",
        "page_size": "12", "mature": "false",
    }
    url = OPENVERSE_API + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers=COMMONS_UA)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except Exception as exc:
        log(f"    openverse search failed: {str(exc)[:70]}")
        return None

    stop = {"the", "of", "in", "at", "a", "and", "bangladesh", "building", "photo"}
    role_topic = {
        "cricketer": "cricket", "cricket": "cricket", "footballer": "football",
        "politician": "politic", "minister": "politic", "actor": "actor",
        "actress": "actress", "singer": "sing", "musician": "music",
    }
    words = re.findall(r"[a-z]+", query.lower())
    roles = [w for w in words if w in role_topic]
    topic = role_topic[roles[0]] if roles else ""
    wanted = [w for w in words
              if len(w) > 2 and w not in stop and w not in role_topic]

    for r in data.get("results", []):
        width, height = r.get("width") or 0, r.get("height") or 1
        if width < 800 or width / max(height, 1) > 2.2:
            continue
        title = (r.get("title") or "").lower()
        tags = " ".join(t.get("name", "") for t in (r.get("tags") or [])).lower()
        if wanted and not all(w in title or w in tags for w in wanted):
            continue
        if topic and topic not in title and topic not in tags:
            continue
        thumb = r.get("url")
        if not thumb:
            continue
        licence = (r.get("license") or "").upper()
        # Openverse returns "by-sa"; the licence is named "CC BY-SA" and the
        # attribution has to state it correctly to actually satisfy the terms.
        if licence and not licence.startswith(("CC", "PDM")):
            licence = f"CC {licence}"
        licence = f"{licence} {r.get('license_version') or ''}".strip()
        creator = (r.get("creator") or "").strip()[:60]
        source = (r.get("source") or "openverse").title()
        return {
            "thumb": thumb,
            "credit": f"{creator}, {licence} — {source}" if creator
                      else f"{licence} — {source}",
        }
    return None


def attach_image(article: dict, query: str, of_subject: bool = False) -> None:
    """Download a representative photo and attach it with an honest label.

    Two different labels, because they are two different claims. A photo of
    the person the story is about is a ফাইল ছবি — genuinely them, just not
    from this event. A stand-in that merely illustrates the topic is a
    প্রতীকী ছবি. Calling a stand-in a file photo would imply we photographed
    something we did not.
    """
    query = query.strip()
    if not query:
        return
    found = find_commons_image(query)
    # Commons first — its category data is what makes same-name people safe to
    # tell apart. Openverse second, for the far larger pool of Flickr CC news
    # and location photography that Commons simply does not hold.
    if not found:
        time.sleep(0.5)
        found = find_openverse_image(query)
    # A narrow query ("Bangladesh Bank headquarters Motijheel") can miss where a
    # broader one hits, so fall back to the first two words before giving up.
    if not found:
        words = query.split()
        if len(words) > 2:
            time.sleep(1.0)
            found = find_commons_image(" ".join(words[:2]))
    if not found or not found["thumb"]:
        log(f"    no usable image for: {query[:44]}")
        return
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    dest = COVERS_DIR / f"{article['slug']}.jpg"
    try:
        req = urllib.request.Request(found["thumb"], headers=COMMONS_UA)
        with urllib.request.urlopen(req, timeout=40) as img:
            payload = img.read()
        if len(payload) < 15_000:  # too small to be a usable cover
            return
        dest.write_bytes(payload)
    except Exception as exc:
        log(f"    image download failed: {str(exc)[:70]}")
        return

    label = "ফাইল ছবি" if of_subject else "প্রতীকী ছবি"
    article["image"] = {
        "url": f"/covers/{article['slug']}.jpg",
        "alt": f"{query} — {label}",
        "credit": found["credit"],
        "illustrative": not of_subject,
    }
    log(f"    ✽ image: {query} ({len(payload) // 1024} KB)")


def attach_second_portrait(article: dict, query: str, person: str) -> None:
    """The other face on a two-portrait card.

    Silent no-op on any failure: one portrait and a headline is a perfectly
    good card, while half a duo card is a broken one.
    """
    found = find_commons_image(query)
    if not found or not found["thumb"]:
        log(f"    no second portrait for: {query[:36]}")
        return
    dest = COVERS_DIR / f"{article['slug']}-2.jpg"
    try:
        req = urllib.request.Request(found["thumb"], headers=COMMONS_UA)
        with urllib.request.urlopen(req, timeout=40) as img:
            payload = img.read()
        if len(payload) < 15_000:
            return
        dest.write_bytes(payload)
    except Exception as exc:
        log(f"    second portrait failed: {str(exc)[:60]}")
        return
    article["image2"] = {
        "url": f"/covers/{article['slug']}-2.jpg",
        "alt": f"{query} — ফাইল ছবি",
        "credit": found["credit"],
        "illustrative": False,
        "person": person,
    }
    log(f"    ✽✽ second portrait: {query} ({len(payload) // 1024} KB)")


# ── Facebook ────────────────────────────────────────────────────────────
FB_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
FB_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN", "").strip().lstrip("﻿").strip()
FB_API = "https://graph.facebook.com/v21.0"
MAX_FB_POSTS = int(os.environ.get("MAX_FB_POSTS", "1"))
SITE_URL = "https://www.bdsitenews.com"

CATEGORY_TAGS = {
    "বাংলাদেশ": "#বাংলাদেশ", "রাজনীতি": "#রাজনীতি", "অপরাধ": "#অপরাধ",
    "খেলা": "#খেলা", "বিনোদন": "#বিনোদন", "অর্থনীতি": "#অর্থনীতি",
    "বিশ্ব": "#আন্তর্জাতিক", "প্রযুক্তি": "#প্রযুক্তি", "শিক্ষা": "#শিক্ষা",
    "প্রবাস": "#প্রবাস", "জেলা": "#জেলা", "ফ্যাক্ট চেক": "#ফ্যাক্টচেক",
    "ব্যাখ্যা": "#ব্যাখ্যা", "বিতর্ক": "#বিতর্ক", "ফুটবল": "#ফুটবল",
    "বিদেশে পড়াশোনা": "#বিদেশে_পড়াশোনা",
}


def article_url(article: dict) -> str:
    return f"{SITE_URL}/news/{article['slug']}"


def facebook_caption(article: dict, with_link: bool = True) -> str:
    """Headline, the lead, then the link — the shape that actually gets read
    in a Bangladeshi feed.

    with_link=False leaves the URL out so it can go in the first comment
    instead. Facebook demotes posts that send readers off the platform, and
    every Bangla news page works around it the same way — which is what
    "বিস্তারিত কমেন্টে" means on their cards.
    """
    url = article_url(article)
    tags = " ".join(
        t for t in ["#বিডিসাইটনিউজ", CATEGORY_TAGS.get(article["category"], "")] if t
    )
    lead = article["lead"].strip()
    if len(lead) > 280:
        lead = lead[:277].rsplit(" ", 1)[0] + "…"
    if article.get("factcheck"):
        prefix = "🔍 ফ্যাক্ট চেক\n\n"
    elif article["category"] == "বিতর্ক":
        prefix = "⚖ বিতর্ক\n\n"
    elif article.get("questions"):
        prefix = "🧠 ব্যাখ্যা\n\n"
    else:
        prefix = ""
    pointer = f"👉 বিস্তারিত: {url}" if with_link else "👇 বিস্তারিত কমেন্টে"
    return f"{prefix}{article['title']}\n\n{lead}\n\n{pointer}\n\n{tags}"


CRLF = "\r\n"


def _fb_error(raw: str) -> str:
    try:
        err = json.loads(raw).get("error", {})
        code = err.get("code", "?")
        return f"code {code}: " + " ".join(err.get("message", "").split())[:250]
    except json.JSONDecodeError:
        return raw[:220]


def _fb_post(path: str, fields: dict, file: Path | None = None) -> dict | None:
    """One Graph API POST — form-encoded, or multipart when sending a file."""
    payload = {**fields, "access_token": FB_TOKEN}
    if file is None:
        data = urllib.parse.urlencode(payload).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
    else:
        boundary = "----bdsitenews" + uuid.uuid4().hex
        chunks: list[bytes] = []
        for name, value in payload.items():
            chunks.append(
                ("--" + boundary + CRLF
                 + 'Content-Disposition: form-data; name="' + name + '"'
                 + CRLF + CRLF + str(value) + CRLF).encode()
            )
        chunks.append(
            ("--" + boundary + CRLF
             + 'Content-Disposition: form-data; name="source"; filename="'
             + file.name + '"' + CRLF
             + "Content-Type: image/jpeg" + CRLF + CRLF).encode()
        )
        chunks.append(file.read_bytes())
        chunks.append((CRLF + "--" + boundary + "--" + CRLF).encode())
        data = b"".join(chunks)
        headers = {"Content-Type": "multipart/form-data; boundary=" + boundary}

    req = urllib.request.Request(f"{FB_API}/{path}", data=data, method="POST",
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        log(f"    ! facebook {path}: {_fb_error(exc.read().decode('utf-8', 'ignore'))}")
    except Exception as exc:
        log(f"    ! facebook {path} failed: {str(exc)[:140]}")
    return None


def post_photocard_to_facebook(article: dict, card: Path) -> bool:
    """Publish the card as its own feed post, with the link in a comment.

    Two choices, both learned from what the Page actually looked like:

    The photo is uploaded UNPUBLISHED and then attached to a feed post rather
    than posted straight to /photos. Photos posted directly join the Page's
    album, and Facebook merges those into one "added N new photos" story —
    fifty posts were showing on the Page as a single item.

    The link goes in the first comment, not the caption. Facebook demotes
    posts that send readers off the platform.
    """
    photo = _fb_post(f"{FB_PAGE_ID}/photos", {"published": "false"}, file=card)
    if not photo or not photo.get("id"):
        return False

    post = _fb_post(f"{FB_PAGE_ID}/feed", {
        "message": facebook_caption(article, with_link=False),
        "attached_media[0]": json.dumps({"media_fbid": photo["id"]}),
    })
    if not post or not post.get("id"):
        return False
    log(f"    🖼 posted: {post['id']}")

    url = article_url(article)
    if _fb_post(f"{post['id']}/comments", {"message": f"বিস্তারিত পড়ুন 👇\n{url}"}):
        log("    💬 link added as the first comment")
        return True

    # Commenting needs pages_manage_engagement, which may not be granted.
    # Never leave a post with no route to the story: put the link back into
    # the caption rather than publish a dead end.
    log("    ! could not comment — restoring the link to the caption")
    _fb_post(post["id"], {"message": facebook_caption(article, with_link=True)})
    return True


def post_to_facebook(article: dict) -> bool:
    """Publish one article to the Page as a link post (link posts are what
    drive readers back to the site; photo posts keep them on Facebook)."""
    payload = urllib.parse.urlencode(
        {
            "message": facebook_caption(article),
            "link": f"{SITE_URL}/news/{article['slug']}",
            "access_token": FB_TOKEN,
        }
    ).encode()
    req = urllib.request.Request(
        f"{FB_API}/{FB_PAGE_ID}/feed", data=payload, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.load(resp)
        log(f"    📘 posted: {body.get('id', 'ok')}")
        return True
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "ignore")
        # Facebook's message opens with boilerplate and names the missing
        # permission at the very end, so a short truncation hides the cause.
        try:
            error = json.loads(raw).get("error", {})
            detail = " ".join(error.get("message", raw).split())
            code = error.get("code", "?")
            log(f"    ! facebook rejected the post (code {code}): {detail[:400]}")
        except json.JSONDecodeError:
            log(f"    ! facebook rejected the post: {raw[:300]}")
    except Exception as exc:
        log(f"    ! facebook post failed: {str(exc)[:120]}")
    return False


def share_new_articles(written: list[dict], cards: dict | None = None) -> None:
    """Share this run's articles, newest-first, capped so the page never
    gets flooded. Marks each one so it is never posted twice."""
    if not (FB_PAGE_ID and FB_TOKEN):
        log("  facebook not configured — skipping (set FACEBOOK_PAGE_ID/TOKEN)")
        return
    cards = cards or {}
    posted = 0
    failures = 0
    for article in written:
        if posted >= MAX_FB_POSTS:
            break
        if article.get("sharedToFacebook"):
            continue
        card = cards.get(article["slug"])
        # Photocard when we managed to render one, link post otherwise — a
        # failed card must never cost us the post entirely.
        sent = (post_photocard_to_facebook(article, card) if card
                else post_to_facebook(article))
        if sent:
            article["sharedToFacebook"] = True
            posted += 1
            failures = 0
            # Wide spacing when more than one is allowed: posts made
            # close together are merged into one aggregated story.
            time.sleep(90)
        else:
            failures += 1
            # A bad token fails identically every time. Retrying it once per
            # article just repeats the same rejection at Meta, which reads as
            # abuse; stop and let the log say why.
            if failures >= 2:
                log("  facebook: giving up after 2 consecutive rejections "
                    "— check the page token's permissions")
                break
    log(f"  facebook: {posted} post(s) published")


def biggest_story(items: list[dict], min_sources: int = 3) -> list[dict]:
    """Cluster the day's items and return the one covered by the most
    independent outlets. Breadth of coverage is the honest signal for
    'biggest story' — and it also gives the explainer enough facts to work
    from, which a single snippet never does."""
    clusters: list[list[dict]] = []
    for item in items:
        for cluster in clusters:
            if _same_story(item["title"], cluster[0]["title"]):
                cluster.append(item)
                break
        else:
            clusters.append([item])

    def distinct_sources(cluster: list[dict]) -> int:
        return len({c["source"] for c in cluster})

    clusters.sort(key=distinct_sources, reverse=True)
    if not clusters or distinct_sources(clusters[0]) < min_sources:
        return []
    return clusters[0]


def parse_draft(message, label: str) -> dict | None:
    """Read a model reply as JSON, or skip this piece and let the run continue.

    Bangla costs many tokens per character, so a long answer can hit the token
    ceiling and come back as truncated JSON. One unusable draft must never
    discard the articles already written earlier in the same run.
    """
    if getattr(message, "stop_reason", None) == "max_tokens":
        log(f"  ! {label}: reply hit the token limit and was cut off — skipped")
        return None
    text = next((b.text for b in message.content if b.type == "text"), None)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        log(f"  ! {label}: malformed JSON reply — skipped ({exc})")
        return None


def already_explained_today(articles: list[dict]) -> bool:
    today = datetime.now(timezone(timedelta(hours=6))).date().isoformat()
    return any(
        a.get("category") == "ব্যাখ্যা" and a.get("publishedAt", "").startswith(today)
        for a in articles
    )


def write_explainer(client, cluster: list[dict]) -> dict | None:
    """One explainer built from every outlet covering the same story."""
    reports = [
        {"outlet": c["source"], "headline": c["title"], "summary": c["summary"][:400]}
        for c in cluster[:8]
    ]
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=EXPLAINER_PROMPT,
            messages=[
                {"role": "user", "content": json.dumps({"reports": reports},
                                                       ensure_ascii=False)}
            ],
            output_config={"format": {"type": "json_schema",
                                      "schema": EXPLAINER_SCHEMA}},
        )
    except Exception as exc:
        log(f"  ! explainer failed: {str(exc)[:140]}")
        return None

    draft = parse_draft(message, "explainer")
    if not draft:
        return None

    usage = message.usage
    cost = (usage.input_tokens * 3 + usage.output_tokens * 15) / 1_000_000
    log(
        f"  ★ ব্যাখ্যা: {draft['title'][:44]}… "
        f"({len(cluster)} sources, ~${cost:.4f})"
    )

    seen_urls: set[str] = set()
    sources = []
    for c in cluster[:6]:
        if c["url"] in seen_urls:
            continue
        seen_urls.add(c["url"])
        sources.append({"name": c["source"], "url": c["url"]})

    return {
        "slug": slugify("ব্যাখ্যা " + draft["title"], cluster[0]["url"], "ব্যাখ্যা"),
        "title": draft["title"],
        "category": "ব্যাখ্যা",
        "topic": draft.get("category", ""),
        "lead": draft["lead"],
        "body": [],
        "questions": [
            {"question": q["question"], "answer": [p for p in q["answer"] if p.strip()]}
            for q in draft["questions"]
            if q.get("question")
        ],
        "sources": sources,
        "publishedAt": datetime.now(timezone(timedelta(hours=6))).isoformat(
            timespec="seconds"
        ),
    }


def already_debated_today(articles: list[dict]) -> bool:
    today = datetime.now(timezone(timedelta(hours=6))).date().isoformat()
    return any(
        a.get("category") == "বিতর্ক" and a.get("publishedAt", "").startswith(today)
        for a in articles
    )


def write_debate(client, cluster: list[dict]) -> dict | None:
    """A both-sides piece — but only when the sources actually disagree.

    The model is asked to judge that first and may decline, which is the whole
    point of the desk: manufactured controversy is what destroys a news site's
    credibility, and it is also what gets a Page throttled.
    """
    reports = [
        {"outlet": c["source"], "headline": c["title"], "summary": c["summary"][:400]}
        for c in cluster[:8]
    ]
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=DEBATE_PROMPT,
            messages=[
                {"role": "user", "content": json.dumps({"reports": reports},
                                                       ensure_ascii=False)}
            ],
            output_config={"format": {"type": "json_schema",
                                      "schema": DEBATE_SCHEMA}},
        )
    except Exception as exc:
        log(f"  ! debate failed: {str(exc)[:140]}")
        return None

    draft = parse_draft(message, "debate")
    if not draft:
        return None

    if not draft.get("has_real_disagreement"):
        log("  no genuine disagreement in today's coverage — no বিতর্ক piece")
        return None

    usage = message.usage
    cost = (usage.input_tokens * 3 + usage.output_tokens * 15) / 1_000_000
    log(f"  ⚖ বিতর্ক: {draft['title'][:44]}… ({len(cluster)} sources, ~${cost:.4f})")

    seen_urls: set[str] = set()
    sources = []
    for c in cluster[:6]:
        if c["url"] in seen_urls:
            continue
        seen_urls.add(c["url"])
        sources.append({"name": c["source"], "url": c["url"]})

    def clean(lines) -> list[str]:
        return [p.strip() for p in (lines or []) if p and p.strip()]

    # Rendered as Q&A blocks so the debate reuses the explainer layout that
    # already exists on the article page.
    questions = [
        {"question": draft["side_a_label"], "answer": clean(draft["side_a"])},
        {"question": draft["side_b_label"], "answer": clean(draft["side_b"])},
        {"question": "যা নিয়ে বিতর্ক নেই", "answer": clean(draft["settled"])},
        {"question": "যে প্রশ্নের উত্তর এখনো মেলেনি",
         "answer": clean([draft["open_question"]])},
    ]
    questions = [q for q in questions if q["question"] and q["answer"]]
    if len(questions) < 3:
        log("  ! debate draft was too thin to publish")
        return None

    return {
        "slug": slugify("বিতর্ক " + draft["title"], cluster[0]["url"], "বিতর্ক"),
        "title": draft["title"],
        "category": "বিতর্ক",
        "lead": draft["lead"],
        "body": [],
        "questions": questions,
        "sources": sources,
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

    # One explainer a day, on whichever story the most outlets are covering.
    if not already_explained_today(articles):
        cluster = biggest_story(items)
        if cluster:
            explainer = write_explainer(client, cluster)
            if explainer:
                written.insert(0, explainer)
        else:
            log("  no story has broad enough coverage for an explainer today")

    # One বিতর্ক piece a day, and only where the sources genuinely conflict.
    if not already_debated_today(articles):
        cluster = biggest_story(items, min_sources=4)
        if cluster:
            debate = write_debate(client, cluster)
            if debate:
                written.insert(0, debate)

    if not written:
        log("  no articles produced")
        return 0

    # Save before sharing: the articles are already paid for, so a failure in
    # Facebook posting must not throw away the run's work.
    articles = written + articles
    save_json(ARTICLES_PATH, articles[:MAX_ARTICLES_KEPT])
    log(f"\n✓ published {len(written)} new Bangla article(s); {len(articles[:MAX_ARTICLES_KEPT])} total on site")

    log("\n[4/4] sharing to Facebook…")
    cards = render_cards(written[:MAX_FB_POSTS], log=log)
    share_new_articles(written, cards)

    # Sharing stamps sharedToFacebook on the articles it posted, so the file
    # has to be written again for that mark to survive to the next run.
    save_json(ARTICLES_PATH, articles[:MAX_ARTICLES_KEPT])
    return 0


if __name__ == "__main__":
    sys.exit(main())
