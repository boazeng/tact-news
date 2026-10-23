"""פרסום אוטומטי — הלוגיקה המשותפת ל-MCP (גרוק) ול-REST (/api/publish).

אימות: טוקן אחד, TACT_NEWS_PUBLISH_TOKEN, ב-Authorization: Bearer. אין לו גישה למחיקה או לניהול.
"""
import hmac
import json
import os

from fastapi import HTTPException

from .storage import Storage, StorageError, strip_code_fences, today


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


def publish(storage: Storage, content, date: str = "", podcasts: list | None = None) -> dict:
    """content = ה-JSON של הניוזלטר (מחרוזת או אובייקט). podcasts = רשימת קישורים (לא חובה)."""
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
        storage.save_links(day, podcasts)
    info = storage.day_info(day)
    items = sum(len(s.get("items", [])) for s in ((info["newsletter"] or {}).get("data") or {}).get("sections", []))
    return {
        "ok": True,
        "date": day,
        "kind": kind,
        "items": items,
        "podcast_links": len(info["links"]),
        "materials": len(info["materials"]),
        "url": f"https://tact-news.newavera.co.il/d/{day}",
    }


def add_podcasts(storage: Storage, podcasts, date: str = "") -> dict:
    if isinstance(podcasts, str):
        try:
            podcasts = json.loads(strip_code_fences(podcasts))
        except ValueError as e:
            raise StorageError(f"רשימת הפרקים אינה JSON תקין: {e}") from e
    if not isinstance(podcasts, list) or not podcasts:
        raise StorageError("צריך רשימה של פרקים")
    day = resolve_date(storage, date, None)
    return {"ok": True, "date": day, "podcast_links": storage.save_links(day, podcasts)}
