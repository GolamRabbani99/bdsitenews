#!/usr/bin/env python3
"""Ask Facebook what is actually on the Page.

The publisher records a post ID for every successful call, but a returned ID
only proves Facebook accepted the request — not that anyone can see the
result. This reads the Page back and reports what is really there.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://graph.facebook.com/v21.0"
PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN", "").strip().lstrip("﻿").strip()


def get(path: str, **params) -> dict:
    params["access_token"] = TOKEN
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=40) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "ignore")
        try:
            err = json.loads(raw).get("error", {})
            return {"__error": f"code {err.get('code')}: "
                               f"{' '.join(err.get('message', '').split())[:220]}"}
        except json.JSONDecodeError:
            return {"__error": raw[:220]}
    except Exception as exc:
        return {"__error": str(exc)[:180]}


def main() -> int:
    if not (PAGE_ID and TOKEN):
        print("FACEBOOK_PAGE_ID / FACEBOOK_PAGE_TOKEN not set")
        return 1

    print("── page ────────────────────────────────────")
    page = get(PAGE_ID, fields="name,fan_count,followers_count,is_published,"
                               "verification_status,link")
    for k, v in page.items():
        print(f"  {k}: {v}")

    # published_posts is what visitors see; feed also includes other stories.
    for edge in ("published_posts", "feed"):
        print(f"\n── {edge} ──────────────────────────────")
        data = get(f"{PAGE_ID}/{edge}",
                   fields="id,created_time,is_published,is_hidden,"
                          "is_expired,privacy,status_type,permalink_url",
                   limit="50")
        if "__error" in data:
            print(f"  ERROR {data['__error']}")
            continue
        posts = data.get("data", [])
        print(f"  returned: {len(posts)} post(s)")
        hidden = sum(1 for p in posts if p.get("is_hidden"))
        unpub = sum(1 for p in posts if p.get("is_published") is False)
        print(f"  hidden: {hidden}   not published: {unpub}")
        for p in posts[:8]:
            priv = (p.get("privacy") or {}).get("value", "?")
            print(f"    {p.get('created_time', '')[:16]}  "
                  f"published={p.get('is_published')}  hidden={p.get('is_hidden')}  "
                  f"privacy={priv}  {p.get('status_type', '')}")

    print("\n── token ───────────────────────────────────")
    me = get("me", fields="id,name")
    for k, v in me.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
