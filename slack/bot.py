"""
Slack Bolt app initialization.

The Bolt AsyncApp is mounted inside the FastAPI app via SlackRequestHandler.
"""

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from config import get_settings
from slack.handlers import handle_message

settings = get_settings()

bolt_app = AsyncApp(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
)

# ── Event subscriptions ───────────────────────────────────────────────────────

@bolt_app.event("message")
async def on_message(event, client, say):
    """Handle DMs sent directly to the bot."""
    # Ignore bot messages (prevents infinite loops)
    if event.get("bot_id") or event.get("subtype"):
        return
    await handle_message(event, client, say)


@bolt_app.event("app_mention")
async def on_mention(event, client, say):
    """Handle @SmartMate mentions in channels."""
    if event.get("bot_id"):
        return
    await handle_message(event, client, say)


# Handler used by FastAPI to forward requests to Bolt
slack_handler = AsyncSlackRequestHandler(bolt_app)
