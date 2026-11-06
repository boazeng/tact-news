"""פרסום אוטומטי — הלוגיקה המשותפת ל-MCP (גרוק) ול-REST (/api/publish).

אימות: טוקן אחד, TACT_NEWS_PUBLISH_TOKEN, ב-Authorization: Bearer. אין לו גישה למחיקה או לניהול.
מ-2026-11-02 את הניוזלטר בונה Claude (evening_agent.py). גרוק לא מפרסם ניוזלטר — רק ממלא את "מעקב פייסבוק"
(set_section) וקורא את הגיליון בשביל NotebookLM (newsletter).
"""
import hmac
import json
import os
import threading

from fastapi import HTTPException

from .storage import Storage, StorageError, strip_code_fences, today

SITE = "https://tact-news.newavera.co.il"
FACEBOOK = "מעקב פייסבוק"
# כל כתיבה לגיליון קיים (Claude ממזג, גרוק מחליף את פייסבוק) — קוראים מחדש וכותבים בתוך המנעול
NEWSLETTER_LOCK = threading.Lock()


def token_ok(header: str | None) -> bool:
    expected = os.getenv("TACT_NEWS_PUBLISH_TOKEN", "")
    got = (header or "").removeprefix("Bearer ").removeprefix("bearer ").strip()
    return bool(expected) and hmac.compare_digest(got.encode(), expected.encode())


def require_token(header: str | None) -> None:
    if not token_ok(header):
        raise HTTPException(401, "טוקן פרסום חסר או שגוי")


def resolve_date(storage: Storage, date: str, data: dict | None) -> str:
    """תאריך מפורש → ה-date שב-JSON → היום (שעון ישראל)."""
    day = (date or (data or {}).get("date") or today().isoformat()).strip()
    storage.day_dir(day)  # מאמת פורמט
    return day


def page_url(storage: Storage, day: str, tab: str = "") -> str:
    return f"{SITE}/{storage.topic}/{day}" + (f"/{tab}" if tab else "")


def publish(storage: Storage, content, date: str = "", podcasts: list | None = None,
            youtube: list | None = None, guides: list | None = None, papers: list | None = None) -> dict:
    """REST /api/publish. ניוזלטר (content) כבר לא מתקבל — Claude בונה אותו. הרשימות כן."""
    if content:
        raise StorageError("את הניוזלטר בונה עכשיו Claude, ואי אפשר להחליף אותו. לפייסבוק: set_facebook_section. "
                           "לפודקאסטים, YouTube, מדריכים ומאמרים: add_podcast_links / add_youtube_links / "
                           "add_guide_links / add_papers")
    day = resolve_date(storage, date, None)
    for which, items in (("links", podcasts), ("youtube", youtube), ("guides", guides), ("papers", papers)):
        if items:
            storage.save_list(day, which, items)
    return status(storage, day) | {"ok": True}


def _as_list(value, what: str) -> list:
    if isinstance(value, str):
        try:
            value = json.loads(strip_code_fences(value))
        except ValueError as e:
            raise StorageError(f"רשימת ה{what} אינה JSON תקין: {e}") from e
    if not isinstance(value, list) or not value:
        raise StorageError(f"צריך רשימה של {what}")
    return value


def add_list(storage: Storage, which: str, items, date: str = "") -> dict:
    """which = links (פרקי פודקאסט) | youtube | guides | papers. מחליף את הרשימה של היום."""
    what = {"links": "פרקים", "youtube": "סרטונים", "guides": "מדריכים", "papers": "מאמרים"}[which]
    day = resolve_date(storage, date, None)
    count = storage.save_list(day, which, _as_list(items, what))
    tab = "podcasts" if which == "links" else which
    return {"ok": True, "topic": storage.topic, "date": day, "saved": count, "url": page_url(storage, day, tab)}


def status(storage: Storage, day: str) -> dict:
    info = storage.day_info(day)
    data = (info["newsletter"] or {}).get("data") or {}
    return {
        "topic": storage.topic,
        "date": day,
        "published": bool(info["newsletter"]),
        "items": sum(len(s.get("items", [])) for s in data.get("sections", [])),
        "audio_files": [p["title"] for p in info["podcasts"]],
        "podcast_links": [link["title"] for link in info["links"]],
        "youtube": [v["title"] for v in info["youtube"]],
        "guides": [v["title"] for v in info["guides"]],
        "papers": [p["title"] for p in info["papers"]],
        "url": page_url(storage, day),
    }


def topic_title(name: str) -> str:
    return f"חדשות לבועז — {name}"


def issue_title(topic: dict) -> str:
    """כותרת הגיליון: באתר — "חדשות לבועז — <תחום>"; בתחום של אפליקציה אחרת (Longeviora) — שם התחום בלבד."""
    return topic["name"] if topic.get("app") else topic_title(topic["name"])


def edit_newsletter(storage: Storage, day: str, title: str, fn) -> dict:
    """קורא את הגיליון של היום (או מתחיל ריק), fn(data) משנה אותו, ושומר — הכול בתוך המנעול."""
    with NEWSLETTER_LOCK:
        nl = storage.day_info(day)["newsletter"]
        if nl and nl["kind"] != "json":
            raise StorageError(f"הגיליון של {day} הוא {nl['kind']} — אין עריכה")
        data = (nl or {}).get("data") or {"date": day, "title": title, "sections": []}
        if fn(data):
            # פייסבוק תמיד בסוף
            data["sections"] = sorted(data["sections"], key=lambda s: s.get("name") == FACEBOOK)
            storage.publish_text(day, json.dumps(data, ensure_ascii=False))
        return data


def _stories(items) -> list[dict]:
    """רשימת ידיעות (JSON או list). רשימה ריקה מותרת."""
    if isinstance(items, str):
        try:
            items = json.loads(strip_code_fences(items) or "[]")
        except ValueError as e:
            raise StorageError(f"הידיעות אינן JSON תקין: {e}") from e
    if not isinstance(items, list):
        raise StorageError("צריך רשימה של ידיעות")
    for x in items:
        if not isinstance(x, dict) or not str(x.get("title", "")).strip():
            raise StorageError('כל ידיעה צריכה "title"')
    return items


def set_section(storage: Storage, title: str, name: str, items, date: str = "") -> dict:
    """מחליף קטגוריה אחת בגיליון (פייסבוק של גרוק) — בלי לגעת בשאר. רשימה ריקה = מוחק את הקטגוריה."""
    clean = [{k: str(x.get(k, "")).strip() for k in ("title", "summary", "details", "source_url", "source_name")}
             for x in _stories(items)]
    day = resolve_date(storage, date, None)

    def apply(data):
        data["sections"] = [s for s in data.get("sections", []) if s.get("name") != name]
        if clean:
            data["sections"].append({"name": name, "items": clean})
        return True
    edit_newsletter(storage, day, title, apply)
    return status(storage, day) | {"ok": True, "saved": len(clean)}


def newsletter(storage: Storage, day: str) -> dict:
    """הגיליון המלא (בשביל NotebookLM)."""
    nl = storage.day_info(day)["newsletter"]
    return {"topic": storage.topic, "date": day, "published": bool(nl),
            "newsletter": (nl or {}).get("data"), "url": page_url(storage, day)}


PROMOTED = {"he": "מקודם", "en": "Promoted"}


def save_promoted(storage: Storage, topic: dict, items, date: str = "") -> dict:
    """פוסטים ממומנים (תחום kind=promote) — מחליף את כל הפוסטים של היום. רשימה ריקה = מוחק אותם.
    כל פוסט: title, summary, details?, source_url, source_name (= הארגון המממן), image_url?, cta_label?, section?"""
    if topic.get("kind") != "promote":
        raise StorageError(f'set_promoted רק לתחומי פוסטים ממומנים (kind=promote); "{topic["id"]}" אינו כזה')
    sections: dict[str, list[dict]] = {}
    for x in _stories(items):
        url, image = str(x.get("source_url", "")).strip(), str(x.get("image_url") or "").strip()
        if not url.startswith(("https://", "http://")):
            raise StorageError(f'"{x["title"]}": צריך source_url — הקישור של הארגון')
        if not str(x.get("source_name", "")).strip():
            raise StorageError(f'"{x["title"]}": צריך source_name — שם הארגון המממן')
        if image and not image.startswith("https://"):
            raise StorageError(f'"{x["title"]}": image_url חייב להתחיל ב-https://')
        post = {"title": str(x["title"]).strip()[:200], "summary": str(x.get("summary", "")).strip()[:1200],
                "details": str(x.get("details", "")).strip()[:4000], "source_url": url,
                "source_name": str(x["source_name"]).strip()[:120]}
        if image:
            post["image_url"] = image
        if str(x.get("cta_label") or "").strip():
            post["cta_label"] = str(x["cta_label"]).strip()[:30]
        name = str(x.get("section") or "").strip()[:40] or PROMOTED.get(topic.get("lang", "he"), PROMOTED["en"])
        sections.setdefault(name, []).append(post)
    day = resolve_date(storage, date, None)
    with NEWSLETTER_LOCK:
        if sections:
            data = {"title": topic["name"], "date": day,
                    "sections": [{"name": n, "items": v} for n, v in sections.items()]}
            storage.publish_text(day, json.dumps(data, ensure_ascii=False))
        elif (nl := storage.day_info(day)["newsletter"]):
            storage.delete_file(day, "newsletter", nl["name"])
    return status(storage, day) | {"ok": True, "saved": sum(len(v) for v in sections.values())}
