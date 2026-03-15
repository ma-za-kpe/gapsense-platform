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
    "ghana": "ghana",
    "GH": "ghana",
    "uganda": "uganda",
    "UG": "uganda",
    "kenya": "kenya",
    "KE": "kenya",
    "nigeria": "nigeria",
    "NG": "nigeria",
}


def get_country_from_student(student: Student | None) -> str:
    """Derive country from student's school location.

    Args:
        student: Student model with school relationship loaded

    Returns:
        Country key (e.g., "ghana", "uganda")

    Notes:
        For MVP: Returns "ghana" default
        For multi-country: Will query student.school.district.region.country
    """
    if not student:
        return "ghana"  # MVP default

    # Future multi-country implementation:
    # if student.school and student.school.district:
    #     region = student.school.district.region
    #     if region and region.country:
    #         return _COUNTRY_DEFAULTS.get(region.country, region.country.lower())

    # MVP: Default to Ghana
    return "ghana"


def get_country_from_teacher(teacher: Teacher | None) -> str:
    """Derive country from teacher's school location.

    Args:
        teacher: Teacher model with school relationship loaded

    Returns:
        Country key (e.g., "ghana", "uganda")
    """
    if not teacher:
        return "ghana"  # MVP default

    # Future multi-country implementation:
    # if teacher.school and teacher.school.district:
    #     region = teacher.school.district.region
    #     if region and region.country:
    #         return _COUNTRY_DEFAULTS.get(region.country, region.country.lower())

    # MVP: Default to Ghana
    return "ghana"


def get_country_from_parent(parent: Parent | None, student: Student | None) -> str:
    """Derive country from parent's location or linked student.

    Args:
        parent: Parent model
        student: Optional linked student with school

    Returns:
        Country key (e.g., "ghana", "uganda")
    """
    # Try to get from student's school first
    if student:
        return get_country_from_student(student)

    # Future: Could add parent.country field or derive from phone prefix
    # For now, default to Ghana for MVP
    return "ghana"


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
