#!/usr/bin/env python3
# Reads analytics/feature_summary.csv and updates ops/rules.json style_weights

import csv, json, os

SUM = "analytics/feature_summary.csv"
RULES = "ops/rules.json"

def load_csv(path):
    if not os.path.exists(path): return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main():
    rows = load_csv(SUM)
    style_rows = [r for r in rows if r.get("feature")=="style"]
    # Simple update: new_weight = clamp(0.6, 1.6, 1.0 + (avg/50 - 0.5)*0.6) scaled by performance
    weights = {}
    for r in style_rows:
        try:
            avg = float(r["avg_eng_score"])
        except:
            avg = 0.0
        delta = ((avg/50.0) - 0.5) * 0.6
        w = max(0.6, min(1.6, 1.0 + delta))
        weights[r["bucket"]] = round(w,2)

    rules = {}
    if os.path.exists(RULES):
        rules = json.load(open(RULES,"r",encoding="utf-8"))
    rules.setdefault("style_weights", {})
    rules["style_weights"].update(weights)
    os.makedirs(os.path.dirname(RULES), exist_ok=True)
    json.dump(rules, open(RULES,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print("Updated style_weights:", weights)

if __name__ == "__main__":
    main()
