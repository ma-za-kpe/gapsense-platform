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
]
