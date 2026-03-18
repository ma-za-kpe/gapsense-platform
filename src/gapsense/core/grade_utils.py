"""
Grade Normalization Utilities (Phase 4)

Converts display-format grades (e.g., "JHS1", "Primary 6") to canonical curriculum codes
(e.g., "B7", "B6") for precise RAG retrieval across Ghana, Uganda, Kenya, Nigeria.

Based on docs/improvements/phase4_spec.md
"""

from __future__ import annotations

# ------------------------------------------------------------------
# Grade Maps: Display Format → Canonical Curriculum Code
# ------------------------------------------------------------------

GRADE_MAPS: dict[str, dict[str, str]] = {
    "ghana": {
        # Basic 1-6 (Primary)
        "B1": "B1",
        "Primary 1": "B1",
        "P1": "B1",
        "Grade 1": "B1",
        "Class 1": "B1",
        "B2": "B2",
        "Primary 2": "B2",
        "P2": "B2",
        "Grade 2": "B2",
        "Class 2": "B2",
        "B3": "B3",
        "Primary 3": "B3",
        "P3": "B3",
        "Grade 3": "B3",
        "Class 3": "B3",
        "B4": "B4",
        "Primary 4": "B4",
        "P4": "B4",
        "Grade 4": "B4",
        "Class 4": "B4",
        "B5": "B5",
        "Primary 5": "B5",
        "P5": "B5",
        "Grade 5": "B5",
        "Class 5": "B5",
        "B6": "B6",
        "Primary 6": "B6",
        "P6": "B6",
        "Grade 6": "B6",
        "Class 6": "B6",
        # Basic 7-9 (Junior High School / JHS / JSS)
        "B7": "B7",
        "JHS1": "B7",
        "JHS 1": "B7",
        "JSS1": "B7",
        "JSS 1": "B7",
        "Junior High 1": "B7",
        "Grade 7": "B7",
        "Form 1": "B7",
        "B8": "B8",
        "JHS2": "B8",
        "JHS 2": "B8",
        "JSS2": "B8",
        "JSS 2": "B8",
        "Junior High 2": "B8",
        "Grade 8": "B8",
        "Form 2": "B8",
        "B9": "B9",
        "JHS3": "B9",
        "JHS 3": "B9",
        "JSS3": "B9",
        "JSS 3": "B9",
        "Junior High 3": "B9",
        "Grade 9": "B9",
        "Form 3": "B9",
    },
    "uganda": {
        # Primary 1-7
        "P1": "P1",
        "Primary 1": "P1",
        "Grade 1": "P1",
        "Class 1": "P1",
        "P2": "P2",
        "Primary 2": "P2",
        "Grade 2": "P2",
        "Class 2": "P2",
        "P3": "P3",
        "Primary 3": "P3",
        "Grade 3": "P3",
        "Class 3": "P3",
        "P4": "P4",
        "Primary 4": "P4",
        "Grade 4": "P4",
        "Class 4": "P4",
        "P5": "P5",
        "Primary 5": "P5",
        "Grade 5": "P5",
        "Class 5": "P5",
        "P6": "P6",
        "Primary 6": "P6",
        "Grade 6": "P6",
        "Class 6": "P6",
        "P7": "P7",
        "Primary 7": "P7",
        "Grade 7": "P7",
        "Class 7": "P7",
        # Secondary 1-4 (O-Level)
        "S1": "S1",
        "Senior 1": "S1",
        "Grade 8": "S1",
        "Form 1": "S1",
        "S2": "S2",
        "Senior 2": "S2",
        "Grade 9": "S2",
        "Form 2": "S2",
        "S3": "S3",
        "Senior 3": "S3",
        "Grade 10": "S3",
        "Form 3": "S3",
        "S4": "S4",
        "Senior 4": "S4",
        "Grade 11": "S4",
        "Form 4": "S4",
    },
    "kenya": {
        # Grade 1-9 (8-4-4 system)
        "Grade 1": "G1",
        "G1": "G1",
        "Standard 1": "G1",
        "Class 1": "G1",
        "Grade 2": "G2",
        "G2": "G2",
        "Standard 2": "G2",
        "Class 2": "G2",
        "Grade 3": "G3",
        "G3": "G3",
        "Standard 3": "G3",
        "Class 3": "G3",
        "Grade 4": "G4",
        "G4": "G4",
        "Standard 4": "G4",
        "Class 4": "G4",
        "Grade 5": "G5",
        "G5": "G5",
        "Standard 5": "G5",
        "Class 5": "G5",
        "Grade 6": "G6",
        "G6": "G6",
        "Standard 6": "G6",
        "Class 6": "G6",
        "Grade 7": "G7",
        "G7": "G7",
        "Standard 7": "G7",
        "Class 7": "G7",
        "Grade 8": "G8",
        "G8": "G8",
        "Standard 8": "G8",
        "Class 8": "G8",
        "Grade 9": "G9",
        "G9": "G9",
        "Form 1": "G9",
    },
    "nigeria": {
        # Primary 1-6
        "Primary 1": "P1",
        "P1": "P1",
        "Grade 1": "P1",
        "Class 1": "P1",
        "Primary 2": "P2",
        "P2": "P2",
        "Grade 2": "P2",
        "Class 2": "P2",
        "Primary 3": "P3",
        "P3": "P3",
        "Grade 3": "P3",
        "Class 3": "P3",
        "Primary 4": "P4",
        "P4": "P4",
        "Grade 4": "P4",
        "Class 4": "P4",
        "Primary 5": "P5",
        "P5": "P5",
        "Grade 5": "P5",
        "Class 5": "P5",
        "Primary 6": "P6",
        "P6": "P6",
        "Grade 6": "P6",
        "Class 6": "P6",
        # Junior Secondary School (JSS) 1-3
        "JSS1": "JSS1",
        "JSS 1": "JSS1",
        "Junior Secondary 1": "JSS1",
        "Grade 7": "JSS1",
        "JS1": "JSS1",
        "JSS2": "JSS2",
        "JSS 2": "JSS2",
        "Junior Secondary 2": "JSS2",
        "Grade 8": "JSS2",
        "JS2": "JSS2",
        "JSS3": "JSS3",
        "JSS 3": "JSS3",
        "Junior Secondary 3": "JSS3",
        "Grade 9": "JSS3",
        "JS3": "JSS3",
    },
}


# ------------------------------------------------------------------
# Grade Sequences (for adjacent_grades)
# ------------------------------------------------------------------

GRADE_SEQUENCES: dict[str, list[str]] = {
    "ghana": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"],
    "uganda": ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "S1", "S2", "S3", "S4"],
    "kenya": ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"],
    "nigeria": ["P1", "P2", "P3", "P4", "P5", "P6", "JSS1", "JSS2", "JSS3"],
}


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------


def normalise_grade(grade: str, country: str) -> str | None:
    """Normalise a grade to canonical curriculum format.

    Args:
        grade: Display-format grade (e.g., "JHS1", "Primary 6", "B7")
        country: Country code (e.g., "ghana", "uganda", "GH", "UG")

    Returns:
        Canonical grade code (e.g., "B7", "P6") or None if not found

    Examples:
        >>> normalise_grade("JHS1", "ghana")
        "B7"
        >>> normalise_grade("jhs 1", "GH")
        "B7"
        >>> normalise_grade("Primary 6", "uganda")
        "P6"
        >>> normalise_grade("Unknown", "ghana")
        None
    """
    # Normalize country code to lowercase full name
    country_key = country.lower()
    if country_key == "gh":
        country_key = "ghana"
    elif country_key == "ug":
        country_key = "uganda"
    elif country_key == "ke":
        country_key = "kenya"
    elif country_key == "ng":
        country_key = "nigeria"

    country_map = GRADE_MAPS.get(country_key, {})
    if not country_map:
        return None

    # Case-insensitive lookup with stripped whitespace
    grade_normalized = grade.strip()

    # Try exact match first (preserves canonical codes like "B7")
    if grade_normalized in country_map:
        return country_map[grade_normalized]

    # Try case-insensitive match
    for display, canonical in country_map.items():
        if display.lower() == grade_normalized.lower():
            return canonical

    return None


def adjacent_grades(grade: str, country: str, radius: int = 1) -> list[str]:
    """Return grades within radius steps of target grade.

    Used to widen curriculum queries to avoid over-filtering when retrieving
    prerequisite/related content.

    Args:
        grade: Canonical grade code (e.g., "B7", "P6")
        country: Country code (e.g., "ghana", "uganda", "GH", "UG")
        radius: Number of grades before/after to include (default: 1)

    Returns:
        List of canonical grade codes within radius, including target grade

    Examples:
        >>> adjacent_grades("B7", "ghana", radius=1)
        ["B6", "B7", "B8"]
        >>> adjacent_grades("P6", "uganda", radius=2)
        ["P4", "P5", "P6", "P7", "S1"]
    """
    # Normalize country code
    country_key = country.lower()
    if country_key == "gh":
        country_key = "ghana"
    elif country_key == "ug":
        country_key = "uganda"
    elif country_key == "ke":
        country_key = "kenya"
    elif country_key == "ng":
        country_key = "nigeria"

    sequence = GRADE_SEQUENCES.get(country_key, [])
    if not sequence or grade not in sequence:
        # Fallback: return only the target grade if sequence not found
        return [grade]

    idx = sequence.index(grade)
    start = max(0, idx - radius)
    end = min(len(sequence), idx + radius + 1)

    return sequence[start:end]
