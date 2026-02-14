"""
Engagement Models

Parent engagement via WhatsApp (Wolf/Aurino dignity-first model).
Based on docs/specs/gapsense_data_model.sql (Section 4)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from .curriculum import CurriculumNode
    from .diagnostics import DiagnosticSession, GapProfile
    from .prompts import PromptVersion
    from .students import Student
    from .users import Parent

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin


class ParentInteraction(Base, UUIDPrimaryKeyMixin):
    """Every WhatsApp message exchange with parents.

    Wolf/Aurino compliance: Never generic, always specific, always dignity-preserving.
    """

    __tablename__ = "parent_interactions"
    __table_args__ = (
        CheckConstraint("direction IN ('inbound', 'outbound')", name="check_direction"),
        CheckConstraint(
            "delivery_status IN ('queued', 'sent', 'delivered', 'read', 'failed')",
            name="check_delivery_status",
        ),
        Index("idx_interactions_parent", "parent_id"),
        Index("idx_interactions_student", "student_id"),
        Index("idx_interactions_purpose", "interaction_purpose"),
    )

    parent_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("parents.id"), nullable=False
    )
    student_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=True
    )

    # Message metadata
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="inbound or outbound"
    )
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp")
    wa_message_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="WhatsApp message ID for tracking"
    )

    # Content
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="text, image, voice, button, list, template"
    )
    interaction_purpose: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="diagnostic, activity, check_in, onboarding, feedback, reminder",
    )

    message_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Actual message text (encrypted at rest)"
    )
    media_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Media attachment URL"
    )
    template_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="WhatsApp template name if applicable"
    )

    # Language
    language_used: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="Language this message was in"
    )

    # AI processing
    ai_generated: Mapped[bool] = mapped_column(default=False)
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=True
    )
    sentiment_score: Mapped[float | None] = mapped_column(
        nullable=True, comment="Sentiment -1.0 to 1.0"
    )

    # Status
    delivery_status: Mapped[str] = mapped_column(
        String(20), default="sent", comment="queued, sent, delivered, read, failed"
    )

    sent_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    parent: Mapped[Parent] = relationship(back_populates="interactions")
    student: Mapped[Student] = relationship()
    prompt_version: Mapped[PromptVersion] = relationship()


class ParentActivity(Base, UUIDPrimaryKeyMixin):
    """Specific learning activities sent to parents.

    3-minute dignity-preserving activities using household materials.
    """

    __tablename__ = "parent_activities"
    __table_args__ = (
        Index("idx_activities_parent", "parent_id"),
        Index("idx_activities_node", "focus_node_id"),
    )

    parent_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("parents.id"), nullable=False
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("students.id"), nullable=False
    )
    gap_profile_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("gap_profiles.id"), nullable=True
    )

    # Activity details
    focus_node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("curriculum_nodes.id"), nullable=False
    )
    activity_title: Mapped[str] = mapped_column(String(200), nullable=False)
    activity_description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="The 3-minute activity"
    )
    materials_needed: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="What parent needs (bottle caps, paper, etc.)"
    )
    estimated_minutes: Mapped[int] = mapped_column(SmallInteger, default=3)

    # Language
    language: Mapped[str] = mapped_column(String(30), nullable=False)

    # Tracking
    sent_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))
    started_at: Mapped[datetime | None] = mapped_column(
        nullable=True, comment="Parent confirmed they started"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True, comment="Parent confirmed completion"
    )
    parent_feedback: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional feedback from parent"
    )

    # Effectiveness
    follow_up_session_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("diagnostic_sessions.id"), nullable=True
    )
    skill_improved: Mapped[bool | None] = mapped_column(
        nullable=True, comment="Did follow-up show improvement?"
    )

    # Relationships
    parent: Mapped[Parent] = relationship(back_populates="activities")
    student: Mapped[Student] = relationship(back_populates="parent_activities")
    gap_profile: Mapped[GapProfile] = relationship(back_populates="parent_activities")
    focus_node: Mapped[CurriculumNode] = relationship()
    follow_up_session: Mapped[DiagnosticSession] = relationship()
