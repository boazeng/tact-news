# Longeviora on the TACT News server — contract

Longeviora (consumer longevity app, repo `boazeng/longeviora-app`) reads its News and Promote content from this server.
The topics are defined in code (`backend/apps.py`) and added at startup if they are missing. Name, description and
sources can be edited on `/admin`. They never appear on the TACT News site or app.

## Topics

| id | lang | kind | tabs | who writes |
|---|---|---|---|---|
| `longevity` | he | news | newsletter, podcasts, youtube, papers | Claude (newsletter, 05:30 + 19:00) · Grok (papers, podcasts, YouTube) |
| `longevity-en` | en | news | same | same, in English |
| `longeviora-promote` | he | promote | newsletter | Grok only (`set_promoted`) |
| `longeviora-promote-en` | en | promote | newsletter | Grok only |

All four topics have `review: true`.

## Read API (public, anonymous, no tracking)

- `GET /api/topics?app=longeviora` returns only these 4 topics. Each topic has `{id, name, color, description, tabs, default, app, lang, kind, review}`, and `default` is true for the first one.
- `GET /api/topics` (with no `app`) returns only TACT News topics.
- `GET /api/issues?topic=<id>` lists the **approved** days, newest first.
- `GET /api/issues/<YYYY-MM-DD>?topic=<id>` returns the **approved** version of that day: same shape as TACT News, or 404.
- `/files/<topic>/<day>/podcasts/<name>`: audio is served only if the file is in the approved version.
  - The newsletter file itself is not served for these topics. Read `newsletter.data` from the issue instead.

## Promote stories

These are newsletter stories with extra fields:

```
{title, summary, details, source_url, source_name /* = sponsor */, image_url? /* https */, cta_label? /* ≤30 chars */}
```

- Sections default to `מקודם` (he) or `Promoted` (en). Grok may set its own `section`.
- Days are deleted after 14 days, like every topic. A day with no posts has no issue.

## Approval (`backend/review.py`)

- Writes by Claude and Grok are saved immediately but are not public.
- `/admin` → "אישור לפני פרסום — Longeviora" approves a day, which saves a snapshot (`<day>/.approved.json`). The public API serves that snapshot.
- Changes made after approval (the evening update, Grok fixes) wait until the day is approved again. Until then the public API keeps serving the earlier snapshot.
- Admin-only routes: `GET /api/review`, `GET /api/review/<day>?topic=` (live preview), `POST` (approve), `DELETE` (revoke), and `GET /api/issues?topic=&all=1`.

## Grok (MCP `/mcp`, same connector and token)

- `set_promoted(items_json, date?, topic)` replaces the day's posts. It works only on `kind=promote` topics.
- `add_papers`, `add_podcast_links` and `add_youtube_links` work as on every topic.
- `set_facebook_section` is blocked on app topics.
- `get_status` returns `approval`: pending / approved / changed.
- The prompt is the "Longeviora" section of `docs/GROK-PROMPT.md`.
