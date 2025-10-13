#!/usr/bin/env python3
# rss_x.xml (all) + rss_x_live.xml (latest 1), X-safe truncation (no hashtags)

import xml.etree.ElementTree as ET, re, hashlib, html, sys, os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

IN_FEED="rss.xml"
OUT_ALL="rss_x.xml"
OUT_LIVE="rss_x_live.xml"

RESERVED_PREFIX=""          # nothing before
RESERVED_SUFFIX=""          # removed hashtag suffix for X
BASE_LIMIT=280

STAMP_RE=re.compile(r"""(?isx)\s*(?:—|–|-|\||:)?\s*(?:\(|\[)?\s*(?:\d{4}[-/]\d{2}[-/]\d{2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)?)?(?:\s?[A-Z]{2,4})?|\d{1,2}/\d{1,2}/\d{2,4})\s*(?:\)|\])?\s*$""")
HASHTAG_RE = re.compile(r"(?<!\w)#[A-Za-z0-9_]+")  # strip hashtags

def strip_stamp(s): 
    return STAMP_RE.sub("", s or "").strip()

def strip_hashtags(s):
    s = HASHTAG_RE.sub("", s or "")
    return re.sub(r"\s{2,}", " ", s).strip()

def collapse_ws(s):
    s=re.sub(r"<[^>]+>","",s or "")
    s=(s.replace("&nbsp;"," ").replace("&mdash;","—").replace("&#8212;","—").replace("&ndash;","–").replace("&#8211;","–"))
    s=html.unescape(s)
    return re.sub(r"\s+"," ",s).strip()

ZWJ="\u200d"
def is_vs(ch):      o=ord(ch); return 0xFE0E <= o <= 0xFE0F
def is_skin(ch):    o=ord(ch); return 0x1F3FB <= o <= 0x1F3FF
def is_regional(ch):o=ord(ch); return 0x1F1E6 <= o <= 0x1F1FF
def is_keycap(ch):  return ord(ch)==0x20E3

def emoji_safe_truncate(text, limit):
    if limit<=0: return ""
    if len(text)<=limit: return text
    cut=max(0,limit-1); s=text[:cut]
    def unsafe_tail(chrs): 
        return chrs.endswith(ZWJ) or (chrs and (is_vs(chrs[-1]) or is_skin(chrs[-1]) or is_keycap(chrs[-1]) or is_regional(chrs[-1])))
    while s and unsafe_tail(s): s=s[:-1]
    if " " in s: s=s.rsplit(" ",1)[0]
    return s+"…"

def smart_text(body):
    # remove any hashtags from body, then truncate with reserved space
    body = strip_hashtags(body)
    reserve=len(RESERVED_PREFIX)+len(RESERVED_SUFFIX)
    txt=emoji_safe_truncate(body, max(0,BASE_LIMIT-reserve))
    if RESERVED_PREFIX: txt=f"{RESERVED_PREFIX}{txt}"
    if RESERVED_SUFFIX: txt=f"{txt}{RESERVED_SUFFIX}"
    if len(txt)>BASE_LIMIT: txt=emoji_safe_truncate(txt, BASE_LIMIT)
    return txt

def load_items():
    if not os.path.exists(IN_FEED): 
        print("rss.xml not found", file=sys.stderr); sys.exit(1)
    t=ET.parse(IN_FEED); ch=t.getroot().find("channel"); items=[]
    for it in ch.findall("item"):
        pub=it.findtext("pubDate") or ""
        try:
            dt=parsedate_to_datetime(pub); 
            dt=dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except:
            dt=datetime.min.replace(tzinfo=timezone.utc)
        items.append((dt,it))
    items.sort(key=lambda x:x[0], reverse=True)
    return [i for _,i in items], ch

def transform(src_items):
    out=[]
    for it in src_items:
        title=strip_stamp(collapse_ws(it.findtext("title") or ""))
        desc =strip_stamp(collapse_ws(it.findtext("description") or ""))
        link=(it.findtext("link") or "").strip()
        body=title or desc
        text=smart_text(body)
        n=ET.Element("item")
        ET.SubElement(n,"title").text=text
        ET.SubElement(n,"description").text=text
        ET.SubElement(n,"link").text=link
        base=(it.findtext("guid") or link or title or desc).encode("utf-8","ignore")
        ET.SubElement(n,"guid",attrib={"isPermaLink":"false"}).text=hashlib.sha1(base).hexdigest()
        pub=it.findtext("pubDate")
        if pub: ET.SubElement(n,"pubDate").text=pub
        out.append(n)
    return out

def write_feed(path, ch_src, items):
    root=ET.Element("rss",attrib={"version":"2.0"})
    ch=ET.SubElement(root,"channel")
    for tag in ["title","link","description","language","lastBuildDate","pubDate"]:
        src=ch_src.find(tag)
        if src is not None:
            val=(src.text or "")
            if tag=="title": val=(val or "RSS")+" (X)"
            ET.SubElement(ch,tag).text=val
    for it in items: ch.append(it)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    print("Wrote", path)

all_src, ch = load_items()
all_x = transform(all_src)
write_feed(OUT_ALL, ch, all_x)
write_feed(OUT_LIVE, ch, all_x[:1])
