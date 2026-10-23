"""שרת MCP ב-/mcp — דרכו גרוק (custom connector) מפרסם לאתר בלי שאף אדם יגע.

streamable HTTP, stateless, JSON — אותה תבנית כמו ב-Longeviora. אימות: Bearer TACT_NEWS_PUBLISH_TOKEN בכל קריאה.
"""
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from . import audio_intake
from .publish import add_podcasts, publish, resolve_date, token_ok
from .storage import Storage, StorageError

INSTRUCTIONS = (
    "This is the TACT News site (tact-news.newavera.co.il) — Boaz's daily Hebrew tech/AI news digest. "
    "After you write the daily newsletter, publish it with publish_newsletter (one call, the full JSON). "
    "Include 2–3 podcast episodes (~45 minutes total) in the 'podcasts' field. "
    "Check the result with get_status. All text in Hebrew. Issues are deleted automatically after 14 days."
)

NEWSLETTER_FORMAT = """\
newsletter_json — JSON object (as a string):
{
  "date": "YYYY-MM-DD",
  "title": "חדשות לבועז — טכנולוגיה ו-AI",
  "sections": [ { "name": "בינה מלאכותית",
                  "items": [ { "title": "...", "summary": "2–4 sentences",
                               "details": "full expansion, paragraphs separated by \\n",
                               "source_url": "https://...", "source_name": "CNBC" } ] } ],
  "podcasts": [ { "title": "episode title", "show": "podcast name",
                  "url": "https://... (direct .mp3 preferred, else Spotify/Apple/YouTube episode page)",
                  "duration_minutes": 25, "description": "one line in Hebrew: why this episode today" } ],
  "closing": "optional closing line"
}
Fixed section order: בינה מלאכותית · סייבר ואבטחה · ביג טק ועסקים · שבבים וחומרה · סטארטאפים והייטק ישראלי (omit empty ones).
Publishing again for the same date replaces that day's issue."""


def build_mcp(storage: Storage) -> MCPServer:
    server = MCPServer(name="tact-news", instructions=INSTRUCTIONS, version="1.0.0")

    def call(ctx: Context, fn, *args) -> dict[str, Any]:
        headers = ctx.headers or {}
        if not token_ok(headers.get("authorization") or headers.get("Authorization")):
            raise ToolError("[401] missing or wrong token")
        try:
            return fn(*args)
        except StorageError as e:
            raise ToolError(f"[400] {e}") from None

    @server.tool(description="Publish today's newsletter to the site (creates or replaces the day's page).\n" + NEWSLETTER_FORMAT)
    def publish_newsletter(ctx: Context, newsletter_json: str, date: str = "") -> dict[str, Any]:
        return call(ctx, publish, storage, newsletter_json, date, None)

    @server.tool(description=(
        "Set the podcast episodes for a day (replaces the existing list). podcasts_json = JSON array of "
        '{"title","show","url","duration_minutes","description"}. date defaults to today (Israel).'))
    def add_podcast_links(ctx: Context, podcasts_json: str, date: str = "") -> dict[str, Any]:
        return call(ctx, add_podcasts, storage, podcasts_json, date)

    @server.tool(description=(
        "Upload an audio file (voice brief / NotebookLM episode) by giving a DIRECT public link to the file "
        "(.mp3/.m4a/.wav). The server downloads it and it plays in the site's player for that day. "
        "A notebooklm.google.com page link will NOT work (it is a login page, not a file). "
        "title = the episode title in Hebrew (start with '0 ' for the voice brief so it is listed first). date defaults to today."))
    def upload_audio_from_url(ctx: Context, url: str, title: str, date: str = "") -> dict[str, Any]:
        return call(ctx, lambda: audio_intake.from_url(storage, resolve_date(storage, date, None), url, title))

    @server.tool(description=(
        "Upload an audio file you hold (voice brief / NotebookLM episode) as base64, in chunks of up to 4MB of base64 each. "
        "Use the same upload_id for all chunks of one file, index 0..total-1 in order. The file is saved after the last chunk. "
        "filename = original name with extension (e.g. brief.mp3). title = episode title in Hebrew. date defaults to today."))
    def upload_audio_base64(ctx: Context, upload_id: str, index: int, total: int, data_base64: str,
                            title: str, filename: str = "audio.mp3", date: str = "") -> dict[str, Any]:
        return call(ctx, lambda: audio_intake.base64_chunk(
            storage, resolve_date(storage, date, None), upload_id, index, total, data_base64, title, filename))

    @server.tool(description="What the site has for a date (default today): item count, podcast links, plus the list of all days on the site.")
    def get_status(ctx: Context, date: str = "") -> dict[str, Any]:
        def status():
            day = resolve_date(storage, date, None)
            info = storage.day_info(day)
            data = (info["newsletter"] or {}).get("data") or {}
            return {
                "date": day,
                "published": bool(info["newsletter"]),
                "items": sum(len(s.get("items", [])) for s in data.get("sections", [])),
                "podcast_links": [link["title"] for link in info["links"]],
                "audio_files": [p["title"] for p in info["podcasts"]],
                "days_on_site": [d["date"] for d in storage.list_days()],
                "url": f"https://tact-news.newavera.co.il/d/{day}",
            }
        return call(ctx, status)

    return server


class _Endpoint:
    """ASGI app שמפנה ל-session manager הנוכחי (אובייקט ולא פונקציה — אחרת Starlette עוטף כ-request handler)."""

    def __init__(self, server: MCPServer) -> None:
        self.server = server

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.server.session_manager.handle_request(scope, receive, send)


def install_mcp(app, storage: Storage):
    """מוסיף את /mcp ומחזיר context manager שצריך לרוץ בתוך ה-lifespan."""
    server = build_mcp(storage)
    app.router.routes.insert(0, Route("/mcp", endpoint=_Endpoint(server), methods=["GET", "POST", "DELETE"]))

    @asynccontextmanager
    async def lifespan():
        server.streamable_http_app(
            streamable_http_path="/mcp",
            json_response=True,
            stateless_http=True,
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
            host="0.0.0.0",
        )
        async with server.session_manager.run():
            yield

    return lifespan
