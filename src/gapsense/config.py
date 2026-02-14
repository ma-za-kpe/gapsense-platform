"""
Application Configuration

Uses Pydantic Settings for type-safe environment variable management.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # ========================================================================
    # DATABASE
    # ========================================================================

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://gapsense:localdev@localhost:5432/gapsense",
        description="PostgreSQL connection string (async)",
    )

    # ========================================================================
    # ANTHROPIC AI
    # ========================================================================

    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key for Claude")

    ANTHROPIC_MAX_REQUESTS_PER_MINUTE: int = 50
    ANTHROPIC_MAX_CONCURRENT_REQUESTS: int = 10

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
    def validate_data_path(cls: type[Settings], v: str | Path) -> Path:  # noqa: ARG003
        """Convert string to Path and validate existence."""
        path = Path(v) if isinstance(v, str) else v

        if not path.exists():
            raise ValueError(
                f"GAPSENSE_DATA_PATH does not exist: {path.absolute()}\n"
                "Please set GAPSENSE_DATA_PATH to point to gapsense-data repo."
            )

        if not (path / "curriculum").exists():
            raise ValueError(
                f"GAPSENSE_DATA_PATH missing curriculum/ directory: {path.absolute()}\n"
                "Expected structure: curriculum/, prompts/, business/"
            )

        return path

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @property
    def prerequisite_graph_path(self) -> Path:
        """Path to latest prerequisite graph JSON."""
        return self.GAPSENSE_DATA_PATH / "curriculum" / "gapsense_prerequisite_graph_v1.2.json"

    @property
    def prompt_library_path(self) -> Path:
        """Path to latest prompt library JSON."""
        return self.GAPSENSE_DATA_PATH / "prompts" / "gapsense_prompt_library_v1.1.json"

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
