"""אחסון הגיליונות — תיקייה לכל יום, ומחיקה אוטומטית אחרי RETENTION_DAYS.

    database/issues/2026-10-23/
        newsletter.json | newsletter.html | newsletter.pdf   ← הניוזלטר (אחד בלבד)
        podcasts/<קבצי אודיו>                               ← פרקים מ-NotebookLM
        materials/<קבצים>                                    ← חומר הרקע ל-NotebookLM
"""
import json
import os
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Jerusalem")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "14"))

KINDS = ("newsletter", "podcasts", "materials")
NEWSLETTER_EXTS = (".json", ".html", ".pdf")
AUDIO_EXTS = (".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac", ".aif", ".aiff", ".webm")
MATERIAL_EXTS = (".md", ".txt", ".pdf", ".html", ".docx", ".json")

MEDIA_TYPES = {
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".ogg": "audio/ogg",
    ".opus": "audio/ogg", ".wav": "audio/wav", ".flac": "audio/flac", ".aif": "audio/aiff",
    ".aiff": "audio/aiff", ".webm": "audio/webm",
    ".json": "application/json", ".html": "text/html; charset=utf-8", ".pdf": "application/pdf",
    ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UNSAFE = re.compile(r"[^\w\s\-.()—–,'!&+]", re.UNICODE)


class StorageError(ValueError):
    """שגיאה שמוצגת למשתמש כמו שהיא (400)."""


class Storage:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / "issues"
        self.root.mkdir(parents=True, exist_ok=True)

    # ───────── paths & validation ─────────
    def day_dir(self, day: str, create: bool = False) -> Path:
        if not _DATE_RE.match(day or ""):
            raise StorageError("תאריך לא תקין (YYYY-MM-DD)")
        try:
            date.fromisoformat(day)
        except ValueError as e:
            raise StorageError("תאריך לא תקין") from e
        path = self.root / day
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def file_path(self, day: str, kind: str, name: str) -> Path:
        """נתיב לקובץ קיים — או StorageError. מגן מפני ../ ושמות מזויפים."""
        if kind not in KINDS or safe_name(name) != name:
            raise StorageError("קובץ לא קיים")
        base = self.day_dir(day)
        path = (base / name) if kind == "newsletter" else (base / kind / name)
        if kind == "newsletter" and not name.startswith("newsletter."):
            raise StorageError("קובץ לא קיים")
        if not path.is_file():
            raise StorageError("קובץ לא קיים")
        return path

    # ───────── reading ─────────
    def list_days(self) -> list[dict]:
        days = []
        for d in sorted(self.root.iterdir(), reverse=True):
            if d.is_dir() and _DATE_RE.match(d.name):
                info = self.day_info(d.name)
                if info["newsletter"] or info["podcasts"] or info["materials"]:
                    days.append(_summary(info))
        return days

    def day_info(self, day: str) -> dict:
        base = self.day_dir(day)
        newsletter = None
        for ext in NEWSLETTER_EXTS:
            p = base / f"newsletter{ext}"
            if p.is_file():
                newsletter = {"kind": ext[1:], "name": p.name,
                              "url": file_url(day, "newsletter", p.name)}
                if ext == ".json":
                    try:
                        newsletter["data"] = json.loads(p.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        newsletter["data"] = None
                break
        return {
            "date": day,
            "expires": expires_on(day),
            "newsletter": newsletter,
            "podcasts": _list_files(base / "podcasts", day, "podcasts"),
            "materials": _list_files(base / "materials", day, "materials"),
        }

    # ───────── writing ─────────
    def save_newsletter(self, day: str, src: Path, ext: str) -> None:
        """מחליף את הניוזלטר של היום (יש רק אחד לכל יום)."""
        ext = ext.lower()
        if ext not in NEWSLETTER_EXTS:
            raise StorageError("ניוזלטר: JSON, HTML או PDF בלבד")
        base = self.day_dir(day, create=True)
        if ext == ".json":
            data = parse_newsletter_json(src.read_text(encoding="utf-8-sig"))
            self._extract_embedded_material(day, data)
            src.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        for old in NEWSLETTER_EXTS:
            (base / f"newsletter{old}").unlink(missing_ok=True)
        shutil.move(str(src), base / f"newsletter{ext}")

    def save_file(self, day: str, kind: str, src: Path, name: str) -> str:
        name = safe_name(name)
        ext = Path(name).suffix.lower()
        allowed = AUDIO_EXTS if kind == "podcasts" else MATERIAL_EXTS
        if kind not in ("podcasts", "materials") or ext not in allowed:
            raise StorageError(f"סוג קובץ לא נתמך: {ext or 'ללא סיומת'}")
        folder = self.day_dir(day, create=True) / kind
        folder.mkdir(exist_ok=True)
        shutil.move(str(src), folder / name)
        return name

    def save_text_material(self, day: str, title: str, text: str) -> str:
        name = safe_name((title or "חומר ל-NotebookLM").strip()) + ".md"
        folder = self.day_dir(day, create=True) / "materials"
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(text, encoding="utf-8")
        return name

    def _extract_embedded_material(self, day: str, data: dict) -> None:
        """שדה notebooklm אופציונלי ב-JSON → נשמר כקובץ חומר נפרד."""
        material = data.pop("notebooklm", None)
        if isinstance(material, str) and material.strip():
            self.save_text_material(day, "חומר ל-NotebookLM", material)
        elif isinstance(material, list):
            for i, part in enumerate(material, 1):
                if isinstance(part, dict) and str(part.get("text", "")).strip():
                    self.save_text_material(day, part.get("title") or f"חומר {i}", part["text"])

    def delete_day(self, day: str) -> None:
        shutil.rmtree(self.day_dir(day), ignore_errors=True)

    def delete_file(self, day: str, kind: str, name: str) -> None:
        self.file_path(day, kind, name).unlink()

    def upload_tmp(self, day: str) -> Path:
        tmp = self.day_dir(day, create=True) / ".uploads"
        tmp.mkdir(exist_ok=True)
        return tmp

    # ───────── retention ─────────
    def purge_expired(self) -> list[str]:
        """מוחק ימים ישנים מ-RETENTION_DAYS. מחזיר את התאריכים שנמחקו."""
        cutoff = today() - timedelta(days=RETENTION_DAYS)
        removed = []
        for d in self.root.iterdir():
            if d.is_dir() and _DATE_RE.match(d.name):
                try:
                    if date.fromisoformat(d.name) < cutoff:
                        shutil.rmtree(d, ignore_errors=True)
                        removed.append(d.name)
                except ValueError:
                    continue
        return removed


# ───────── helpers ─────────
def today() -> date:
    return datetime.now(TZ).date()


def expires_on(day: str) -> str:
    return (date.fromisoformat(day) + timedelta(days=RETENTION_DAYS)).isoformat()


def file_url(day: str, kind: str, name: str) -> str:
    from urllib.parse import quote
    return f"/files/{day}/{kind}/{quote(name)}"


def safe_name(name: str) -> str:
    """שם קובץ בטוח: בלי נתיבים, בלי תווים מוזרים, לא מתחיל בנקודה. עברית מותרת."""
    name = Path(str(name or "").replace("\\", "/")).name
    name = _UNSAFE.sub("_", name).strip().lstrip(".")
    return name[:150] or "file"


def strip_code_fences(text: str) -> str:
    """גרוק עוטף לפעמים ב-```json … ``` — מסירים את העטיפה."""
    text = text.strip()
    m = re.match(r"^```[\w-]*\s*\n(.*)\n```\s*$", text, re.DOTALL)
    return m.group(1).strip() if m else text


def parse_newsletter_json(text: str) -> dict:
    try:
        data = json.loads(strip_code_fences(text))
    except ValueError as e:
        raise StorageError(f"ה-JSON לא תקין: {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("sections"), list):
        raise StorageError('ה-JSON חייב להכיל "sections" — רשימת קטגוריות')
    for s in data["sections"]:
        if not isinstance(s, dict) or not isinstance(s.get("items"), list):
            raise StorageError('לכל קטגוריה צריך "name" ו-"items"')
        for item in s["items"]:
            if not isinstance(item, dict) or not item.get("title"):
                raise StorageError(f'ידיעה בלי "title" בקטגוריה "{s.get("name", "?")}"')
    return data


def _list_files(folder: Path, day: str, kind: str) -> list[dict]:
    if not folder.is_dir():
        return []
    return [
        {"name": p.name, "title": " ".join(p.stem.replace("_", " ").split()), "size": p.stat().st_size,
         "ext": p.suffix.lower()[1:], "url": file_url(day, kind, p.name)}
        for p in sorted(folder.iterdir()) if p.is_file()
    ]


def _summary(info: dict) -> dict:
    nl = info["newsletter"] or {}
    data = nl.get("data") or {}
    items = sum(len(s.get("items", [])) for s in data.get("sections", []))
    return {
        "date": info["date"],
        "expires": info["expires"],
        "title": data.get("title") or "",
        "newsletter": nl.get("kind"),
        "items": items,
        "podcasts": len(info["podcasts"]),
        "materials": len(info["materials"]),
    }
