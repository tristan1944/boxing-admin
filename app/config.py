from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = BASE_DIR / "boxing_admin.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_prefix="APP_", case_sensitive=False)

    api_token: str = Field(default="dev-token", description="Bearer token required for all API calls")
    database_url: str = Field(default=DEFAULT_SQLITE_URL, description="SQLAlchemy database URL")
    # Read as a simple string from env to avoid JSON parsing issues in pydantic-settings
    # Use comma-separated values or '*' for all
    cors_origins: str = Field(default="*")
    environment: str = Field(default="development")

    # Embeddings
    embeddings_provider: str = Field(default="fake", description="fake|openai")
    openai_api_key: Optional[str] = Field(default=None)
    openai_embeddings_model: str = Field(default="text-embedding-3-small")
    embeddings_dimensions: int = Field(default=64, description="Used by fake provider")

    # Rate limiting (per token+IP per minute)
    rate_limit_enabled: bool = Field(default=False)
    rate_limit_per_minute: int = Field(default=600)

    # QR check-in prototype
    qr_token: str = Field(default="dev-qr-token")

    @property
    def cors_origins_list(self) -> List[str]:
        s = (self.cors_origins or "").strip()
        if not s or s == "*":
            return ["*"]
        return [part.strip() for part in s.split(",") if part.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


