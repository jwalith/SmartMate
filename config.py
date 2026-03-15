from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (Groq - free tier)
    groq_api_key: str

    # Slack
    slack_bot_token: str
    slack_signing_secret: str

    # Google
    google_credentials_file: str = "credentials.json"
    google_token_file: str = "token.json"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    public_url: str = "http://localhost:8000"
    oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Notes
    notes_db_path: str = "notes.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
