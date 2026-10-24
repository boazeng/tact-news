"""תחומי על — לכל תחום ימים ותוכן משלו: database/issues/<topic>/<date>/...

תחום חדש (ספורט, פוליטיקה...) = שורה אחת ב-TOPICS. הראשון ברשימה הוא ברירת המחדל.
גרוק מפרסם לתחום עם הפרמטר topic (ברירת מחדל: הראשון).
"""
import logging
import re
import shutil
from pathlib import Path

from .storage import Storage, StorageError

logger = logging.getLogger("tact-news")

TOPICS = [
    {"id": "ai", "name": "בינה מלאכותית"},
    # {"id": "sport", "name": "ספורט"},
    # {"id": "politics", "name": "פוליטיקה"},
]
DEFAULT_TOPIC = TOPICS[0]["id"]
_DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Topics:
    def __init__(self, data_dir: Path) -> None:
        _migrate_legacy(data_dir / "issues")
        self._stores = {t["id"]: Storage(data_dir, t["id"]) for t in TOPICS}

    def get(self, topic: str | None) -> Storage:
        store = self._stores.get((topic or DEFAULT_TOPIC).strip().lower())
        if not store:
            raise StorageError(f"תחום לא מוכר: {topic}. התחומים באתר: {', '.join(self._stores)}")
        return store

    def all(self) -> list[Storage]:
        return list(self._stores.values())

    @staticmethod
    def listing() -> list[dict]:
        return [dict(t, default=t["id"] == DEFAULT_TOPIC) for t in TOPICS]


def _migrate_legacy(root: Path) -> None:
    """לפני התחומים כל יום ישב ב-issues/<date>. מעבירים פעם אחת לתחום ברירת המחדל."""
    if not root.is_dir():
        return
    legacy = [d for d in root.iterdir() if d.is_dir() and _DATE_DIR.match(d.name)]
    if not legacy:
        return
    target = root / DEFAULT_TOPIC
    target.mkdir(parents=True, exist_ok=True)
    for d in legacy:
        if not (target / d.name).exists():
            shutil.move(str(d), target / d.name)
    logger.info("הועברו %d ימים לתחום %s", len(legacy), DEFAULT_TOPIC)
