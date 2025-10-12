#!/usr/bin/env python3
# Reads rss.xml, extracts features (incl. style/cta), joins engagement.csv, writes CSVs + reports.

import os, re, csv, statistics, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime
from zoneinfo import ZoneInfo

REPO_TZ = ZoneInfo("America/Phoenix")
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
AN_DIR = os.path.join(REPO, "analytics")
os.makedirs(AN_DIR, exist_ok=True)

RSS_MAIN = os.path.join(REPO, "rss.xml")
ENG_CSV  = os.path.join(AN_DIR, "engagement.csv")

OUT_POSTS  = os.path.join(AN_DIR, "posts_features.csv")
OUT_SUM    = os.path.join(AN_DIR, "feature_summary.csv")
OUT_MD     = os.path.join(AN_DIR, "latest_report.md")
OUT_CHAT   = os.path.join(AN_DIR, "for_chatgpt.md")

def read_rss(path):
    if not os.path.exists(path): return []
    tree = ET.parse(path); ch = tree.getroot().find("channel"); items=[]
    for it in ch.findall("item"):
        style="unknown"; cta="unknown"
        for cat in it.findall("category"):
            dom=(cat.get("domain") or "").strip().lower(); val=(cat.text or "").strip()
            if dom=="style" and val: style=val
            elif dom=="cta" and val: cta=val
        items.append({
          "title": (it.findtext("title") or "").strip(),
          "description": (it.findtext("description") or "").strip(),
          "link": (it.findtext("link") or "").strip(),
          "guid": (it.findtext("guid") or "").strip(),
          "pubDate": (it.findtext("pubDate") or "").strip(),
          "style": style, "cta": cta
        })
    return items

def count_emojis(s): 
    c=0
    for ch in s:
        o=ord(ch)
        if (0x1F300<=o<=0x1FAFF) or (0x1F1E6<=o<=0x1F1FF) or (0x1F900<=o<=0x1F9FF) or (0x2600<=o<=0x27BF) or (o in (0xFE0F,0x200D)): c+=1
    return c

def has_number(s): import re; return 1 if re.search(r"\b\d+%?|\$\d+", s) else 0
def has_question(s): return 1 if "?" in s else 0
def quote_count(s): return s.count('"') + s.count("“") + s.count("”") + s.count("'")
def bullet_count(s): import re; return s.count("•") + len(re.findall(r"^\s*-\s+", s, flags=re.M))
def safe_len(s): return len(s or "")

def to_local(dt_str):
    try:
        dt=parsedate_to_datetime(dt_str)
        if dt.tzinfo is None:
            from zoneinfo import ZoneInfo as _ZI; dt=dt.replace(tzinfo=_ZI("UTC"))
        return dt.astimezone(REPO_TZ)
    except Exception: return None

def hour_bucket(dt):
    if not dt: return ""
    h=dt.hour
    if 5<=h<9: return "early-morning"
    if 9<=h<12: return "morning"
    if 12<=h<15: return "early-afternoon"
    if 15<=h<18: return "late-afternoon"
    if 18<=h<22: return "evening"
    return "night"

def read_engagement(path):
    rows=[]
    if not os.path.exists(path): return rows
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("guid") or "").startswith("#") or not (r.get("guid") or "").strip(): continue
            rows.append({
                "guid": r.get("guid","").strip(),
                "platform": (r.get("platform","") or "").strip().lower(),
                "likes": int(r.get("likes") or 0),
                "replies": int(r.get("replies") or 0),
                "reposts": int(r.get("reposts") or 0),
                "impressions": int(r.get("impressions") or 0),
                "clicks": int(r.get("clicks") or 0),
                "saves": int(r.get("saves") or 0)
            })
    return rows

def build_posts():
    items=read_rss(RSS_MAIN); posts=[]
    for it in items:
        dt=to_local(it["pubDate"]); title=it["title"]; desc=it["description"]
        posts.append({
          "guid": it["guid"], "pubDate_local": dt.isoformat() if dt else "", "hour_bucket": hour_bucket(dt),
          "style": it["style"], "cta": it["cta"],
          "title_len": safe_len(title), "desc_len": safe_len(desc),
          "title_emoji_ct": count_emojis(title), "desc_emoji_ct": count_emojis(desc),
          "has_number": has_number(title) or has_number(desc),
          "has_question": has_question(title) or has_question(desc),
          "quote_count": max(quote_count(title), quote_count(desc)),
          "bullet_count": bullet_count(desc),
          "has_hashtag": 1 if "#" in desc else 0,
          "title_sample": title[:220], "link": it["link"]
        })
    return posts

def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,"") for k in fields})

def agg_mean(vals): 
    vals=[v for v in vals if isinstance(v,(int,float))]
    import statistics as S
    return round(S.mean(vals),2) if vals else 0.0

def summarize(posts, eng_by_guid):
    joined=[]
    for p in posts:
        g=p["guid"]; totals={"likes":0,"replies":0,"reposts":0,"impressions":0,"clicks":0,"saves":0}
        for m in eng_by_guid.get(g, []):
            for k in totals: totals[k]+=m.get(k,0)
        score=totals["likes"]*1.0 + totals["replies"]*2.0 + totals["reposts"]*3.0 + totals["clicks"]*0.5 + totals["saves"]*1.5
        row=dict(p); row.update(totals); row["eng_score"]=round(score,2); joined.append(row)
    def bucketize(v, edges):
        for e in edges:
            if v <= e: return f"<= {e}"
        return f"> {edges[-1]}"
    for r in joined:
        r["b_title_len"]=bucketize(r["title_len"], [120,160,200,240,280,320])
        r["b_emoji"]="0" if r["title_emoji_ct"]==0 else ("1" if r["title_emoji_ct"]==1 else ("2" if r["title_emoji_ct"]==2 else "3+"))
    agg={}
    def add(k,val): agg.setdefault(k,[]).append(val)
    for r in joined:
        add(("emoji", r["b_emoji"]), r["eng_score"])
        add(("len", r["b_title_len"]), r["eng_score"])
        add(("number", "yes" if r["has_number"] else "no"), r["eng_score"])
        add(("question", "yes" if r["has_question"] else "no"), r["eng_score"])
        add(("bullets", "0" if r["bullet_count"]==0 else "1+"), r["eng_score"])
        add(("time", r["hour_bucket"] or "unknown"), r["eng_score"])
        add(("style", r["style"] or "unknown"), r["eng_score"])
        add(("cta", r["cta"] or "unknown"), r["eng_score"])
    rows_sum=[{"feature":f,"bucket":b,"avg_eng_score":agg_mean(v),"n_posts":len(v)} for (f,b),v in sorted(agg.items())]
    return joined, rows_sum

def main():
    posts=build_posts(); eng=read_engagement(ENG_CSV)
    eng_by_guid={}; 
    for r in eng: eng_by_guid.setdefault(r["guid"], []).append(r)
    joined, rows_sum=summarize(posts, eng_by_guid)
    post_fields=["guid","pubDate_local","hour_bucket","style","cta","title_len","desc_len","title_emoji_ct","desc_emoji_ct","has_number","has_question","quote_count","bullet_count","has_hashtag","likes","replies","reposts","impressions","clicks","saves","eng_score","title_sample","link","b_title_len","b_emoji"]
    write_csv(OUT_POSTS, joined, post_fields)
    write_csv(OUT_SUM, rows_sum, ["feature","bucket","avg_eng_score","n_posts"])
    top5=sorted(joined, key=lambda r:r.get("eng_score",0), reverse=True)[:5]
    lines=["# Career Forge — Analytics Report\n", f"_Generated: {datetime.now(REPO_TZ).isoformat()}_\n", "## Top 5 Posts (by engagement score)\n"]
    for r in top5:
        lines.append(f"- **{r['title_sample']}**  \n  score={r['eng_score']} | likes={r['likes']} | replies={r['replies']} | reposts={r['reposts']} | clicks={r['clicks']} | saves={r['saves']} | time={r['pubDate_local']} | style={r['style']} | cta={r['cta']}")
    def sec(key,title):
        rows=[x for x in rows_sum if x["feature"]==key]; rows.sort(key=lambda x: x["avg_eng_score"], reverse=True)
        lines.append(f"\n## {title}\n"); 
        for x in rows: lines.append(f"- {x['bucket']}: avg_score={x['avg_eng_score']} (n={x['n_posts']})")
    for k,t in [("style","Performance by Style"),("cta","Performance by CTA Type"),("emoji","Emoji Count in Title"),("len","Title Length"),("number","Numbers / % / $ Present"),("question","Question Mark Present"),("bullets","Bullets Present in Description"),("time","Local Post Time Bucket")]: sec(k,t)
    lines+=["\n## Next experiments\n","- Double down on top style + top CTA next week.","- If **Numbers** bucket wins, include a % or $ in the X line.","- Bias schedule toward the best time bucket for a week."]
    open(OUT_MD,"w",encoding="utf-8").write("\n".join(lines))
    brief=["# Career Forge — Analytics Brief for ChatGPT\n","We generate self-contained, emoji-forward posts twice daily. Below are feature averages, including **style** and **CTA**.\n","## Feature Summary (averages)\n"]
    for r in rows_sum: brief.append(f"- {r['feature']} :: {r['bucket']} => avg_score={r['avg_eng_score']} (n={r['n_posts']})")
    brief+=["\n## Ask ChatGPT\n","Using the summary and top posts, propose 5 editing rules to maximize engagement, incl. 1 rec for **style mix** and 1 for **CTA**.","\n## Top Posts (samples)\n"]
    for r in top5: brief.append(f"- {r['title_sample']}  | score={r['eng_score']} | emojis={r['title_emoji_ct']} | len={r['title_len']} | style={r['style']} | cta={r['cta']}")
    open(OUT_CHAT,"w",encoding="utf-8").write("\n".join(brief))
    print("Analytics written.")

if __name__=="__main__": main()
