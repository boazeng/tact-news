"""TACT News — אתר החדשות היומי.

1. מגיש את ה-SPA (dist/).
2. API לגיליונות: ניוזלטר (JSON/HTML/PDF) + פרקי פודקאסט + חומר NotebookLM לכל יום.
3. כל יום נמחק אוטומטית אחרי RETENTION_DAYS (ברירת מחדל 14).
4. כניסת Google (shared-auth): הקריאה פתוחה לכולם, ההעלאה והמחיקה — admin בלבד.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# ── env resolution (אותו דפוס כמו tact-main) ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_override = os.getenv("TACT_NEWS_ENV_FILE")
_shared = PROJECT_ROOT.parent / "env" / ".env"
_local = PROJECT_ROOT / ".env"
if _override and Path(_override).exists():
    _env_path = Path(_override)
elif _shared.exists():
    _env_path = _shared
else:
    _env_path = _local
load_dotenv(_env_path, override=True)

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from shared_auth import install_auth  # noqa: E402

from .api import build_router  # noqa: E402
from .storage import Storage  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tact-news")

DIST_DIR = PROJECT_ROOT / "dist"
DATA_DIR = Path(os.getenv("TACT_NEWS_DATA_DIR", str(PROJECT_ROOT / "database")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
storage = Storage(DATA_DIR)


async def _retention_loop():
    """מחיקת ימים ישנים — בעלייה ואז פעם בשעה."""
    while True:
        try:
            removed = await asyncio.to_thread(storage.purge_expired)
            if removed:
                logger.info("נמחקו גיליונות ישנים: %s", ", ".join(sorted(removed)))
        except Exception:  # noqa: BLE001
            logger.exception("מחיקת גיליונות ישנים נכשלה")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_app):
    task = asyncio.create_task(_retention_loop())
    yield
    task.cancel()


app = FastAPI(title="TACT News", docs_url=None, redoc_url=None, lifespan=lifespan)

# כל הנתיבים ציבוריים (public_prefixes="/"); פעולות כתיבה נעולות ב-require_role("admin").
install_auth(
    app,
    db_path=str(DATA_DIR / "auth.db"),
    redirect_uri=os.getenv("AUTH_REDIRECT_URI", "https://tact-news.newavera.co.il/auth/callback"),
    initial_users=[{"email": "boazen@gmail.com", "role": "admin"}],
    public_prefixes=("/",),
)
app.include_router(build_router(storage))


# ───────────────── serve the built SPA ─────────────────
def _serve(path: Path, *, immutable: bool) -> FileResponse:
    resp = FileResponse(str(path))
    if immutable:
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        # index.html חייב להתרענן, אחרת דפדפנים נתקעים על build ישן
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    """קובץ אמיתי אם קיים, אחרת index.html (ניתוב בצד הלקוח)."""
    if full_path.startswith(("api/", "files/")):
        # בלי זה כל נתיב API שגוי מחזיר HTML עם 200 ובדיקות בריאות "עוברות"
        raise HTTPException(404, "לא נמצא")
    candidate = (DIST_DIR / full_path).resolve()
    if full_path and candidate.is_file() and DIST_DIR.resolve() in candidate.parents:
        return _serve(candidate, immutable=full_path.startswith("assets/"))
    return _serve(DIST_DIR / "index.html", immutable=False)
