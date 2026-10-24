"""תחומי על — לכל תחום ימים ותוכן משלו: database/issues/<topic>/<date>/...

הרשימה נשמרת ב-database/topics.json ומנוהלת מדף הניהול (הוספה, עריכה, סדר, מחיקה). הראשון = ברירת המחדל.
בתיאור אפשר להדגיש: **מודגש** (חשוב) ו-==מסומן== (עדיפות עליונה).
לכל תחום יש description — מה לכסות בו. גרוק קורא את הרשימה (list_topics) כל בוקר ומפיק תוכן לכל תחום,
כך שתחום חדש באתר מתחיל לקבל תוכן בלי לשנות לו את ההוראות.
"""
import json
import logging
import re
import shutil
import threading
from pathlib import Path

from .storage import Storage, StorageError

logger = logging.getLogger("tact-news")

# הרשימה ההתחלתית — רק כשאין עדיין topics.json
SEED = [
    {"id": "ai", "name": "בינה מלאכותית", "color": "#6d28d9",
     "description": "חדשות בינה מלאכותית: מודלים ומעבדות, בטיחות AI, סייבר, ביג טק ועסקים, שבבים וחומרה, "
                    "סטארטאפים והייטק ישראלי."},
    {"id": "tech", "name": "טכנולוגיה", "color": "#0b72b9",
     "description": "פיתוחים טכנולוגיים חדשים — מוצרים, המצאות ופריצות דרך: חומרה, שבבים, אנרגיה, רפואה, "
                    "תחבורה, חלל, תקשורת. לא ידיעות בינה מלאכותית (הן בתחום ai)."},
]
LEGACY_TOPIC = "ai"   # לשם הועברו הימים מלפני התחומים, ולשם מפנות כתובות /files ישנות

MAX_DESCRIPTION = 1500
_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,23}$")
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# מזהה תחום הוא גם תחילת כתובת באתר — אסור שיתנגש בנתיבים קיימים
_RESERVED = {"admin", "d", "api", "files", "auth", "login", "logout", "assets", "mcp",
             "emergency-login", "no-access", "favicon", "static"}


class Topics:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.file = data_dir / "topics.json"
        self._lock = threading.Lock()
        _migrate_legacy(data_dir / "issues")
        self._list = self._load()
        self._stores = {t["id"]: Storage(data_dir, t["id"]) for t in self._list}

    # ───────── קריאה ─────────
    def get(self, topic: str | None) -> Storage:
        """topic ריק → ברירת המחדל (הראשון ברשימה)."""
        tid = (topic or "").strip().lower() or self._list[0]["id"]
        store = self._stores.get(tid)
        if not store:
            raise StorageError(f"תחום לא מוכר: {topic}. התחומים באתר: {', '.join(self._stores)}")
        return store

    def all(self) -> list[Storage]:
        return list(self._stores.values())

    def listing(self) -> list[dict]:
        return [dict(t, default=i == 0) for i, t in enumerate(self._list)]

    # ───────── ניהול ─────────
    def add(self, tid: str, name: str, color: str = "", description: str = "") -> dict:
        tid = (tid or "").strip().lower()
        name = (name or "").strip()
        if not _ID_RE.match(tid):
            raise StorageError("מזהה: אותיות אנגליות קטנות, ספרות ומקף, 2–24 תווים, מתחיל באות (למשל sport)")
        if tid in _RESERVED:
            raise StorageError(f'המזהה "{tid}" שמור לאתר — בחר מזהה אחר')
        if not name or len(name) > 40:
            raise StorageError("צריך שם לתחום (עד 40 תווים)")
        if color and not _COLOR_RE.match(color):
            raise StorageError("צבע בפורמט #RRGGBB")
        with self._lock:
            if any(t["id"] == tid for t in self._list):
                raise StorageError(f'כבר יש תחום עם המזהה "{tid}"')
            if any(t["name"] == name for t in self._list):
                raise StorageError(f'כבר יש תחום בשם "{name}"')
            topic = {"id": tid, "name": name, "color": color or "#475569",
                     "description": (description or "").strip()[:MAX_DESCRIPTION]}
            self._list.append(topic)
            self._save()
            self._stores[tid] = Storage(self.data_dir, tid)
        logger.info("נוסף תחום %s (%s)", tid, name)
        return topic

    def update(self, tid: str, name: str, color: str = "", description: str = "") -> dict:
        """עריכת שם, צבע ותיאור. המזהה לא משתנה — הכתובות והימים השמורים קשורים אליו."""
        name = (name or "").strip()
        if not name or len(name) > 40:
            raise StorageError("צריך שם לתחום (עד 40 תווים)")
        if color and not _COLOR_RE.match(color):
            raise StorageError("צבע בפורמט #RRGGBB")
        with self._lock:
            topic = next((t for t in self._list if t["id"] == tid), None)
            if not topic:
                raise StorageError(f"תחום לא מוכר: {tid}")
            if any(t["name"] == name and t["id"] != tid for t in self._list):
                raise StorageError(f'כבר יש תחום בשם "{name}"')
            topic.update(name=name, color=color or topic.get("color") or "#475569",
                         description=(description or "").strip()[:MAX_DESCRIPTION])
            self._save()
        return topic

    def reorder(self, ids: list[str]) -> None:
        """סדר חדש — חייב לכלול כל תחום פעם אחת בדיוק. הראשון הופך לברירת המחדל."""
        with self._lock:
            current = {t["id"]: t for t in self._list}
            if sorted(ids) != sorted(current):
                raise StorageError("הסדר חייב לכלול כל תחום פעם אחת בדיוק")
            self._list = [current[i] for i in ids]
            self._save()

    def delete(self, tid: str) -> None:
        """מוחק את התחום וכל הימים שלו. חייב להישאר לפחות תחום אחד."""
        with self._lock:
            if not any(t["id"] == tid for t in self._list):
                raise StorageError(f"תחום לא מוכר: {tid}")
            if len(self._list) == 1:
                raise StorageError("זה התחום האחרון — חייב להישאר לפחות תחום אחד")
            self._list = [t for t in self._list if t["id"] != tid]
            self._save()
            store = self._stores.pop(tid)
        shutil.rmtree(store.root, ignore_errors=True)
        logger.info("נמחק תחום %s וכל הימים שלו", tid)

    # ───────── קובץ ─────────
    def _load(self) -> list[dict]:
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
            if isinstance(data, list) and data and all(_ID_RE.match(str(t.get("id", ""))) for t in data):
                return data
        except (OSError, ValueError):
            pass
        topics = [dict(t) for t in SEED]
        self.file.write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")
        return topics

    def _save(self) -> None:
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._list, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.file)


def _migrate_legacy(root: Path) -> None:
    """לפני התחומים כל יום ישב ב-issues/<date>. מעבירים פעם אחת לתחום ai."""
    if not root.is_dir():
        return
    legacy = [d for d in root.iterdir() if d.is_dir() and _DATE_DIR.match(d.name)]
    if not legacy:
        return
    target = root / LEGACY_TOPIC
    target.mkdir(parents=True, exist_ok=True)
    for d in legacy:
        if not (target / d.name).exists():
            shutil.move(str(d), target / d.name)
    logger.info("הועברו %d ימים לתחום %s", len(legacy), LEGACY_TOPIC)
