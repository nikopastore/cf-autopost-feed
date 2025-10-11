# scripts/make_x_feed.py
import xml.etree.ElementTree as ET
import re, hashlib, html, sys, os

IN_FEED = "rss.xml"        # your existing feed, already generated upstream
OUT_FEED = "rss_x.xml"     # new, X-only feed
MAX_BODY = 240             # leave room for tools that auto-append links/UTMs
APPEND_LINK_IN_TEXT = False  # set True if your tool does NOT auto-attach <link>

STAMP_PATTERNS = [
    r"\s*[—\-|]\s*\d{4}-\d{2}-\d{2}.*$",     # " — 2025-10-11 13:45"
    r"\s*\[\d{4}-\d{2}-\d{2}.*?\]\s*$",      # " [2025-10-11 13:45]"
]

def strip_stamp(s: str) -> str:
    for pat in STAMP_PATTERNS:
        s = re.sub(pat, "", s).strip()
    return s

def clean_text(s: str) -> str:
    # remove HTML tags and unescape entities
    s = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(s).strip()

def smart_truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    cut = max(0, limit - 1)  # space for ellipsis
    s = s[:cut]
    # don't chop mid-word if we can help it
    if " " in s:
        s = s.rsplit(" ", 1)[0]
    return s + "…"

if not os.path.exists(IN_FEED):
    print(f"Input feed '{IN_FEED}' not found.", file=sys.stderr)
    sys.exit(1)

tree = ET.parse(IN_FEED)
root = tree.getroot()
channel = root.find("channel")

# new RSS root
new_root = ET.Element("rss", attrib={"version": "2.0"})
new_channel = ET.SubElement(new_root, "channel")

# copy channel metadata (lightly adjusted title)
for tag in ["title", "link", "description", "language", "lastBuildDate", "pubDate"]:
    src = channel.find(tag)
    if src is not None:
        val = (src.text or "")
        if tag == "title":
            val = val.replace("RSS", "RSS (X)")
        ET.SubElement(new_channel, tag).text = val

# transform items
for item in channel.findall("item"):
    title = strip_stamp(clean_text(item.findtext("title") or ""))
    desc  = strip_stamp(clean_text(item.findtext("description") or ""))
    link  = (item.findtext("link") or "").strip()

    # choose base body (prefer title)
    body = title if title else desc

    # optionally append the link into the text (if your poster doesn't auto-attach it)
    reserve = 0
    if APPEND_LINK_IN_TEXT and link:
        # t.co wraps to ~23 chars; be conservative and reserve 25
        reserve = 25

    text = smart_truncate(body, MAX_BODY - reserve)
    if APPEND_LINK_IN_TEXT and link:
        text = f"{text} {link}"

    nitem = ET.SubElement(new_channel, "item")
    ET.SubElement(nitem, "title").text = text
    ET.SubElement(nitem, "description").text = text
    ET.SubElement(nitem, "link").text = link

    # stable GUID so we don't need timestamps in titles
    orig_guid = item.findtext("guid") or ""
    base = (orig_guid or link or title or desc).encode("utf-8", errors="ignore")
    guid = hashlib.sha1(base).hexdigest()
    ET.SubElement(nitem, "guid", attrib={"isPermaLink": "false"}).text = guid

    pub = item.findtext("pubDate")
    if pub:
        ET.SubElement(nitem, "pubDate").text = pub

# write out the new feed
ET.ElementTree(new_root).write(OUT_FEED, encoding="utf-8", xml_declaration=True)
print(f"Wrote {OUT_FEED}")
