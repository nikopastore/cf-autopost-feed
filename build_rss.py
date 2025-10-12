#!/usr/bin/env python3
"""
Career Forge — build_rss.py
Professional Social Media Manager mode with multi-style rotation.

Outputs per run:
- <title>: X-ready, self-contained, emoji-forward single line (no links, no hashtags, no dialogue markers)
- <description>: Richer copy for LinkedIn/FB (hook + bullets/checklist + CTA + 2 short tags)
- <category domain="style">...</category> and <category domain="cta">...</category>
- Stable GUID + link (no dead references in X; other networks may use link)

Env (required): OPENAI_API_KEY
Env (optional): BRAND, SITE_URL, MODEL (defaults to "gpt-5")
"""

import os, re, json, hashlib, random
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

# ---------------- Config ----------------
MODEL = os.getenv("MODEL", "gpt-5")  # try gpt-5 by default; script falls back if needed
BRAND = os.getenv("BRAND", "Career Forge")
SITE_URL = os.getenv("SITE_URL", "https://example.com/")

TOPICS_FILE   = "content/seeds_topics.txt"
FEED_FILE     = "rss.xml"
CHANNEL_TITLE = f"{BRAND} — Daily Career Post"
CHANNEL_DESC  = f"{BRAND} — actionable career tactics, AI shortcuts, and systems."
CHANNEL_LANG  = "en-us"
# ----------------------------------------

# Style catalog (rotation pool)
STYLE_CATALOG = [
    ("template_drop",    "Share a fill-in-the-blank template + 1 tiny example."),
    ("myth_vs_fact",     "Debunk 1 myth and replace with 1 fact + a quick how-to."),
    ("mistake_fix",      "Name 1 common mistake and show the concise fix."),
    ("checklist",        "Give a tight 4-item checklist for a narrow task."),
    ("data_bite",        "One stat/number, why it matters, and what to do."),
    ("challenge",        "Issue a 24–48h micro-challenge with clear steps."),
    ("hot_take",         "A contrarian but respectful take with 1 actionable tip."),
    ("caselet",          "A 1-sentence mini-case: role → action → result."),
    ("hook_lab",         "Provide 3 alternative hooks for the same idea."),
    ("swipe_headlines",  "Provide 3 headline angles anyone can reuse."),
]

EMOJI_PALETTE = ["✅","💬","📌","✍️","🚀","🧠","💼","⏱️","📈","🤝","🔎","📣","🗂️","🧩","🎯","⚡","🔥","🌟"]

FORBIDDEN_MARKERS_RX = re.compile(r"\b(You:|Them:|Q:|A:|in this thread|see below)\b", re.I)

def rss_now():
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

def read_topics(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            topics = [ln.strip() for ln in f if ln.strip()]
        return topics or ["Job search systems", "Interview frameworks", "Resume quant tactics"]
    except FileNotFoundError:
        return ["Job search systems", "Interview frameworks", "Resume quant tactics"]

def hour_slot_phoenix():
    # Lightweight slotting to vary styles by time of day
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("America/Phoenix"))
    return "am" if now.hour < 12 else "pm"

def choose_style():
    pool = STYLE_CATALOG[:]
    # Slightly different bias by slot to keep variety
    am_bias = {"checklist":2, "template_drop":2, "data_bite":1, "caselet":1}
    pm_bias = {"hot_take":2, "challenge":2, "myth_vs_fact":1, "swipe_headlines":1, "hook_lab":1}
    bias = am_bias if hour_slot_phoenix()=="am" else pm_bias
    weighted = []
    for key, desc in pool:
        w = 1 + bias.get(key, 0)
        weighted += [(key, desc)] * w
    random.seed(int(datetime.now(timezone.utc).strftime("%Y%m%d%H")))
    return random.choice(weighted)

def slugify(text, n=60):
    text = re.sub(r"[^\w\s-]", "", (text or "")).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:n] or "post"

def has_emoji(s: str) -> int:
    # Rough count of emoji-like chars
    return sum(1 for ch in s if ord(ch) >= 0x1F300 or ch in ("✍️","✅","⚡","🎯","🔥","🌟","📈","💼","🧠","📌","🤝","⏱️"))

def add_minimum_emojis(line: str, topic: str, need_min=2) -> str:
    count = has_emoji(line)
    if count >= need_min:
        return line
    # sprinkle from palette
    random.shuffle(EMOJI_PALETTE)
    needed = need_min - count
    if needed == 1:
        return f"{EMOJI_PALETTE[0]} {line}"
    else:
        return f"{EMOJI_PALETTE[0]} {line} {EMOJI_PALETTE[1]}"

def sanitize_xline(s: str) -> str:
    s = FORBIDDEN_MARKERS_RX.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    # No URLs or hashtags in X line (we append brand tag in X feed script)
    s = re.sub(r"https?://\S+", "", s).strip()
    s = re.sub(r"#[A-Za-z0-9_]+", "", s).strip()
    return s

def call_openai(topic, style_key, style_desc):
    """
    Ask the model for a self-contained X line + richer body WITH emojis,
    no dialogue markers, and explicit style.
    """
    payload = None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        sys_msg = {
            "role": "system",
            "content": (
                "You are a professional social media manager for a career brand. "
                "Your sole goal is growth via useful, engaging, on-brand posts. "
                "Write non-cringe, specific, action-first copy. Avoid dialogue markers like 'You:' or 'Them:'."
            ),
        }
        user_msg = {
            "role": "user",
            "content": f"""
STYLE: {style_key}
STYLE_DESC: {style_desc}
TOPIC_SEED: "{topic}"

Return STRICT JSON with keys:

- style: echo the chosen style id ("{style_key}")
- cta_type: one of ["question","pollish","challenge","tip"]
- x_line: a SINGLE, self-contained line (<= 230 chars), **no links**, **no hashtags**, **no dialogue markers**.
  Include 2–4 tasteful emojis woven into the text. Avoid "You:"/"Them:"/"Q:"/"A:" labels.
  The line must stand alone and deliver value (template, list with •, myth→fact, data bite, etc.).

- desc_title: concise hook (<= 80 chars) with 1–2 emojis for LinkedIn/FB.
- desc_points: 3–5 bullets, each <= 80 chars, with concrete steps/templates (allow 1 emoji each).
- desc_cta: 1 question inviting replies with options (<= 110 chars), may include 1 emoji.
- tags: 2 short tags (<= 16 chars each, lowercase, no '#').

Constraints:
- Be specific (numbers, templates, examples). No deictic language (“this thread”, “see below”).
- Keep x_line self-contained: no references to external docs or links.
Return ONLY JSON.
""",
        }

        # Try preferred model; if it fails, fallback to strong alternates.
        model_attempts = [MODEL, "gpt-4o", "gpt-4o-mini"]
        last_err = None
        for mdl in model_attempts:
            try:
                resp = client.chat.completions.create(
                    model=mdl, temperature=0.6, messages=[sys_msg, user_msg]
                )
                txt = (resp.choices[0].message.content or "").strip()
                start, end = txt.find("{"), txt.rfind("}")
                payload = json.loads(txt[start:end+1])
                break
            except Exception as e:
                last_err = e
        if payload is None:
            raise last_err or RuntimeError("No model succeeded")
    except Exception:
        # Fallback (still style-aware and emoji-forward)
        if style_key == "myth_vs_fact":
            payload = {
                "style": style_key,
                "cta_type": "question",
                "x_line": "Myth: ATS = keywords only. Fact: impact + context win. Try: role • action • metric • outcome. 📌✅",
                "desc_title": "ATS myth busted ✍️",
                "desc_points": [
                    "Lead with impact (numbers) 📈",
                    "Name the lever you pulled ⚙️",
                    "Add brief context (scope) 🧠",
                    "Finish with outcome ✅",
                ],
                "desc_cta": "What part do you skip most—numbers, context, or lever? 🤔",
                "tags": ["resume", "jobsearch"],
            }
        else:
            payload = {
                "style": style_key,
                "cta_type": "question",
                "x_line": "Template: “I did X to achieve Y, measured by Z%.” Swap in role, scope, and 1 metric. ✅📌",
                "desc_title": "Steal this bullet template ✍️",
                "desc_points": [
                    "Start with the action (X) ⚡",
                    "Name the outcome (Y) 🎯",
                    "Prove it with a number (Z%) 📈",
                    "Trim to 1 line, no fluff ✅",
                ],
                "desc_cta": "Drop a role; I’ll suggest a metric to use. 💬",
                "tags": ["resume", "careerforge"],
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

def make_item(payload, topic):
    style_key  = (payload.get("style") or "").strip().lower() or "unspecified"
    cta_type   = (payload.get("cta_type") or "").strip().lower() or "question"

    # X line: sanitize + ensure emojis + length safety (extra cap handled later in X feed script)
    x_line_raw = (payload.get("x_line") or "").strip()
    x_line = sanitize_xline(x_line_raw)
    x_line = add_minimum_emojis(x_line, topic, need_min=2)
    if len(x_line) > 230:
        x_line = x_line[:229].rsplit(" ", 1)[0] + "…"

    # Description (for LinkedIn/FB)
    hook     = (payload.get("desc_title") or "").strip()
    points   = [p.strip(" •-") for p in (payload.get("desc_points") or []) if p and p.strip()]
    cta      = (payload.get("desc_cta") or "").strip()
    tags_raw = [t for t in (payload.get("tags") or []) if t][:2]
    bullets_fmt = "\n".join([f"• {b}" for b in points])
    tag_str = " ".join([f"#{t}" for t in tags_raw]) if tags_raw else ""
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

    # Build item
    item = ET.Element("item")
    ET.SubElement(item, "title").text = x_line
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "link").text = link
    ET.SubElement(item, "guid", attrib={"isPermaLink": "false"}).text = guid
    ET.SubElement(item, "pubDate").text = rss_now()

    # Add categories for analytics
    cat_style = ET.SubElement(item, "category", attrib={"domain": "style"})
    cat_style.text = style_key
    cat_cta = ET.SubElement(item, "category", attrib={"domain": "cta"})
    cat_cta.text = cta_type

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
    # Choose topic & style
    topics  = read_topics(TOPICS_FILE)
    topic   = random.choice(topics)
    style_key, style_desc = choose_style()

    # Generate
    payload = call_openai(topic, style_key, style_desc)
    tree    = ensure_feed_scaffold()
    item    = make_item(payload, topic)
    prepend_item(tree, item)

    print("Generated:", (payload.get("x_line") or payload.get("desc_title")), "| style:", payload.get("style"), "| cta:", payload.get("cta_type"))

if __name__ == "__main__":
    main()
