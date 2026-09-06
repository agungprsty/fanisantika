"""Configuration settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings sourced from .env file or OS env vars."""

    TELEGRAM_BOT_TOKEN: str
    GOOGLE_SHEETS_CREDENTIALS: str  # JSON string of service account
    SPREADSHEET_ID: str
    APP_ENV: str = "development"

    # Admin Dashboard
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    GEMINI_API_KEY: str = ""
    CAPTION_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
