"""אחסון הגיליונות — תיקייה לכל יום בכל תחום, ומחיקה אוטומטית אחרי RETENTION_DAYS.

    database/issues/<topic>/2026-10-23/
        newsletter.json | newsletter.html | newsletter.pdf   ← לשונית "ניוזלטר" (אחד בלבד)
        podcasts/<קבצי אודיו> + links.json + materials/      ← לשונית "פודקאסטים"
        youtube.json                                          ← לשונית "YouTube"
        guides.json                                           ← לשונית "מדריכים" (גם YouTube)
        papers.json                                           ← לשונית "מאמרים" (מאמרים אקדמיים)
        tech.json                                             ← לשונית "טכנולוגיה" (פיתוחים חדשים)
"""
import json
import os
import re
import shutil
from urllib.parse import parse_qs, quote, urlparse
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
    def __init__(self, data_dir: Path, topic: str) -> None:
        self.topic = topic
        self.root = data_dir / "issues" / topic
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
                if has_content(info):
                    days.append(_summary(info))
        return days

    def day_info(self, day: str) -> dict:
        base = self.day_dir(day)
        newsletter = None
        for ext in NEWSLETTER_EXTS:
            p = base / f"newsletter{ext}"
            if p.is_file():
                newsletter = {"kind": ext[1:], "name": p.name,
                              "url": file_url(self.topic, day, "newsletter", p.name)}
                if ext == ".json":
                    try:
                        newsletter["data"] = json.loads(p.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        newsletter["data"] = None
                break
        return {
            "topic": self.topic,
            "date": day,
            "expires": expires_on(day),
            "newsletter": newsletter,
            "podcasts": _list_files(base / "podcasts", self.topic, day, "podcasts"),
            "materials": _list_files(base / "materials", self.topic, day, "materials"),
            "links": self.load_list(day, "links"),
            "youtube": self.load_list(day, "youtube"),
            "guides": self.load_list(day, "guides"),
            "papers": self.load_list(day, "papers"),
            "tech": self.load_list(day, "tech"),
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
            # רשימות שגרוק שולח בתוך הניוזלטר → ללשוניות שלהן
            if isinstance(data.get("podcasts"), list):
                self.save_list(day, "links", data.pop("podcasts"))
            for which in ("youtube", "guides", "papers", "tech"):
                if isinstance(data.get(which), list):
                    self.save_list(day, which, data.pop(which))
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

    def publish_text(self, day: str, text: str) -> str:
        """ניוזלטר כטקסט (JSON או HTML) — מהדבקה, מ-REST או מ-MCP. מחזיר את הסוג."""
        bare = strip_code_fences(text or "")
        if bare.startswith("{"):
            ext = ".json"
        elif bare.lstrip().startswith("<"):
            ext = ".html"
        else:
            raise StorageError("הניוזלטר צריך להיות JSON (או HTML)")
        tmp = self.upload_tmp(day) / f"paste{ext}"
        tmp.write_text(bare, encoding="utf-8")
        try:
            self.save_newsletter(day, tmp, ext)
        finally:
            tmp.unlink(missing_ok=True)
        return ext[1:]

    # ───────── link lists: links (פרקי פודקאסט) · youtube · guides (מדריכים) · papers (מאמרים) ─────────
    def load_list(self, day: str, which: str) -> list[dict]:
        p = self.day_dir(day) / f"{which}.json"
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []
        except (OSError, ValueError):
            return []

    def save_list(self, day: str, which: str, items: list) -> int:
        """מחליף את הרשימה של היום. מחזיר כמה נשמרו."""
        parse = {"links": parse_link, "youtube": parse_video, "guides": parse_video, "papers": parse_paper,
                 "tech": parse_tech}[which]
        clean = [parse(x) for x in items]
        (self.day_dir(day, create=True) / f"{which}.json").write_text(
            json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(clean)

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


def file_url(topic: str, day: str, kind: str, name: str) -> str:
    return f"/files/{topic}/{day}/{kind}/{quote(name)}"


def has_content(info: dict) -> bool:
    return any(info[k] for k in ("newsletter", "podcasts", "materials", "links", "youtube", "guides", "papers", "tech"))


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


def parse_link(x) -> dict:
    """קישור לפרק: {title, url, show?, description?, duration_minutes?}. audio=True אם זה קובץ אודיו ישיר."""
    if not isinstance(x, dict) or not str(x.get("title", "")).strip():
        raise StorageError('לכל פרק צריך "title"')
    url = str(x.get("url", "")).strip()
    if not re.match(r"^https?://", url):
        raise StorageError(f'קישור לא תקין בפרק "{x["title"]}"')
    try:
        minutes = float(x.get("duration_minutes") or 0) or None
    except (TypeError, ValueError):
        minutes = None
    path = url.split("?")[0].lower()
    return {
        "title": str(x["title"]).strip()[:200],
        "url": url,
        "show": str(x.get("show") or "").strip()[:120],
        "description": str(x.get("description") or "").strip()[:600],
        "duration_minutes": minutes,
        "audio": path.endswith(AUDIO_EXTS),
    }


_YT_HOSTS = ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be")
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def youtube_id(url: str) -> str | None:
    """watch?v= · youtu.be/ · /shorts/ · /live/ · /embed/ → מזהה הסרטון (11 תווים)."""
    p = urlparse(url)
    if p.hostname == "youtu.be":
        vid = p.path.strip("/").split("/")[0]
    elif p.path == "/watch":
        vid = (parse_qs(p.query).get("v") or [""])[0]
    else:
        parts = p.path.strip("/").split("/")
        vid = parts[1] if len(parts) > 1 and parts[0] in ("shorts", "live", "embed") else ""
    return vid if _YT_ID.match(vid or "") else None


def parse_video(x) -> dict:
    """סרטון YouTube: {title, url, channel?, description?, duration_minutes?}."""
    if not isinstance(x, dict) or not str(x.get("title", "")).strip():
        raise StorageError('לכל סרטון צריך "title"')
    url = str(x.get("url", "")).strip()
    host = (urlparse(url).hostname or "").lower()
    if not re.match(r"^https?://", url) or host not in _YT_HOSTS:
        raise StorageError(f'"{x["title"]}": צריך קישור של YouTube (youtube.com / youtu.be)')
    try:
        minutes = float(x.get("duration_minutes") or 0) or None
    except (TypeError, ValueError):
        minutes = None
    return {
        "title": str(x["title"]).strip()[:200],
        "url": url,
        "video_id": youtube_id(url),
        "channel": str(x.get("channel") or x.get("show") or "").strip()[:120],
        "description": str(x.get("description") or "").strip()[:600],
        "duration_minutes": minutes,
    }


_ARXIV_ABS = re.compile(r"^https?://(?:www\.)?arxiv\.org/abs/([\w.\-/]+?)(?:v\d+)?/?$")


def _text(x: dict, key: str, limit: int) -> str:
    return str(x.get(key) or "").strip()[:limit]


def parse_paper(x) -> dict:
    """מאמר אקדמי: {title, url, authors?, venue?, published?, summary?, details?, pdf_url?}."""
    if not isinstance(x, dict) or not str(x.get("title", "")).strip():
        raise StorageError('לכל מאמר צריך "title"')
    url = str(x.get("url", "")).strip()
    if not re.match(r"^https?://", url):
        raise StorageError(f'קישור לא תקין במאמר "{x["title"]}"')
    pdf = str(x.get("pdf_url") or "").strip()
    if not pdf and (m := _ARXIV_ABS.match(url)):
        pdf = f"https://arxiv.org/pdf/{m.group(1)}"
    authors = x.get("authors") or ""
    if isinstance(authors, list):
        authors = ", ".join(str(a).strip() for a in authors if str(a).strip())
    return {
        "title": _text(x, "title", 300),
        "url": url,
        "pdf_url": pdf if re.match(r"^https?://", pdf) else "",
        "authors": str(authors).strip()[:300],
        "venue": _text(x, "venue", 120),
        "published": _text(x, "published", 40),
        "summary": _text(x, "summary", 1200),
        "details": _text(x, "details", 4000),
    }


def parse_tech(x) -> dict:
    """פיתוח טכנולוגי: {title, url, summary?, details?, source_name?, company?} — מוצג כמו ידיעה בניוזלטר."""
    if not isinstance(x, dict) or not str(x.get("title", "")).strip():
        raise StorageError('לכל פיתוח צריך "title"')
    url = str(x.get("url") or x.get("source_url") or "").strip()
    if not re.match(r"^https?://", url):
        raise StorageError(f'קישור לא תקין בפיתוח "{x["title"]}"')
    return {
        "title": _text(x, "title", 300),
        "source_url": url,
        "source_name": _text(x, "source_name", 120),
        "company": _text(x, "company", 120),
        "summary": _text(x, "summary", 1200),
        "details": _text(x, "details", 4000),
    }


def _display_title(stem: str) -> str:
    """"0 תקציר קולי" → "תקציר קולי": המספר בתחילת השם קובע רק את הסדר בנגן."""
    title = " ".join(stem.replace("_", " ").split())
    return re.sub(r"^\d{1,2}\s*[-.)]?\s+", "", title) or title


def _list_files(folder: Path, topic: str, day: str, kind: str) -> list[dict]:
    if not folder.is_dir():
        return []
    return [
        {"name": p.name, "title": _display_title(p.stem), "size": p.stat().st_size,
         "ext": p.suffix.lower()[1:], "url": file_url(topic, day, kind, p.name)}
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
        "podcasts": len(info["podcasts"]) + len(info["links"]),
        "materials": len(info["materials"]),
        "youtube": len(info["youtube"]),
        "guides": len(info["guides"]),
        "papers": len(info["papers"]),
        "tech": len(info["tech"]),
    }
