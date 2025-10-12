#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import csv, os, textwrap
IN="analytics/posts_features.csv"; OUTDIR="carousels/latest"
def latest_title():
    if not os.path.exists(IN): return "Career Forge"
    rows=list(csv.DictReader(open(IN,encoding="utf-8")))
    rows.sort(key=lambda r: r.get("pubDate_local") or "", reverse=True)
    return rows[0]["title_sample"] if rows else "Career Forge"
def wrap(text, width):
    words=text.split(); lines=[]; line=[]
    for w in words:
        line.append(w)
        if len(" ".join(line))>=width: lines.append(" ".join(line)); line=[]
    if line: lines.append(" ".join(line))
    return lines
def slide(text, idx):
    W,H=1080,1350; img=Image.new("RGB",(W,H),(17,19,24)); d=ImageDraw.Draw(img)
    try: font=ImageFont.truetype("DejaVuSans.ttf", 56)
    except: font=ImageFont.load_default()
    y=120
    for ln in wrap(text, 32):
        d.text((80,y), ln, font=font, fill=(230,233,238)); y+=70
    os.makedirs(OUTDIR, exist_ok=True)
    path=f"{OUTDIR}/slide{idx}.png"; img.save(path); print("Wrote", path)
def main():
    title=latest_title()
    chunks=[ "Career Forge — Key Idea", title, "How to use it today:", "• Apply on your resume\n• Try next interview\n• Share a win", "Follow @CareerForge" ]
    for i,t in enumerate(chunks, start=1): slide(t, i)
if __name__=="__main__": main()
