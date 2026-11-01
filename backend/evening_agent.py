"""עדכון ערב — סוכן Claude שמוסיף לגיליון של היום ידיעות שפורסמו מאז הבוקר.

גרוק מפרסם את גיליון הבוקר. בשעה EVENING_TIME (ברירת מחדל 19:00, שעון ישראל) הסוכן עובר על כל תחום
שיש בו לשונית ניוזלטר, מחפש ברשת (בעיקר במקורות של התחום — שדה sources בתחום), ומחזיר רק ידיעות חדשות.
הקוד ממזג אותן לראש הקטגוריות עם הקידומת "🆕 עדכון ערב: " ומפרסם מחדש — שום דבר מהבוקר לא נמחק.

מפתח: ANTHROPIC_API_KEY ב-.env של האתר. יומן ריצות: database/agent_runs.json.
"""
import json
import logging
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .storage import StorageError, today
from .topics import Topics

logger = logging.getLogger("tact-news")

IL = ZoneInfo("Asia/Jerusalem")
MODEL = os.getenv("AGENT_MODEL", "claude-opus-5-5")
EVENING_TIME = os.getenv("EVENING_TIME", "19:00")
PREFIX = "🆕 עדכון ערב: "
MAX_ITEMS = 12          # לתחום, לריצה
MAX_TURNS = 12          # סבבי API לתחום (pause_turn + תזכורת אחת)
KEEP_RUNS = 60
# הערכת עלות בלבד — המחיר המחייב בקונסול של Anthropic
PRICE_IN, PRICE_OUT, PRICE_SEARCH = 4 / 1e6, 20 / 1e6, 10 / 1000

_run_lock = threading.Lock()

SUBMIT_TOOL = {
    "name": "submit_evening_update",
    "description": "מגיש את הידיעות החדשות של הערב לתחום. קוראים לו פעם אחת, בסוף, גם אם אין ידיעות (רשימה ריקה).",
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["note", "items"],
        "properties": {
            "note": {"type": "string", "description": "שורה-שתיים: מה בדקת, ולמה נבחרו (או לא נבחרו) ידיעות"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["section", "title", "summary", "details", "source_url", "source_name"],
                    "properties": {
                        "section": {"type": "string", "description": "שם קטגוריה מהגיליון, או שם קצר חדש"},
                        "title": {"type": "string", "description": "כותרת בעברית, בלי הקידומת 'עדכון ערב'"},
                        "summary": {"type": "string", "description": "2–4 משפטים בעברית"},
                        "details": {"type": "string", "description": "הרחבה בעברית. פסקה חדשה = \\n"},
                        "source_url": {"type": "string", "description": "הכתובת של הכתבה עצמה"},
                        "source_name": {"type": "string", "description": "שם המקור, למשל Reuters"},
                    },
                },
            },
        },
    },
}

SYSTEM = """אתה עורך החדשות של עדכון הערב באתר TACT News. הקוראים קראו את גיליון הבוקר; התפקיד שלך הוא להוסיף רק מה שחדש מאז.

כללים:
- חפש ידיעות שפורסמו היום, אחרי גיליון הבוקר, בנושא התחום. העדף את המקורות של התחום; מקור אחר מותר רק אם הוא אמין והידיעה חשובה.
- אל תחזור על ידיעה שכבר בגיליון (גם לא בניסוח אחר). עדכון משמעותי לסיפור שכבר הופיע — מותר, וכתוב בכותרת שזה עדכון.
- רק ידיעות אמיתיות שמצאת בחיפוש. source_url = הכתבה עצמה (לא דף בית, לא דף חיפוש). אל תמציא כתובות, ציטוטים או מספרים.
- לא פייסבוק ולא רשתות חברתיות — את אלה מכסה מישהו אחר.
- הכול בעברית (שמות חברות ומוצרים כמקובל). summary: 2–4 משפטים. details: הרחבה של 2–4 פסקאות — מה קרה, הרקע, למה זה חשוב.
- section: שם של קטגוריה קיימת בגיליון כשהידיעה מתאימה לה; אחרת שם קצר חדש.
- כמות: לפי מה שבאמת חדש וחשוב — בדרך כלל 3–8, לכל היותר 12. ערב שקט = מעט ידיעות או אף אחת, וזה בסדר.
- בסוף קרא ל-submit_evening_update פעם אחת עם כל הידיעות."""


def _client():
    import anthropic  # noqa: PLC0415 — רק כשהסוכן רץ
    return anthropic.Anthropic(timeout=600, max_retries=3)


# ───────────────────────── יומן ריצות ─────────────────────────
def _runs_file(topics: Topics) -> Path:
    return topics.data_dir / "agent_runs.json"


def load_runs(topics: Topics) -> list[dict]:
    try:
        data = json.loads(_runs_file(topics).read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save_run(topics: Topics, run: dict) -> None:
    runs = [r for r in load_runs(topics) if r.get("id") != run["id"]]
    runs.insert(0, run)
    f = _runs_file(topics)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(runs[:KEEP_RUNS], ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)


def status(topics: Topics) -> dict:
    return {
        "enabled": bool(os.getenv("ANTHROPIC_API_KEY")),
        "model": MODEL,
        "evening_time": EVENING_TIME,
        "running": _run_lock.locked(),
        "runs": load_runs(topics)[:20],
    }


# ───────────────────────── ריצה ─────────────────────────
def start_in_background(topics: Topics, only: str = "", trigger: str = "manual") -> bool:
    """מחזיר False אם כבר רצה ריצה."""
    if _run_lock.locked():
        return False
    threading.Thread(target=run_evening, args=(topics, only, trigger), daemon=True).start()
    return True


def run_evening(topics: Topics, only: str = "", trigger: str = "schedule") -> dict:
    if not _run_lock.acquire(blocking=False):
        logger.warning("עדכון ערב כבר רץ — מדלגים")
        return {}
    try:
        now = datetime.now(IL)
        run = {"id": now.strftime("%Y%m%d-%H%M%S"), "started": now.isoformat(timespec="seconds"),
               "trigger": trigger, "model": MODEL, "date": today().isoformat(), "topics": []}
        _save_run(topics, run)
        for t in topics.listing():
            if only and t["id"] != only:
                continue
            if "newsletter" not in t["tabs"]:
                continue
            try:
                result = _run_topic(topics, t)
            except Exception as e:  # noqa: BLE001 — תחום אחד לא עוצר את השאר
                logger.exception("עדכון ערב נכשל בתחום %s", t["id"])
                result = {"topic": t["id"], "error": str(e)[:300]}
            run["topics"].append(result)
            _save_run(topics, run)
        run["finished"] = datetime.now(IL).isoformat(timespec="seconds")
        run["cost_usd"] = round(sum(r.get("cost_usd", 0) for r in run["topics"]), 2)
        _save_run(topics, run)
        logger.info("עדכון ערב הסתיים: %s", ", ".join(f'{r["topic"]}+{r.get("added", 0)}' for r in run["topics"]))
        return run
    finally:
        _run_lock.release()


def _run_topic(topics: Topics, topic: dict) -> dict:
    storage = topics.get(topic["id"])
    day = today().isoformat()
    newsletter = storage.day_info(day)["newsletter"]
    if newsletter and newsletter["kind"] != "json":
        return {"topic": topic["id"], "skipped": f"הגיליון של היום הוא {newsletter['kind']} — אין מיזוג"}
    data = (newsletter or {}).get("data") or {"title": f"חדשות לבועז — {topic['name']}", "sections": []}

    items, usage = _ask_claude(topic, data, day)
    added = _merge(data, items)
    if added:
        storage.publish_text(day, json.dumps(data, ensure_ascii=False))
    cost = (usage["input"] * PRICE_IN + usage["output"] * PRICE_OUT + usage["searches"] * PRICE_SEARCH)
    return {"topic": topic["id"], "proposed": len(items), "added": added, **usage, "cost_usd": round(cost, 3)}


def _brief(topic: dict, data: dict, day: str) -> str:
    sections = data.get("sections") or []
    seen = "\n".join(
        f"- [{s.get('name', '')}] {i.get('title', '')} — {i.get('source_url', '')}"
        for s in sections for i in s.get("items", [])
    ) or "(אין עדיין גיליון היום — כל ידיעה חשובה מהיום היא חדשה)"
    names = ", ".join(s.get("name", "") for s in sections) or "(אין)"
    sources = (topic.get("sources") or "").strip() or "(לא הוגדרו — בחר מקורות אמינים בתחום)"
    return (
        f"התחום: {topic['name']} ({topic['id']})\n"
        f"מה מכסים בו:\n{topic.get('description') or topic['name']}\n\n"
        f"המקורות של התחום:\n{sources}\n\n"
        f"היום: {day}, השעה עכשיו בישראל: {datetime.now(IL):%H:%M}.\n"
        f"הקטגוריות בגיליון: {names}\n\n"
        f"מה כבר פורסם היום (אל תחזור על זה):\n{seen}"
    )


def _ask_claude(topic: dict, data: dict, day: str) -> tuple[list[dict], dict]:
    client = _client()
    tools = [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 10},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 6},
        SUBMIT_TOOL,
    ]
    messages = [{"role": "user", "content": _brief(topic, data, day)}]
    usage = {"input": 0, "output": 0, "searches": 0, "fetches": 0}
    nudged = False
    for _ in range(MAX_TURNS):
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=16000, system=SYSTEM, tools=tools, messages=messages,
            thinking={"type": "adaptive"}, output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
        _add_usage(usage, resp.usage)
        messages.append({"role": "assistant", "content": resp.content})
        submit = next((b for b in resp.content if b.type == "tool_use" and b.name == SUBMIT_TOOL["name"]), None)
        if submit:
            usage["note"] = str(submit.input.get("note", ""))[:400]
            return [i for i in (submit.input.get("items") or []) if _valid(i)][:MAX_ITEMS], usage
        if resp.stop_reason == "refusal":
            raise StorageError("Claude סירב לבקשה")
        if resp.stop_reason == "pause_turn":
            continue  # הלולאה בצד השרת עצרה באמצע — שולחים שוב והיא ממשיכה
        if resp.stop_reason == "tool_use":
            # כלי לקוח אחר מאשר submit לא קיים — עונים בשגיאה כדי שימשיך
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b.id, "content": "כלי לא מוכר", "is_error": True}
                for b in resp.content if b.type == "tool_use"]})
            continue
        if nudged:
            break
        nudged = True
        messages.append({"role": "user", "content": "סיים עכשיו: קרא ל-submit_evening_update עם הידיעות שמצאת."})
    raise StorageError("Claude לא הגיש ידיעות")


def _add_usage(usage: dict, u) -> None:
    usage["input"] += (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0) \
        + (getattr(u, "cache_creation_input_tokens", 0) or 0)
    usage["output"] += u.output_tokens or 0
    stu = getattr(u, "server_tool_use", None)
    if stu:
        usage["searches"] += getattr(stu, "web_search_requests", 0) or 0
        usage["fetches"] += getattr(stu, "web_fetch_requests", 0) or 0


def _valid(item: dict) -> bool:
    url = str(item.get("source_url", ""))
    return bool(item.get("title")) and bool(item.get("summary")) and url.startswith(("https://", "http://"))


def _norm_url(url: str) -> str:
    return url.split("#")[0].split("?")[0].rstrip("/").lower().removeprefix("https://").removeprefix("http://") \
        .removeprefix("www.")


def _merge(data: dict, items: list[dict]) -> int:
    """ידיעות חדשות → לראש הקטגוריה שלהן (או קטגוריה חדשה בסוף). כפילויות לפי כתובת נזרקות."""
    sections = data.setdefault("sections", [])
    seen = {_norm_url(i.get("source_url", "")) for s in sections for i in s.get("items", [])}
    by_name = {s.get("name", "").strip(): s for s in sections}
    fresh: dict[str, list[dict]] = {}
    for it in items:
        key = _norm_url(it["source_url"])
        if key in seen:
            continue
        seen.add(key)
        title = it["title"].strip()
        title = title if title.startswith("🆕") else PREFIX + title
        fresh.setdefault(it["section"].strip() or "עדכון ערב", []).append({
            "title": title, "summary": it["summary"].strip(), "details": it["details"].strip(),
            "source_url": it["source_url"].strip(), "source_name": it["source_name"].strip(),
        })
    for name, new in fresh.items():
        if name in by_name:
            by_name[name]["items"] = new + by_name[name].get("items", [])
        else:
            sections.append({"name": name, "items": new})
    return sum(len(v) for v in fresh.values())


# ───────────────────────── תזמון ─────────────────────────
def seconds_until_evening() -> float:
    hh, mm = (int(x) for x in EVENING_TIME.split(":"))
    now = datetime.now(IL)
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target = datetime.combine(target.date() + timedelta(days=1), target.timetz())
    return (target - now).total_seconds()
