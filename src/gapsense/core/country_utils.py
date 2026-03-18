"""
Country Context Resolution Utilities

Derives country from student/teacher/parent context for multi-country support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gapsense.core.models import Parent, Student, Teacher

# Country code mapping
# In future: read from database regions/districts table with country field
_COUNTRY_DEFAULTS = {
    "ghana": "GH",
    "GH": "GH",
    "uganda": "UG",
    "UG": "UG",
    "kenya": "KE",
    "KE": "KE",
    "nigeria": "NG",
    "NG": "NG",
}


def get_country_from_student(student: Student | None) -> str:
    """Derive country from student's school location.

    Args:
        student: Student model with school relationship loaded

    Returns:
        Country ISO code (e.g., "GH", "UG")

    Notes:
        For MVP: Returns "GH" default
        For multi-country: Will query student.school.district.region.country
    """
    if not student:
        return "GH"  # MVP default

    # Future multi-country implementation:
    # if student.school and student.school.district:
    #     region = student.school.district.region
    #     if region and region.country:
    #         return _COUNTRY_DEFAULTS.get(region.country, region.country.lower())

    # MVP: Default to Ghana
    return "GH"


def get_country_from_teacher(teacher: Teacher | None) -> str:
    """Derive country from teacher's school location.

    Args:
        teacher: Teacher model with school relationship loaded

    Returns:
        Country ISO code (e.g., "GH", "UG")
    """
    if not teacher:
        return "GH"  # MVP default

    # Future multi-country implementation:
    # if teacher.school and teacher.school.district:
    #     region = teacher.school.district.region
    #     if region and region.country:
    #         return _COUNTRY_DEFAULTS.get(region.country, region.country.lower())

    # MVP: Default to Ghana
    return "GH"


def get_country_from_parent(parent: Parent | None, student: Student | None) -> str:
    """Derive country from parent's location or linked student.

    Args:
        parent: Parent model
        student: Optional linked student with school

    Returns:
        Country ISO code (e.g., "GH", "UG")
    """
    # Try to get from student's school first
    if student:
        return get_country_from_student(student)

    # Future: Could add parent.country field or derive from phone prefix
    # For now, default to Ghana for MVP
    return "GH"


def get_subject_from_teacher(teacher: Teacher | None, default: str = "mathematics") -> str:
    """Derive primary subject from teacher's subjects.

    Args:
        teacher: Teacher model
        default: Default subject if none found

    Returns:
        Subject name (e.g., "mathematics", "english")
    """
    if not teacher or not teacher.subjects:
        return default

    # Return first subject from teacher's subjects list
    subjects = teacher.subjects
    if isinstance(subjects, list) and subjects:
        return subjects[0].lower()

    return default
