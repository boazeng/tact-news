# TACT News — אתר החדשות היומי

**בתחילת סשן:** לקרוא את הסיכום האחרון ב-`sessions/`. **כשאומרים "סכם":** לכתוב `sessions/YYYY-MM-DD-<נושא>.md`.
עונים בעברית. קובץ קוד לא עובר ~500 שורות.

## מה זה
תקציר החדשות היומי שבוט של Grok מכין + 2–3 פרקי פודקאסט, עמוד לכל יום,
**נשמר 14 יום ונמחק אוטומטית**. קריאה פתוחה לכולם.

**הכול אוטומטי — המשתמש לא מנהל את זה.** גרוק (הצרכני, משימה יומית) מחובר כ-custom connector
ל-`/mcp` עם `TACT_NEWS_PUBLISH_TOKEN` וקורא ל-`publish_newsletter` בעצמו. הפודקאסטים = קישורים
לפרקים קיימים שגרוק בוחר (mp3 ישיר מתנגן באתר; Spotify/YouTube נפתחים בלשונית).
הגדרת החיבור + הטוקן: `Aiprojects\env\tact-news-grok.md` (מחוץ לריפו). `/admin` (Google) נשאר לתיקונים ידניים.

- **חי:** https://tact-news.newavera.co.il — Mac mini, `~/server/tact-news`, פורט 8110, מנהרה ייעודית. פרטים: `deploy/DEPLOY.md`
- **ריפו:** github.com/boazeng/tact-news (**ציבורי** — לא להכניס סודות)

## תחומי על ולשוניות
- **תחום על** (`backend/topics.py` → `TOPICS`): לכל תחום ימים משלו. כרגע רק `ai`. תחום חדש = שורה אחת שם.
  כתובות: `/<topic>/<date>[/podcasts|/youtube]`; `/` = תחום ברירת המחדל + היום; `/d/<date>` ישן → `ai`.
- **לשוניות ביום:** ניוזלטר (ברירת מחדל) · פודקאסטים (אודיו + `links.json` + materials) · YouTube (`youtube.json`, מתנגן ב-youtube-nocookie) · מדריכים (`guides.json`, אותו פורמט ואותה תצוגה, רשימה נפרדת) · מאמרים (`papers.json`, מאמרים אקדמיים; ל-arXiv נוצר קישור PDF אוטומטית) · טכנולוגיה (`tech.json`, פיתוחים חדשים, מוצג כמו ידיעות + שם החברה). בטלפון שורת הלשוניות נגללת.
- כל נתיב API מקבל `?topic=`; כל כלי MCP מקבל `topic`. נתונים מלפני התחומים הועברו אוטומטית ל-`issues/ai/` בעלייה.

## מבנה
- `backend/` — FastAPI. `storage.py` (תיקייה לכל יום, retention, קישורי פודקאסט), `api.py` (נתיבים + `POST /api/publish`), `publish.py` (טוקן + לוגיקת פרסום משותפת), `mcp_server.py` (`/mcp`: list_topics · publish_newsletter · add_podcast_links · add_youtube_links · add_guide_links · add_papers · add_tech · upload_audio_from_url · upload_audio_base64 · get_status), `topics.py` (תחומי על + הגירה), `audio_intake.py` (אודיו מגרוק: URL / base64 בחתיכות / `POST /api/publish/audio`; חוסם כתובות פנימיות), `media.py` (WAV→M4A), `server.py` (auth + SPA)
- `src/` — React/Vite RTL. `pages/DayPage` (הגיליון), `pages/AdminPage` (העלאה), `components/Player` (נגן גלובלי — זוכר מיקום ומהירות, Media Session)
- `docs/GROK-PROMPT.md` — ההוראה לגרוק לפרסם לבד. **מקור יחיד** — דף הניהול מייבא אותו (`?raw`)
- `samples/2026-10-23.json` — גיליון אמיתי בפורמט, לבדיקות

## נתונים
`database/issues/<topic>/YYYY-MM-DD/` → `newsletter.{json|html|pdf}` + `links.json` (פרקים מגרוק) + `youtube.json` + `podcasts/` (אודיו שהועלה) + `materials/`. אין DB מלבד `auth.db` (משתמשים).
JSON של ניוזלטר: `{title, sections:[{name, color?, items:[{title, summary, details, source_url, source_name}]}], podcasts?, closing?, notebooklm?}` —
`podcasts` (`[{title, url, show, duration_minutes, description}]`) נשלף ל-`links.json`;
`notebooklm` (מחרוזת או `[{title,text}]`) נשלף לקובץ ב-`materials/` בזמן השמירה.

## פיתוח מקומי
```powershell
$env:TACT_NEWS_ENV_FILE="<קובץ עם AUTH_DISABLED=true>"; $env:TACT_NEWS_DATA_DIR="<תיקייה>"
python -m uvicorn backend.server:app --port 8115   # API
npm run dev                                          # http://localhost:5335 (proxy ל-8115)
```

## מלכודות
- העלאה **בחתיכות של 25MB** — Cloudflare חוסם בקשה מעל 100MB, ו-WAV של NotebookLM עובר את זה.
- `/api/*` ו-`/files/*` שלא קיימים מחזירים 404 JSON (לא index.html) — כדי שבדיקות בריאות לא ישקרו.
- HTML שהועלה מוגש עם `CSP: sandbox` — בלי סקריפטים, גם בגישה ישירה.
- מספרים/זמנים בתוך RTL מתהפכים ("1:00 / 0:01") — לעטוף ב-`dir="ltr"`.
- מקומית: `pip install mcp` משדרג את starlette ל-1.x, ו-fastapi ישן (0.115) נופל ב-`on_startup` — לשדרג fastapi. בדוקר זה לא קורה.
- גרוק מגיע ל-/mcp דרך ה-middleware של shared-auth — עובד כי `public_prefixes=("/",)`. אם האתר יינעל, להוסיף `/mcp` לרשימה.
- אודיו מגרוק: לא ידוע איזו משלוש הדרכים עובדת אצלו בפועל — base64 של קובץ גדול כנראה מעבר ליכולת של מודל. קידומת `0 ` בכותרת = ראשון בנגן, ולא מוצגת.
