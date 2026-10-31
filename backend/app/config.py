from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from SAVEPOINT_* environment variables or a local .env."""

    model_config = SettingsConfigDict(env_prefix="SAVEPOINT_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "production"
    database_url: str = "sqlite:///./savepoint.db"
    secret_key: SecretStr
    cookie_secure: bool = True
    cookie_name: str = "sp_session"
    session_ttl_hours: int = Field(24 * 14, ge=1)
    admin_session_ttl_hours: int = Field(8, ge=1)
    allowed_origins: list[str] = Field(default_factory=list)
    public_base_url: str = "http://localhost:5173"

    login_window_minutes: int = Field(15, ge=1)
    login_max_failures_per_account: int = Field(8, ge=1)
    login_max_failures_per_ip: int = Field(40, ge=1)
    trust_forwarded_for: bool = False

    @field_validator("secret_key")
    @classmethod
    def _secret_must_be_strong(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < 32 or secret.lower().startswith("change-me"):
            raise ValueError(
                "SAVEPOINT_SECRET_KEY must be a random value of at least 32 characters"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
