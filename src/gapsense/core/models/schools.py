"""
School Models

Geographic hierarchy and school administration for Ghana.
Based on docs/specs/gapsense_data_model.sql (Section 2)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .students import Student
    from .users import Teacher

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GESSchool(Base, TimestampMixin):
    """GES (Ghana Education Service) School Database.

    Imported from ges.gov.gh - used for autocomplete and validation.
    Read-only reference data for school registration.
    """

    __tablename__ = "ges_schools"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ges_id: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, comment="GES school ID"
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False, comment="Official school name")
    region: Mapped[str] = mapped_column(String(100), nullable=False, comment="Region name")
    district: Mapped[str] = mapped_column(String(100), nullable=False, comment="District name")
    school_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="School type (e.g., Senior High School)"
    )
    courses_offered: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Courses/programs offered"
    )
    contact: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Contact person from GES database"
    )


class Region(Base):
    """Ghana's 16 administrative regions."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="Region name"
    )
    code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False, comment="Region code")

    # Relationships
    districts: Mapped[list[District]] = relationship(
        back_populates="region", cascade="all, delete-orphan"
    )


class District(Base, TimestampMixin):
    """Districts within regions (Ghana Education Service districts)."""

    __tablename__ = "districts"
    __table_args__ = (UniqueConstraint("region_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    ges_district_code: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Ghana Education Service district code"
    )

    # Relationships
    region: Mapped[Region] = relationship(back_populates="districts")
    schools: Mapped[list[School]] = relationship(
        back_populates="district", cascade="all, delete-orphan"
    )


class School(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual schools."""

    __tablename__ = "schools"
    __table_args__ = (
        CheckConstraint(
            "school_type IN ('primary', 'jhs', 'combined', 'private')", name="check_school_type"
        ),
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), nullable=False)
    school_type: Mapped[str] = mapped_column(
        String(20), default="primary", comment="Type: primary, jhs, combined, private"
    )
    ges_school_code: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="Ghana Education Service school code"
    )

    # Link to GES database (optional - for schools in GES database)
    ges_school_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="FK to ges_schools table"
    )

    # Registration info (for self-service school registration)
    registered_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Headmaster/contact who registered"
    )
    registered_at: Mapped[str | None] = mapped_column(
        nullable=True, comment="When school registered in GapSense"
    )

    # Contact
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(nullable=True)
    location_lng: Mapped[float | None] = mapped_column(nullable=True)

    # Metadata
    total_enrollment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language_of_instruction: Mapped[str] = mapped_column(
        String(30), default="English", comment="Primary language of instruction"
    )
    dominant_l1: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="Most common mother tongue"
    )

    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    district: Mapped[District] = relationship(back_populates="schools")
    teachers: Mapped[list[Teacher]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    students: Mapped[list[Student]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    invitations: Mapped[list[SchoolInvitation]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )


class SchoolInvitation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """School invitation codes for teacher onboarding.

    Generated when school registers, allows teachers to join with a code.
    """

    __tablename__ = "school_invitations"

    school_id: Mapped[str] = mapped_column(
        ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    invitation_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="e.g., STMARYS-ABC123"
    )

    created_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Headmaster/contact who created"
    )
    expires_at: Mapped[str | None] = mapped_column(
        nullable=True, comment="Optional expiration date"
    )

    max_teachers: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Max number of teachers who can use this code"
    )
    teachers_joined: Mapped[int] = mapped_column(
        Integer, default=0, comment="How many teachers have used this code"
    )

    is_active: Mapped[bool] = mapped_column(default=True, comment="Can still be used?")

    # Relationship
    school: Mapped[School] = relationship(back_populates="invitations")
