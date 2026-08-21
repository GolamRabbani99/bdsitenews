#!/usr/bin/env python3
"""Generate the ইংরেজি শিখুন course — once, into a queue.

    python scripts/make_lessons.py            # generate every missing lesson
    python scripts/make_lessons.py 5          # generate the next 5 only

Lessons go into src/data/lesson_queue.json. The daily publishing run moves
one lesson into the site per day and makes NO model call to do it, so the
course costs a few dollars once rather than a few dollars a month.

The curriculum is fixed and ordered on purpose. A learner needs lesson 3 to
make sense of lesson 7; a feed of unconnected grammar tips teaches nobody.
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
QUEUE = ROOT / "src" / "data" / "lesson_queue.json"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

# Ordered beginner course. Each entry: (topic in English, the Bangla title).
CURRICULUM: list[tuple[str, str]] = [
    ("The three parts of a basic sentence: subject + verb + object",
     "বাক্যের তিনটি অংশ: কে, কী করে, কাকে"),
    ("Am, is, are — when to use which",
     "am, is, are — কোনটি কখন বসবে"),
    ("Making simple present tense sentences",
     "সাধারণ বর্তমান কাল: প্রতিদিনের কাজ বোঝাতে"),
    ("Adding 's' to the verb: he goes, she works",
     "he/she/it-এর সঙ্গে verb-এ 's' কেন বসে"),
    ("Making sentences negative with 'not' and 'do not'",
     "না-বোধক বাক্য: not আর don't-এর ব্যবহার"),
    ("Asking simple questions: do, does, is, are",
     "প্রশ্ন করার সহজ নিয়ম: do, does, is, are"),
    ("Simple past tense: talking about yesterday",
     "সাধারণ অতীত কাল: গতকালের কথা বলা"),
    ("Irregular past verbs Bangladeshi learners use most",
     "যে অনিয়মিত past verb গুলো সবচেয়ে বেশি লাগে"),
    ("Future with 'will' and 'going to'",
     "ভবিষ্যতের কথা: will আর going to"),
    ("Present continuous: what is happening now",
     "এখন যা ঘটছে: present continuous"),
    ("A, an, the — the articles that Bangla does not have",
     "a, an, the — বাংলায় নেই যে শব্দগুলো"),
    ("Prepositions of place: in, on, at",
     "in, on, at — জায়গা বোঝাতে কোনটি"),
    ("Prepositions of time: in, on, at",
     "in, on, at — সময় বোঝাতে কোনটি"),
    ("This, that, these, those",
     "this, that, these, those — কোনটি কখন"),
    ("Countable and uncountable: much, many, some, any",
     "much, many, some, any — গোনা যায় আর যায় না"),
    ("Adjectives: where they go in an English sentence",
     "বিশেষণ ইংরেজি বাক্যে কোথায় বসে"),
    ("Comparing things: bigger, biggest, more, most",
     "তুলনা করা: bigger, biggest, more, most"),
    ("Can, could, should, must — asking and advising",
     "can, could, should, must — অনুমতি ও পরামর্শ"),
    ("Joining two ideas: and, but, because, so",
     "দুটি কথা জোড়া লাগানো: and, but, because, so"),
    ("Introducing yourself in English",
     "নিজের পরিচয় দেওয়া ইংরেজিতে"),
    ("Asking for directions and understanding the answer",
     "রাস্তা জিজ্ঞাসা করা ও উত্তর বোঝা"),
    ("Talking on the phone: the sentences you actually need",
     "ফোনে কথা বলা: যে বাক্যগুলো সত্যিই লাগে"),
    ("Writing a short formal email",
     "ছোট একটি আনুষ্ঠানিক ইমেইল লেখা"),
    ("Writing a job application in simple English",
     "সহজ ইংরেজিতে চাকরির আবেদন লেখা"),
    ("The mistakes Bangla speakers make most in English",
     "বাংলাভাষীরা ইংরেজিতে যে ভুলগুলো সবচেয়ে বেশি করেন"),
    ("Word order: why 'I rice eat' is wrong",
     "শব্দের ক্রম: 'I rice eat' কেন ভুল"),
    ("Talking about your family and your day",
     "পরিবার ও দৈনন্দিন রুটিন নিয়ে বলা"),
    ("Numbers, dates and prices in English",
     "সংখ্যা, তারিখ ও দাম ইংরেজিতে"),
    ("Polite English: please, sorry, excuse me, thank you",
     "ভদ্রভাবে বলা: please, sorry, excuse me"),
    ("Putting it together: holding a two-minute conversation",
     "সব মিলিয়ে: দুই মিনিটের কথোপকথন"),
]

LESSON_PROMPT = """You teach English to absolute beginners in Bangladesh, in
Bangla. Your reader finished school in Bangla medium, can read Bangla
comfortably, and freezes when asked to speak English.

Write ONE lesson on the topic given. It must work for BOTH speaking and
writing — every pattern you teach should be usable in a real conversation
and in a written sentence.

HOW TO TEACH:
- Explain in BANGLA. English appears only as the examples being taught.
- Give the pattern as a simple formula the reader can copy, e.g.
  "Subject + am/is/are + বাকি অংশ".
- Every English example gets its Bangla meaning. Every single one.
- Compare with Bangla where it helps: Bangla puts the verb last, English
  puts it in the middle. Naming the difference is what makes it stick.
- Warn about the specific mistake a Bangla speaker makes here. You know
  these: dropping articles, "I am agree", "he go", verb at the end.
- Never use grammar jargon without explaining it in Bangla first.

FIELDS:
- title: the Bangla title given to you, unchanged.
- intro: 2-3 sentences in Bangla — what this lesson lets the reader DO.
  Concrete: "এই পাঠ শেষে আপনি নিজের পরিচয় দিতে পারবেন", not "আপনি শিখবেন"।
- pattern: the formula, one line.
- pattern_explained: 2-4 short Bangla paragraphs explaining the pattern.
- examples: 6-8 objects, each {english, bangla, note}. `note` is a short
  Bangla remark where one helps, otherwise empty. Order them easy → harder.
- mistakes: 3-4 objects, each {wrong, right, why} — `wrong` and `right` are
  English sentences, `why` is the Bangla explanation.
- practice: 4-5 Bangla instructions telling the reader to build their own
  sentences. Give the answer pattern, not the answer.
- speaking_tip: one short Bangla paragraph on saying this out loud —
  rhythm, which word to stress, what learners get wrong when speaking.

Keep it SHORT enough to finish in five minutes. A beginner who finishes one
lesson comes back; one who abandons a long lesson does not."""

LESSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "intro": {"type": "string"},
        "pattern": {"type": "string"},
        "pattern_explained": {"type": "array", "items": {"type": "string"}},
        "examples": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "english": {"type": "string"},
                    "bangla": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["english", "bangla", "note"],
            },
        },
        "mistakes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "wrong": {"type": "string"},
                    "right": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["wrong", "right", "why"],
            },
        },
        "practice": {"type": "array", "items": {"type": "string"}},
        "speaking_tip": {"type": "string"},
    },
    "required": ["title", "intro", "pattern", "pattern_explained", "examples",
                 "mistakes", "practice", "speaking_tip"],
}

BN_TRANSLIT_HINT = re.compile(r"[a-z0-9-]+")


def log(msg: str) -> None:
    print(msg, flush=True)


def slug_for(index: int, topic_en: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", topic_en.lower()).strip("-")
    return f"english-{index:02d}-{'-'.join(base.split('-')[:6])}"


def load_queue() -> list[dict]:
    if QUEUE.exists():
        return json.loads(QUEUE.read_text(encoding="utf-8"))
    return []


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(CURRICULUM)
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip().lstrip("﻿").strip()
    if not key:
        log("ANTHROPIC_API_KEY is not set.")
        return 1

    import anthropic
    client = anthropic.Anthropic(api_key=key)

    queue = load_queue()
    have = {l["lessonNumber"] for l in queue}
    spent = 0.0
    made = 0

    for i, (topic_en, title_bn) in enumerate(CURRICULUM, 1):
        if i in have:
            continue
        if made >= limit:
            break
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=6000,
                system=LESSON_PROMPT,
                messages=[{"role": "user", "content": json.dumps(
                    {"lesson_number": i, "topic": topic_en,
                     "bangla_title": title_bn}, ensure_ascii=False)}],
                output_config={"format": {"type": "json_schema",
                                          "schema": LESSON_SCHEMA}},
            )
        except Exception as exc:
            log(f"  ! lesson {i} failed: {str(exc)[:140]}")
            break

        if getattr(message, "stop_reason", None) == "max_tokens":
            log(f"  ! lesson {i} hit the token limit — skipped")
            continue
        text = next((b.text for b in message.content if b.type == "text"), None)
        if not text:
            continue
        try:
            draft = json.loads(text)
        except json.JSONDecodeError as exc:
            log(f"  ! lesson {i} malformed: {exc}")
            continue

        usage = message.usage
        cost = (usage.input_tokens * 3 + usage.output_tokens * 15) / 1_000_000
        spent += cost
        made += 1

        queue.append({
            "lessonNumber": i,
            "slug": slug_for(i, topic_en),
            "title": f"ইংরেজি শিখুন {i}: {draft['title']}",
            "topicEn": topic_en,
            "intro": draft["intro"],
            "pattern": draft["pattern"],
            "patternExplained": [p for p in draft["pattern_explained"] if p.strip()],
            "examples": [e for e in draft["examples"] if e.get("english")],
            "mistakes": [m for m in draft["mistakes"] if m.get("wrong")],
            "practice": [p for p in draft["practice"] if p.strip()],
            "speakingTip": draft["speaking_tip"],
        })
        log(f"  ✓ lesson {i:>2}: {draft['title'][:52]} (~${cost:.4f})")

    queue.sort(key=lambda l: l["lessonNumber"])
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    log(f"\n{made} new lesson(s), ~${spent:.2f}. Queue holds {len(queue)} of "
        f"{len(CURRICULUM)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
