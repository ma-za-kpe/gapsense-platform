"""
Student Models

Student profiles and gap tracking.
Based on docs/specs/gapsense_data_model.sql (Section 2)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from .diagnostics import DiagnosticSession, GapProfile
    from .engagement import ParentActivity
    from .schools import School
    from .users import Parent, Teacher

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Student(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Students being assessed with GapSense.

    Dignity-first: Minimal data collection, no sensitive personal info beyond
    what's needed for effective diagnosis.
    """

    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("gender IN ('male', 'female', 'other')", name="check_gender"),
        Index("idx_students_parent", "primary_parent_id"),
        Index("idx_students_school", "school_id"),
        Index("idx_students_grade", "current_grade"),
    )

    # Identity (minimal)
    full_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Full name from teacher's class register (e.g., 'Kwame Mensah')",
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="First name only (some parents may not want to share last name)",
    )
    age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="Approximate age")
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Academic context
    school_id: Mapped[UUID | None] = mapped_column(ForeignKey("schools.id"), nullable=True)
    current_grade: Mapped[str] = mapped_column(
        String(5), nullable=False, comment="Enrolled grade (B1-B9)"
    )
    grade_as_of: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
        comment="When this grade was recorded",
    )
    teacher_id: Mapped[UUID | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)

    # Parent linkage (nullable until parent onboards and links)
    primary_parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parents.id"), nullable=True, comment="Linked when parent onboards"
    )
    secondary_parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("parents.id"), nullable=True
    )

    # Language context (critical for diagnosis)
    home_language: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="L1 spoken at home"
    )
    school_language: Mapped[str] = mapped_column(
        String(30), default="English", comment="Language of instruction at school"
    )

    # Diagnostic state
    latest_gap_profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("gap_profiles.id", name="fk_students_latest_gap_profile"),
        nullable=True,
        comment="FK to current gap profile",
    )
    diagnosis_count: Mapped[int] = mapped_column(Integer, default=0)
    first_diagnosed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_diagnosed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    school: Mapped[School | None] = relationship(back_populates="students")
    teacher: Mapped[Teacher | None] = relationship(back_populates="students")
    primary_parent: Mapped[Parent | None] = relationship(
        foreign_keys=[primary_parent_id], back_populates="primary_students"
    )
    secondary_parent: Mapped[Parent | None] = relationship(
        foreign_keys=[secondary_parent_id], back_populates="secondary_students"
    )
    latest_gap_profile: Mapped[GapProfile] = relationship(
        foreign_keys=[latest_gap_profile_id],
        post_update=True,  # Allows circular FK with gap_profiles
        uselist=False,
    )
    diagnostic_sessions: Mapped[list[DiagnosticSession]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    gap_profiles: Mapped[list[GapProfile]] = relationship(
        foreign_keys="GapProfile.student_id", back_populates="student", cascade="all, delete-orphan"
    )
    parent_activities: Mapped[list[ParentActivity]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
