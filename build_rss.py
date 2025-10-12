#!/usr/bin/env python3
"""
build_rss.py — Career Forge: meaningful, viral-ready posts

Creates/updates rss.xml by generating 1 new <item> per run:
- Title = crisp hook (X-friendly; our X feed will truncate if needed)
- Description = value-packed mini post + explicit CTA question
- Link = stable GUID-backed link to your SITE_URL (no extra pages needed)
Requires env: OPENAI_API_KEY, BRAND, SITE_URL
"""

import os, re, json, hashlib, random
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

# ----------------- Config -----------------
MODEL = os.getenv("MODEL", "gpt-4o-mini")
BRAND = os.getenv("BRAND", "Career Forge")
SITE_URL = os.getenv("SITE_URL", "https://example.com/")

TOPICS_FILE = "content/seeds_topics.txt"
FEED_FILE = "rss.xml"
CHANNEL_TITLE = f"{BRAND} — Daily Career Post"
CHANNEL_DESC = f"{BRAND} — actionable career tactics, AI shortcuts, and systems."
CHANNEL_LANG = "en-us"
# ------------------------------------------

def read_topics(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            topics = [ln.strip() for ln in f if ln.strip()]
        return topics
    except FileNotFoundError:
        return ["AI shortcuts for job search", "Interview frameworks that land offers"]

def choose_topic(topics):
    # deterministic daily pick so AM/PM runs can differ slightly
    day_seed = int(datetime.now(timezone.utc).strftime("%Y%m%d%H"))
    random.seed(day_seed)
    return random.choice(topics)

def slugify(text, n=60):
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:n] or "post"

def call_openai(topic):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    sys_msg = {
        "role": "system",
        "content": (
            "You are a social writing expert for a career-growth brand. "
            "Write scroll-stopping, useful, *non-cringe* copy. "
            "Voice: confident, clear, practical, kind. No fluff. "
            "Goal: trigger saves/comments by giving 1 valuable idea users can apply today."
        ),
    }
    user_msg = {
        "role": "user",
        "content": f"""
Produce STRICT JSON with keys:
- hook: a compelling 1-line hook (<= 130 chars), no emojis.
- value: 2–4 punchy bullets (max 65 chars each) with a micro-how-to.
- cta: 1 question that invites replies with concrete options (<= 110 chars).
- tags: 2 short hashtags (no more than 16 chars each, lowercase).

Topic: "{topic}"

Constraints:
- Be specific. Avoid generic advice.
- Use numbers, scripts, or mini-templates where possible.
- Do NOT repeat the topic text verbatim.
- No emojis, no ALL CAPS, no spammy hype.
Return ONLY JSON.
""",
    }
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.6,
        messages=[sys_msg, user_msg]
    )
    txt = resp.choices[0].message.content.strip()
    # Extract JSON robustly
    try:
        start = txt.find("{"); end = txt.rfind("}")
        payload = json.loads(txt[start:end+1])
    except Exception:
        # Fallback minimal payload
        payload = {
            "hook": f"{topic}: 3 tactics that actually work",
            "value": ["Cut fluff: show numbers.", "Use scripts, not wishes.", "Ship weekly proof of work."],
            "cta": "Which tactic would you try first — 1, 2, or 3?",
            "tags": ["careerforge", "jobsearch"]
        }
    return payload

def ensure_channel():
    if not os.path.exists(FEED_FILE):
        # create new RSS
        rss = ET.Element("rss", attrib={"version": "2.0"})
        ch = ET.SubElement(rss, "channel")
        ET.SubElement(ch, "title").text = CHANNEL_TITLE
        ET.SubElement(ch, "link").text = SITE_URL
        ET.SubElement(ch, "description").text = CHANNEL_DESC
        ET.SubElement(ch, "language").text = CHANNEL_LANG
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
        ET.SubElement(ch, "lastBuildDate").text = now
        ET.SubElement(ch, "pubDate").text = now
        ET.ElementTree(rss).write(FEED_FILE, encoding="utf-8", xml_declaration=True)

    tree = ET.parse(FEED_FILE)
    return tree

def make_item(payload, topic):
    hook = payload.get("hook", "").strip()
    bullets = [b.strip(" •-") for b in payload.get("value", []) if b.strip()]
    cta = payload.get("cta", "").strip()
    tags = payload.get("tags", [])[:2]

    # Title: hook + subtle benefit (keep X-friendly; our X feed truncates if needed)
    title = hook

    # Description: mini post with bullets + explicit CTA
    bullets_fmt = "\n".join([f"• {b}" for b in bullets])
    tag_str = " ".join([f"#{t}" for t in tags]) if tags else ""
    description = f"{hook}\n\n{bullets_fmt}\n\n{cta}"
    if tag_str:
        description += f"\n{tag_str}"

    # Stable link & GUID
    now = datetime.now(timezone.utc)
    slug = slugify(hook)
    base = f"{slug}-{now.strftime('%Y%m%d%H%M%S')}"
    guid = hashlib.sha1(base.encode("utf-8")).hexdigest()
    link = f"{SITE_URL}?p={guid}"

    item = ET.Element("item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "link").text = link
    ET.SubElement(item, "guid", attrib={"isPermaLink": "false"}).text = guid
    ET.SubElement(item, "pubDate").text = now.strftime("%a, %d %b %Y %H:%M:%S %z")
    return item

def prepend_item(tree, item):
    root = tree.getroot()
    ch = root.find("channel")
    # prepend as first item
    items = ch.findall("item")
    if items:
        ch.insert(list(ch).index(items[0]), item)
    else:
        ch.append(item)
    # update build date
    ch.find("lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    tree.write(FEED_FILE, encoding="utf-8", xml_declaration=True)

def main():
    topics = read_topics(TOPICS_FILE)
    topic = choose_topic(topics)
    payload = call_openai(topic)
    tree = ensure_channel()
    item = make_item(payload, topic)
    prepend_item(tree, item)
    print("Generated new RSS item:", payload.get("hook"))

if __name__ == "__main__":
    main()
