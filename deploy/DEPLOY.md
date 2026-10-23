# פריסה — Mac mini

| פרמטר | ערך |
|---|---|
| תיקייה | `~/server/tact-news` (שכפול https — הריפו ציבורי) |
| פורט | `127.0.0.1:8110` → 8000 (לבדיקות מהמק בלבד) |
| Containers | `tact-news`, `tact-news-tunnel` |
| מנהרה | `tact-news` · `aa9d35e1-059e-4d21-a307-b1ca935099e6` · creds+config ב-`tunnel/` (gitignored) |
| נתונים | `database/` → `issues/` + `auth.db` |
| סודות | `.env` (chmod 600): `GOOGLE_OAUTH_CLIENT_ID/SECRET` (הועתקו מ-`~/server/energy-dd/.env`, client `30184743393-…`), `AUTH_SESSION_SECRET`, `AUTH_EMERGENCY_TOKEN`, `TACT_NEWS_PUBLISH_TOKEN` (גרוק; מקור: כספת `prod/apps/tact-news`) |

## עדכון קוד
```bash
ssh mac-remote
cd ~/server/tact-news && git pull && ~/.orbstack/bin/docker compose up -d --build
curl -s http://127.0.0.1:8110/api/health    # {"ok":true}
```

## חד-פעמי — Google Cloud Console
ל-OAuth client `30184743393-98ci…` (פרויקט newavera-auth) להוסיף ב-Authorized redirect URIs:
`https://tact-news.newavera.co.il/auth/callback`. עד אז: `/emergency-login?token=<AUTH_EMERGENCY_TOKEN מה-.env במק>`.

## DNS
`cloudflared --config /dev/null tunnel route dns --overwrite-dns aa9d35e1-059e-4d21-a307-b1ca935099e6 tact-news.newavera.co.il`
(בלי `--config /dev/null` הוא מנתב בשקט למנהרה המשותפת).
