 from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "production"] = Field(
        default="development", validation_alias="APP_ENV"
    )

    database_url: str = Field(..., validation_alias="DATABASE_URL", min_length=1)

    jwt_secret_key: SecretStr = Field(..., validation_alias="JWT_SECRET_KEY")
    access_token_expire_minutes: int = Field(
        default=60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES", ge=1, le=60 * 24 * 30
    )

    resume_storage_path: Path = Field(
        default=Path("./storage/resumes"), validation_alias="RESUME_STORAGE_PATH"
    )

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
