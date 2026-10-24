"""פרסום אוטומטי — הלוגיקה המשותפת ל-MCP (גרוק) ול-REST (/api/publish).

אימות: טוקן אחד, TACT_NEWS_PUBLISH_TOKEN, ב-Authorization: Bearer. אין לו גישה למחיקה או לניהול.
"""
import hmac
import json
import os

from fastapi import HTTPException

from .storage import Storage, StorageError, strip_code_fences, today

SITE = "https://tact-news.newavera.co.il"


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
            youtube: list | None = None, guides: list | None = None, papers: list | None = None,
            tech: list | None = None) -> dict:
    """content = ה-JSON של הניוזלטר (מחרוזת או אובייקט). podcasts/youtube/guides = רשימות קישורים (לא חובה)."""
    if isinstance(content, dict):
        text, data = json.dumps(content, ensure_ascii=False), content
    else:
        text = strip_code_fences(str(content or ""))
        try:
            data = json.loads(text) if text.startswith("{") else None
        except ValueError:
            data = None  # publish_text יחזיר את שגיאת ה-JSON המדויקת
    day = resolve_date(storage, date, data)
    kind = storage.publish_text(day, text)
    if podcasts:
        storage.save_list(day, "links", podcasts)
    if youtube:
        storage.save_list(day, "youtube", youtube)
    if guides:
        storage.save_list(day, "guides", guides)
    if papers:
        storage.save_list(day, "papers", papers)
    if tech:
        storage.save_list(day, "tech", tech)
    return status(storage, day) | {"ok": True, "kind": kind}


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
    """which = links (פרקי פודקאסט) | youtube | guides | papers | tech. מחליף את הרשימה של היום."""
    what = {"links": "פרקים", "youtube": "סרטונים", "guides": "מדריכים", "papers": "מאמרים",
            "tech": "פיתוחים"}[which]
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
        "tech": [t["title"] for t in info["tech"]],
        "url": page_url(storage, day),
    }
