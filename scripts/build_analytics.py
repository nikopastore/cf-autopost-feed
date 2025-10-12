#!/usr/bin/env python3
"""
build_analytics.py
Reads rss.xml (and rss_x.xml), extracts each post, computes content features, joins optional
metrics from analytics/engagement.csv, and writes:
- analytics/posts_features.csv        (one row per post)
- analytics/feature_summary.csv       (aggregates by buckets)
- analytics/latest_report.md          (human-readable summary)
- analytics/for_chatgpt.md            (compact brief to paste into ChatGPT)

No paid APIs. Runs in GitHub Actions on a schedule.
"""

import os, re, csv, math, statistics
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

def read_rss(path):
    if not os.path.exists(path):
        return []
    tree = ET.parse(path)
    ch = tree.getroot().find("channel")
    items = []
    for it in ch.findall("item"):
        d = {
            "title": (it.findtext("title") or "").strip(),
            "description": (it.findtext("description") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "guid": (it.findtext("guid") or "").strip(),
            "pubDate": (it.findtext("pubDate") or "").strip(),
        }
        items.append(d)
    return items

def count_emojis(s: str) -> int:
    # crude but effective: count codepoints in common emoji ranges
    count = 0
    for ch in s:
        o = ord(ch)
        if (
            0x1F300 <= o <= 0x1FAFF or  # symbols & pictographs, supplemental symbols
            0x1F1E6 <= o <= 0x1F1FF or  # regional indicator symbols
            0x1F900 <= o <= 0x1F9FF or
            0x2600  <= o <= 0x27BF or   # misc symbols / dingbats
            o in (0xFE0F, 0x200D)      # variation selector / ZWJ
        ):
            count += 1
    return count

def has_dialogue(s: str) -> int:
    return 1 if re.search(r"\b(You:|Them:|Q:|A:)\b", s) else 0

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
            return dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(REPO_TZ)
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
            "title_len": safe_len(title),
            "desc_len": safe_len(desc),
            "title_emoji_ct": count_emojis(title),
            "desc_emoji_ct": count_emojis(desc),
            "has_dialogue": has_dialogue(title) or has_dialogue(desc),
            "has_number": has_number(title) or has_number(desc),
            "has_question": has_question(title) or has_question(desc),
            "quote_count": max(quote_count(title), quote_count(desc)),
            "bullet_count": bullet_count(desc),
            "has_hashtag": 1 if hashtag_count(desc) > 0 else 0,
            "title_sample": title[:200],
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
    # Build joined rows (aggregate per guid across platforms using simple weights)
    joined = []
    for p in posts:
        guid = p["guid"]
        metrics = [e for e in eng_by_guid.get(guid, [])]
        # Weighted engagement score (tweakable)
        total_score = 0
        totals = {"likes":0, "replies":0, "reposts":0, "impressions":0, "clicks":0, "saves":0}
        for m in metrics:
            totals["likes"] += m["likes"]
            totals["replies"] += m["replies"]
            totals["reposts"] += m["reposts"]
            totals["impressions"] += m["impressions"]
            totals["clicks"] += m["clicks"]
            totals["saves"] += m["saves"]
        total_score = (
            totals["likes"]*1.0 + totals["replies"]*2.0 + totals["reposts"]*3.0 +
            totals["clicks"]*0.5 + totals["saves"]*1.5
        )
        row = dict(p)
        row.update(totals)
        row["eng_score"] = round(total_score,2)
        joined.append(row)

    # Buckets
    def bucketize(v, edges):
        for i,edge in enumerate(edges):
            if v <= edge: return f"<= {edge}"
        return f"> {edges[-1]}"

    for r in joined:
        r["b_title_len"] = bucketize(r["title_len"], [120,160,200,240,280,320])
        r["b_emoji"] = "0" if r["title_emoji_ct"]==0 else ("1" if r["title_emoji_ct"]==1 else ("2" if r["title_emoji_ct"]==2 else "3+"))

    # Aggregate means by feature buckets
    agg = {}
    def add(key, val):
        agg.setdefault(key, []).append(val)

    for r in joined:
        add(("emoji", r["b_emoji"]), r["eng_score"])
        add(("len", r["b_title_len"]), r["eng_score"])
        add(("dialogue", "yes" if r["has_dialogue"] else "no"), r["eng_score"])
        add(("number", "yes" if r["has_number"] else "no"), r["eng_score"])
        add(("question", "yes" if r["has_question"] else "no"), r["eng_score"])
        add(("bullets", "0" if r["bullet_count"]==0 else "1+"), r["eng_score"])
        add(("time", r["hour_bucket"] or "unknown"), r["eng_score"])

    rows_sum = []
    for (ft, bucket), vals in sorted(agg.items()):
        rows_sum.append({"feature": ft, "bucket": bucket, "avg_eng_score": round(agg_mean(vals),2), "n_posts": len(vals)})
    return joined, rows_sum

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
        "guid","pubDate_local","hour_bucket","title_len","desc_len","title_emoji_ct","desc_emoji_ct",
        "has_dialogue","has_number","has_question","quote_count","bullet_count","has_hashtag",
        "likes","replies","reposts","impressions","clicks","saves","eng_score","title_sample","link",
        "b_title_len","b_emoji"
    ]
    write_csv(OUT_POSTS, joined, post_fields)

    # Write feature_summary.csv
    sum_fields = ["feature","bucket","avg_eng_score","n_posts"]
    write_csv(OUT_SUM, rows_sum, sum_fields)

    # Markdown report
    top5 = sorted(joined, key=lambda r: r.get("eng_score",0), reverse=True)[:5]
    lines = []
    lines.append("# Career Forge — Analytics Report\n")
    lines.append(f"_Generated: {datetime.now(REPO_TZ).isoformat()}_\n")
    lines.append("## Top 5 Posts (by engagement score)\n")
    for r in top5:
        lines.append(f"- **{r['title_sample']}**  \n  score={r['eng_score']} | likes={r['likes']} | replies={r['replies']} | reposts={r['reposts']} | clicks={r['clicks']} | saves={r['saves']} | time={r['pubDate_local']}")
    lines.append("\n## What patterns look promising\n")
    def top_rows(ft):
        return [row for row in rows_sum if row["feature"]==ft]
    for ft,label in [("emoji","Emoji count in title"),("len","Title length"),("dialogue","Dialogue pattern (You:/Them:)"),("number","Has numbers/%/$"),("question","Has a question"),("time","Post time (local)")]:
        lines.append(f"### {label}")
        rows = sorted(top_rows(ft), key=lambda r: r["avg_eng_score"], reverse=True)
        for r in rows:
            lines.append(f"- {r['bucket']}: avg_score={r['avg_eng_score']} (n={r['n_posts']})")
        lines.append("")
    lines.append("\n## Next experiments\n")
    lines.append("- Try 3-post mini-test next week maximizing the top 2 buckets from **Emoji** and **Title length**.")
    lines.append("- If **Dialogue** = yes outperforms, bias toward ‘You:/Them:’ scripts.")
    lines.append("- If **Numbers** bucket wins, include a % or $ in the X line.")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ChatGPT brief
    brief = []
    brief.append("# Career Forge — Analytics Brief for ChatGPT\n")
    brief.append("Paste this message to ChatGPT (or your AI assistant) to get data-driven guidance.\n")
    brief.append("## Context\n")
    brief.append("We generate self-contained, emoji-forward posts twice daily. Below are features and engagement (when available).\n")
    brief.append("## Feature Summary (averages)\n")
    for r in rows_sum:
        brief.append(f"- {r['feature']} :: {r['bucket']} => avg_score={r['avg_eng_score']} (n={r['n_posts']})")
    brief.append("\n## Ask ChatGPT\n")
    brief.append("Using the feature summary and the top posts below, propose 5 concrete editing rules (max 1 line each) I should apply to future posts to maximize engagement.\n")
    brief.append("Return a checklist with examples.\n")
    brief.append("\n## Top Posts (samples)\n")
    for r in top5:
        brief.append(f"- {r['title_sample']}  | score={r['eng_score']} | emojis={r['title_emoji_ct']} | len={r['title_len']}")
    with open(OUT_CHAT, "w", encoding="utf-8") as f:
        f.write("\n".join(brief))

    print("Analytics written:",
          os.path.relpath(OUT_POSTS, REPO),
          os.path.relpath(OUT_SUM, REPO),
          os.path.relpath(OUT_MD, REPO),
          os.path.relpath(OUT_CHAT, REPO))

if __name__ == "__main__":
    main()
