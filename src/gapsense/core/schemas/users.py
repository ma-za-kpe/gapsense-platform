"""
User Schemas (Parents and Teachers)

Pydantic models for API request/response validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Parent Schemas
class ParentBase(BaseModel):
    """Base parent schema with common fields."""

    phone: str = Field(..., min_length=10, max_length=20, description="WhatsApp phone number")
    preferred_name: str | None = Field(None, max_length=100, description="Preferred name")
    preferred_language: str = Field(default="en", max_length=30, description="Language preference")
    district_id: int | None = None
    community: str | None = Field(None, max_length=200)


class ParentCreate(ParentBase):
    """Schema for creating a new parent."""

    opted_in: bool = Field(default=True, description="WhatsApp opt-in consent")


class ParentUpdate(BaseModel):
    """Schema for updating parent information."""

    preferred_name: str | None = None
    preferred_language: str | None = None
    district_id: int | None = None
    community: str | None = None
    literacy_level: str | None = Field(None, description="literate, semi_literate, non_literate")


class ParentSchema(ParentBase):
    """Full parent schema for responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone_verified: bool
    literacy_level: str | None
    onboarded_at: datetime | None
    last_interaction_at: datetime | None
    total_interactions: int
    engagement_score: float | None
    opted_in: bool
    opted_in_at: datetime | None
    opted_out: bool
    opted_out_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Teacher Schemas
class TeacherBase(BaseModel):
    """Base teacher schema with common fields."""

    school_id: UUID
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20, description="WhatsApp phone number")
    grade_taught: str | None = Field(None, max_length=5, description="Grade taught (B1-B9)")
    subjects: list[str] | None = Field(None, description="Subjects taught")


class TeacherCreate(TeacherBase):
    """Schema for creating a new teacher."""

    pass


class TeacherUpdate(BaseModel):
    """Schema for updating teacher information."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    grade_taught: str | None = None
    subjects: list[str] | None = None


class TeacherSchema(TeacherBase):
    """Full teacher schema for responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    phone_verified: bool
    onboarded_at: datetime | None
    last_active_at: datetime | None
    total_students_diagnosed: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
