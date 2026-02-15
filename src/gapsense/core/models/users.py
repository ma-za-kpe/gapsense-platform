"""
User Models

Teachers and Parents for the GapSense platform.
Based on docs/specs/gapsense_data_model.sql (Section 2)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from .engagement import ParentActivity, ParentInteraction
    from .schools import District, School
    from .students import Student

from sqlalchemy import ForeignKey, Integer, String, event
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Teacher(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Teachers using GapSense to diagnose students."""

    __tablename__ = "teachers"

    school_id: Mapped[UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)

    # Identity
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="WhatsApp number")
    phone_verified: Mapped[bool] = mapped_column(default=False)

    # Teaching context
    grade_taught: Mapped[str | None] = mapped_column(
        String(5), nullable=True, comment="Current grade (B1-B9)"
    )
    subjects: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)), nullable=True, comment="Array of subjects taught"
    )

    # GapSense engagement
    onboarded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(nullable=True)
    total_students_diagnosed: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    school: Mapped[School] = relationship(back_populates="teachers")
    students: Mapped[list[Student]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )


class Parent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Parents engaging via WhatsApp (Wolf/Aurino dignity-first model).

    Minimal data collection - only what's necessary for effective support.
    """

    __tablename__ = "parents"

    # Identity (minimal required)
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="WhatsApp number (primary identifier)"
    )
    phone_verified: Mapped[bool] = mapped_column(default=False)
    preferred_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="How they want to be addressed"
    )

    # Language (critical for engagement)
    preferred_language: Mapped[str] = mapped_column(
        String(30), default="en", comment="ISO code or 'tw', 'ee', 'ga', 'dag'"
    )
    literacy_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="SENSITIVE: literate, semi_literate, non_literate. Determines message complexity. NEVER shared externally.",
    )

    # Location
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"), nullable=True)
    community: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Engagement tracking
    onboarded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_interaction_at: Mapped[datetime | None] = mapped_column(nullable=True)
    total_interactions: Mapped[int] = mapped_column(Integer, default=0)
    engagement_score: Mapped[float | None] = mapped_column(
        nullable=True, comment="Rolling engagement metric"
    )

    # Conversation state (WhatsApp flow orchestration)
    conversation_state: Mapped[dict[str, Any] | None] = mapped_column(
        type_=JSON,
        nullable=True,
        comment="Current flow state: {flow, step, data}. Enables multi-step conversations.",
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        nullable=True, comment="Last WhatsApp message received from parent"
    )
    session_expires_at: Mapped[datetime | None] = mapped_column(
        nullable=True, comment="24-hour session window expiry (WhatsApp constraint)"
    )

    # Wolf/Aurino compliance
    opted_in: Mapped[bool] = mapped_column(default=False, comment="Explicit WhatsApp opt-in")
    opted_in_at: Mapped[datetime | None] = mapped_column(nullable=True)
    opted_out: Mapped[bool] = mapped_column(default=False)
    opted_out_at: Mapped[datetime | None] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    district: Mapped[District] = relationship()
    primary_students: Mapped[list[Student]] = relationship(
        foreign_keys="Student.primary_parent_id",
        back_populates="primary_parent",
        cascade="all, delete-orphan",
    )
    secondary_students: Mapped[list[Student]] = relationship(
        foreign_keys="Student.secondary_parent_id",
        back_populates="secondary_parent",
        cascade="all, delete-orphan",
    )
    interactions: Mapped[list[ParentInteraction]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    activities: Mapped[list[ParentActivity]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )


# Event listener to ensure opted_out defaults to False for in-memory objects
@event.listens_for(Parent, "init", propagate=True)
def receive_init_parent(target, _args, kwargs):  # type: ignore[no-untyped-def]
    """Ensure opted_out defaults to False if not provided."""
    if "opted_out" not in kwargs:
        target.opted_out = False
