"""אישור לפני פרסום — לתחומים עם review=True (Longeviora: אפליקציה לקהל, apps.py).

Claude וגרוק כותבים כרגיל. הציבור (/api/issues, /files) רואה רק את מה שהמנהל אישר:
צילום של היום ברגע האישור, ב-<day>/.approved.json. שינוי אחרי האישור (עדכון הערב, תיקון של גרוק)
נשמר אבל ממתין — היום נשאר ציבורי בגרסה המאושרת עד אישור חוזר.
"""
import json
from datetime import datetime

from .storage import TZ, Storage, StorageError, expires_on, has_content, summary, _DATE_RE

SNAP = ".approved.json"
FIELDS = ("newsletter", "podcasts", "materials", "links", "youtube", "guides", "papers")


def _snap(storage: Storage, day: str) -> dict | None:
    p = storage.day_dir(day) / SNAP
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
    except (OSError, ValueError):
        return None


def _content(info: dict) -> str:
    return json.dumps({k: info.get(k) for k in FIELDS}, ensure_ascii=False, sort_keys=True)


def approve(storage: Storage, day: str, by: str = "") -> dict:
    info = storage.day_info(day)
    if not has_content(info):
        raise StorageError("אין מה לאשר ביום הזה")
    snap = {"approved_at": datetime.now(TZ).isoformat(timespec="seconds"), "by": by,
            "info": {k: info[k] for k in FIELDS}}
    p = storage.day_dir(day) / SNAP
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
    return state(storage, day)


def revoke(storage: Storage, day: str) -> dict:
    (storage.day_dir(day) / SNAP).unlink(missing_ok=True)
    return state(storage, day)


def _approved(storage: Storage, day: str, snap: dict) -> dict:
    """התוכן המאושר, בלי קבצי אודיו שכבר נמחקו (AUDIO_RETENTION_DAYS) — מחיקה כזו לא "משנה" את היום."""
    info = dict(snap["info"])
    info["podcasts"] = [f for f in info.get("podcasts") or []
                        if (storage.day_dir(day) / "podcasts" / f.get("name", "")).is_file()]
    return info


def state(storage: Storage, day: str) -> dict:
    """pending = יש תוכן ולא אושר · approved = הציבור רואה בדיוק את מה שיש · changed = אושר, ויש שינויים שממתינים."""
    info = storage.day_info(day)
    snap = _snap(storage, day)
    if not snap:
        status = "pending" if has_content(info) else "empty"
    else:
        status = "approved" if _content(_approved(storage, day, snap)) == _content(info) else "changed"
    return {"date": day, "status": status, "approved_at": (snap or {}).get("approved_at", ""),
            "live": summary(info),
            "public": summary(public_info(storage, day)) if snap else None}


def public_info(storage: Storage, day: str) -> dict | None:
    """היום כפי שהציבור רואה אותו — הגרסה המאושרת, או None."""
    snap = _snap(storage, day)
    if not snap:
        return None
    info = _approved(storage, day, snap)
    return {"topic": storage.topic, "date": day, "expires": expires_on(day),
            **{k: info.get(k) or ([] if k != "newsletter" else None) for k in FIELDS}}


def public_days(storage: Storage) -> list[dict]:
    out = []
    for d in _days(storage):
        info = public_info(storage, d)
        if info and has_content(info):
            out.append(summary(info))
    return out


def file_allowed(storage: Storage, day: str, kind: str, name: str) -> bool:
    """קובץ ציבורי רק אם הוא בגרסה המאושרת (אותו שם ואותו גודל). את הניוזלטר האפליקציה קוראת מה-JSON."""
    info = public_info(storage, day)
    if not info or kind == "newsletter":
        return False
    try:
        size = storage.file_path(day, kind, name).stat().st_size
    except StorageError:
        return False
    return any(f.get("name") == name and f.get("size") == size for f in info.get(kind) or [])


def overview(storage: Storage) -> list[dict]:
    return [state(storage, d) for d in _days(storage)]


def _days(storage: Storage) -> list[str]:
    return sorted((d.name for d in storage.root.iterdir() if d.is_dir() and _DATE_RE.match(d.name)), reverse=True)
