"""העורך — שתי קריאות קצרות ל-Claude, בלי חיפוש ברשת (הקוד כבר אסף את המועמדים מהפידים):
1. select — מתוך רשימת הכותרות בוחר את החשובות ומשייך כל אחת לקטגוריה.
2. write  — מקבל את הטקסט של הכתבות שנבחרו וכותב כותרת, תקציר והרחבה בעברית.
"""
import os

MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-5-5")
# הערכת עלות בלבד — המחיר המחייב בקונסול של Anthropic. $ למיליון טוקנים: (קלט, פלט)
PRICES = {"claude-opus-5-5": (4, 20), "claude-sonnet-5-5": (2, 10), "claude-haiku-5-5": (0.10, 0.50)}

SELECT_TOOL = {
    "name": "submit_selection",
    "description": "מגיש את הבחירה: מספרי הידיעות שנכנסות לעדכון והקטגוריה של כל אחת. פעם אחת, בסוף.",
    "strict": True,
    "input_schema": {
        "type": "object", "additionalProperties": False, "required": ["note", "picks"],
        "properties": {
            "note": {"type": "string", "description": "משפט-שניים: לפי מה בחרת"},
            "picks": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["id", "section"],
                "properties": {
                    "id": {"type": "integer"},
                    "section": {"type": "string", "description": "קטגוריה קיימת בגיליון, או שם קצר חדש"},
                }}},
        },
    },
}

WRITE_TOOL = {
    "name": "submit_items",
    "description": "מגיש את הידיעות הכתובות בעברית. פעם אחת, בסוף.",
    "strict": True,
    "input_schema": {
        "type": "object", "additionalProperties": False, "required": ["items"],
        "properties": {"items": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["id", "title", "summary", "details"],
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "string", "description": "כותרת בעברית"},
                "summary": {"type": "string", "description": "2–4 משפטים"},
                "details": {"type": "string", "description": "2–4 פסקאות; פסקה חדשה = \\n"},
            }}}},
    },
}

SELECT_SYSTEM = """אתה עורך העדכונים באתר החדשות TACT News: פעמיים ביום משלימים את הגיליון של היום במה שחדש.
תקבל רשימה ממוספרת של ידיעות שפורסמו מאז העדכון הקודם במקורות של התחום (כותרת, מקור, שעה, ולפעמים תקציר).
בחר את הידיעות שנכנסות לעדכון:
- רק מה ששייך לתחום לפי התיאור שלו (פיד כללי מביא גם ידיעות לא רלוונטיות — דלג עליהן).
- לא ידיעה שכבר בגיליון, גם לא בניסוח אחר. עדכון משמעותי לסיפור שכבר הופיע — מותר.
- כמה ידיעות על אותו אירוע ממקורות שונים → בחר אחת, מהמקור הטוב ביותר.
- פזר על כל הקטגוריות של הגיליון (חוץ מ"מעקב פייסבוק"); 1–4 לכל קטגוריה שיש בה חדש.
- חשיבות קודמת לכמות: בתחום עמוס בדרך כלל 8–15, בתחום שקט פחות, לכל היותר 18. אם אין שום דבר חדש וחשוב — רשימה ריקה.
בסוף קרא ל-submit_selection."""

WRITE_SYSTEM = """אתה כותב את העדכונים באתר החדשות TACT News, בעברית.
לכל ידיעה תקבל את הכותרת המקורית, המקור, והטקסט של הכתבה (לפעמים רק תקציר קצר).
לכל ידיעה כתוב:
- title: כותרת עניינית בעברית (שמות חברות ומוצרים כמקובל).
- summary: 2–4 משפטים — מה קרה.
- details: 2–4 פסקאות — מה קרה, הרקע, ולמה זה חשוב.
רק מה שכתוב בטקסט שקיבלת. אל תוסיף מספרים, ציטוטים או פרטים שלא מופיעים בו. כשיש רק כותרת ותקציר קצר — כתוב קצר.
בסוף קרא ל-submit_items עם כל הידיעות."""


def _client():
    import anthropic  # noqa: PLC0415 — רק כשהסוכן רץ
    return anthropic.Anthropic(timeout=600, max_retries=3)


def _extra(model: str) -> dict:
    """fallback בצד השרת — לא קיים ל-Haiku."""
    if model.startswith("claude-haiku"):
        return {}
    return {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}


def _call(system: str, prompt: str, tool: dict, usage: dict, model: str) -> dict:
    """קריאה אחת עם כלי הגשה אחד. מחזיר את הקלט של הכלי."""
    client = _client()
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(2):
        resp = client.beta.messages.create(
            model=model, max_tokens=32000, system=system, tools=[tool], messages=messages,
            thinking={"type": "adaptive"}, output_config={"effort": "medium"}, **_extra(model),
        )
        _add_usage(usage, resp.usage, model)
        for b in resp.content:
            if b.type == "tool_use" and b.name == tool["name"]:
                return b.input
        if resp.stop_reason == "refusal":
            raise RuntimeError("Claude סירב לבקשה")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError("התשובה נחתכה (max_tokens)")
        messages += [{"role": "assistant", "content": resp.content},
                     {"role": "user", "content": f"סיים: קרא ל-{tool['name']}."}]
    raise RuntimeError(f"Claude לא קרא ל-{tool['name']}")


def _add_usage(usage: dict, u, model: str) -> None:
    tokens_in = (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0) \
        + (getattr(u, "cache_creation_input_tokens", 0) or 0)
    usage["input"] += tokens_in
    usage["output"] += u.output_tokens or 0
    p_in, p_out = PRICES.get(model, PRICES["claude-sonnet-5-5"])
    usage["cost"] += (tokens_in * p_in + (u.output_tokens or 0) * p_out) / 1e6


def select(topic: dict, morning: list[str], sections: list[str], candidates: list[dict], now: str,
           usage: dict, model: str = "") -> tuple[list[dict], str]:
    lines = []
    for i, c in enumerate(candidates):
        when = c["published"].astimezone().strftime("%H:%M") if c.get("published") else ""
        snip = f" — {c['snippet'][:220]}" if c.get("snippet") else ""
        lines.append(f"[{i}] {c['title']} ({c['source']}, {when}){snip}")
    prompt = (
        f"התחום: {topic['name']}\nמה מכסים בו:\n{topic.get('description') or topic['name']}\n\n"
        f"השעה עכשיו בישראל: {now}\n"
        f"הקטגוריות בגיליון: {', '.join(sections) or '(אין)'}\n\n"
        "מה כבר בגיליון היום:\n" + ("\n".join(f"- {t}" for t in morning) or "(אין)") + "\n\n"
        "המועמדים:\n" + "\n".join(lines)
    )
    out = _call(SELECT_SYSTEM, prompt, SELECT_TOOL, usage, model or MODEL)
    picks = [p for p in out.get("picks", []) if isinstance(p.get("id"), int) and 0 <= p["id"] < len(candidates)]
    return picks, str(out.get("note", ""))[:400]


def write(topic: dict, chosen: list[dict], usage: dict, model: str = "") -> dict[int, dict]:
    blocks = []
    for i, c in enumerate(chosen):
        body = c.get("text") or c.get("snippet") or "(אין טקסט — רק הכותרת)"
        blocks.append(f"=== ידיעה {i} ===\nכותרת: {c['title']}\nמקור: {c['source']}\nטקסט:\n{body}")
    prompt = f"התחום: {topic['name']}\n\n" + "\n\n".join(blocks)
    out = _call(WRITE_SYSTEM, prompt, WRITE_TOOL, usage, model or MODEL)
    return {it["id"]: it for it in out.get("items", []) if isinstance(it.get("id"), int)}
