import json, re, html, os, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
    ("AQSh", "NPR", "https://feeds.npr.org/1001/rss.xml"),
    ("AQSh", "BBC", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"),
    ("AQSh", "CNN", "http://rss.cnn.com/rss/cnn_us.rss"),
    ("Siyosat", "NPR", "https://feeds.npr.org/1014/rss.xml"),
    ("Iqtisod", "NPR", "https://feeds.npr.org/1006/rss.xml"),
    ("Iqtisod", "BBC", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Texnologiya", "NPR", "https://feeds.npr.org/1019/rss.xml"),
    ("Texnologiya", "BBC", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Sport", "ESPN", "https://www.espn.com/espn/rss/news"),
    ("Sport", "BBC", "https://feeds.bbci.co.uk/sport/rss.xml"),
    ("Dunyo", "NPR", "https://feeds.npr.org/1004/rss.xml"),
    ("Dunyo", "BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
]
PER_FEED = 4
UA = {"User-Agent": "Mozilla/5.0 (news-bot)"}
quota_ok = True

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()

def clean(t):
    t = re.sub(r"<[^>]+>", "", html.unescape(t or ""))
    return re.sub(r"\s+", " ", t).strip()

def tr(text):
    global quota_ok
    if not text:
        return "", True
    if not quota_ok:
        return text, False
    params = {"q": text[:300], "langpair": "en|uz"}
    if os.environ.get("MYMEMORY_EMAIL"):
        params["de"] = os.environ["MYMEMORY_EMAIL"]
    try:
        d = json.loads(get("https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(params)))
        out = d["responseData"]["translatedText"]
        if str(d.get("responseStatus")) == "200" and out and "MYMEMORY WARNING" not in out:
            time.sleep(0.3)
            return html.unescape(out), True
        quota_ok = False
    except Exception as e:
        print("translate error:", e)
    return text, False

old = {}
prev_items = None
try:
    with open("news.json", encoding="utf-8") as f:
        prev_items = json.load(f)["items"]
    for it in prev_items:
        old[it["link"]] = it
except Exception:
    pass

items, seen = [], set()
for cat, src, url in FEEDS:
    try:
        root = ET.fromstring(get(url))
    except Exception as e:
        print("feed error", src, cat, e)
        continue
    n = 0
    for it in root.iter("item"):
        if n >= PER_FEED:
            break
        title = clean(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        if not title or not link or link in seen:
            continue
        seen.add(link)
        n += 1
        try:
            dt = parsedate_to_datetime(it.findtext("pubDate"))
            ts, date = int(dt.timestamp()), dt.strftime("%Y-%m-%d")
        except Exception:
            ts, date = 0, ""
        if link in old and old[link].get("ok", True):
            item = dict(old[link])
            item.setdefault("ok", True)
        else:
            desc = clean(it.findtext("description"))[:200]
            t, ok1 = tr(title)
            s, ok2 = tr(desc)
            item = {"title": t, "summary": s, "link": link, "ok": ok1 and ok2}
        item.update({"cat": cat, "source": src, "ts": ts, "date": date})
        items.append(item)

if items:
    items.sort(key=lambda x: x["ts"], reverse=True)
    if items == prev_items:
        print("no changes")
    else:
        with open("news.json", "w", encoding="utf-8") as f:
            json.dump({"updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "items": items},
                      f, ensure_ascii=False, indent=1)
        print("saved", len(items), "pending:", sum(1 for x in items if not x.get("ok", True)))
else:
    print("no items; keeping old news.json")
