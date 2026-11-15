"""Application configuration loaded from environment variables / .env file."""

import functools

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_bot_token: str
    gemini_api_key: str
    gemini_model: str = "gemini-flash-lite-latest"
    webapp_url: str = ""
    db_path: str = "data/qayta.db"
    # Telegram user id allowed to use /review; 0 disables the command.
    admin_user_id: int = 0


@functools.cache
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()
