#!/usr/bin/env python3
# rss_li.xml (all) + rss_li_live.xml (1): description-focused copy for LinkedIn
import xml.etree.ElementTree as ET, re, hashlib, html, os, sys
IN_FEED="rss.xml"; OUT_ALL="rss_li.xml"; OUT_LIVE="rss_li_live.xml"
LI_SUFFIX = "#CareerForward #CareerFocused #CareerForge"
def clean(s): s=re.sub(r"<[^>]+>","",s or ""); s=html.unescape(s); return re.sub(r"\s+"," ",s).strip()
def li_text(title, desc):
    base = desc if desc else title
    base = base.strip()
    if base.lower().endswith(LI_SUFFIX.lower()):
        return base
    return (base + " " + LI_SUFFIX).strip() if base else LI_SUFFIX
def build(items, ch_src, out_path):
    root=ET.Element("rss",attrib={"version":"2.0"}); ch=ET.SubElement(root,"channel")
    for t in ["title","link","description","language","lastBuildDate","pubDate"]:
        src=ch_src.find(t); 
        if src is not None: ET.SubElement(ch,t).text=(src.text or "")
    for it in items: ch.append(it)
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True); print("Wrote", out_path)
if not os.path.exists(IN_FEED): print("rss.xml not found"); sys.exit(1)
t=ET.parse(IN_FEED); ch=t.getroot().find("channel")
items=[]
for it in ch.findall("item"):
    title=clean(it.findtext("title")); desc=clean(it.findtext("description")); link=(it.findtext("link") or "").strip()
    text=li_text(title, desc)
    n=ET.Element("item"); ET.SubElement(n,"title").text=text; ET.SubElement(n,"description").text=text
    ET.SubElement(n,"link").text=link
    base=(it.findtext("guid") or link or title or desc).encode("utf-8","ignore")
    ET.SubElement(n,"guid",attrib={"isPermaLink":"false"}).text=hashlib.sha1(base).hexdigest()
    pub=it.findtext("pubDate"); 
    if pub: ET.SubElement(n,"pubDate").text=pub
    items.append(n)
build(items, ch, OUT_ALL)
build(items[:1], ch, OUT_LIVE)
