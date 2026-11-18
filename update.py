import json, re, html, os, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [
    ("NPR", "https://feeds.npr.org/1001/rss.xml"),
    ("BBC", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
]
PER_FEED = 5
UA = {"User-Agent": "Mozilla/5.0 (news-bot)"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()

def clean(t):
    t = re.sub(r"<[^>]+>", "", html.unescape(t or ""))
    return re.sub(r"\s+", " ", t).strip()

def tr(text):
    if not text:
        return ""
    params = {"q": text[:300], "langpair": "en|uz"}
    if os.environ.get("MYMEMORY_EMAIL"):
        params["de"] = os.environ["MYMEMORY_EMAIL"]
    try:
        d = json.loads(get("https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(params)))
        out = d["responseData"]["translatedText"]
        if str(d.get("responseStatus")) == "200" and out and "MYMEMORY WARNING" not in out:
            return out
    except Exception as e:
        print("translate error:", e)
    return text

items = []
for name, url in FEEDS:
    try:
        root = ET.fromstring(get(url))
    except Exception as e:
        print("feed error", name, e)
        continue
    for it in root.iter("item"):
        if sum(1 for x in items if x["source"] == name) >= PER_FEED:
            break
        title = clean(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        desc = clean(it.findtext("description"))[:250]
        if not title or not link:
            continue
        items.append({
            "source": name,
            "title": tr(title),
            "summary": tr(desc),
            "link": link,
            "date": (it.findtext("pubDate") or "")[:16],
        })

if items:
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "items": items},
                  f, ensure_ascii=False, indent=1)
    print("saved", len(items))
else:
    print("no items; keeping old news.json")
