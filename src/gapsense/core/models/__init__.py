"""
GapSense SQLAlchemy Models

All models follow the data model specification in docs/specs/gapsense_data_model.sql
"""

from .base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from .curriculum import (
    CascadePath,
    CurriculumIndicator,
    CurriculumMisconception,
    CurriculumNode,
    CurriculumPrerequisite,
    CurriculumStrand,
    CurriculumSubStrand,
    IndicatorErrorPattern,
)
from .diagnostics import DiagnosticQuestion, DiagnosticSession, GapProfile
from .engagement import ParentActivity, ParentInteraction
from .prompts import PromptCategory, PromptTestCase, PromptVersion
from .schools import District, GESSchool, Region, School, SchoolInvitation
from .students import Student
from .users import Parent, Teacher

__all__ = [
    # Base
    "Base",
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    # Curriculum
    "CurriculumStrand",
    "CurriculumSubStrand",
    "CurriculumNode",
    "CurriculumPrerequisite",
    "CurriculumIndicator",
    "IndicatorErrorPattern",
    "CurriculumMisconception",
    "CascadePath",
    # Schools
    "GESSchool",
    "Region",
    "District",
    "School",
    "SchoolInvitation",
    # Users
    "Teacher",
    "Parent",
    # Students
    "Student",
    # Diagnostics
    "DiagnosticSession",
    "DiagnosticQuestion",
    "GapProfile",
    # Engagement
    "ParentInteraction",
    "ParentActivity",
    # Prompts
    "PromptCategory",
    "PromptVersion",
    "PromptTestCase",
]
