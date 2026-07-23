"""
Application Configuration

Uses Pydantic Settings for type-safe environment variable management.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Self

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gapsense.curriculum.coverage import canonical_repository_available


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # ========================================================================
    # APPLICATION
    # ========================================================================

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    DEBUG: bool = False
    ANALYTICS_MODE: Literal["disabled", "local_aggregate"] = "disabled"

    # ========================================================================
    # DATABASE
    # ========================================================================

    DATABASE_URL: str = Field(
        # pragma: allowlist nextline secret -- local-only disposable credential
        default="postgresql+asyncpg://gapsense:localdev@localhost:5432/gapsense",
        description="PostgreSQL connection string (async)",
    )

    # ========================================================================
    # LOCAL AI (OLLAMA)
    # ========================================================================

    OLLAMA_BASE_URL: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://host.docker.internal:11434"),
        description="Local Ollama API reachable from the Docker runtime",
    )
    OLLAMA_MODEL: str = Field(
        default="llama3.1:8b",
        min_length=1,
        max_length=200,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
        description="Locally installed Ollama model selected for optional AI assistance",
    )
    OLLAMA_TIMEOUT_SECONDS: int = Field(default=60, ge=1, le=600)
    OLLAMA_MAX_CONCURRENT_REQUESTS: int = Field(default=2, ge=1, le=16)

    # ========================================================================
    # WHATSAPP CLOUD API
    # ========================================================================

    WHATSAPP_API_TOKEN: str = Field(default="", description="WhatsApp Cloud API token")

    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="", description="WhatsApp phone number ID")

    WHATSAPP_VERIFY_TOKEN: str = Field(
        default="local_verify_token", description="WhatsApp webhook verification token"
    )

    # ========================================================================
    # AWS
    # ========================================================================

    AWS_REGION: str = "af-south-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    SQS_QUEUE_URL: str = Field(
        default="http://localstack:4566/000000000000/gapsense-messages",
        description="SQS FIFO queue URL",
    )

    S3_MEDIA_BUCKET: str = "gapsense-media-local"

    # ========================================================================
    # AUTH (Cognito)
    # ========================================================================

    COGNITO_USER_POOL_ID: str = ""
    COGNITO_CLIENT_ID: str = ""

    # ========================================================================
    # DATA PATH (for proprietary IP)
    # ========================================================================

    GAPSENSE_DATA_PATH: Path = Field(
        default=Path("../gapsense-data"),
        description="Path to gapsense-data repo with proprietary IP",
    )

    @field_validator("GAPSENSE_DATA_PATH", mode="before")
    @classmethod
    def validate_data_path(cls, v: str | Path) -> Path:
        """Convert string to Path and validate existence."""
        path = Path(v) if isinstance(v, str) else v

        if not path.exists():
            raise ValueError(
                f"GAPSENSE_DATA_PATH does not exist: {path.absolute()}\n"
                "Please set GAPSENSE_DATA_PATH to point to gapsense-data repo."
            )

        if not canonical_repository_available(path):
            raise ValueError(
                "GAPSENSE_DATA_PATH missing canonical curricula/ghana and curricula/uganda "
                f"directories: {path.absolute()}"
            )

        return path

    @model_validator(mode="after")
    def validate_analytics_environment(self) -> Self:
        """Keep the temporary aggregate sink inside an explicitly local runtime."""
        if self.ANALYTICS_MODE == "local_aggregate" and self.ENVIRONMENT != "local":
            raise ValueError("local_aggregate analytics is restricted to the local environment")
        return self

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @property
    def curricula_path(self) -> Path:
        """Path to the canonical multi-country curriculum repository root."""
        return self.GAPSENSE_DATA_PATH / "curricula"

    @property
    def prompt_library_path(self) -> Path:
        """Path to latest prompt library JSON."""
        return (
            self.GAPSENSE_DATA_PATH / "prompts" / "gapsense_prompt_library_v2.0_multicountry.json"
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"

    @property
    def is_local(self) -> bool:
        """Check if running locally."""
        return self.ENVIRONMENT == "local"


# Global settings instance
settings = Settings()
