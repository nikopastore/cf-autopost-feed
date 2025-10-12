import xml.etree.ElementTree as ET
import re, hashlib, html, sys, os

# =================== CONFIG ===================
IN_FEED = "rss.xml"        # your existing feed at repo root
OUT_FEED = "rss_x.xml"     # new X-only feed at repo root

# If your X action/app attaches the URL separately (Buffer, or Zapier X action with a Link field),
# keep this False. If your action does NOT have a separate Link field, set True and we'll append
# the link into the post text (and reserve space for it).
APPEND_LINK_IN_TEXT = False

# If you ALWAYS add fixed text (prefix/hashtags) in your X post, put it here so we reserve space.
RESERVED_PREFIX = ""       # e.g., "CF: "
RESERVED_SUFFIX = " #careerforge"       # e.g., " #CareerForge"

BASE_LIMIT   = 280
URL_RESERVE  = 28  # ultra-safe t.co reserve (approx 23), covers any tool extras
# =================================================

STAMP_RE = re.compile(r"""(?isx)
    \s*
    (?:—|–|-|\||:)?\s*                 # optional separator
    (?:\(|\[)?\s*                      # optional open paren/bracket
    (?:
       \d{4}[-/]\d{2}[-/]\d{2}         # 2025-10-11 or 2025/10/11
       (?:[ T]\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)?)?(?:\s?[A-Z]{2,4})?  # optional time/TZ
     |
       \d{1,2}/\d{1,2}/\d{2,4}         # 10/11/2025
    )
    \s*(?:\)|\])?                      # optional close paren/bracket
    \s*$
""")

def strip_stamp(s: str) -> str:
    return STAMP_RE.sub("", s or "").strip()

def collapse_ws(s: str) -> str:
    """Strip HTML, normalize entities/dashes, collapse whitespace."""
    s = re.sub(r"<[^>]+>", "", s or "")
    s = (s.replace("&nbsp;", " ")
           .replace("&mdash;", "—").replace("&#8212;", "—")
           .replace("&ndash;", "–").replace("&#8211;", "–"))
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def smart_truncate(s: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(s) <= limit:
        return s
    cut = max(0, limit - 1)
    s = s[:cut]
    if " " in s:
        s = s.rsplit(" ", 1)[0]
    return s + "…"

if not os.path.exists(IN_FEED):
    print(f"Input feed '{IN_FEED}' not found.", file=sys.stderr)
    sys.exit(1)

tree = ET.parse(IN_FEED)
root = tree.getroot()
channel = root.find("channel")
if channel is None:
    print("No <channel> found in rss.xml", file=sys.stderr)
    sys.exit(1)

# New RSS root
new_root = ET.Element("rss", attrib={"version": "2.0"})
new_channel = ET.SubElement(new_root, "channel")

# Copy channel metadata (adjust title to indicate X feed)
for tag in ["title", "link", "description", "language", "lastBuildDate", "pubDate"]:
    src = channel.find(tag)
    if src is not None:
        val = (src.text or "")
        if tag == "title":
            val = (val or "RSS") + " (X)"
        ET.SubElement(new_channel, tag).text = val

# Transform items
for item in channel.findall("item"):
    # Clean content
    title = strip_stamp(collapse_ws(item.findtext("title") or ""))
    desc  = strip_stamp(collapse_ws(item.findtext("description") or ""))
    link  = (item.findtext("link") or "").strip()

    # Choose base body
    body = title if title else desc

    # Reserve space: URL + fixed prefix/suffix
    reserve = URL_RESERVE + len(RESERVED_PREFIX) + len(RESERVED_SUFFIX)
    max_body = max(0, BASE_LIMIT - reserve)

    # Build text
    text = smart_truncate(body, max_body)
    if RESERVED_PREFIX:
        text = f"{RESERVED_PREFIX}{text}"
    if RESERVED_SUFFIX:
        text = f"{text}{RESERVED_SUFFIX}"
    if APPEND_LINK_IN_TEXT and link:
        text = f"{text} {link}"

    # Final safety cap
    if len(text) > BASE_LIMIT:
        text = smart_truncate(text, BASE_LIMIT)

    # Build item
    nitem = ET.SubElement(new_channel, "item")
    ET.SubElement(nitem, "title").text = text        # short, clean post text
    ET.SubElement(nitem, "description").text = text  # mirror title for simplicity
    ET.SubElement(nitem, "link").text = link

    # Stable GUID (so no timestamps needed)
    orig_guid = item.findtext("guid") or ""
    base = (orig_guid or link or title or desc).encode("utf-8", errors="ignore")
    guid = hashlib.sha1(base).hexdigest()
    ET.SubElement(nitem, "guid", attrib={"isPermaLink": "false"}).text = guid

    pub = item.findtext("pubDate")
    if pub:
        ET.SubElement(nitem, "pubDate").text = pub

# Write the new feed
ET.ElementTree(new_root).write(OUT_FEED, encoding="utf-8", xml_declaration=True)
print(f"Wrote {OUT_FEED}")