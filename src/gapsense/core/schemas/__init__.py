"""Pydantic schemas for API validation."""

from .curriculum import CurriculumNodeSchema, CurriculumStrandSchema
from .diagnostics import (
    DiagnosticAnswerResponse,
    DiagnosticAnswerSubmit,
    DiagnosticSessionCreate,
    DiagnosticSessionSchema,
    GapProfileSchema,
)
from .users import (
    ParentCreate,
    ParentSchema,
    ParentUpdate,
    TeacherCreate,
    TeacherSchema,
    TeacherUpdate,
)

__all__ = [
    # Curriculum
    "CurriculumStrandSchema",
    "CurriculumNodeSchema",
    # Diagnostics
    "DiagnosticSessionCreate",
    "DiagnosticSessionSchema",
    "DiagnosticAnswerSubmit",
    "DiagnosticAnswerResponse",
    "GapProfileSchema",
    # Users
    "ParentCreate",
    "ParentUpdate",
    "ParentSchema",
    "TeacherCreate",
    "TeacherUpdate",
    "TeacherSchema",
]
