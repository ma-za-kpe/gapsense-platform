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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


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
