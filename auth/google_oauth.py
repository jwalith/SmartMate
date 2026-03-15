"""
Google OAuth 2.0 flow for Calendar access.

First run: visit /auth/google/login in your browser.
It will redirect to Google, you approve, and the token is saved to token.json.
All subsequent calls reuse token.json (auto-refreshed).
"""

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from config import get_settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Persisted between /auth/google/login and /auth/google/callback
# Safe for single-user local use
_pending_flow: Flow | None = None


def get_credentials() -> Credentials | None:
    """Load credentials from token.json, refreshing if expired."""
    settings = get_settings()
    token_path = settings.google_token_file

    if not os.path.exists(token_path):
        return None

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)

    return creds if creds and creds.valid else None


def start_auth_flow() -> str:
    """
    Build the OAuth flow, store it globally, and return the auth URL.
    The flow instance must survive until the callback fires.
    """
    global _pending_flow
    settings = get_settings()

    _pending_flow = Flow.from_client_secrets_file(
        settings.google_credentials_file,
        scopes=SCOPES,
        redirect_uri=settings.oauth_redirect_uri,
    )

    auth_url, _ = _pending_flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def complete_auth_flow(code: str) -> Credentials:
    """
    Exchange the authorization code using the stored flow instance
    (which holds the code_verifier for PKCE) and persist the token.
    """
    global _pending_flow
    if _pending_flow is None:
        raise RuntimeError(
            "No pending OAuth flow found. Please visit /auth/google/login first."
        )

    _pending_flow.fetch_token(code=code)
    creds = _pending_flow.credentials
    _save_credentials(creds)
    _pending_flow = None
    return creds


def _save_credentials(creds: Credentials) -> None:
    settings = get_settings()
    with open(settings.google_token_file, "w") as f:
        f.write(creds.to_json())
