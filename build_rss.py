import os, json, uuid, random, time
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from openai import OpenAI

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
BRAND = os.environ.get("BRAND", "Career Forge")
FEED_PATH = "rss.xml"
SITE_URL = os.environ.get("SITE_URL", "https://example.com")  # set to your Pages URL

SEED_TOPICS = [
    "emerging skills employers value in 2025",
    "AI’s impact on hiring and job design",
    "how to recession-proof your career",
    "negotiating remote-work benefits",
    "reskilling vs. upskilling",
    "leadership traits companies seek now",
    "navigating layoffs with resilience",
    "future of hybrid work",
    "career pivots after 40",
    "how Gen Z reshapes the workplace",
    "resume experiments: skills-first vs chronology",
    "ATS myths vs reality",
    "manager hiring: what’s changed post-2024",
    "portfolio careers and side gigs",
    "from IC to manager: signals of readiness",
]

def pick_topic():
    return random.choice(SEED_TOPICS)

def stamp(text: str) -> str:
    t = time.strftime("%Y%m%d-%H%M", time.gmtime())  # UTC stamp
    rnd = uuid.uuid4().hex[:4].upper()
    return f"{text.strip()} — CF {t}-{rnd}"

def generate_post(topic: str) -> tuple[str, str]:
    client = OpenAI(api_key=OPENAI_API_KEY)
    sys = f"You are {BRAND}'s senior social copywriter. Keep it nonpartisan, practical, optimistic."
    usr = (
        "Write ONE LinkedIn-friendly paragraph about: "
        f"{topic}. Length 70–120 words. End with a question inviting replies. "
        "Return ONLY valid JSON like: "
        '{"caption":"...","hashtags":["jobsearch","careeradvice","jobmarket"]}'
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        response_format={"type": "json_object"},
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        obj = json.loads(raw)
    except Exception:
        obj = {}
    caption = (obj.get("caption") or f"Quick take from {BRAND}: {topic}. What’s your take?").strip()
    tags = obj.get("hashtags", [])
    hashtags = " ".join("#" + str(t).lstrip("#").replace(" ", "") for t in tags if str(t).strip())
    return stamp(caption), hashtags

def load_feed():
    try:
        tree = ET.parse(FEED_PATH)
        return tree
    except Exception:
        root = ET.Element("rss", version="2.0")
        channel = ET.SubElement(root, "channel")
        ET.SubElement(channel, "title").text = f"{BRAND} Autopost Feed"
        ET.SubElement(channel, "link").text = SITE_URL
        ET.SubElement(channel, "description").text = "Auto-generated career content"
        return ET.ElementTree(root)

def add_item(tree: ET.ElementTree, title: str, description: str, guid: str):
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        channel = ET.SubElement(root, "channel")

    item = ET.Element("item")
    ET.SubElement(item, "title").text = title[:140]
    ET.SubElement(item, "link").text = SITE_URL
    ET.SubElement(item, "guid").text = guid
    ET.SubElement(item, "pubDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    ET.SubElement(item, "description").text = description

    # Prepend newest
    items = channel.findall("item")
    channel.insert(0, item)
    # Keep last 50
    for old in items[49:]:
        channel.remove(old)

def save_feed(tree: ET.ElementTree):
    tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    topic = pick_topic()
    caption, hashtags = generate_post(topic)
    text = caption + (" " + hashtags if hashtags else "")
    tree = load_feed()
    add_item(tree, title=topic, description=text, guid=str(uuid.uuid4()))
    save_feed(tree)
    print("Wrote rss.xml with new item:", topic)
