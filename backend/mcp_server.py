"""שרת MCP ב-/mcp — דרכו גרוק (custom connector) מפרסם לאתר בלי שאף אדם יגע.

streamable HTTP, stateless, JSON — אותה תבנית כמו ב-Longeviora. אימות: Bearer TACT_NEWS_PUBLISH_TOKEN בכל קריאה.
כל כלי מקבל topic (תחום על, ברירת מחדל: הראשון ב-topics.py).
"""
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from . import audio_intake
from .publish import add_list, publish, resolve_date, status, token_ok
from .storage import StorageError
from .topics import DEFAULT_TOPIC, Topics

INSTRUCTIONS = (
    "This is the TACT News site (tact-news.newavera.co.il) — Boaz's daily Hebrew news digest. "
    "Content is organised by topic (default 'ai' = בינה מלאכותית; list_topics shows all) and each day has 3 tabs: "
    "newsletter, podcasts (voice brief + episodes + podcast links), youtube (video links). "
    "Publish the newsletter with publish_newsletter (one call, full JSON — it may already include 'podcasts' and "
    "'youtube'), upload audio with upload_audio_*, and check with get_status. All text in Hebrew. "
    "Days are deleted automatically after 14 days."
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
                  "url": "https://... (direct .mp3 preferred, else Spotify/Apple episode page)",
                  "duration_minutes": 25, "description": "one line in Hebrew: why this episode today" } ],
  "youtube": [ { "title": "video title", "channel": "channel name",
                 "url": "https://www.youtube.com/watch?v=...", "duration_minutes": 12,
                 "description": "one line in Hebrew: why this video" } ],
  "closing": "optional closing line"
}
"podcasts" → the Podcasts tab, "youtube" → the YouTube tab (both optional).
Publishing again for the same date+topic replaces that day's newsletter."""

TOPIC_ARG = "topic = topic id (default 'ai'; see list_topics)."


def build_mcp(topics: Topics) -> MCPServer:
    server = MCPServer(name="tact-news", instructions=INSTRUCTIONS, version="2.0.0")

    def call(ctx: Context, fn) -> dict[str, Any]:
        headers = ctx.headers or {}
        if not token_ok(headers.get("authorization") or headers.get("Authorization")):
            raise ToolError("[401] missing or wrong token")
        try:
            return fn()
        except StorageError as e:
            raise ToolError(f"[400] {e}") from None

    @server.tool(description="The topics (תחומי על) on the site. Publish to a topic with the topic argument.")
    def list_topics(ctx: Context) -> dict[str, Any]:
        return call(ctx, lambda: {"topics": topics.listing()})

    @server.tool(description="Publish a day's newsletter (creates or replaces it). " + TOPIC_ARG + "\n" + NEWSLETTER_FORMAT)
    def publish_newsletter(ctx: Context, newsletter_json: str, date: str = "",
                           topic: str = DEFAULT_TOPIC) -> dict[str, Any]:
        return call(ctx, lambda: publish(topics.get(topic), newsletter_json, date))

    @server.tool(description=(
        "Set the podcast LINKS for a day (Podcasts tab; replaces the existing list). podcasts_json = JSON array of "
        '{"title","show","url","duration_minutes","description"}. date defaults to today (Israel). ' + TOPIC_ARG))
    def add_podcast_links(ctx: Context, podcasts_json: str, date: str = "",
                          topic: str = DEFAULT_TOPIC) -> dict[str, Any]:
        return call(ctx, lambda: add_list(topics.get(topic), "links", podcasts_json, date))

    @server.tool(description=(
        "Set the YouTube videos for a day (YouTube tab; replaces the existing list). videos_json = JSON array of "
        '{"title","channel","url","duration_minutes","description"}. url must be youtube.com or youtu.be — '
        "the video plays inside the site. date defaults to today (Israel). " + TOPIC_ARG))
    def add_youtube_links(ctx: Context, videos_json: str, date: str = "",
                          topic: str = DEFAULT_TOPIC) -> dict[str, Any]:
        return call(ctx, lambda: add_list(topics.get(topic), "youtube", videos_json, date))

    @server.tool(description=(
        "Upload an audio file (voice brief / NotebookLM episode) to the Podcasts tab by giving a DIRECT public link "
        "to the file (.mp3/.m4a/.wav). The server downloads it. A notebooklm.google.com page link will NOT work. "
        "title = episode title in Hebrew (start with '0 ' for the voice brief so it is first). " + TOPIC_ARG))
    def upload_audio_from_url(ctx: Context, url: str, title: str, date: str = "",
                              topic: str = DEFAULT_TOPIC) -> dict[str, Any]:
        def run():
            storage = topics.get(topic)
            return audio_intake.from_url(storage, resolve_date(storage, date, None), url, title)
        return call(ctx, run)

    @server.tool(description=(
        "Upload an audio file you hold to the Podcasts tab as base64, in chunks of up to 4MB of base64 each. "
        "Same upload_id for all chunks of one file, index 0..total-1 in order; saved after the last chunk. "
        "filename = original name with extension (e.g. brief.mp3). title = episode title in Hebrew. " + TOPIC_ARG))
    def upload_audio_base64(ctx: Context, upload_id: str, index: int, total: int, data_base64: str,
                            title: str, filename: str = "audio.mp3", date: str = "",
                            topic: str = DEFAULT_TOPIC) -> dict[str, Any]:
        def run():
            storage = topics.get(topic)
            return audio_intake.base64_chunk(storage, resolve_date(storage, date, None), upload_id, index,
                                             total, data_base64, title, filename)
        return call(ctx, run)

    @server.tool(description=(
        "What the site has for a date (default today) in a topic: newsletter items, audio files, podcast links, "
        "YouTube videos, and the days on the site. " + TOPIC_ARG))
    def get_status(ctx: Context, date: str = "", topic: str = DEFAULT_TOPIC) -> dict[str, Any]:
        def run():
            storage = topics.get(topic)
            return status(storage, resolve_date(storage, date, None)) | {
                "days_on_site": [d["date"] for d in storage.list_days()]}
        return call(ctx, run)

    return server


class _Endpoint:
    """ASGI app שמפנה ל-session manager הנוכחי (אובייקט ולא פונקציה — אחרת Starlette עוטף כ-request handler)."""

    def __init__(self, server: MCPServer) -> None:
        self.server = server

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.server.session_manager.handle_request(scope, receive, send)


def install_mcp(app, topics: Topics):
    """מוסיף את /mcp ומחזיר context manager שצריך לרוץ בתוך ה-lifespan."""
    server = build_mcp(topics)
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
