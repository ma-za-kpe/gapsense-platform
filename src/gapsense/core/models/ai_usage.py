"""
AI Usage and Cost Tracking Models

Tracks all AI API calls for billing, budgeting, and optimization.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from gapsense.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIUsageLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks AI API usage and costs for budgeting and billing.

    Records every AI call with token counts and calculated costs.
    Enables:
    - Daily/monthly cost reports
    - Per-teacher/student budget tracking
    - Model performance comparison
    - Cost optimization analysis
    """

    __tablename__ = "ai_usage_logs"

    # What was analyzed
    student_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"),
        nullable=True,
        comment="Student being analyzed (if applicable)",
    )
    teacher_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Teacher who triggered analysis",
    )

    # AI call details
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="AI provider: anthropic or grok",
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Model name: claude-haiku-4-5, grok-4-1-fast-reasoning, etc.",
    )
    prompt_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Prompt template ID: ANALYSIS-001, DIAG-001, etc.",
    )

    # Token usage
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Input tokens (includes prompt + image tokens)",
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Output tokens (AI response)",
    )

    # Cost (calculated from tokens and pricing)
    input_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        comment="Input cost in USD",
    )
    output_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        comment="Output cost in USD",
    )
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        comment="Total cost = input + output",
    )

    # Performance
    latency_ms: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="API call latency in milliseconds",
    )

    # Status
    success: Mapped[bool] = mapped_column(
        nullable=False,
        comment="True if call succeeded, False if failed",
    )
    error_message: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Error message if call failed",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_ai_usage_logs_created_at", "created_at"),
        Index("ix_ai_usage_logs_teacher_id", "teacher_id"),
        Index("ix_ai_usage_logs_student_id", "student_id"),
        Index("ix_ai_usage_logs_provider_model", "provider", "model"),
        Index("ix_ai_usage_logs_prompt_id", "prompt_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<AIUsageLog(id={self.id}, provider={self.provider}, "
            f"model={self.model}, cost=${self.total_cost_usd:.4f})>"
        )
