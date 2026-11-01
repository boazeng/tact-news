"""עדכון ערב — מוסיף לגיליון של היום ידיעות שפורסמו מאז הבוקר.

גרוק מפרסם את גיליון הבוקר. בשעה EVENING_TIME (ברירת מחדל 19:00, שעון ישראל), לכל תחום שיש בו לשונית ניוזלטר:
1. הקוד אוסף מהפידים של המקורות (שדה sources: "שם | כתובת-פיד") את מה שפורסם ב-WINDOW_HOURS האחרונות — בחינם.
2. Claude בוחר מהרשימה את החשוב ומשייך לקטגוריות (editor.select).
3. הקוד מתרגם קישורי Google News לכתובת הכתבה ומוריד את הטקסט שלה.
4. Claude כותב כותרת, תקציר והרחבה בעברית מתוך הטקסט (editor.write).
5. הקוד ממזג לראש הקטגוריות עם הקידומת "🆕 עדכון ערב: " ומפרסם מחדש — שום דבר מהבוקר לא נמחק.

בלי חיפוש ברשת — הקישורים והתאריכים מגיעים מהפידים, וזה גם מה שמחזיק את העלות נמוכה.
מפתח: ANTHROPIC_API_KEY ב-.env של האתר. יומן ריצות: database/agent_runs.json.
"""
import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import editor, feeds
from .storage import today
from .topics import Topics

logger = logging.getLogger("tact-news")

IL = ZoneInfo("Asia/Jerusalem")
MODEL = editor.MODEL
EVENING_TIME = os.getenv("EVENING_TIME", "19:00")
WINDOW_HOURS = int(os.getenv("EVENING_WINDOW_HOURS", "20"))   # 19:00 → מ-23:00 אתמול
PREFIX = "🆕 עדכון ערב: "
MAX_CANDIDATES = 160    # כותרות שנשלחות לבחירה, לתחום
MAX_ITEMS = 18          # ידיעות לתחום, לריצה
KEEP_RUNS = 60

_run_lock = threading.Lock()


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
    sources = feeds.parse_sources(topic.get("sources", ""))
    if not sources:
        return {"topic": topic["id"], "skipped": "אין פידים ברשימת המקורות"}

    # 1. איסוף — בלי מודל
    since = datetime.now(IL) - timedelta(hours=WINDOW_HOURS)
    found, stats = feeds.collect(sources, since)
    sections = data.get("sections") or []
    morning = [i for s in sections for i in s.get("items", [])]
    known_titles = {feeds.norm_title(i.get("title", "").removeprefix(PREFIX)) for i in morning}
    known_urls = {_norm_url(i.get("source_url", "")) for i in morning}
    candidates = [c for c in found if feeds.norm_title(c["title"]) not in known_titles
                  and _norm_url(c["url"]) not in known_urls][:MAX_CANDIDATES]
    result = {"topic": topic["id"], "model": MODEL, "feeds": len(sources),
              "feeds_failed": [n for n, v in stats.items() if isinstance(v, str)],
              "candidates": len(candidates), "added": 0}
    usage = {"input": 0, "output": 0, "cost": 0.0}
    if not candidates:
        return result | {"note": "אין ידיעות חדשות בפידים", "cost_usd": 0}

    # 2. בחירה
    now = datetime.now(IL).strftime("%H:%M")
    picks, note = editor.select(topic, [i.get("title", "") for i in morning],
                                [s.get("name", "") for s in sections], candidates, now, usage)
    chosen = []
    for p in picks[:MAX_ITEMS]:
        c = dict(candidates[p["id"]])
        c["section"] = p["section"]
        chosen.append(c)

    # 3. כתובת אמיתית + טקסט הכתבה — בלי מודל
    def enrich(c):
        if c["gnews"]:
            c["url"] = feeds.resolve_url(c["url"])
        c["text"] = feeds.article_text(c["url"])
        return c
    with ThreadPoolExecutor(8) as ex:
        chosen = list(ex.map(enrich, chosen))

    # 4. כתיבה
    written = editor.write(topic, chosen, usage) if chosen else {}
    items = []
    for i, c in enumerate(chosen):
        w = written.get(i)
        if w and w.get("title") and w.get("summary"):
            items.append({"section": c["section"], "title": w["title"], "summary": w["summary"],
                          "details": w.get("details", ""), "source_url": c["url"], "source_name": c["source"]})

    # 5. מיזוג ופרסום
    added = _merge(data, items)
    if added:
        storage.publish_text(day, json.dumps(data, ensure_ascii=False))
    return result | {"picked": len(chosen), "added": added, "note": note,
                     "with_text": sum(1 for c in chosen if len(c.get("text", "")) > 300),
                     "input": usage["input"], "output": usage["output"], "cost_usd": round(usage["cost"], 3)}


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
