"""
Input validation functions for GapSense.

All validation functions follow the pattern:
1. Accept raw user input (string, int, etc.)
2. Normalize/clean the input
3. Validate against business rules
4. Return cleaned value or raise ValidationError

This module addresses Phase A of the TDD implementation plan.
"""

import re


class ValidationError(Exception):
    """Raised when user input fails validation."""

    pass


# ============================================================================
# Phone Number Validation
# ============================================================================


def validate_phone_number(phone: str | None) -> str:
    """
    Validate and normalize Ghana phone numbers.

    Accepts:
    - +233XXXXXXXXX (international format)
    - 0XXXXXXXXX (local format)

    Normalizes to: +233XXXXXXXXX

    Args:
        phone: Raw phone number input

    Returns:
        Normalized phone number in +233XXXXXXXXX format

    Raises:
        ValidationError: If phone number is invalid
    """
    if phone is None or phone == "":
        raise ValidationError("Phone number cannot be empty")

    # Check for obviously invalid formats (contains letters)
    if re.search(r"[a-zA-Z]", phone):
        raise ValidationError("Invalid phone number format")

    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)

    # Handle local format (0XXXXXXXXX → +233XXXXXXXXX)
    if cleaned.startswith("0"):
        cleaned = "+233" + cleaned[1:]

    # Must start with +233
    if not cleaned.startswith("+233"):
        raise ValidationError("Only Ghana phone numbers (+233) are supported")

    # Must be exactly 13 characters (+233 + 9 digits)
    if len(cleaned) != 13:
        raise ValidationError("Invalid phone number length (expected 9 digits after +233)")

    # Must be all digits after +233
    if not cleaned[4:].isdigit():
        raise ValidationError("Invalid phone number format (must contain only digits)")

    return cleaned


# ============================================================================
# School Name Validation
# ============================================================================


def validate_school_name(name: str | None) -> str:
    """
    Validate and normalize school names.

    Args:
        name: Raw school name input

    Returns:
        Normalized school name

    Raises:
        ValidationError: If school name is invalid
    """
    if name is None or name == "":
        raise ValidationError("School name cannot be empty")

    # Strip leading/trailing whitespace
    cleaned = name.strip()

    if cleaned == "":
        raise ValidationError("School name cannot be empty")

    # Normalize multiple spaces to single space
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Must contain at least one letter
    if not re.search(r"[a-zA-Z]", cleaned):
        raise ValidationError("School name must contain letters")

    # Check length
    if len(cleaned) < 3:
        raise ValidationError("School name must be at least 3 characters")

    if len(cleaned) > 200:
        raise ValidationError("School name cannot exceed 200 characters")

    return cleaned


# ============================================================================
# Class Name Validation
# ============================================================================


def validate_class_name(class_name: str | None) -> str:
    """
    Validate and normalize class names.

    Accepts formats:
    - "Basic 7" / "basic 7" / "BASIC 7"
    - "B7" / "b7"
    - "JHS 1" / "jhs 1"

    Normalizes to title case with consistent spacing.

    Args:
        class_name: Raw class name input

    Returns:
        Normalized class name

    Raises:
        ValidationError: If class name is invalid
    """
    if class_name is None or class_name == "":
        raise ValidationError("Class name cannot be empty")

    # Strip and normalize whitespace
    cleaned = re.sub(r"\s+", " ", class_name.strip())

    # Normalize to title case
    cleaned = cleaned.title()

    # Fix JHS to be uppercase (title case makes it "Jhs")
    cleaned = cleaned.replace("Jhs", "JHS")

    # Valid grade levels for JHS: 1, 2, 3 (or Basic 7, 8, 9)
    # Extract grade number
    match = re.search(r"(\d+)", cleaned)
    if not match:
        raise ValidationError("Invalid grade level (must include a number)")

    grade_num = int(match.group(1))

    # Check for valid grade levels
    # JHS 1-3 or Basic 7-9
    if "JHS" in cleaned:
        if grade_num not in [1, 2, 3]:
            raise ValidationError("Invalid grade level (JHS must be 1-3)")
    elif "Basic" in cleaned:
        if grade_num not in [7, 8, 9]:
            raise ValidationError("Invalid grade level (Basic must be 7-9)")
    elif cleaned.startswith("B"):
        # B7, B8, B9 format
        if grade_num not in [7, 8, 9]:
            raise ValidationError("Invalid grade level (B must be 7-9)")
    else:
        raise ValidationError("Invalid class name format (expected 'Basic 7', 'B7', or 'JHS 1')")

    return cleaned


# ============================================================================
# Student Count Validation
# ============================================================================


def validate_student_count(count: int | str | None) -> int:
    """
    Validate student count.

    Args:
        count: Raw student count input (int or string)

    Returns:
        Validated student count as integer

    Raises:
        ValidationError: If student count is invalid
    """
    if count is None:
        raise ValidationError("Student count cannot be empty")

    # Convert string to int if needed
    if isinstance(count, str):
        count = count.strip()
        if not count.isdigit():
            raise ValidationError("Student count must be a number")
        count = int(count)

    # Validate range
    if count <= 0:
        raise ValidationError("Student count must be positive")

    if count > 500:
        raise ValidationError(
            "Student count cannot exceed 500 (if this is a real class, please contact support)"
        )

    return count


# ============================================================================
# Student Name Validation
# ============================================================================


def validate_student_name(name: str | None) -> str:
    """
    Validate and normalize student names.

    Handles:
    - Single names: "Kwame"
    - Full names: "Kwame Mensah"
    - Numbered lists: "1. Kwame" → "Kwame"

    Normalizes to title case.

    Args:
        name: Raw student name input

    Returns:
        Normalized student name

    Raises:
        ValidationError: If student name is invalid
    """
    if name is None or name == "":
        raise ValidationError("Student name cannot be empty")

    # Strip leading/trailing whitespace
    cleaned = name.strip()

    if cleaned == "":
        raise ValidationError("Student name cannot be empty")

    # Remove numbering prefix (e.g., "1. Kwame" → "Kwame")
    cleaned = re.sub(r"^\d+\.\s*", "", cleaned)

    # Normalize multiple spaces to single space
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Normalize to title case
    cleaned = cleaned.title()

    # Must contain at least one letter
    if not re.search(r"[a-zA-Z]", cleaned):
        raise ValidationError("Student name must contain letters")

    # Check length
    if len(cleaned) < 2:
        raise ValidationError("Student name must be at least 2 characters")

    if len(cleaned) > 100:
        raise ValidationError("Student name cannot exceed 100 characters")

    return cleaned
