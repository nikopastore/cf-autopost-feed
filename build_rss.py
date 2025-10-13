#!/usr/bin/env python3
"""
Career Forge — build_rss.py (Coach Voice + Quality Gate)

Key upgrades:
- Persona: expert career coach / recruiter (second-person guidance).
- Guardrails: no dialogue labels; avoid tense conflicts like “When … I … achieved …”.
- First-person allowed only inside quotes (templates), never as narration.
- Quality Gate: detects bad patterns; auto-regenerates with stricter constraints.
- Tags loader now accepts list/dict/string safely (coerces to list).

Requires env: OPENAI_API_KEY
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
    ("coach_tip",        "Direct, second-person advice that a top career coach would give."),
    ("recruiter_inside", "Inside-view tip from a recruiter: what they look for & how to show it."),
    ("template_drop",    "Share a fill-in-the-blank template + 1 tiny example."),
    ("mistake_fix",      "Name 1 common mistake and show the concise fix."),
    ("checklist",        "Give a tight 4-item checklist for a narrow task."),
    ("data_bite",        "One stat/number, why it matters, and what to do."),
    ("challenge",        "Issue a 24–48h micro-challenge with clear steps.")
]
EMOJI_PALETTE = ["✅","💬","📌","✍️","🚀","🧠","💼","⏱️","📈","🤝","🔎","📣","🗂️","🧩","🎯","⚡","🔥","🌟"]

FORBIDDEN_DIALOGUE_RX = re.compile(r"\b(You:|Them:|Q:|A:)\b", re.I)
FORBIDDEN_META_RX = re.compile(r"\b(in this thread|see below)\b", re.I)

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
    r = random.random() * total; c = 0.0
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
    palette = EMOJI_PALETTE[:]
    random.shuffle(palette)
    return f"{palette[0]} {line}" if (need_min - count) == 1 else f"{palette[0]} {line} {palette[1]}"

def sanitize_xline(s: str) -> str:
    s = FORBIDDEN_DIALOGUE_RX.sub("", s)
    s = FORBIDDEN_META_RX.sub("", s)
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

# ---- Tags coercion ----
def coerce_tag_list(obj):
    out = []
    if isinstance(obj, list):
        cand = obj
    elif isinstance(obj, dict):
        cand = list(obj.keys()) + list(obj.values())
    elif isinstance(obj, str):
        cand = re.split(r"[,\s]+", obj)
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
    seen=set(); clean=[]
    for s in out:
        if s not in seen:
            seen.add(s); clean.append(s)
    return clean

# ---- Persona & quality gate utilities ----
QUOTE_CHARS = "\"'“”‘’"
def contains_unquoted_I(text: str) -> bool:
    """Return True if ' I ' appears outside of quotes."""
    inside = False
    prev = ""
    for ch in text:
        if ch in QUOTE_CHARS:
            # toggle on any quote; simple heuristic robust enough for short lines
            inside = not inside
        if ch == "I" and not inside:
            # check word boundary " I " (start or space before; space or punctuation after)
            prev_c = prev
            next_c = " "
        prev = ch
    # Simpler, robust regex approach:
    # 'I' outside quotes → strip quoted segments then search
    tmp = re.sub(r"[\"“”‘’][^\"“”‘’]+[\"“”‘’]", " ", text)
    return bool(re.search(r"\bI\b", tmp))

def has_banned_phrases(text: str, banned: list[str]) -> bool:
    low = text.lower()
    for p in banned:
        if p.strip() and p.lower() in low:
            return True
    return False

WHEN_I_PAST_RX = re.compile(r"\bwhen\s+\w+ing\b.*\bI\b.*\b(achieved|led to|delivered|shipped)\b", re.I)

def quality_gate(x_line: str, rules: dict) -> tuple[bool, str]:
    """
    Returns (ok, reason_if_bad)
    """
    # No dialogue markers or meta
    if FORBIDDEN_DIALOGUE_RX.search(x_line) or FORBIDDEN_META_RX.search(x_line):
        return False, "dialogue/meta markers"
    # Banned phrases
    if has_banned_phrases(x_line, rules.get("banned_phrases", [])):
        return False, "banned phrase"
    # Tense conflict like 'When ... I achieved ...'
    if WHEN_I_PAST_RX.search(x_line):
        return False, "tense conflict (when...I...achieved)"
    # Enforce second-person voice (soft): prefer 'you/your' somewhere
    if rules.get("enforce_second_person", False):
        if not re.search(r"\b(you|your)\b", x_line, re.I):
            # allow templates starting with 'Use:' that quote 1st person
            if not re.search(r"Use:\s*[\"“]", x_line):
                return False, "missing second-person signal"
    # First-person outside quotes not allowed
    if rules.get("allow_first_person_in_quotes_only", False):
        if contains_unquoted_I(x_line):
            return False, "first-person outside quotes"
    return True, ""

# ---- OpenAI call ----
def call_openai(topic, style_key, style_desc, model, rules, pass_hint=""):
    """
    pass_hint: extra constraints for retries (plain text bullets).
    """
    payload = None
    sys = (
        "You are a top-tier career coach and ex-recruiter. "
        "You write concise, concrete, **second-person** advice. "
        "No dialogue labels (‘You:’, ‘Them:’). "
        "Avoid tense conflicts like “When pitching…, I achieved…”. "
        "Use first-person *only* inside quotes when providing a reusable template. "
        "Every post must be self-contained (no 'in this thread', no links)."
    )
    # map rules to prompt toggles
    min_emojis = int(rules.get("min_emojis", 2))
    require_number = bool(rules.get("require_number_in_title", False))
    banned_join = "; ".join(rules.get("banned_phrases", []))

    user = f"""
STYLE: {style_key}
STYLE_DESC: {style_desc}
TOPIC_SEED: "{topic}"

VOICE: expert career coach / recruiter (second-person).
BAN: dialogue labels; meta like "in this thread"; phrases → {banned_join or "—"}.
TENSE: do not mix future/present setup with past-tense boasts like "I achieved".
FIRST PERSON: allowed only inside quotes as a template (e.g., Use: “I achieved X% by Y.”).

OUTPUT RULES
- Return STRICT JSON only.
- x_line: SINGLE line for X (<= 230 chars), second-person, {min_emojis}–4 tasteful emojis, no hashtags/links/dialogue/meta.
- If a template is useful, prefix with 'Use:' then a quoted first-person line (that a candidate could say).
- Ensure no tense conflict; no "When … I … achieved …" constructions.
- desc_title: concise hook (<= 80 chars) + 1–2 emojis.
- desc_points: 3–5 bullets; concrete steps/templates; <= 80 chars; max 1 emoji each.
- desc_cta: 1 thoughtful question (<= 110 chars).
- tags: 2 short lowercase tags (no '#').
- require_number_in_title={str(require_number).lower()}

{pass_hint}
"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        attempts = [model or "gpt-5", "gpt-4o", "gpt-4o-mini"]
        for mdl in attempts:
            try:
                resp = client.chat.completions.create(
                    model=mdl, temperature=0.6,
                    messages=[{"role":"system","content":sys},{"role":"user","content":user}]
                )
                txt = (resp.choices[0].message.content or "").strip()
                start, end = txt.find("{"), txt.rfind("}")
                payload = json.loads(txt[start:end+1])
                if payload: break
            except Exception:
                pass
    except Exception:
        pass

    # Fallback payload (rare)
    if not payload:
        payload = {
            "style": style_key, "cta_type": "question",
            "x_line": "Your update pitch, coach-style: Use: “I improved X% by doing Y — so Z happened.” Keep it tight. ✅📌",
            "desc_title": "Refresh your pitch ✍️",
            "desc_points": ["Lead with outcome 📈","Name the lever ⚙️","Give brief scope 🧠","Close with value ✅"],
            "desc_cta": "What part of your pitch feels weakest now?",
            "tags": ["resume","jobsearch"]
        }
    return payload

# ---- Feed scaffold ----
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

# ---- Build item ----
def make_item(payload, rules):
    style_key = (payload.get("style") or "").strip().lower() or "unspecified"
    cta_type  = (payload.get("cta_type") or "").strip().lower() or "question"

    x_line = sanitize_xline((payload.get("x_line") or "").strip())
    # emojis
    x_line = add_minimum_emojis(x_line, need_min=rules.get("min_emojis",2))
    # require %/$ optional
    if rules.get("require_number_in_title") and not re.search(r"\d+%|[$]\d+", x_line):
        x_line = x_line + " 📈"
    if len(x_line) > 230:
        x_line = x_line[:229].rsplit(" ", 1)[0] + "…"

    hook   = (payload.get("desc_title") or "").strip()
    points = [p.strip(" •-") for p in (payload.get("desc_points") or []) if str(p).strip()]
    cta    = (payload.get("desc_cta") or "").strip()

    tag_bank = coerce_tag_list(load_json(TAGS_PATH, []))
    ptags = coerce_tag_list(payload.get("tags") or [])[:2]
    for t in ptags:
        if t not in tag_bank: tag_bank.append(t)
    tags_raw = (ptags[:2]) if ptags else (tag_bank[:2])

    bullets_fmt = "\n".join([f"• {b}" for b in points])
    tag_str = " ".join([f"#{t}" for t in tags_raw]) if tags_raw else ""
    description = "\n".join([s for s in [hook, "", bullets_fmt, "", cta, "", tag_str] if s]).strip()

    now = datetime.now(timezone.utc)
    base = f"{slugify(x_line)}-{now.strftime('%Y%m%d%H%M%S')}"
    guid = hashlib.sha1(base.encode("utf-8")).hexdigest()
    link = f"{SITE_URL}?p={guid}"

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

style_weights = band.get("style_weights", {
    "coach_tip":1.4, "recruiter_inside":1.3, "checklist":1.1, "mistake_fix":1.1,
    "template_drop":1.0, "data_bite":0.9, "challenge":0.8
})
style_key, style_desc = choose_style(style_weights)
cta_bias = band.get("cta_weights", {})

topic = random.choice(topics)

# Generate with up to 3 attempts, tightening constraints if the quality gate fails
attempt_notes = [
    "",
    "REVISION: Fix any tense conflict; keep second-person; if using a template, prefix 'Use:' then quote the line.",
    "REVISION: Remove any first-person narration; only quote first-person inside 'Use: “...”'; add a concrete number or example if helpful."
]
payload = None
xline = ""; ok=False; reason=""

for note in attempt_notes:
    p = call_openai(topic, style_key, style_desc, model, rules, pass_hint=note)
    # assemble to see x_line and test
    try:
        # dry-run x_line only for validation
        candidate = sanitize_xline((p.get("x_line") or "").strip())
        candidate = add_minimum_emojis(candidate, need_min=rules.get("min_emojis",2))
        if len(candidate) > 230:
            candidate = candidate[:229].rsplit(" ", 1)[0] + "…"
        ok, reason = quality_gate(candidate, rules)
        if ok:
            payload = p; xline = candidate; break
    except Exception:
        pass

if not payload:
    # last resort: keep the final attempt but continue
    payload = p
    xline = sanitize_xline((payload.get("x_line") or "").strip())

tree = ensure_feed_scaffold()
item, guid, title = make_item(payload, rules)

# duplicate guard
fps = load_json(FPS_PATH, [])
dg = cfg.get("dup_guard", {"enabled":True,"ngram":5,"threshold":0.8,"history_size":200})
if dg.get("enabled", True):
    if not dup_guard_ok(title, fps, dg.get("ngram",5), dg.get("threshold",0.8)):
        # reroll style weights a bit
        alt_weights = {k:(1.0 if k!=style_key else 0.35) for k in style_weights} or {"checklist":1.0,"coach_tip":1.2}
        alt_style, alt_desc = choose_style(alt_weights)
        p2 = call_openai(topic, alt_style, alt_desc, model, rules, pass_hint="REVISION: ensure second-person; avoid first-person narration; no tense conflicts.")
        item2, guid2, title2 = make_item(p2, rules)
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

print("Generated:", title)

