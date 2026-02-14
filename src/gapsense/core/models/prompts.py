"""
Prompt Models

AI prompt versioning and quality tracking.
Based on docs/specs/gapsense_data_model.sql (Section 5)

Proprietary IP — Prompt engineering is GapSense's defensible moat.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from .diagnostics import DiagnosticSession
    from .engagement import ParentInteraction

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PromptCategory(Base):
    """Prompt categories for organizing AI prompts."""

    __tablename__ = "prompt_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="diagnostic, parent_engagement, teacher, analysis",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    prompt_versions: Mapped[list[PromptVersion]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class PromptVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Versioned AI prompts with quality tracking.

    Each prompt is tested against test cases before activation.
    PROPRIETARY IP.
    """

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("category_id", "version"),
        CheckConstraint(
            "status IN ('draft', 'testing', 'active', 'deprecated')", name="check_prompt_status"
        ),
        Index("idx_prompt_versions_active", "category_id", postgresql_where="status = 'active'"),
    )

    category_id: Mapped[int] = mapped_column(ForeignKey("prompt_categories.id"), nullable=False)

    # Version tracking
    version: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Semantic versioning: '1.0.0'"
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="e.g., 'Diagnostic Reasoning Prompt v2'"
    )

    # Prompt content
    system_prompt: Mapped[str] = mapped_column(
        Text, nullable=False, comment="The actual system prompt"
    )
    user_template: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Template for user messages (with {{placeholders}})"
    )
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Expected output format"
    )

    # Configuration
    model_target: Mapped[str] = mapped_column(
        String(50), default="claude-sonnet-4-5", comment="Which model this is optimized for"
    )
    temperature: Mapped[float] = mapped_column(default=0.3)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)

    # Quality tracking
    test_cases_passed: Mapped[int] = mapped_column(Integer, default=0)
    test_cases_total: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_score: Mapped[float | None] = mapped_column(
        nullable=True, comment="% accuracy on test cases"
    )

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20), default="draft", comment="draft, testing, active, deprecated"
    )
    activated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deprecated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deprecated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    category: Mapped[PromptCategory] = relationship(back_populates="prompt_versions")
    test_cases: Mapped[list[PromptTestCase]] = relationship(
        back_populates="prompt_version", cascade="all, delete-orphan"
    )
    diagnostic_sessions: Mapped[list[DiagnosticSession]] = relationship(
        back_populates="prompt_version"
    )
    parent_interactions: Mapped[list[ParentInteraction]] = relationship(
        back_populates="prompt_version"
    )


class PromptTestCase(Base, UUIDPrimaryKeyMixin):
    """Test scenarios for validating prompts."""

    __tablename__ = "prompt_test_cases"

    prompt_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("prompt_versions.id", ondelete="CASCADE"), nullable=False
    )

    # Test input
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    test_input: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="Simulated input data"
    )
    expected_output: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="What the prompt should produce"
    )

    # Test results
    actual_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    passed: Mapped[bool | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_run_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    prompt_version: Mapped[PromptVersion] = relationship(back_populates="test_cases")
