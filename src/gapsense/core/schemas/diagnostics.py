"""
Diagnostic Pydantic Schemas

Request/response models for diagnostic API endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Request schemas
class DiagnosticSessionCreate(BaseModel):
    """Request schema for creating a diagnostic session."""

    student_id: UUID
    entry_grade: str = Field(pattern=r"^B[1-9]$")
    initiated_by: str = Field(pattern=r"^(parent|teacher|system|self)$")
    channel: str = Field(default="whatsapp", pattern=r"^(whatsapp|web|app|sms|paper)$")


class DiagnosticAnswerSubmit(BaseModel):
    """Request schema for submitting an answer."""

    node_id: UUID
    student_response: str
    is_correct: bool
    response_time_seconds: int | None = None
    response_media_url: str | None = None


# Response schemas
class DiagnosticSessionSchema(BaseModel):
    """Diagnostic session response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    initiated_by: str
    channel: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    entry_grade: str
    entry_node_id: UUID | None = None
    total_questions: int
    correct_answers: int
    root_gap_node_id: UUID | None = None
    root_gap_confidence: float | None = None
    created_at: datetime


class DiagnosticQuestionSchema(BaseModel):
    """Diagnostic question response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    question_order: int
    node_id: UUID
    question_text: str
    question_type: str
    question_media_url: str | None = None
    student_response: str | None = None
    is_correct: bool | None = None
    response_time_seconds: int | None = None
    asked_at: datetime
    answered_at: datetime | None = None


class GapProfileSchema(BaseModel):
    """Gap profile response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: UUID
    session_id: UUID
    mastered_nodes: list[UUID]
    gap_nodes: list[UUID]
    uncertain_nodes: list[UUID]
    primary_gap_node: UUID | None = None
    primary_cascade: str | None = None
    recommended_focus_node: UUID | None = None
    recommended_activity: str | None = None
    estimated_grade_level: str | None = None
    grade_gap: int | None = None
    is_current: bool
    created_at: datetime


class DiagnosticAnswerResponse(BaseModel):
    """Response after submitting an answer."""

    question_id: UUID
    is_correct: bool
    student_response: str
    next_question: DiagnosticQuestionSchema | None = None
    session_completed: bool = False
    message: str | None = None
