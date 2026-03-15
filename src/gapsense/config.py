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
    # AI PROVIDERS
    # ========================================================================

    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key for Claude")

    ANTHROPIC_MAX_REQUESTS_PER_MINUTE: int = 50
    ANTHROPIC_MAX_CONCURRENT_REQUESTS: int = 10

    GROK_API_KEY: str = Field(default="", description="xAI Grok API key (fallback provider)")

    # ========================================================================
    # WHATSAPP PROVIDER
    # ========================================================================

    WHATSAPP_PROVIDER: str = Field(
        default="meta",
        description="WhatsApp provider: 'meta' (Cloud API) or 'twilio'",
    )

    @field_validator("WHATSAPP_PROVIDER")
    @classmethod
    def validate_whatsapp_provider(cls, v: str) -> str:
        """Validate WhatsApp provider is either 'meta' or 'twilio'."""
        if v not in ("meta", "twilio"):
            raise ValueError(
                f"WHATSAPP_PROVIDER must be 'meta' or 'twilio', got '{v}'. "
                "Check your .env file or environment variables."
            )
        return v

    # Meta WhatsApp Cloud API
    WHATSAPP_API_TOKEN: str = Field(default="", description="WhatsApp Cloud API token")

    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="", description="WhatsApp phone number ID")

    WHATSAPP_VERIFY_TOKEN: str = Field(
        default="local_verify_token", description="WhatsApp webhook verification token"
    )

    # Twilio WhatsApp API
    TWILIO_ACCOUNT_SID: str = Field(default="", description="Twilio Account SID")
    TWILIO_AUTH_TOKEN: str = Field(
        default="", description="Twilio Auth Token (or leave empty if using API Key)"
    )
    TWILIO_API_KEY_SID: str = Field(
        default="", description="Twilio API Key SID (optional, more secure than Auth Token)"
    )
    TWILIO_API_KEY_SECRET: str = Field(default="", description="Twilio API Key Secret")
    TWILIO_WHATSAPP_NUMBER: str = Field(
        default="", description="Twilio WhatsApp sender (e.g., whatsapp:+14155238886)"
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
    def validate_data_path(cls: type[Settings], v: str | Path) -> Path:
        """Convert string to Path and validate existence."""
        import os

        path = Path(v) if isinstance(v, str) else v

        # Skip validation in CI environment (gapsense-data repo not available)
        if os.getenv("CI") == "true":
            return path

        if not path.exists():
            raise ValueError(
                f"GAPSENSE_DATA_PATH does not exist: {path.absolute()}\n"
                "Please set GAPSENSE_DATA_PATH to point to gapsense-data repo."
            )

        if not (path / "curricula").exists():
            raise ValueError(
                f"GAPSENSE_DATA_PATH missing curricula/ directory: {path.absolute()}\n"
                "Expected structure: curricula/, prompts/, cultural_context/, languages/"
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
        """Path to v2.0 multi-country prompt library JSON."""
        return (
            self.GAPSENSE_DATA_PATH / "prompts" / "gapsense_prompt_library_v2.0_multicountry.json"
        )

    @property
    def curricula_base_path(self) -> Path:
        """Multi-country curricula directory."""
        return self.GAPSENSE_DATA_PATH / "curricula"

    @property
    def cultural_context_path(self) -> Path:
        """Cultural context files directory."""
        return self.GAPSENSE_DATA_PATH / "cultural_context"

    @property
    def languages_base_path(self) -> Path:
        """L1 language files directory."""
        return self.GAPSENSE_DATA_PATH / "languages"

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
