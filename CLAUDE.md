# TACT News — אתר החדשות היומי

**בתחילת סשן:** לקרוא את הסיכום האחרון ב-`sessions/`. **כשאומרים "סכם":** לכתוב `sessions/YYYY-MM-DD-<נושא>.md`.
עונים בעברית. קובץ קוד לא עובר ~500 שורות.

## מה זה
תקציר החדשות היומי — **הניוזלטר בונה Claude** (מ-2.11.2026), גרוק מוסיף פייסבוק + פודקאסטים/NotebookLM/YouTube/מדריכים/מאמרים. עמוד לכל יום,
**נשמר 14 יום ונמחק אוטומטית**. קריאה פתוחה לכולם.

**הכול אוטומטי — המשתמש לא מנהל את זה.** גרוק (הצרכני, משימה יומית) מחובר כ-custom connector
ל-`/mcp` עם `TACT_NEWS_PUBLISH_TOKEN`: קורא את הגיליון (`get_newsletter`), ממלא את "מעקב פייסבוק" (`set_facebook_section`) והלשוניות האחרות. `publish_newsletter` **חסום** (גם `content` ב-`/api/publish`). הפודקאסטים = קישורים
לפרקים קיימים שגרוק בוחר (mp3 ישיר מתנגן באתר; Spotify/YouTube נפתחים בלשונית).
הגדרת החיבור + הטוקן: `Aiprojects\env\tact-news-grok.md` (מחוץ לריפו). `/admin` (Google) נשאר לתיקונים ידניים.

- **חי:** https://tact-news.newavera.co.il — Mac mini, `~/server/tact-news`, פורט 8110, מנהרה ייעודית. פרטים: `deploy/DEPLOY.md`
- **ריפו:** github.com/boazeng/tact-news (**ציבורי** — לא להכניס סודות)

## תחומי על ולשוניות
- **תחום על**: לכל תחום ימים משלו. הרשימה ב-`database/topics.json` (לא בקוד) — **מנוהלת מדף הניהול** (הוספה, עריכה, סדר, מחיקה; `POST/PATCH/DELETE /api/topics`, `PUT /api/topics-order`, admin). המזהה לא ניתן לשינוי. לכל תחום `tabs` — אילו לשוניות גרוק ממלא ומה מוצג באתר (ברירת מחדל: כולן; לשונית כבויה עם תוכן קיים עדיין מוצגת). בתיאור: `**מודגש**` ו-`==מסומן==` (`src/lib/marks.jsx`) — גרוק מקבל אותם כטקסט ויודע שזה דגש. הראשון = ברירת מחדל. לכל תחום `description` = מה גרוק מכסה; גרוק קורא `list_topics` כל בוקר ומפרסם לכל תחום. `SEED` ב-`topics.py` רק כשאין קובץ. מחיקת תחום מוחקת גם את הימים שלו.
  ⚠️ "קטגוריה" אצל המשתמש = **תחום על**, לא לשונית. ב-2026-10-24 נבנתה בטעות לשונית "טכנולוגיה" ובוטלה (revert).
  כתובות: `/<topic>/<date>[/podcasts|/youtube]`; `/` = תחום ברירת המחדל + היום; `/d/<date>` ישן → `ai`.
- **לשוניות ביום:** ניוזלטר (ברירת מחדל) · פודקאסטים (אודיו + `links.json` + materials) · YouTube (`youtube.json`, מתנגן ב-youtube-nocookie) · מדריכים (`guides.json`, אותו פורמט ואותה תצוגה, רשימה נפרדת) · מאמרים (`papers.json`, מאמרים אקדמיים; ל-arXiv נוצר קישור PDF אוטומטית).
- כל נתיב API מקבל `?topic=`; כל כלי MCP מקבל `topic`. נתונים מלפני התחומים הועברו אוטומטית ל-`issues/ai/` בעלייה.
- **תחומים של Longeviora (מ-6.11.2026)** — אפליקציה לקהל שקוראת חדשות מהשרת הזה. מוגדרים בקוד (`backend/apps.py`, נוספים בעלייה), עם `app/lang/kind/review`. **לא מופיעים באתר ובאפליקציה של TACT News** (`/api/topics` בלי `app` מסנן אותם; `?app=longeviora` — רק הם; `?app=*` — מנהל). `review` = **הציבור רואה רק צילום מאושר** (`backend/review.py`, `<day>/.approved.json`, פאנל אישור בדף הניהול). `kind=promote` — רק גרוק (`set_promoted`), Claude לא רץ עליהם. `lang=en` — Claude כותב באנגלית (`editor.LANG_EN`). החוזה: `docs/LONGEVIORA.md`.

## מבנה
- `backend/` — FastAPI. `storage.py` (תיקייה לכל יום, retention, קישורי פודקאסט), `api.py` (נתיבים + `POST /api/publish` — רשימות בלבד), `publish.py` (טוקן, `edit_newsletter` = קריאה-שינוי-כתיבה בתוך `NEWSLETTER_LOCK`, `set_section`), `mcp_server.py` (`/mcp`: list_topics · get_newsletter · set_facebook_section · add_podcast_links · add_youtube_links · add_guide_links · add_papers · upload_audio_from_url · upload_audio_base64 · get_status · publish_newsletter=שגיאה), `topics.py` (תחומי על + הגירה), `audio_intake.py` (אודיו מגרוק: URL / base64 בחתיכות / `POST /api/publish/audio`; חוסם כתובות פנימיות), `media.py` (WAV→M4A), `server.py` (auth + SPA)
- `src/` — React/Vite RTL. `pages/DayPage` (הגיליון), `pages/AdminPage` (העלאה), `components/Player` (נגן גלובלי — זוכר מיקום ומהירות, Media Session)
- `docs/GROK-PROMPT.md` — ההוראה לגרוק לפרסם לבד. **מקור יחיד** — דף הניהול מייבא אותו (`?raw`)
- `backend/evening_agent.py` + `feeds.py` + `editor.py` — **הניוזלטר של Claude** (עדכון ערב מ-1.11, כל הגיליון מ-2.11): כל יום ב-`RUN_TIMES` (ברירת מחדל `05:30,19:00` ישראל) לכל תחום עם לשונית ניוזלטר.
  **ריצה לפני 14:00 = גיליון בסיס:** פידים מ-24 השעות האחרונות, עד 260 כותרות → Claude בוחר 25–45 (עד 50), קובע קטגוריות (אותם שמות כמו אתמול) ושורת סיום; ידיעות בלי סימון, לסוף הקטגוריה. **אחרי 14:00 = עדכון ערב:** מאז הריצה הקודמת, עד 18, לראש הקטגוריות עם "🆕 עדכון ערב: ". ריצה ידנית בבוקר על יום קיים רק מוסיפה (בלי כפילויות).
  הקוד אוסף (בחינם) → Claude (`AGENT_MODEL`, ברירת מחדל `claude-sonnet-5-5`) בוחר מהכותרות → הקוד מתרגם קישורי Google News (`resolve_url`, ברווח 1.5 ש' — אחרת 429) ומוריד את הטקסט → Claude כותב בעברית רק ממה שבטקסט, במנות של 12 במקביל → מיזוג. מה שפורסם היום ואתמול (כל הגיליון) לא נבחר שוב.
  **בלי חיפוש ברשת** — עדכון ערב ~0.3–0.5$ לכל התחומים, גיליון בסיס מוערך ~1$ (חיפוש ברשת עם Opus עלה ~10$). יומן: `database/agent_runs.json` + "הניוזלטר של Claude" בדף הניהול (`GET /api/agent`, `POST /api/agent/run?topic=` — מנהל או טוקן הפרסום).
  **פייסבוק:** גרוק שולח `set_facebook_section` מתי שהוא רוצה; גם Claude וגם גרוק כותבים דרך `edit_newsletter` (קוראים מחדש בתוך המנעול), ולכן אף אחד לא דורס את השני. "מעקב פייסבוק" תמיד הקטגוריה האחרונה. גרוק מתחיל אחרי 06:00 כדי שהגיליון יהיה מוכן ל-NotebookLM.
  מלכודות: DNS של הקונטיינר נופל רגעית תחת 12 בקשות במקביל → כל פיד שנכשל מקבל ניסיון שני. גוגל מחזיר 429 אחרי הרבה בקשות → קישור שלא תורגם נשאר קישור גוגל (עובד בדפדפן). גיליונות 1–2.11 מכילים "🆕 עדכון בוקר:" (ניסוי קודם).
- `sources` בכל תחום — שורה לכל מקור: `שם | כתובת-פיד` (RSS/Atom, או חיפוש Google News `site:` עם `when:1d` למקור בלי פיד; לאתרים בעברית `hl=he&gl=IL`). נערך בדף הניהול, חוזר ב-`list_topics` לגרוק. שורה בלי פיד — לא נאספת.
- `docs/CLAUDE-AUTOMATION.md` — התכנון הרחב (Claude במקום גרוק). בוצע: כל הניוזלטר (2.11). NotebookLM + פייסבוק + שאר הלשוניות — גרוק
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
