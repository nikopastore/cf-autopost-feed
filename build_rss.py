#!/usr/bin/env python3
"""
Career Forge — build_rss.py (Pro SMM + Pause + DupGuard + Bandit + Tags + Trends)

- Respects ops/config.json ("paused", dup_guard, model)
- Loads ops/rules.json to bias output (min emojis, forbid dialogue, %/$ requirement)
- Loads ops/bandit.json to weight style/cta choices (updated by analytics workflow)
- Enriches topics using content/seeds_topics.txt + content/trends.json
- Emits <category domain="style"> and <category domain="cta">
- Title = self-contained X line (no links/hashtags/dialogue labels, emoji-forward)
- Description = LI/FB richer copy (hook + bullets + CTA + 2 tags)

Env (required): OPENAI_API_KEY
Optional: BRAND, SITE_URL, MODEL
"""

import os, re, json, hashlib, random
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

# ---------- Paths ----------
CONFIG_PATH = "ops/config.json"
RULES_PATH  = "ops/rules.json"
BANDIT_PATH = "ops/bandit.json"
TAGS_PATH   = "content/tags.json"
TRENDS_PATH = "content/trends.json"
FPS_PATH    = "analytics/fingerprints.json"
TOPICS_FILE = "content/seeds_topics.txt"
FEED_FILE   = "rss.xml"

# ---------- Branding ----------
BRAND = os.getenv("BRAND", "Career Forge")
SITE_URL = os.getenv("SITE_URL", "https://example.com/")
CHANNEL_TITLE = f"{BRAND} — Daily Career Post"
CHANNEL_DESC  = f"{BRAND} — actionable career tactics, AI shortcuts, and systems."
CHANNEL_LANG  = "en-us"

# ---------- Style catalog ----------
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

# ---------- Helpers ----------
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def rss_now():
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

def read_topics(path):
    base = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            base = [ln.strip() for ln in f if ln.strip()]
    except FileNotFoundError:
        base = ["Job search systems", "Interview frameworks", "Resume quant tactics"]
    trends = load_json(TRENDS_PATH, {}).get("items", [])
    t_titles = [t.get("title","") for t in trends if t.get("title")] [:10]
    # preserve order, de-dup
    seen = set(); out=[]
    for t in base + t_titles:
        if t not in seen:
            out.append(t); seen.add(t)
    return out

def choose_style(weights):
    pool = []
    for key, desc in STYLE_CATALOG:
        w = max(0.01, float(weights.get(key, 1.0)))
        pool.append((key, desc, w))
    total = sum(w for _,_,w in pool)
    import random as _r
    r = _r.random() * total; c = 0.0
    for key, desc, w in pool:
        c += w
        if r <= c: return key, desc
    return pool[0][0], pool[0][1]

def slugify(text, n=60):
    text = re.sub(r"[^\w\s-]", "", (text or "")).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:n] or "post"

def has_emoji(s: str) -> int:
    return sum(1 for ch in s if ord(ch) >= 0x1F300 or ch in ("✍️","✅","⚡","🎯","🔥","🌟","📈","💼","🧠","📌","🤝","⏱️"))

def add_minimum_emojis(line: str, need_min=2) -> str:
    count = has_emoji(line)
    if count >= need_min: return line
    import random as _r; _r.shuffle(EMOJI_PALETTE)
    return f"{EMOJI_PALETTE[0]} {line}" if (need_min - count) == 1 else f"{EMOJI_PALETTE[0]} {line} {EMOJI_PALETTE[1]}"

def sanitize_xline(s: str) -> str:
    s = FORBIDDEN_MARKERS_RX.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"https?://\S+", "", s).strip()
    s = re.sub(r"#[A-Za-z0-9_]+", "", s).strip()
    return s

def ngrams(text, n=5):
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {" ".join(toks[i:i+n]) for i in range(0, max(0, len(toks)-n+1))}

def jaccard(a, b):
    if not a or not b: return 0.0
    inter = len(a & b); uni = len(a | b)
    return inter / uni if uni else 0.0

def dup_guard_ok(title, fps, n, thr):
    probe = ngrams(title, n)
    for fp in fps:
        if jaccard(probe, set(fp.get("ngrams", []))) >= thr:
            return False
    return True

# ---- NEW: robust tag coercion ----
def coerce_tag_list(obj):
    """
    Accepts list | dict | string | None and returns a clean list[str] (lowercased, unique, non-empty).
    - list: keep string items
    - dict: take string KEYS + any string values; also flatten list values
    - string: split on commas/whitespace
    """
    out = []
    if isinstance(obj, list):
        cand = obj
    elif isinstance(obj, dict):
        cand = list(obj.keys()) + list(obj.values())
    elif isinstance(obj, str):
        import re as _re
        cand = _re.split(r"[,\s]+", obj)
    else:
        cand = []
    for x in cand:
        if isinstance(x, str):
            s = x.strip().lower()
            if s: out.append(s)
        elif isinstance(x, list):
            for y in x:
                if isinstance(y, str):
                    s = y.strip().lower()
                    if s: out.append(s)
    # de-dup, preserve order
    seen=set(); clean=[]
    for s in out:
        if s not in seen:
            seen.add(s); clean.append(s)
    return clean

def call_openai(topic, style_key, style_desc, model, cta_bias=None, min_emojis=2, require_number=False):
    payload = None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        sys_msg = {"role":"system","content":
            "You are a professional social media manager for a career brand. Optimize for growth via useful, engaging, on-brand posts. Avoid dialogue markers like 'You:' or 'Them:'."}
        user_msg = {"role":"user","content":f"""
STYLE: {style_key}
STYLE_DESC: {style_desc}
TOPIC_SEED: "{topic}"
CTA_BIAS: {cta_bias or {}}
MIN_EMOJIS: {min_emojis}
REQUIRE_NUMBER_IN_TITLE: {require_number}

Return STRICT JSON with keys:
- style: string (echo style id)
- cta_type: one of ["question","pollish","challenge","tip"]
- x_line: SINGLE, self-contained line (<= 230 chars), no links/hashtags/dialogue labels; include {min_emojis}–4 tasteful emojis; be specific; if REQUIRE_NUMBER_IN_TITLE=true, include a % or $.
- desc_title: concise hook (<= 80 chars) with 1–2 emojis.
- desc_points: 3–5 bullets, each <= 80 chars, concrete steps/templates (1 emoji max each).
- desc_cta: 1 question inviting replies (<= 110 chars), may include 1 emoji.
- tags: 2 short tags (<= 16 chars each, lowercase, no '#').
Return ONLY JSON.
"""}
        attempts = [model or "gpt-5", "gpt-4o", "gpt-4o-mini"]
        for mdl in attempts:
            try:
                resp = client.chat.completions.create(model=mdl, temperature=0.6, messages=[sys_msg,user_msg])
                txt = (resp.choices[0].message.content or "").strip()
                start, end = txt.find("{"), txt.rfind("}")
                import json as _json
                payload = _json.loads(txt[start:end+1]); break
            except Exception: pass
    except Exception: pass

    if not payload:
        payload = {
            "style": style_key, "cta_type": "question",
            "x_line": "Template: “Action → measurable outcome (%/time/$) in one line.” Keep it punchy. ✅📌",
            "desc_title": "Steal this bullet format ✍️",
            "desc_points": ["Lead with a number 📈","Name the lever ⚙️","Add brief scope 🧠","End with outcome ✅"],
            "desc_cta": "Where do you struggle—numbers, scope, or lever? 🤔",
            "tags": ["resume","jobsearch"]
        }
    return payload

def ensure_feed_scaffold():
    if not os.path.exists(FEED_FILE):
        rss = ET.Element("rss", attrib={"version":"2.0"})
        ch = ET.SubElement(rss,"channel")
        ET.SubElement(ch,"title").text = CHANNEL_TITLE
        ET.SubElement(ch,"link").text = SITE_URL
        ET.SubElement(ch,"description").text = CHANNEL_DESC
        ET.SubElement(ch,"language").text = CHANNEL_LANG
        now = rss_now()
        ET.SubElement(ch,"lastBuildDate").text = now
        ET.SubElement(ch,"pubDate").text = now
        ET.ElementTree(rss).write(FEED_FILE, encoding="utf-8", xml_declaration=True)
    tree = ET.parse(FEED_FILE)
    root = tree.getroot(); ch = root.find("channel") or ET.SubElement(root,"channel")
    def ensure(tag, text=None):
        node = ch.find(tag)
        if node is None: node = ET.SubElement(ch, tag)
        if text is not None and (node.text or "").strip() == "": node.text = text
        return node
    ensure("title", CHANNEL_TITLE); ensure("link", SITE_URL)
    ensure("description", CHANNEL_DESC); ensure("language", CHANNEL_LANG)
    ensure("lastBuildDate", rss_now()); ensure("pubDate", rss_now())
    tree.write(FEED_FILE, encoding="utf-8", xml_declaration=True)
    return tree

def make_item(payload):
    # style / cta
    style_key = (payload.get("style") or "").strip().lower() or "unspecified"
    cta_type  = (payload.get("cta_type") or "").strip().lower() or "question"
    # title line (X-ready)
    x_line = sanitize_xline((payload.get("x_line") or "").strip())
    x_line = add_minimum_emojis(x_line, need_min=rules.get("min_emojis",2))
    if rules.get("require_number_in_title") and not re.search(r"\d+%|[$]\d+", x_line):
        x_line = x_line + " 📈"
    if len(x_line) > 230:
        x_line = x_line[:229].rsplit(" ", 1)[0] + "…"
    # description (LI/FB)
    hook   = (payload.get("desc_title") or "").strip()
    points = [p.strip(" •-") for p in (payload.get("desc_points") or []) if str(p).strip()]
    cta    = (payload.get("desc_cta") or "").strip()
    # tags (robust)
    tag_bank = coerce_tag_list(load_json(TAGS_PATH, []))
    ptags = coerce_tag_list(payload.get("tags") or [])[:2]
    # merge ptags into bank (no write-back; just use here)
    for t in ptags:
        if t not in tag_bank: tag_bank.append(t)
    tags_raw = (ptags[:2]) if ptags else (tag_bank[:2])
    # build description
    bullets_fmt = "\n".join([f"• {b}" for b in points])
    tag_str = " ".join([f"#{t}" for t in tags_raw]) if tags_raw else ""
    description = "\n".join([s for s in [hook, "", bullets_fmt, "", cta, "", tag_str] if s]).strip()
    # guid/link
    now = datetime.now(timezone.utc)
    base = f"{slugify(x_line)}-{now.strftime('%Y%m%d%H%M%S')}"
    guid = hashlib.sha1(base.encode("utf-8")).hexdigest()
    link = f"{SITE_URL}?p={guid}"
    # xml item
    item = ET.Element("item")
    ET.SubElement(item,"title").text = x_line
    ET.SubElement(item,"description").text = description
    ET.SubElement(item,"link").text = link
    ET.SubElement(item,"guid", attrib={"isPermaLink":"false"}).text = guid
    ET.SubElement(item,"pubDate").text = rss_now()
    ET.SubElement(item,"category", attrib={"domain":"style"}).text = style_key
    ET.SubElement(item,"category", attrib={"domain":"cta"}).text = cta_type
    return item, guid, x_line

def prepend_item(tree, item):
    ch = tree.getroot().find("channel") or ET.SubElement(tree.getroot(),"channel")
    items = ch.findall("item")
    if items: ch.insert(list(ch).index(items[0]), item)
    else: ch.append(item)
    for tag in ("lastBuildDate","pubDate"):
        node = ch.find(tag) or ET.SubElement(ch, tag)
        node.text = rss_now()
    tree.write(FEED_FILE, encoding="utf-8", xml_declaration=True)

# ---------- Main ----------
cfg   = load_json(CONFIG_PATH, {})
rules = load_json(RULES_PATH, {})
band  = load_json(BANDIT_PATH, {})
if cfg.get("paused"):
    print("Paused by ops/config.json"); raise SystemExit(0)

topics = read_topics(TOPICS_FILE)
random.seed(int(datetime.now(timezone.utc).strftime("%Y%m%d%H")))
model  = os.getenv("MODEL") or cfg.get("model") or "gpt-5"

style_weights = band.get("style_weights", {})
style_key, style_desc = choose_style(style_weights)
cta_bias = band.get("cta_weights", {})

topic = random.choice(topics)
payload = call_openai(topic, style_key, style_desc, model,
                      cta_bias=cta_bias,
                      min_emojis=rules.get("min_emojis",2),
                      require_number=rules.get("require_number_in_title", False))

tree = ensure_feed_scaffold()
item, guid, title = make_item(payload)

# duplicate guard
fps = load_json(FPS_PATH, [])
dg = cfg.get("dup_guard", {"enabled":True,"ngram":5,"threshold":0.8,"history_size":200})
if dg.get("enabled", True):
    if not dup_guard_ok(title, fps, dg.get("ngram",5), dg.get("threshold",0.8)):
        # one reroll with different style weight
        alt_weights = {k:(1.0 if k!=style_key else 0.2) for k in style_weights} or {"checklist":1.0,"template_drop":1.0}
        alt_style, alt_desc = choose_style(alt_weights)
        payload2 = call_openai(topic, alt_style, alt_desc, model,
                               cta_bias=cta_bias,
                               min_emojis=rules.get("min_emojis",2),
                               require_number=rules.get("require_number_in_title", False))
        item2, guid2, title2 = make_item(payload2)
        if dup_guard_ok(title2, fps, dg.get("ngram",5), dg.get("threshold",0.8)):
            item, guid, title = item2, guid2, title2

prepend_item(tree, item)

# save fingerprint
probe = list(ngrams(title, dg.get("ngram",5)))
fps = (fps + [{"guid":guid, "ngrams":probe}])[-int(dg.get("history_size",200)):]
os.makedirs("analytics", exist_ok=True)
with open(FPS_PATH, "w", encoding="utf-8") as f:
    json.dump(fps, f, ensure_ascii=False, indent=2)

print("Generated:", title)
