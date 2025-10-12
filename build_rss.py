#!/usr/bin/env python3
"""
build_rss.py — Career Forge: self-contained posts

Creates/updates rss.xml by generating 1 new <item> per run:
- title  = X-ready, self-contained micro-post (contains the actual tactic/script; no "this/see below")
- description = richer version for LinkedIn/FB (bullets + CTA + tags)
- link   = stable GUID URL (optional to use in non-X platforms)

Env: OPENAI_API_KEY, BRAND, SITE_URL
"""

import os, re, json, hashlib, random
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

# ------------- Config -------------
MODEL = os.getenv("MODEL", "gpt-4o-mini")
BRAND = os.getenv("BRAND", "Career Forge")
SITE_URL = os.getenv("SITE_URL", "https://example.com/")
TOPICS_FILE   = "content/seeds_topics.txt"
FEED_FILE     = "rss.xml"
CHANNEL_TITLE = f"{BRAND} — Daily Career Post"
CHANNEL_DESC  = f"{BRAND} — actionable career tactics, AI shortcuts, and systems."
CHANNEL_LANG  = "en-us"
# ----------------------------------

def rss_now():
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

def read_topics(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            topics = [ln.strip() for ln in f if ln.strip()]
        return topics or ["AI resume rewrite tactics", "Interview frameworks that land offers"]
    except FileNotFoundError:
        return ["AI resume rewrite tactics", "Interview frameworks that land offers"]

def choose_topic(topics):
    seed = int(datetime.now(timezone.utc).strftime("%Y%m%d%H"))
    random.seed(seed)
    return random.choice(topics)

def slugify(text, n=60):
    text = re.sub(r"[^\w\s-]", "", (text or "")).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:n] or "post"

def call_openai(topic):
    # Robust call with fallback
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        sys_msg = {
            "role": "system",
            "content": (
                "You are a social-writing expert for a career-growth brand. "
                "Write clear, useful, non-cringe copy. Voice: confident, practical, kind."
            ),
        }
        user_msg = {
            "role": "user",
            "content": f"""
Return STRICT JSON with keys:

- x_line: a SINGLE self-contained line (<= 220 chars) that includes the actual tactic/script inline.
  * Must NOT say "this/see below/in thread".
  * Include the core script/template in quotes if useful, e.g.: You: "…"; Them: "…"; You: "…"
  * No hashtags. No links. No emojis.

- hook: concise hook (<= 80 chars) for richer networks (no emojis).
- bullets: 2–4 short lines (<= 65 chars each) with concrete steps/templates.
- cta: 1 question inviting replies with options (<= 110 chars). No emojis.
- tags: 2 short tags (<= 16 chars each, lowercase), without '#' (we'll add).

Topic: "{topic}"

Constraints:
- Be specific. Prefer numbers, scripts, mini-templates.
- Avoid generic advice. Avoid deictic language ("this/above/below").
Return ONLY JSON.
""",
        }
        resp = client.chat.completions.create(
            model=MODEL, temperature=0.6, messages=[sys_msg, user_msg]
        )
        txt = (resp.choices[0].message.content or "").strip()
        start, end = txt.find("{"), txt.rfind("}")
        payload = json.loads(txt[start:end+1])
    except Exception:
        payload = {
            "x_line": 'Salary talk? Try: You: "Based on scope & market, I’m targeting $X–$Y." Them: "Lower budget." You: "Is there flex on base, sign-on, or equity?"',
            "hook": "Salary negotiation that feels natural",
            "bullets": [
                "Open with scope + market data",
                "State a range you can defend",
                "Trade: base vs. sign-on vs. equity",
            ],
            "cta": "Which lever would you use first — base, sign-on, or equity?",
            "tags": ["careerforge", "jobsearch"],
        }
    return payload

def ensure_feed_scaffold():
    if not os.path.exists(FEED_FILE):
        rss = ET.Element("rss", attrib={"version": "2.0"})
        ch  = ET.SubElement(rss, "channel")
        ET.SubElement(ch, "title").text       = CHANNEL_TITLE
        ET.SubElement(ch, "link").text        = SITE_URL
        ET.SubElement(ch, "description").text = CHANNEL_DESC
        ET.SubElement(ch, "language").text    = CHANNEL_LANG
        now = rss_now()
        ET.SubElement(ch, "lastBuildDate").text = now
        ET.SubElement(ch, "pubDate").text       = now
        ET.ElementTree(rss).write(FEED_FILE, encoding="utf-8", xml_declaration=True)

    tree = ET.parse(FEED_FILE)
    root = tree.getroot()
    ch   = root.find("channel") or ET.SubElement(root, "channel")

    def ensure(tag, text=None):
        node = ch.find(tag)
        if node is None:
            node = ET.SubElement(ch, tag)
        if text is not None and (node.text or "").strip() == "":
            node.text = text
        return node

    ensure("title",       CHANNEL_TITLE)
    ensure("link",        SITE_URL)
    ensure("description", CHANNEL_DESC)
    ensure("language",    CHANNEL_LANG)
    ensure("lastBuildDate", rss_now())
    ensure("pubDate",       rss_now())

    tree.write(FEED_FILE, encoding="utf-8", xml_declaration=True)
    return tree

def make_item(payload):
    x_line  = (payload.get("x_line") or "").strip()
    hook    = (payload.get("hook") or "").strip()
    bullets = [b.strip(" •-") for b in (payload.get("bullets") or payload.get("value") or []) if b and b.strip()]
    cta     = (payload.get("cta") or "").strip()
    tags    = [t for t in (payload.get("tags") or []) if t][:2]

    # Title = the self-contained X line
    title = x_line

    # Description = richer body for LinkedIn/FB
    bullets_fmt = "\n".join([f"• {b}" for b in bullets])
    tag_str = " ".join([f"#{t}" for t in tags]) if tags else ""
    desc_parts = [hook] if hook else []
    if bullets_fmt: desc_parts += ["", bullets_fmt]
    if cta:         desc_parts += ["", cta]
    if tag_str:     desc_parts += ["", tag_str]
    description = "\n".join(desc_parts).strip()

    # Stable link & GUID
    now  = datetime.now(timezone.utc)
    base = f"{slugify(x_line)}-{now.strftime('%Y%m%d%H%M%S')}"
    guid = hashlib.sha1(base.encode("utf-8")).hexdigest()
    link = f"{SITE_URL}?p={guid}"

    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "link").text = link
    ET.SubElement(item, "guid", attrib={"isPermaLink": "false"}).text = guid
    ET.SubElement(item, "pubDate").text = rss_now()
    return item

def prepend_item(tree, item):
    ch = tree.getroot().find("channel") or ET.SubElement(tree.getroot(), "channel")
    items = ch.findall("item")
    if items:
        ch.insert(list(ch).index(items[0]), item)
    else:
        ch.append(item)
    # Update channel dates
    for tag in ("lastBuildDate", "pubDate"):
        node = ch.find(tag) or ET.SubElement(ch, tag)
        node.text = rss_now()
    tree.write(FEED_FILE, encoding="utf-8", xml_declaration=True)

def main():
    topics  = read_topics(TOPICS_FILE)
    topic   = choose_topic(topics)
    payload = call_openai(topic)
    tree    = ensure_feed_scaffold()
    item    = make_item(payload)
    prepend_item(tree, item)
    print("Generated new RSS item:", payload.get("x_line") or payload.get("hook"))

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
