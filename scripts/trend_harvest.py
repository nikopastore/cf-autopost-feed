#!/usr/bin/env python3
import os, json, feedparser
from datetime import datetime, timezone
OUT="content/trends.json"; SRC="content/news_feeds.txt"
def normalize(e): return {"title": (e.get("title") or "").strip(), "link": (e.get("link") or "").strip(), "published": e.get("published") or e.get("updated") or ""}
def main():
    feeds=[]; 
    if os.path.exists(SRC): feeds=[ln.strip() for ln in open(SRC,encoding="utf-8") if ln.strip() and not ln.startswith("#")]
    items=[]
    for url in feeds:
        try:
            d=feedparser.parse(url)
            for e in d.entries[:10]:
                it=normalize(e)
                if it["title"]: items.append(it)
        except Exception: pass
    seen=set(); uniq=[]
    for it in items:
        k=it["title"].lower()
        if k not in seen: uniq.append(it); seen.add(k)
    payload={"updated": datetime.now(timezone.utc).isoformat(), "count": len(uniq), "items": uniq[:30]}
    os.makedirs("content",exist_ok=True); json.dump(payload, open(OUT,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Wrote", OUT)
if __name__=="__main__": main()
