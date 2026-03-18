"""
Processing Ledger Model

Tracks SQS message processing for idempotency (deduplication).
A unique constraint on (sqs_message_id, task_type) prevents duplicate
processing of redelivered SQS messages.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gapsense.core.models.base import Base


class ProcessingLedger(Base):
    """Idempotency guard for SQS message processing.

    Each row represents a single processing attempt for an SQS message.
    The unique constraint on (sqs_message_id, task_type) enables
    INSERT ... ON CONFLICT DO NOTHING deduplication.
    """

    __tablename__ = "processing_ledger"
    __table_args__ = (
        UniqueConstraint("sqs_message_id", "task_type", name="uq_ledger_msg_task"),
        Index("idx_ledger_expires", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sqs_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="processing")
    student_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW() + INTERVAL '48 hours'"),
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ProcessingLedger(id={self.id}, msg={self.sqs_message_id}, "
            f"task={self.task_type}, status={self.status})>"
        )
