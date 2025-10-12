#!/usr/bin/env python3
import csv, json, os, math
IN_SUM="analytics/feature_summary.csv"; OUT="ops/bandit.json"
def load_bandit(p): 
    try: return json.load(open(p,"r",encoding="utf-8"))
    except: return {"style_weights":{},"cta_weights":{}}
def rows(feature):
    if not os.path.exists(IN_SUM): return []
    with open(IN_SUM, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r["feature"]==feature]
def softmax(scores, temp=0.6):
    if not scores: return {}
    mx=max(scores.values()); ex={k: math.exp((v-mx)/max(1e-6,temp)) for k,v in scores.items()}
    s=sum(ex.values()) or 1; return {k: round(ex[k]/s,3) for k in ex}
def main():
    s={r["bucket"]: float(r["avg_eng_score"] or 0) for r in rows("style")} or {"template_drop":1,"checklist":1}
    c={r["bucket"]: float(r["avg_eng_score"] or 0) for r in rows("cta")} or {"question":1,"challenge":1}
    band=load_bandit(OUT); band["style_weights"].update(softmax(s,0.6)); band["cta_weights"].update(softmax(c,0.6))
    os.makedirs("ops", exist_ok=True); json.dump(band, open(OUT,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Updated", OUT)
if __name__=="__main__": main()
