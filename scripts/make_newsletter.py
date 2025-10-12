#!/usr/bin/env python3
import csv, os
from datetime import date
IN_FEAT="analytics/feature_summary.csv"; IN_POSTS="analytics/posts_features.csv"; OUT="newsletter.md"
def read_csv(p): 
    if not os.path.exists(p): return []
    return list(csv.DictReader(open(p,encoding="utf-8")))
def main():
    feat=read_csv(IN_FEAT); posts=read_csv(IN_POSTS)
    top=sorted(posts, key=lambda r: float(r.get("eng_score") or 0), reverse=True)[:7]
    lines=[f"# Career Forge — Weekly Digest ({date.today().isoformat()})","", "## Top Posts"]
    for r in top: lines.append(f"- **{r['title_sample']}**  \n  score={r['eng_score']} | style={r['style']} | cta={r['cta']}")
    lines+=["","## What worked (averages)"]
    def sec(key, label):
        rows=[x for x in feat if x["feature"]==key]; rows.sort(key=lambda x: float(x["avg_eng_score"] or 0), reverse=True)
        lines.append(f"### {label}"); 
        for x in rows[:6]: lines.append(f"- {x['bucket']}: {x['avg_eng_score']}")
    for k,l in [("style","Styles"),("cta","CTAs"),("emoji","Emojis in title"),("len","Title length")]: sec(k,l)
    lines+=["","## Next tests","- Double down on top style + top CTA next week.","- Add a number (% or $) in 3 posts to validate the Numbers effect."]
    open(OUT,"w",encoding="utf-8").write("\n".join(lines)); print("Wrote", OUT)
if __name__=="__main__": main()
