"""
SmartMate — FastAPI entry point


Endpoints:
  POST /slack/events          → Slack event webhook (Bolt handler)
  GET  /auth/google/login     → Start Google OAuth flow
  GET  /auth/google/callback  → Google OAuth callback
  GET  /health                → Health check
"""

# Load .env into os.environ FIRST — LangChain reads LANGCHAIN_* vars directly
# from os.environ, not from pydantic-settings
from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse

from config import get_settings
from tools.notes import init_db
from slack.bot import slack_handler
from auth.google_oauth import start_auth_flow, complete_auth_flow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SmartMate starting up…")
    await init_db()
    logger.info("Notes DB initialized.")
    yield
    logger.info("SmartMate shutting down.")


app = FastAPI(title="SmartMate", lifespan=lifespan)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "SmartMate"}


# ── Slack ─────────────────────────────────────────────────────────────────────

@app.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)


# ── Google OAuth ──────────────────────────────────────────────────────────────

@app.get("/auth/google/login")
async def google_login():
    """Redirect the user to Google's OAuth consent screen."""
    auth_url = start_auth_flow()
    return RedirectResponse(url=auth_url)


@app.get("/auth/google/callback")
async def google_callback(code: str, request: Request):
    """Exchange the auth code for credentials and save them."""
    try:
        complete_auth_flow(code)
        return HTMLResponse(
            content="""
            <html><body style="font-family:sans-serif;text-align:center;padding:60px">
              <h2>✅ Google Calendar connected!</h2>
              <p>You can close this tab and return to Slack.</p>
            </body></html>
            """
        )
    except Exception as e:
        logger.exception("OAuth callback error: %s", e)
        return HTMLResponse(
            content=f"<html><body><h2>❌ Error: {e}</h2></body></html>",
            status_code=500,
        )


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
