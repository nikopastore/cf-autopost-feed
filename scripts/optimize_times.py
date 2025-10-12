#!/usr/bin/env python3
# Suggest better cron windows from analytics/posts_features.csv buckets

import csv, os, statistics, re, sys, subprocess

POSTS = "analytics/posts_features.csv"
WF = ".github/workflows/post.yml"
BRANCH = "optimize-times"

def load_posts():
    if not os.path.exists(POSTS): return []
    with open(POSTS, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def best_buckets(rows):
    # Avg score by hour_bucket, fallback to defaults
    by = {}
    for r in rows:
        b = r.get("hour_bucket") or "unknown"
        by.setdefault(b, []).append(float(r.get("eng_score") or 0))
    avgs = [(b, (sum(v)/len(v))) for b,v in by.items() if b!="unknown" and v]
    if not avgs: return ["morning","late-afternoon"]
    avgs.sort(key=lambda x: x[1], reverse=True)
    return [avgs[0][0], avgs[1][0]] if len(avgs)>1 else [avgs[0][0], "late-afternoon"]

def to_utc_min(bucket):
    # crude mapping from local bucket to UTC minute-of-day (choose fixed hh:mm)
    m = {
        "early-morning": ("14","40"), # 07:40 Phoenix
        "morning": ("15","10"),       # 08:10
        "early-afternoon": ("21","10"),# 14:10
        "late-afternoon": ("21","40"), # 14:40
        "evening": ("2","5"),         # 19:05 (next day UTC-ish) — keep simple
        "night": ("9","5")
    }
    return m.get(bucket, ("15","40"))

def rewrite_cron(wf_path, buckets):
    with open(wf_path,"r",encoding="utf-8") as f:
        y = f.read()
    # replace the two cron lines inside 'on: schedule:'
    b1,b2 = buckets
    h1,m1 = to_utc_min(b1); h2,m2 = to_utc_min(b2)
    y = re.sub(r'cron:\s*".*?"', "", y)  # remove all old crons
    y = re.sub(r'(schedule:\s*\n)(\s*-\s*cron:.*\n)*', f"schedule:\n    - cron: \"{m1} {h1} * * *\"\n    - cron: \"{m2} {h2} * * *\"\n", y)
    return y

def main():
    posts = load_posts()
    buckets = best_buckets(posts)
    print("Suggested buckets:", buckets)
    new_y = rewrite_cron(WF, buckets)

    # Create PR
    subprocess.run(["git","checkout","-b",BRANCH], check=False)
    with open(WF,"w",encoding="utf-8") as f: f.write(new_y)
    subprocess.run(["git","add",WF], check=True)
    subprocess.run(["git","config","user.name","cf-bot"], check=True)
    subprocess.run(["git","config","user.email","cf-bot@users.noreply.github.com"], check=True)
    subprocess.run(["git","commit","-m","perf(cron): optimize posting times from analytics [skip ci]"], check=True)
    subprocess.run(["git","push","--set-upstream","origin",BRANCH], check=True)
    print("Pushed branch:", BRANCH)
    # Leave PR creation to GitHub's UI or enable create-pull-request action if desired.

if __name__ == "__main__":
    main()
