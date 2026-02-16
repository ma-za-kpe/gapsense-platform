"""
Diagnostic Models

Adaptive diagnostic sessions, questions, and gap profiles.
Based on docs/specs/gapsense_data_model.sql (Section 3)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from .curriculum import (
        CascadePath,
        CurriculumIndicator,
        CurriculumMisconception,
        CurriculumNode,
    )
    from .engagement import ParentActivity
    from .prompts import PromptVersion
    from .students import Student

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin


class DiagnosticSession(Base, UUIDPrimaryKeyMixin):
    """Adaptive diagnostic assessment session for a student.

    Each session traces backward from current grade to identify root gap.
    """

    __tablename__ = "diagnostic_sessions"
    __table_args__ = (
        CheckConstraint(
            "initiated_by IN ('parent', 'teacher', 'system', 'self')", name="check_initiated_by"
        ),
        CheckConstraint(
            "channel IN ('whatsapp', 'web', 'app', 'sms', 'paper')", name="check_channel"
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'abandoned', 'timed_out')",
            name="check_session_status",
        ),
        Index("idx_sessions_student", "student_id"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_root_gap", "root_gap_node_id"),
    )

    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("students.id", name="fk_diagnostic_sessions_student"),
        nullable=False,
    )

    # Session context
    initiated_by: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Who started: parent, teacher, system, self"
    )
    channel: Mapped[str] = mapped_column(
        String(20), default="whatsapp", comment="Where: whatsapp, web, app, sms, paper"
    )

    # Session state
    status: Mapped[str] = mapped_column(
        String(20), default="in_progress", comment="in_progress, completed, abandoned, timed_out"
    )
    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()"),
        comment="Session start time",
        type_=DateTime(timezone=True),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True, type_=DateTime(timezone=True)
    )

    # Entry point
    entry_grade: Mapped[str] = mapped_column(
        String(5), nullable=False, comment="Grade level started at (B1-B9)"
    )
    entry_node_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_nodes.id"),
        nullable=True,
        comment="First node tested",
    )

    # Results
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    nodes_tested: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), default=[], comment="Array of tested node IDs"
    )
    nodes_mastered: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), default=[])
    nodes_gap: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), default=[])

    # Root cause identified
    root_gap_node_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_nodes.id"),
        nullable=True,
        comment="Deepest root gap identified",
    )
    root_gap_confidence: Mapped[float | None] = mapped_column(
        nullable=True, comment="Confidence 0.0-1.0"
    )
    cascade_path_id: Mapped[int | None] = mapped_column(
        ForeignKey("cascade_paths.id"), nullable=True, comment="Which cascade pattern matched"
    )

    # AI metadata
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=True
    )
    model_used: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="e.g., 'claude-sonnet-4-5'"
    )
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_reasoning_log: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Full chain-of-thought (encrypted at rest)"
    )

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    student: Mapped[Student] = relationship(back_populates="diagnostic_sessions")
    entry_node: Mapped[CurriculumNode] = relationship(foreign_keys=[entry_node_id])
    root_gap_node: Mapped[CurriculumNode] = relationship(foreign_keys=[root_gap_node_id])
    cascade_path: Mapped[CascadePath] = relationship()
    prompt_version: Mapped[PromptVersion] = relationship()
    questions: Mapped[list[DiagnosticQuestion]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    gap_profile: Mapped[GapProfile] = relationship(back_populates="session", uselist=False)


class DiagnosticQuestion(Base, UUIDPrimaryKeyMixin):
    """Individual question within a diagnostic session."""

    __tablename__ = "diagnostic_questions"
    __table_args__ = (
        Index("idx_questions_session", "session_id"),
        Index("idx_questions_node", "node_id"),
    )

    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Question context
    question_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, comment="Order within session"
    )
    node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("curriculum_nodes.id"), nullable=False
    )
    indicator_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("curriculum_indicators.id"), nullable=True
    )

    # Question content
    question_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="The actual question asked"
    )
    question_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="multiple_choice, free_response, image, voice"
    )
    question_media_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Image/audio if applicable"
    )
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Response
    student_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_media_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Photo of exercise book, voice note"
    )
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    response_time_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="How long student took"
    )

    # AI analysis
    error_pattern_detected: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Which error pattern matched"
    )
    misconception_id: Mapped[str | None] = mapped_column(
        String(30), ForeignKey("curriculum_misconceptions.id"), nullable=True
    )
    ai_analysis: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Detailed AI reasoning about the response"
    )

    asked_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("NOW()"), type_=DateTime(timezone=True)
    )
    answered_at: Mapped[datetime | None] = mapped_column(
        nullable=True, type_=DateTime(timezone=True)
    )

    # Relationships
    session: Mapped[DiagnosticSession] = relationship(back_populates="questions")
    node: Mapped[CurriculumNode] = relationship()
    indicator: Mapped[CurriculumIndicator] = relationship()
    misconception: Mapped[CurriculumMisconception] = relationship()


class GapProfile(Base, UUIDPrimaryKeyMixin):
    """Student's learning gap profile (updated after each session).

    Only one is_current=TRUE per student at any time.
    """

    __tablename__ = "gap_profiles"
    __table_args__ = (
        Index("idx_gap_profiles_student", "student_id"),
        Index("idx_gap_profiles_current", "student_id", postgresql_where="is_current = TRUE"),
    )

    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("students.id", name="fk_gap_profiles_student"),
        nullable=False,
    )
    session_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("diagnostic_sessions.id", name="fk_gap_profiles_session"),
        nullable=False,
    )

    # Gap summary
    mastered_nodes: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), default=[], comment="Nodes confirmed mastered"
    )
    gap_nodes: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), default=[], comment="Nodes with confirmed gaps"
    )
    uncertain_nodes: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), default=[], comment="Need more data"
    )

    # Root cause analysis
    primary_gap_node: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_nodes.id"),
        nullable=True,
        comment="The deepest root gap",
    )
    primary_cascade: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Which cascade path"
    )
    secondary_gaps: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), default=[], comment="Additional gap roots"
    )

    # Actionable output
    recommended_focus_node: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("curriculum_nodes.id"),
        nullable=True,
        comment="What to work on FIRST",
    )
    recommended_activity: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Specific activity for parent"
    )
    estimated_grade_level: Mapped[str | None] = mapped_column(
        String(5), nullable=True, comment="Functional grade level"
    )
    grade_gap: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="Difference from enrolled grade"
    )

    # Confidence
    overall_confidence: Mapped[float | None] = mapped_column(
        nullable=True, comment="How confident we are in this profile (0.0-1.0)"
    )

    is_current: Mapped[bool] = mapped_column(
        default=True, comment="Only one current profile per student"
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=text("NOW()"))

    # Relationships
    student: Mapped[Student] = relationship(
        foreign_keys=[student_id], back_populates="gap_profiles"
    )
    session: Mapped[DiagnosticSession] = relationship(back_populates="gap_profile")
    primary_gap: Mapped[CurriculumNode] = relationship(foreign_keys=[primary_gap_node])
    recommended_focus: Mapped[CurriculumNode] = relationship(foreign_keys=[recommended_focus_node])
    parent_activities: Mapped[list[ParentActivity]] = relationship(
        back_populates="gap_profile", cascade="all, delete-orphan"
    )
