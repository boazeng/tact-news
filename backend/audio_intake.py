"""קבלת קבצי אודיו מגרוק (תקציר קולי, פרקי NotebookLM) — שלוש דרכים, כי לא ידוע מה עובד אצלו:

1. from_url    — גרוק נותן כתובת לקובץ, השרת מוריד בעצמו.
2. base64      — הקובץ עצמו בתוך קריאת הכלי, בחתיכות (MCP מעביר רק טקסט).
3. save_upload — multipart רגיל ל-POST /api/publish/audio (אם יש לו סביבת קוד שיודעת לשלוח קבצים).

בכל הדרכים: WAV נדחס ל-M4A, והפרק נכנס ל-podcasts/ של היום ומתנגן בנגן של האתר.
"""
import base64
import binascii
import ipaddress
import re
import socket
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .media import maybe_transcode
from .storage import AUDIO_EXTS, Storage, StorageError, safe_name

MAX_BYTES = 500 * 1024 * 1024
MAX_CHUNK_B64 = 4 * 1024 * 1024          # ~3MB אודיו לכל קריאה
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_CT_EXT = {"audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a",
           "audio/aac": ".aac", "audio/ogg": ".ogg", "audio/opus": ".opus", "audio/wav": ".wav",
           "audio/x-wav": ".wav", "audio/wave": ".wav", "audio/webm": ".webm", "audio/flac": ".flac"}


def _filename(title: str, ext: str) -> str:
    ext = ext.lower() if ext.lower() in AUDIO_EXTS else ".mp3"
    stem = safe_name(title or "פרק")
    if stem.lower().endswith(AUDIO_EXTS):
        stem = Path(stem).stem
    return stem + ext


def _store(storage: Storage, day: str, part: Path, title: str, ext: str) -> dict:
    name = _filename(title, ext)
    head = part.read_bytes()[:16]
    if head.lstrip().startswith((b"<", b"{")):
        part.unlink(missing_ok=True)
        raise StorageError("זה לא קובץ אודיו (התקבל דף HTML או JSON) — צריך קישור ישיר ל-mp3/m4a/wav")
    try:
        part, name = maybe_transcode(part, name)
        saved = storage.save_file(day, "podcasts", part, name)
    finally:
        part.unlink(missing_ok=True)
    return {"ok": True, "date": day, "name": saved,
            "url": f"https://tact-news.newavera.co.il/d/{day}"}


def _public_host(host: str) -> None:
    """לא מורידים מכתובות פנימיות (localhost, רשת ביתית, מטא-דאטה של ענן)."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as e:
        raise StorageError(f"לא מצליח לפתור את הכתובת {host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise StorageError("כתובת פנימית — אסור")


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    """גם הפניה (redirect) לא יכולה להוביל לכתובת פנימית."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _public_host(urlparse(newurl).hostname or "")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def from_url(storage: Storage, day: str, url: str, title: str) -> dict:
    p = urlparse(url or "")
    if p.scheme not in ("http", "https") or not p.hostname:
        raise StorageError("צריך כתובת http/https")
    if "notebooklm.google" in p.hostname:
        raise StorageError("קישור של NotebookLM הוא דף אינטרנט שדורש התחברות, לא קובץ. "
                           "צריך להוריד את האודיו ולהעלות אותו (upload_audio_base64) או לתת קישור ישיר לקובץ")
    _public_host(p.hostname)
    opener = urllib.request.build_opener(_SafeRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (tact-news)"})
    part = storage.upload_tmp(day) / f"url_{abs(hash(url))}.part"
    try:
        with opener.open(req, timeout=120) as r:
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype.startswith("text/html"):
                raise StorageError("הכתובת מחזירה דף אינטרנט ולא קובץ אודיו — צריך קישור ישיר לקובץ")
            size = 0
            with open(part, "wb") as f:
                while block := r.read(1024 * 1024):
                    size += len(block)
                    if size > MAX_BYTES:
                        raise StorageError("הקובץ גדול מ-500MB")
                    f.write(block)
    except StorageError:
        part.unlink(missing_ok=True)
        raise
    except OSError as e:
        part.unlink(missing_ok=True)
        raise StorageError(f"ההורדה נכשלה: {e}") from e
    ext = Path(p.path).suffix.lower()
    if ext not in AUDIO_EXTS:
        ext = _CT_EXT.get(ctype, ".mp3")
    return _store(storage, day, part, title, ext)


def base64_chunk(storage: Storage, day: str, upload_id: str, index: int, total: int,
                 data_b64: str, title: str, filename: str) -> dict:
    if not _ID_RE.match(upload_id or ""):
        raise StorageError("upload_id: אותיות/ספרות/מקף בלבד, עד 64 תווים")
    if total < 1 or not 0 <= index < total:
        raise StorageError("index חייב להיות בין 0 ל-total-1")
    data_b64 = re.sub(r"^data:[^,]*,", "", (data_b64 or "").strip())
    if len(data_b64) > MAX_CHUNK_B64:
        raise StorageError("חתיכה גדולה מדי — עד 4MB של base64 לכל קריאה")
    try:
        data = base64.b64decode(data_b64, validate=False)
    except (binascii.Error, ValueError) as e:
        raise StorageError(f"base64 לא תקין: {e}") from e
    part = storage.upload_tmp(day) / f"b64_{upload_id}.part"
    if index > 0 and not part.exists():
        raise StorageError("חסרה החתיכה הראשונה (index 0) — מתחילים מחדש")
    with open(part, "wb" if index == 0 else "ab") as f:
        f.write(data)
    if part.stat().st_size > MAX_BYTES:
        part.unlink(missing_ok=True)
        raise StorageError("הקובץ גדול מ-500MB")
    if index < total - 1:
        return {"ok": True, "received": index + 1, "of": total}
    return _store(storage, day, part, title, Path(filename or "").suffix or ".mp3")


def save_upload(storage: Storage, day: str, fileobj, filename: str, title: str) -> dict:
    part = storage.upload_tmp(day) / f"rest_{abs(hash(filename))}.part"
    size = 0
    with open(part, "wb") as f:
        while block := fileobj.read(1024 * 1024):
            size += len(block)
            if size > MAX_BYTES:
                f.close()
                part.unlink(missing_ok=True)
                raise StorageError("הקובץ גדול מ-500MB")
            f.write(block)
    return _store(storage, day, part, title or Path(filename).stem, Path(filename or "").suffix)
