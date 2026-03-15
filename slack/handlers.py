"""
Slack event handlers.

Uses FastAPI BackgroundTasks to process agent runs asynchronously,
avoiding Slack's 3-second acknowledgement timeout.
"""

import logging
from slack_sdk.web.async_client import AsyncWebClient
from agents.graph import run_agent

logger = logging.getLogger(__name__)


async def handle_message(
    event: dict,
    client: AsyncWebClient,
    say,
) -> None:
    """
    Handle an incoming DM or app_mention.

    Slack requires a 3s ACK — the Bolt framework handles that.
    We post a "thinking" message immediately, then stream the real answer.
    """
    user_id = event.get("user")
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts") or event.get("ts")
    text = event.get("text", "").strip()

    # Strip bot mention if present (e.g. "<@UBOTID> show my calendar")
    if text.startswith("<@"):
        text = text.split(">", 1)[-1].strip()

    if not text:
        return

    # Post a "typing" placeholder so user knows we're working
    placeholder = await client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text="_SmartMate is thinking..._",
    )

    try:
        response_text = await run_agent(
            user_message=text,
            slack_user_id=user_id,
            slack_channel_id=channel_id,
            slack_thread_ts=thread_ts,
        )
    except Exception as e:
        logger.exception("Agent error: %s", e)
        response_text = f"Something went wrong: `{str(e)}`"

    # Update the placeholder with the real answer
    await client.chat_update(
        channel=channel_id,
        ts=placeholder["ts"],
        text=response_text,
    )
