#!/usr/bin/env python3
"""
build_analytics.py
Reads rss.xml (and rss_x.xml), extracts each post, computes content features, joins optional
metrics from analytics/engagement.csv, and writes:
- analytics/posts_features.csv        (one row per post; now includes style & cta)
- analytics/feature_summary.csv       (aggregates incl. style & cta)
- analytics/latest_report.md          (human-readable summary; adds style/cta sections)
- analytics/for_chatgpt.md            (compact brief incl. style/cta to paste into ChatGPT)

Zero paid APIs. Runs in GitHub Actions on a schedule.
"""

import os, re, csv, statistics
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime
from zoneinfo import ZoneInfo

REPO_TZ = ZoneInfo("America/Phoenix")

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
AN_DIR = os.path.join(REPO, "analytics")
os.makedirs(AN_DIR, exist_ok=True)

RSS_MAIN = os.path.join(REPO, "rss.xml")
RSS_X    = os.path.join(REPO, "rss_x.xml")
ENG_CSV  = os.path.join(AN_DIR, "engagement.csv")

OUT_POSTS  = os.path.join(AN_DIR, "posts_features.csv")
OUT_SUM    = os.path.join(AN_DIR, "feature_summary.csv")
OUT_MD     = os.path.join(AN_DIR, "latest_report.md")
OUT_CHAT   = os.path.join(AN_DIR, "for_chatgpt.md")

# ---------------------- Helpers ----------------------

def read_rss(path):
    if not os.path.exists(path):
        return []
    tree = ET.parse(path)
    ch = tree.getroot().find("channel")
    items = []
    for it in ch.findall("item"):
        # Pull style/cta categories (if present)
        style = "unknown"
        cta   = "unknown"
        for cat in it.findall("category"):
            dom = (cat.get("domain") or "").strip().lower()
            val = (cat.text or "").strip()
            if dom == "style" and val:
                style = val
            elif dom == "cta" and val:
                cta = val

        d = {
            "title": (it.findtext("title") or "").strip(),
            "description": (it.findtext("description") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "guid": (it.findtext("guid") or "").strip(),
            "pubDate": (it.findtext("pubDate") or "").strip(),
            "style": style,
            "cta": cta,
        }
        items.append(d)
    return items

def count_emojis(s: str) -> int:
    # Count in common emoji ranges; good enough for analytics
    count = 0
    for ch in s:
        o = ord(ch)
        if (
            0x1F300 <= o <= 0x1FAFF or  # symbols & pictographs, supplemental symbols
            0x1F1E6 <= o <= 0x1F1FF or  # regional flags
            0x1F900 <= o <= 0x1F9FF or
            0x2600  <= o <= 0x27BF or   # misc symbols / dingbats
            o in (0xFE0F, 0x200D)      # VS / ZWJ
        ):
            count += 1
    return count

def has_number(s: str) -> int:
    return 1 if re.search(r"\b\d+%?|\$\d+", s) else 0

def has_question(s: str) -> int:
    return 1 if "?" in s else 0

def quote_count(s: str) -> int:
    return s.count('"') + s.count("“") + s.count("”") + s.count("'")

def bullet_count(s: str) -> int:
    return s.count("•") + len(re.findall(r"^\s*-\s+", s, flags=re.M))

def hashtag_count(s: str) -> int:
    return s.count("#")

def safe_len(s: str) -> int:
    return len(s or "")

def rfc822_to_local(dt_str: str):
    try:
        dt = parsedate_to_datetime(dt_str)
        if dt.tzinfo is None:
            from zoneinfo import ZoneInfo as _ZI
            dt = dt.replace(tzinfo=_ZI("UTC"))
        return dt.astimezone(REPO_TZ)
    except Exception:
        return None

def hour_bucket(dt):
    if not dt: return ""
    h = dt.hour
    if 5 <= h < 9:  return "early-morning"
    if 9 <= h < 12: return "morning"
    if 12 <= h < 15:return "early-afternoon"
    if 15 <= h < 18:return "late-afternoon"
    if 18 <= h < 22:return "evening"
    return "night"

def read_engagement(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("guid") or "").startswith("#") or not (r.get("guid") or "").strip():
                continue
            rows.append({
                "guid": r.get("guid","").strip(),
                "platform": (r.get("platform","") or "").strip().lower(),
                "likes": int(r.get("likes") or 0),
                "replies": int(r.get("replies") or 0),
                "reposts": int(r.get("reposts") or 0),
                "impressions": int(r.get("impressions") or 0),
                "clicks": int(r.get("clicks") or 0),
                "saves": int(r.get("saves") or 0),
                "notes": (r.get("notes") or "").strip(),
            })
    return rows

# ---------------------- Build datasets ----------------------

def build_posts():
    items = read_rss(RSS_MAIN)
    posts = []
    for it in items:
        dt_local = rfc822_to_local(it["pubDate"])
        title = it["title"]
        desc  = it["description"]

        row = {
            "guid": it["guid"] or "",
            "pubDate_local": dt_local.isoformat() if dt_local else "",
            "hour_bucket": hour_bucket(dt_local),

            "style": it["style"],       # NEW
            "cta": it["cta"],           # NEW

            "title_len": safe_len(title),
            "desc_len": safe_len(desc),
            "title_emoji_ct": count_emojis(title),
            "desc_emoji_ct": count_emojis(desc),
            "has_number": has_number(title) or has_number(desc),
            "has_question": has_question(title) or has_question(desc),
            "quote_count": max(quote_count(title), quote_count(desc)),
            "bullet_count": bullet_count(desc),
            "has_hashtag": 1 if hashtag_count(desc) > 0 else 0,

            "title_sample": title[:220],
            "link": it["link"],
        }
        posts.append(row)
    return posts

def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

def agg_mean(values):
    vals = [v for v in values if isinstance(v, (int,float))]
    return round(statistics.mean(vals),2) if vals else 0.0

def summarize(posts, eng_by_guid):
    # Join engagement per guid (sum across platforms)
    joined = []
    for p in posts:
        guid = p["guid"]
        metrics = [e for e in eng_by_guid.get(guid, [])]
        totals = {"likes":0, "replies":0, "reposts":0, "impressions":0, "clicks":0, "saves":0}
        for m in metrics:
            for k in totals.keys():
                totals[k] += m.get(k,0)

        # Simple weighted score (tuneable)
        eng_score = (
            totals["likes"]*1.0 + totals["replies"]*2.0 + totals["reposts"]*3.0 +
            totals["clicks"]*0.5 + totals["saves"]*1.5
        )
        row = dict(p)
        row.update(totals)
        row["eng_score"] = round(eng_score,2)
        joined.append(row)

    # Create buckets
    def bucketize(v, edges):
        for edge in edges:
            if v <= edge: return f"<= {edge}"
        return f"> {edges[-1]}"

    for r in joined:
        r["b_title_len"] = bucketize(r["title_len"], [120,160,200,240,280,320])
        r["b_emoji"] = "0" if r["title_emoji_ct"]==0 else ("1" if r["title_emoji_ct"]==1 else ("2" if r["title_emoji_ct"]==2 else "3+"))

    # Aggregate means by feature buckets (includes style & cta)
    agg = {}
    def add(key, val):
        agg.setdefault(key, []).append(val)

    for r in joined:
        add(("emoji", r["b_emoji"]), r["eng_score"])
        add(("len", r["b_title_len"]), r["eng_score"])
        add(("number", "yes" if r["has_number"] else "no"), r["eng_score"])
        add(("question", "yes" if r["has_question"] else "no"), r["eng_score"])
        add(("bullets", "0" if r["bullet_count"]==0 else "1+"), r["eng_score"])
        add(("time", r["hour_bucket"] or "unknown"), r["eng_score"])
        add(("style", r["style"] or "unknown"), r["eng_score"])   # NEW
        add(("cta", r["cta"] or "unknown"), r["eng_score"])       # NEW

    rows_sum = []
    for (ft, bucket), vals in sorted(agg.items()):
        rows_sum.append({"feature": ft, "bucket": bucket, "avg_eng_score": agg_mean(vals), "n_posts": len(vals)})
    return joined, rows_sum

# ---------------------- Main ----------------------

def main():
    posts = build_posts()

    # Load engagement rows and group by guid
    eng_rows = read_engagement(ENG_CSV)
    eng_by_guid = {}
    for r in eng_rows:
        eng_by_guid.setdefault(r["guid"], []).append(r)

    joined, rows_sum = summarize(posts, eng_by_guid)

    # Write posts_features.csv
    post_fields = [
        "guid","pubDate_local","hour_bucket",
        "style","cta",                           # NEW
        "title_len","desc_len","title_emoji_ct","desc_emoji_ct",
        "has_number","has_question","quote_count","bullet_count","has_hashtag",
        "likes","replies","reposts","impressions","clicks","saves","eng_score",
        "title_sample","link",
        "b_title_len","b_emoji"
    ]
    write_csv(OUT_POSTS, joined, post_fields)

    # Write feature_summary.csv (includes style & cta)
    sum_fields = ["feature","bucket","avg_eng_score","n_posts"]
    write_csv(OUT_SUM, rows_sum, sum_fields)

    # Markdown report
    top5 = sorted(joined, key=lambda r: r.get("eng_score",0), reverse=True)[:5]
    lines = []
    lines.append("# Career Forge — Analytics Report\n")
    lines.append(f"_Generated: {datetime.now(REPO_TZ).isoformat()}_\n")

    lines.append("## Top 5 Posts (by engagement score)\n")
    for r in top5:
        lines.append(f"- **{r['title_sample']}**  \n  score={r['eng_score']} | likes={r['likes']} | replies={r['replies']} | reposts={r['reposts']} | clicks={r['clicks']} | saves={r['saves']} | time={r['pubDate_local']} | style={r['style']} | cta={r['cta']}")

    def section(feature_key, title):
        lines.append(f"\n## {title}\n")
        rows = [x for x in rows_sum if x["feature"]==feature_key]
        rows = sorted(rows, key=lambda x: x["avg_eng_score"], reverse=True)
        for x in rows:
            lines.append(f"- {x['bucket']}: avg_score={x['avg_eng_score']} (n={x['n_posts']})")

    section("style",   "Performance by Style")         # NEW
    section("cta",     "Performance by CTA Type")      # NEW
    section("emoji",   "Emoji Count in Title")
    section("len",     "Title Length")
    section("number",  "Numbers / % / $ Present")
    section("question","Question Mark Present")
    section("bullets", "Bullets Present in Description")
    section("time",    "Local Post Time Bucket")

    lines.append("\n## Next experiments\n")
    lines.append("- Publish a 3-post mini-test emphasizing the top 2 **styles** and top 1 **CTA** bucket.")
    lines.append("- If **Numbers** bucket wins, include a % or $ in the X line.")
    lines.append("- If a specific **time** bucket dominates, bias schedule toward it for a week.")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ChatGPT brief
    brief = []
    brief.append("# Career Forge — Analytics Brief for ChatGPT\n")
    brief.append("We generate self-contained, emoji-forward posts twice daily. Below are feature averages, including **style** and **CTA**.\n")
    brief.append("## Feature Summary (averages)\n")
    for r in rows_sum:
        brief.append(f"- {r['feature']} :: {r['bucket']} => avg_score={r['avg_eng_score']} (n={r['n_posts']})")
    brief.append("\n## Ask ChatGPT\n")
    brief.append("Using the feature summary and the top posts below, propose 5 concrete editing rules (max 1 line each) I should apply to future posts to maximize engagement. Include 1 recommendation for **style mix** and 1 for **CTA type**.")
    brief.append("\n## Top Posts (samples)\n")
    for r in top5:
        brief.append(f"- {r['title_sample']}  | score={r['eng_score']} | emojis={r['title_emoji_ct']} | len={r['title_len']} | style={r['style']} | cta={r['cta']}")
    with open(OUT_CHAT, "w", encoding="utf-8") as f:
        f.write("\n".join(brief))

    print("Analytics written:",
          os.path.relpath(OUT_POSTS, REPO),
          os.path.relpath(OUT_SUM, REPO),
          os.path.relpath(OUT_MD, REPO),
          os.path.relpath(OUT_CHAT, REPO))

if __name__ == "__main__":
    main()
