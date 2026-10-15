#!/usr/bin/env python3
"""Download the DMCC RSS feed and write it to news.json (run by GitHub Actions)."""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

RSS_URL = "https://dmcc.ae/latest-news/rss.xml"
OUT_FILE = "news.json"
MAX_ITEMS = 10
PREVIEW_CHARS = 340


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; dmcc-news-feed/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def first_image(s):
    m = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", s or "", re.I)
    return m.group(1) if m else ""


def main():
    root = ET.fromstring(fetch(RSS_URL))
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        raw_desc = it.findtext("description") or ""
        # The feed escapes its HTML (&lt;div&gt;...), ElementTree already unescapes once.
        text = strip_html(raw_desc)
        if len(text) > PREVIEW_CHARS:
            text = text[:PREVIEW_CHARS].rstrip() + "…"
        pub = it.findtext("pubDate") or ""
        try:
            iso = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
        except Exception:
            iso = ""
        if title and link:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "date": iso,
                    "image": first_image(raw_desc),
                    "description": text,
                }
            )
    if not items:
        print("No items parsed from feed; leaving news.json untouched.", file=sys.stderr)
        sys.exit(1)

    out = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": RSS_URL,
        "items": items[:MAX_ITEMS],
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(out['items'])} items to {OUT_FILE}")


if __name__ == "__main__":
    main()
