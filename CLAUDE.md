# TACT News — אתר החדשות היומי

**בתחילת סשן:** לקרוא את הסיכום האחרון ב-`sessions/`. **כשאומרים "סכם":** לכתוב `sessions/YYYY-MM-DD-<נושא>.md`.
עונים בעברית. קובץ קוד לא עובר ~500 שורות.

## מה זה
תקציר החדשות היומי שבוט של Grok מכין + 2–3 פרקי פודקאסט מ-NotebookLM, עמוד לכל יום,
**נשמר 14 יום ונמחק אוטומטית**. קריאה פתוחה לכולם; העלאה/מחיקה — admin בלבד (Google).

- **חי:** https://tact-news.newavera.co.il — Mac mini, `~/server/tact-news`, פורט 8110, מנהרה ייעודית. פרטים: `deploy/DEPLOY.md`
- **ריפו:** github.com/boazeng/tact-news (**ציבורי** — לא להכניס סודות)

## מבנה
- `backend/` — FastAPI. `storage.py` (תיקייה לכל יום, retention), `api.py` (נתיבים), `media.py` (WAV→M4A ב-ffmpeg), `server.py` (auth + SPA)
- `src/` — React/Vite RTL. `pages/DayPage` (הגיליון), `pages/AdminPage` (העלאה), `components/Player` (נגן גלובלי — זוכר מיקום ומהירות, Media Session)
- `docs/GROK-PROMPT.md` — ההוראה לגרוק להפיק JSON. **מקור יחיד** — דף הניהול מייבא אותו (`?raw`)
- `samples/2026-10-23.json` — גיליון אמיתי בפורמט, לבדיקות

## נתונים
`database/issues/YYYY-MM-DD/` → `newsletter.{json|html|pdf}` + `podcasts/` + `materials/`. אין DB מלבד `auth.db` (משתמשים).
JSON של ניוזלטר: `{title, sections:[{name, color?, items:[{title, summary, details, source_url, source_name}]}], closing?, notebooklm?}` —
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
