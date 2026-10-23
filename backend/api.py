"""נתיבי ה-API: קריאה ציבורית, העלאה ומחיקה למנהל בלבד."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from shared_auth import require_role

from .media import maybe_transcode
from . import audio_intake
from .publish import publish, require_token, resolve_date
from .storage import MEDIA_TYPES, RETENTION_DAYS, Storage, StorageError, safe_name, today

MAX_UPLOAD_BYTES = 1024 * 1024 * 1024   # 1GB לקובץ — WAV ארוך עדיין נכנס


def build_router(storage: Storage) -> APIRouter:
    router = APIRouter()
    admin = Depends(require_role("admin"))

    def guard(fn, *args):
        try:
            return fn(*args)
        except StorageError as e:
            raise HTTPException(400, str(e)) from e

    # ───────── ציבורי ─────────
    @router.get("/api/health")
    def health():
        return {"ok": True}

    @router.get("/api/issues")
    def list_issues():
        return {"issues": storage.list_days(), "today": today().isoformat(),
                "retention_days": RETENTION_DAYS}

    @router.get("/api/issues/{day}")
    def get_issue(day: str):
        info = guard(storage.day_info, day)
        if not (info["newsletter"] or info["podcasts"] or info["materials"]):
            raise HTTPException(404, "אין גיליון לתאריך הזה")
        return info

    @router.get("/files/{day}/{kind}/{name}", include_in_schema=False)
    def get_file(day: str, kind: str, name: str):
        try:
            path = storage.file_path(day, kind, name)
        except StorageError as e:
            raise HTTPException(404, str(e)) from e
        resp = FileResponse(str(path), media_type=MEDIA_TYPES.get(path.suffix.lower()))
        if path.suffix.lower() == ".html":
            # HTML שהועלה מוצג בארגז חול — בלי סקריפטים, גם בגישה ישירה
            resp.headers["Content-Security-Policy"] = (
                "sandbox allow-popups allow-popups-to-escape-sandbox")
        if kind == "materials" and path.suffix.lower() in (".docx",):
            resp.headers["Content-Disposition"] = "attachment"
        return resp

    # ───────── מנהל ─────────
    @router.post("/api/issues/{day}/upload")
    def upload_chunk(day: str, kind: str = Form(...), name: str = Form(...),
                     index: int = Form(...), total: int = Form(...),
                     chunk: UploadFile = File(...), _admin=admin):
        """העלאה בחתיכות (Cloudflare חוסם בקשות מעל 100MB).
        הלקוח שולח את החתיכות לפי הסדר; בחתיכה האחרונה הקובץ נשמר במקומו."""
        if kind not in ("newsletter", "podcasts", "materials"):
            raise HTTPException(400, "סוג לא מוכר")
        if total < 1 or not 0 <= index < total:
            raise HTTPException(400, "מספור חתיכות לא תקין")
        name = safe_name(name)
        part = guard(storage.upload_tmp, day) / f"{kind}__{name}.part"
        with open(part, "wb" if index == 0 else "ab") as f:
            while block := chunk.file.read(1024 * 1024):
                f.write(block)
        if part.stat().st_size > MAX_UPLOAD_BYTES:
            part.unlink(missing_ok=True)
            raise HTTPException(413, "הקובץ גדול מדי")
        if index < total - 1:
            return {"ok": True, "received": index + 1}
        return _finish(part, day, kind, name)

    def _finish(part: Path, day: str, kind: str, name: str) -> dict:
        try:
            if kind == "newsletter":
                storage.save_newsletter(day, part, Path(name).suffix)
                return {"ok": True, "name": name}
            if kind == "podcasts":
                part, name = maybe_transcode(part, name)
            return {"ok": True, "name": storage.save_file(day, kind, part, name)}
        except StorageError as e:
            raise HTTPException(400, str(e)) from e
        finally:
            part.unlink(missing_ok=True)

    class Paste(BaseModel):
        kind: str             # newsletter | materials
        text: str
        title: str = ""

    @router.post("/api/issues/{day}/paste")
    def paste(day: str, body: Paste, _admin=admin):
        """הדבקת טקסט ישר מהצ'אט של גרוק — בלי לשמור קובץ קודם."""
        text = body.text.strip()
        if not text:
            raise HTTPException(400, "הטקסט ריק")
        if body.kind == "materials":
            return {"ok": True, "name": guard(storage.save_text_material, day, body.title, text)}
        if body.kind != "newsletter":
            raise HTTPException(400, "סוג לא מוכר")
        return {"ok": True, "kind": guard(storage.publish_text, day, text)}

    class Publish(BaseModel):
        content: str | dict
        date: str = ""
        podcasts: list | None = None

    @router.post("/api/publish")
    def publish_rest(body: Publish, request: Request):
        """פרסום אוטומטי (סקריפטים / בדיקות) — Authorization: Bearer <TACT_NEWS_PUBLISH_TOKEN>.
        גרוק עצמו מפרסם דרך /mcp, עם אותו טוקן ואותה לוגיקה."""
        require_token(request.headers.get("authorization"))
        try:
            return publish(storage, body.content, body.date, body.podcasts)
        except StorageError as e:
            raise HTTPException(400, str(e)) from e

    @router.post("/api/publish/audio")
    def publish_audio(request: Request, file: UploadFile = File(...), title: str = Form(""),
                      date: str = Form("")):
        """העלאת קובץ אודיו עם טוקן הפרסום (multipart: file, title, date)."""
        require_token(request.headers.get("authorization"))
        try:
            day = resolve_date(storage, date, None)
            return audio_intake.save_upload(storage, day, file.file, file.filename or "audio.mp3", title)
        except StorageError as e:
            raise HTTPException(400, str(e)) from e

    @router.delete("/api/issues/{day}")
    def delete_day(day: str, _admin=admin):
        guard(storage.delete_day, day)
        return {"ok": True}

    @router.delete("/api/issues/{day}/{kind}/{name}")
    def delete_file(day: str, kind: str, name: str, _admin=admin):
        guard(storage.delete_file, day, kind, name)
        return {"ok": True}

    return router
