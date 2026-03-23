from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BOT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = BOT_DIR.parent / ".env.bot.secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str | None = Field(default=None, alias="BOT_TOKEN")
    lms_api_base_url: str = Field(alias="LMS_API_BASE_URL")
    lms_api_key: str = Field(alias="LMS_API_KEY")
    llm_api_model: str = Field(alias="LLM_API_MODEL")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_api_base_url: str = Field(alias="LLM_API_BASE_URL")


def load_settings() -> Settings:
    return Settings()
