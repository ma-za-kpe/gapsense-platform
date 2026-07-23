"""
SQLAlchemy Base Model and Mixins

Provides base class and common mixins for all GapSense models.
Follows the data model specification in docs/specs/gapsense_data_model.sql
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, event, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class UUIDPrimaryKeyMixin:
    """Mixin for UUID primary key.

    Per ADR-003: All entities use UUID primary keys for:
    - Better scalability (no sequence bottleneck)
    - Offline generation capability
    - Security (non-sequential IDs)
    """

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, comment="UUID primary key")


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps.

    All timestamps use UTC (timezone-aware).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        nullable=False,
        comment="Creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("NOW()"),
        nullable=False,
        comment="Last update timestamp (UTC)",
    )


# Event listeners to auto-generate UUIDs and timestamps for in-memory objects
@event.listens_for(UUIDPrimaryKeyMixin, "init", propagate=True)
def receive_init_uuid(target, args, kwargs):  # type: ignore[no-untyped-def]
    """Auto-generate UUID on instance creation if not provided."""
    if "id" not in kwargs:
        target.id = uuid4()


@event.listens_for(TimestampMixin, "init", propagate=True)
def receive_init_timestamps(target, args, kwargs):  # type: ignore[no-untyped-def]
    """Auto-generate timestamps on instance creation if not provided."""
    now = datetime.now(UTC)
    if "created_at" not in kwargs:
        target.created_at = now
    if "updated_at" not in kwargs:
        target.updated_at = now


class SoftDeleteMixin:
    """Mixin for soft deletion support.

    Per Ghana Data Protection Act: Support right to deletion
    with 30-day grace period before anonymization.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Soft delete timestamp (NULL = not deleted)",
    )

    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = datetime.now(UTC)

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None
