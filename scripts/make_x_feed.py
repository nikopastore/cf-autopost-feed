#!/usr/bin/env python3
# scripts/make_x_feed.py — builds two X feeds:
#  1) rss_x.xml       (all items, X-safe)
#  2) rss_x_live.xml  (ONLY the latest item, X-safe)  <-- point your Zap here

import xml.etree.ElementTree as ET
import re, hashlib, html, sys, os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# ================= CONFIG =================
IN_FEED = "rss.xml"
OUT_FEED_ALL = "rss_x.xml"
OUT_FEED_LIVE = "rss_x_live.xml"

# For X we post the line itself (no link in text).
APPEND_LINK_IN_TEXT = False
RESERVED_PREFIX = ""
RESERVED_SUFFIX = " #careerforge"     # short brand tag
BASE_LIMIT = 280
URL_RESERVE = 0                       # no link in text on X
# =========================================

STAMP_RE = re.compile(r"""(?isx)
    \s*
    (?:—|–|-|\||:)?\s*
    (?:\(|\[)?\s*
    (?:
       \d{4}[-/]\d{2}[-/]\d{2}
       (?:[ T]\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)?)?(?:\s?[A-Z]{2,4})?
     |
       \d{1,2}/\d{1,2}/\d{2,4}
    )
    \s*(?:\)|\])?
    \s*$
""")

def strip_stamp(s: str) -> str:
    return STAMP_RE.sub("", s or "").strip()

def collapse_ws(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    s = (s.replace("&nbsp;", " ")
           .replace("&mdash;", "—").replace("&#8212;", "—")
           .replace("&ndash;", "–").replace("&#8211;", "–"))
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# --- Emoji/glyph safe truncation ---
ZWJ = "\u200d"
def is_vs(ch):  # variation selectors
    o = ord(ch); return 0xFE0E <= o <= 0xFE0F
def is_skin(ch):
    o = ord(ch); return 0x1F3FB <= o <= 0x1F3FF
def is_regional(ch):
    o = ord(ch); return 0x1F1E6 <= o <= 0x1F1FF
def is_keycap(ch): return ord(ch) == 0x20E3

def emoji_safe_truncate(text: str, limit: int) -> str:
    if limit <= 0: return ""
    if len(text) <= limit: return text
    cut = max(0, limit - 1); s = text[:cut]
    def unsafe_tail(chrs):
        return chrs.endswith(ZWJ) or (chrs and (is_vs(chrs[-1]) or is_skin(chrs[-1]) or is_keycap(chrs[-1]) or is_regional(chrs[-1])))
    while s and unsafe_tail(s): s = s[:-1]
    if " " in s: s = s.rsplit(" ", 1)[0]
    return s + "…"
# -----------------------------------

def smart_text(body: str) -> str:
    reserve = URL_RESERVE + len(RESERVED_PREFIX) + len(RESERVED_SUFFIX)
    max_body = max(0, BASE_LIMIT - reserve)
    text = emoji_safe_truncate(body, max_body)
    if RESERVED_PREFIX: text = f"{RESERVED_PREFIX}{text}"
    if RESERVED_SUFFIX: text = f"{text}{RESERVED_SUFFIX}"
    if len(text) > BASE_LIMIT: text = emoji_safe_truncate(text, BASE_LIMIT)
    return text

def load_items():
    if not os.path.exists(IN_FEED):
        print(f"Input feed '{IN_FEED}' not found.", file=sys.stderr); sys.exit(1)
    t = ET.parse(IN_FEED); ch = t.getroot().find("channel")
    if ch is None: print("No <channel> found in rss.xml", file=sys.stderr); sys.exit(1)
    items = []
    for it in ch.findall("item"):
        pub = it.findtext("pubDate") or ""
        try:
            dt = parsedate_to_datetime(pub)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            dt = datetime.min.replace(tzinfo=timezone.utc)
        items.append((dt, it))
    # newest first
    items.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in items], ch

def transform_items(src_items):
    out_items = []
    for item in src_items:
        title = strip_stamp(collapse_ws(item.findtext("title") or ""))
        desc  = strip_stamp(collapse_ws(item.findtext("description") or ""))
        link  = (item.findtext("link") or "").strip()
        body = title if title else desc
        text = smart_text(body)

        nitem = ET.Element("item")
        ET.SubElement(nitem, "title").text = text
        ET.SubElement(nitem, "description").text = text
        ET.SubElement(nitem, "link").text = link

        orig_guid = item.findtext("guid") or ""
        base = (orig_guid or link or title or desc).encode("utf-8", errors="ignore")
        guid = hashlib.sha1(base).hexdigest()
        ET.SubElement(nitem, "guid", attrib={"isPermaLink": "false"}).text = guid

        pub = item.findtext("pubDate")
        if pub: ET.SubElement(nitem, "pubDate").text = pub
        out_items.append(nitem)
    return out_items

def write_feed(path, ch_src, items):
    new_root = ET.Element("rss", attrib={"version": "2.0"})
    new_channel = ET.SubElement(new_root, "channel")
    for tag in ["title", "link", "description", "language", "lastBuildDate", "pubDate"]:
        src = ch_src.find(tag)
        if src is not None:
            val = (src.text or "")
            if tag == "title": val = (val or "RSS") + " (X)"
            ET.SubElement(new_channel, tag).text = val
    for it in items: new_channel.append(it)
    ET.ElementTree(new_root).write(path, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {path}")

# --- main ---
all_src_items, src_channel = load_items()
all_x_items = transform_items(all_src_items)
latest_x_items = all_x_items[:1]  # ONLY the newest

write_feed(OUT_FEED_ALL, src_channel, all_x_items)
write_feed(OUT_FEED_LIVE, src_channel, latest_x_items)

