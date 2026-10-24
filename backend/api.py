"""נתיבי ה-API: קריאה ציבורית, העלאה ומחיקה למנהל בלבד.
כל נתיב מקבל ?topic= (ברירת מחדל: התחום הראשון ב-topics.py)."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from shared_auth import require_role

from . import audio_intake
from .media import maybe_transcode
from .publish import publish, require_token, resolve_date
from .storage import MEDIA_TYPES, RETENTION_DAYS, StorageError, has_content, safe_name, today
from .topics import DEFAULT_TOPIC, Topics

MAX_UPLOAD_BYTES = 1024 * 1024 * 1024   # 1GB לקובץ — WAV ארוך עדיין נכנס


def build_router(topics: Topics) -> APIRouter:
    router = APIRouter()
    admin = Depends(require_role("admin"))

    def guard(fn, *args):
        try:
            return fn(*args)
        except StorageError as e:
            raise HTTPException(400, str(e)) from e

    def store(topic: str):
        return guard(topics.get, topic)

    # ───────── ציבורי ─────────
    @router.get("/api/health")
    def health():
        return {"ok": True}

    @router.get("/api/topics")
    def list_topics():
        return {"topics": topics.listing()}

    @router.get("/api/issues")
    def list_issues(topic: str = DEFAULT_TOPIC):
        return {"topic": topic, "issues": store(topic).list_days(), "today": today().isoformat(),
                "retention_days": RETENTION_DAYS}

    @router.get("/api/issues/{day}")
    def get_issue(day: str, topic: str = DEFAULT_TOPIC):
        info = guard(store(topic).day_info, day)
        if not has_content(info):
            raise HTTPException(404, "אין גיליון לתאריך הזה")
        return info

    def serve_file(topic: str, day: str, kind: str, name: str):
        try:
            path = topics.get(topic).file_path(day, kind, name)
        except StorageError as e:
            raise HTTPException(404, str(e)) from e
        resp = FileResponse(str(path), media_type=MEDIA_TYPES.get(path.suffix.lower()))
        if path.suffix.lower() == ".html":
            # HTML שהועלה מוצג בארגז חול — בלי סקריפטים, גם בגישה ישירה
            resp.headers["Content-Security-Policy"] = "sandbox allow-popups allow-popups-to-escape-sandbox"
        if kind == "materials" and path.suffix.lower() == ".docx":
            resp.headers["Content-Disposition"] = "attachment"
        return resp

    @router.get("/files/{topic}/{day}/{kind}/{name}", include_in_schema=False)
    def get_file(topic: str, day: str, kind: str, name: str):
        return serve_file(topic, day, kind, name)

    @router.get("/files/{day}/{kind}/{name}", include_in_schema=False)
    def get_file_legacy(day: str, kind: str, name: str):
        """קישורים מלפני התחומים."""
        return serve_file(DEFAULT_TOPIC, day, kind, name)

    # ───────── מנהל ─────────
    @router.post("/api/issues/{day}/upload")
    def upload_chunk(day: str, topic: str = DEFAULT_TOPIC, kind: str = Form(...), name: str = Form(...),
                     index: int = Form(...), total: int = Form(...),
                     chunk: UploadFile = File(...), _admin=admin):
        """העלאה בחתיכות (Cloudflare חוסם בקשות מעל 100MB).
        הלקוח שולח את החתיכות לפי הסדר; בחתיכה האחרונה הקובץ נשמר במקומו."""
        storage = store(topic)
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
    def paste(day: str, body: Paste, topic: str = DEFAULT_TOPIC, _admin=admin):
        """הדבקת טקסט ישר מהצ'אט של גרוק — בלי לשמור קובץ קודם."""
        text = body.text.strip()
        if not text:
            raise HTTPException(400, "הטקסט ריק")
        if body.kind == "materials":
            return {"ok": True, "name": guard(store(topic).save_text_material, day, body.title, text)}
        if body.kind != "newsletter":
            raise HTTPException(400, "סוג לא מוכר")
        return {"ok": True, "kind": guard(store(topic).publish_text, day, text)}

    @router.delete("/api/issues/{day}")
    def delete_day(day: str, topic: str = DEFAULT_TOPIC, _admin=admin):
        guard(store(topic).delete_day, day)
        return {"ok": True}

    @router.delete("/api/issues/{day}/{kind}/{name}")
    def delete_file(day: str, kind: str, name: str, topic: str = DEFAULT_TOPIC, _admin=admin):
        guard(store(topic).delete_file, day, kind, name)
        return {"ok": True}

    # ───────── פרסום אוטומטי (טוקן) ─────────
    class Publish(BaseModel):
        content: str | dict
        date: str = ""
        topic: str = DEFAULT_TOPIC
        podcasts: list | None = None
        youtube: list | None = None
        guides: list | None = None
        papers: list | None = None

    @router.post("/api/publish")
    def publish_rest(body: Publish, request: Request):
        """Authorization: Bearer <TACT_NEWS_PUBLISH_TOKEN>. גרוק עצמו מפרסם דרך /mcp — אותה לוגיקה."""
        require_token(request.headers.get("authorization"))
        return guard(publish, store(body.topic), body.content, body.date, body.podcasts, body.youtube, body.guides, body.papers)

    @router.post("/api/publish/audio")
    def publish_audio(request: Request, file: UploadFile = File(...), title: str = Form(""),
                      date: str = Form(""), topic: str = Form(DEFAULT_TOPIC)):
        """העלאת קובץ אודיו ללשונית הפודקאסטים (multipart: file, title, date, topic)."""
        require_token(request.headers.get("authorization"))
        storage = store(topic)

        def save():
            day = resolve_date(storage, date, None)
            return audio_intake.save_upload(storage, day, file.file, file.filename or "audio.mp3", title)
        return guard(save)

    return router
