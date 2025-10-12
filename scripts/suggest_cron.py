#!/usr/bin/env python3
import csv, os
from datetime import time, timedelta, datetime, timezone
OUT_MD="analytics/cron_suggestion.md"
BUCKET_TIMES_LOCAL={"early-morning": time(7,40),"morning": time(10,10),"early-afternoon": time(14,10),"late-afternoon": time(16,40),"evening": time(19,10),"night": time(21,10)}
def to_utc_str(t):
    dt=datetime(2000,1,1,t.hour,t.minute, tzinfo=timezone(timedelta(hours=-7)))
    du=dt.astimezone(timezone.utc); return f"{du.minute:02d} {du.hour:02d} * * *"
def best_buckets():
    p="analytics/feature_summary.csv"
    if not os.path.exists(p): return []
    rows=[r for r in csv.DictReader(open(p,encoding="utf-8")) if r["feature"]=="time"]
    rows.sort(key=lambda r: float(r["avg_eng_score"] or 0), reverse=True)
    return [(r["bucket"], float(r["avg_eng_score"] or 0), int(r["n_posts"])) for r in rows]
def main():
    b=best_buckets(); sel=[bk for bk,_,_ in b[:2] if bk in BUCKET_TIMES_LOCAL] or ["early-afternoon","morning"]
    crons=[to_utc_str(BUCKET_TIMES_LOCAL[x]) for x in sel]
    lines=["# Cron Suggestion","Based on average engagement by **local time bucket** (America/Phoenix).","",
           "## Top buckets"]
    for bk,avg,n in b[:6]: lines.append(f"- {bk}: avg_score={avg:.2f} (n={n})")
    lines+=["","## Proposed crons (UTC)"]
    for c,bk in zip(crons, sel): lines.append(f"- `{c}`  ← {bk}")
    os.makedirs("analytics", exist_ok=True); open(OUT_MD,"w",encoding="utf-8").write("\n".join(lines)); print("Wrote", OUT_MD)
if __name__=="__main__": main()
