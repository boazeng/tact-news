"""איסוף ידיעות מפידים — בלי מודל ובלי עלות.

מקור בתחום (שדה sources, שורה לכל מקור): "שם | כתובת-פיד". שורה בלי "|" = שם בלבד (לגרוק), לא נאסף.
כתובת יכולה להיות פיד RSS/Atom רגיל או חיפוש של Google News (news.google.com/rss/search?q=site:...).
לידיעות מ-Google News הקישור הוא הפניה של גוגל — resolve_url() מתרגם אותה לכתובת הכתבה עצמה.
"""
import html
import json
import logging
import re
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import feedparser

logger = logging.getLogger("tact-news")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130 Safari/537.36")
TIMEOUT = 20
MAX_PER_FEED = 40
GOOGLE_GAP = 1.5      # שניות בין בקשות לגוגל — אחרת 429
_google_lock = threading.Lock()
_google_last = [0.0]


def parse_sources(text: str) -> list[dict]:
    out = []
    for line in (text or "").splitlines():
        name, sep, url = line.partition("|")
        url = url.strip()
        if sep and url.startswith(("http://", "https://")):
            out.append({"name": name.strip(), "url": url})
    return out


def _get(url: str, data: bytes | None = None, headers: dict | None = None, limit: int = 4_000_000) -> tuple[str, bytes]:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 — כתובות מרשימת המקורות שהמנהל הגדיר
        return r.geturl(), r.read(limit)


def _clean(text: str, limit: int) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _when(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def _read_feed(src: dict) -> list[dict]:
    _, raw = _get(src["url"])
    feed = feedparser.parse(raw)
    gnews = "news.google.com" in src["url"]
    items = []
    for e in feed.entries[:MAX_PER_FEED]:
        title = _clean(e.get("title", ""), 300)
        link = e.get("link", "")
        if not title or not link:
            continue
        if gnews:  # "כותרת - שם המקור" → כותרת
            title = re.sub(r"\s+-\s+[^-]{2,60}$", "", title)
        items.append({
            "source": src["name"], "title": title, "url": link, "gnews": gnews,
            "published": _when(e),
            "snippet": "" if gnews else _clean(e.get("summary", ""), 400),
        })
    return items


def collect(sources: list[dict], since: datetime) -> tuple[list[dict], dict]:
    """כל הידיעות מהפידים שפורסמו אחרי since. מחזיר (ידיעות, {שם מקור: מספר או 'שגיאה'})."""
    stats: dict = {}
    found: list[dict] = []

    def one(src):
        try:
            return src, _read_feed(src), None
        except Exception as e:  # noqa: BLE001 — פיד אחד שנפל לא עוצר את השאר
            return src, [], f"{type(e).__name__}"

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(one, sources))
    # שגיאה רגעית (DNS של הקונטיינר תחת עומס, timeout) → ניסיון נוסף אחד, בזה אחר זה
    results = [one(src) if err else (src, items, err) for src, items, err in results]
    for src, items, err in results:
        fresh = [i for i in items if i["published"] and i["published"] >= since]
        stats[src["name"]] = err or len(fresh)
        found.extend(fresh)
    # אותה כתבה בשני פידים → פעם אחת
    seen, unique = set(), []
    for i in sorted(found, key=lambda x: x["published"], reverse=True):
        key = norm_title(i["title"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(i)
    return unique, stats


def norm_title(title: str) -> str:
    return re.sub(r"[^\w]+", " ", (title or "").lower()).strip()[:80]


# ───────── Google News → כתובת הכתבה ─────────
def _google_slot() -> None:
    """בקשה אחת לגוגל בכל פעם, ברווח של GOOGLE_GAP."""
    with _google_lock:
        wait = _google_last[0] + GOOGLE_GAP - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _google_last[0] = time.monotonic()


def resolve_url(url: str) -> str:
    """לא הצליח (429, שינוי אצל גוגל) → קישור גוגל, שגם הוא פותח את הכתבה בדפדפן."""
    if "news.google.com" not in url or "/articles/" not in url:
        return url
    try:
        _google_slot()
        aid = url.split("/articles/")[1].split("?")[0]
        _, page = _get("https://news.google.com/articles/" + aid, limit=800_000)
        page = page.decode("utf-8", "ignore")
        sg = re.search(r'data-n-a-sg="([^"]+)"', page)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page)
        if not (sg and ts):
            return url
        inner = ["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None,
                                 0, 1], "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
                 aid, int(ts.group(1)), sg.group(1)]
        _google_slot()
        body = "f.req=" + urllib.parse.quote(json.dumps([[["Fbv4je", json.dumps(inner), None, "generic"]]]))
        _, resp = _get("https://news.google.com/_/DotsSplashUi/data/batchexecute", data=body.encode(),
                       headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
        m = re.search(r'https?://(?!news\.google)[^\\"]+', resp.decode("utf-8", "ignore"))
        return m.group(0) if m else url
    except Exception:  # noqa: BLE001
        return url


# ───────── טקסט הכתבה (לסיכום מדויק) ─────────
def article_text(url: str, limit: int = 6000) -> str:
    """פסקאות הכתבה, או לפחות og:description. ריק אם האתר חוסם."""
    try:
        _, raw = _get(url, limit=2_000_000)
    except Exception:  # noqa: BLE001
        return ""
    page = raw.decode("utf-8", "ignore")
    page = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", page)
    paras = [_clean(p, 2000) for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", page)]
    text = " \n".join(p for p in paras if len(p) > 60)
    if len(text) < 300:
        og = re.search(r'(?is)<meta[^>]+(?:property|name)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)',
                       page)
        text = (html.unescape(og.group(1)) + "\n" + text) if og else text
    return text[:limit]
