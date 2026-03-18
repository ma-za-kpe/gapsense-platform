"""
Curriculum Pydantic Schemas

Response models for curriculum API endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CurriculumStrandSchema(BaseModel):
    """Curriculum strand response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    strand_number: int
    name: str
    color_hex: str | None = None
    description: str | None = None
    created_at: datetime


class CurriculumSubStrandSchema(BaseModel):
    """Curriculum sub-strand response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    strand_id: int
    sub_strand_number: int
    phase: str
    name: str
    description: str | None = None


class CurriculumNodeSchema(BaseModel):
    """Curriculum node response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    grade: str
    strand_id: int
    sub_strand_id: int
    content_standard_number: int
    title: str
    description: str
    severity: int = Field(ge=1, le=5)
    severity_rationale: str | None = None
    questions_required: int = 2
    confidence_threshold: float = 0.80
    ghana_evidence: str | None = None
    population_status: str = "skeleton"
    created_at: datetime


class CurriculumStrandDetailSchema(CurriculumStrandSchema):
    """Curriculum strand with sub-strands."""

    sub_strands: list[CurriculumSubStrandSchema] = []


class CurriculumNodeDetailSchema(CurriculumNodeSchema):
    """Curriculum node with relationships."""

    strand: CurriculumStrandSchema
    sub_strand: CurriculumSubStrandSchema


class PrerequisiteGraphSchema(BaseModel):
    """Prerequisite graph for a node."""

    node: CurriculumNodeSchema
    prerequisites: list[CurriculumNodeSchema] = []
